"""Local website routes around the existing Gradio practice application."""
from contextlib import asynccontextmanager
import os
import socket
import threading
import time
import urllib.request
import webbrowser

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse, PlainTextResponse, JSONResponse
from starlette.exceptions import HTTPException
from starlette.middleware.gzip import GZipMiddleware
from starlette.staticfiles import StaticFiles
import gradio as gr
import uvicorn

from analysis_service import SERVICE
from site_pages import (ASSETS, ROOT, PRACTICE_DESCRIPTION, help_page, meta_html,
                        not_found_page, privacy_page, terms_page, stylesheet_html)


def create_site(demo, theme, css):
    @asynccontextmanager
    async def lifespan(app):
        yield
        SERVICE.close()

    site = FastAPI(title='Accent Coach', docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    site.add_middleware(GZipMiddleware, minimum_size=1000)

    @site.get('/help', response_class=HTMLResponse)
    def help_route():
        return help_page()

    @site.get('/privacy', response_class=HTMLResponse)
    def privacy_route():
        return privacy_page()

    @site.get('/terms', response_class=HTMLResponse)
    def terms_route():
        return terms_page()

    @site.get('/favicon.ico', include_in_schema=False)
    def favicon():
        return FileResponse(ASSETS / 'favicon.ico', media_type='image/x-icon')

    @site.get('/robots.txt', response_class=PlainTextResponse)
    def robots():
        return 'User-agent: *\nDisallow: /\n'

    @site.get('/site-health')
    def health():
        return {'service': 'accent-coach', 'status': 'ready', 'public_launch': False}

    site.mount('/site-assets', StaticFiles(directory=ASSETS), name='site-assets')
    site = gr.mount_gradio_app(site, demo.queue(default_concurrency_limit=1, max_size=8, api_open=False),
        path='/', server_name='127.0.0.1', server_port=int(os.environ.get('GRADIO_SERVER_PORT', '7861')),
        footer_links=[], favicon_path=str(ASSETS / 'favicon.ico'), max_file_size='10mb',
        allowed_paths=[str(ROOT / 'runs')], theme=theme,
        js=(ASSETS / 'practice.js').read_text(encoding='utf-8'),
        # A shared stylesheet avoids Gradio rewriting root/media selectors inside
        # each HTML component. The same rules also style standalone policy pages.
        head=meta_html(PRACTICE_DESCRIPTION) + stylesheet_html(), show_error=False,
        app_kwargs={'docs_url': None, 'redoc_url': None, 'openapi_url': None})

    async def not_found_handler(request: Request, exc: HTTPException):
        if exc.status_code == 404 and 'text/html' in request.headers.get('accept', '') and not request.url.path.startswith('/gradio_api/'):
            return HTMLResponse(not_found_page(), status_code=404)
        return JSONResponse({'detail': exc.detail}, status_code=exc.status_code, headers=exc.headers)

    site.add_exception_handler(HTTPException, not_found_handler)
    # The root mount owns unmatched paths, so it needs the HTML 404 handler too.
    site.routes[-1].app.add_exception_handler(HTTPException, not_found_handler)
    return site


def serve(demo, theme, css):
    port = int(os.environ.get('GRADIO_SERVER_PORT', '7861'))
    with socket.socket() as probe:
        if probe.connect_ex(('127.0.0.1', port)) == 0:
            raise SystemExit(f'Port {port} is already in use. Open http://127.0.0.1:{port}/ if Accent Coach is already running, or set GRADIO_SERVER_PORT to a free port.')
    site = create_site(demo, theme, css)
    address = f'http://127.0.0.1:{port}/'
    def open_when_ready():
        for _ in range(30):
            try:
                with urllib.request.urlopen(address + 'site-health', timeout=1) as response:
                    if response.status == 200:
                        webbrowser.open(address)
                        return
            except OSError:
                time.sleep(1)
    if os.environ.get('ACCENT_COACH_OPEN_BROWSER', '1') == '1':
        threading.Thread(target=open_when_ready, daemon=True).start()
    print(f'Accent Coach: {address}', flush=True)
    uvicorn.run(site, host='127.0.0.1', port=port, log_level='info')
