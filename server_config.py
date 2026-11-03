"""Portable web settings; local defaults stay unchanged."""
from dataclasses import dataclass
import ipaddress
import os
from pathlib import Path
import re
from urllib.parse import urlsplit

LOCAL_HOSTS=('localhost','127.0.0.1','[::1]')


@dataclass(frozen=True)
class ServerConfig:
    mode:str
    bind_host:str
    port:int
    allowed_hosts:tuple
    data_dir:Path
    public_url:str
    forwarded_allow_ips:str

    @property
    def hosted(self):return self.mode=='hosted'


def load_server_config(environ=None):
    env=os.environ if environ is None else environ
    mode=env.get('ACCENT_COACH_MODE','local').strip().lower()
    if mode not in ('local','hosted'):raise ValueError('ACCENT_COACH_MODE must be local or hosted.')
    hosted=mode=='hosted'
    raw_data=env.get('ACCENT_COACH_DATA_DIR','')
    data=Path(raw_data).expanduser() if raw_data else Path(__file__).resolve().parent/'private_data'
    hosts=tuple(h.strip().lower() for h in env.get('ACCENT_COACH_ALLOWED_HOSTS',','.join(LOCAL_HOSTS)).split(',') if h.strip())
    if not hosts or any(h!='[::1]' and not re.fullmatch(r'[a-z0-9.-]+',h) for h in hosts):
        raise ValueError('ACCENT_COACH_ALLOWED_HOSTS must list exact hostnames without schemes, ports or wildcards.')
    public_url=env.get('ACCENT_COACH_PUBLIC_URL','').rstrip('/')
    if hosted:
        if env.get('ACCENT_COACH_DEMO')=='1':raise ValueError('The sample demo workspace cannot run in hosted mode.')
        if not raw_data or not data.is_absolute():raise ValueError('Hosted mode requires an absolute ACCENT_COACH_DATA_DIR on persistent storage.')
        if not env.get('ACCENT_COACH_ALLOWED_HOSTS'):raise ValueError('Hosted mode requires ACCENT_COACH_ALLOWED_HOSTS for your domain.')
        url=urlsplit(public_url)
        if (url.scheme!='https' or not url.hostname or url.hostname.lower() not in hosts or url.username or url.password
                or url.path or url.query or url.fragment):
            raise ValueError('ACCENT_COACH_PUBLIC_URL must be an HTTPS origin whose hostname is explicitly allowed; serve the app at the domain root.')
    forwarded=env.get('FORWARDED_ALLOW_IPS','127.0.0.1').strip()
    if hosted:
        if not forwarded:raise ValueError('Set FORWARDED_ALLOW_IPS to the trusted reverse proxy address.')
        try:
            for address in forwarded.split(','):
                if ipaddress.ip_network(address.strip(),strict=False).prefixlen==0:raise ValueError()
        except ValueError:
            raise ValueError('FORWARDED_ALLOW_IPS must list specific proxy IPs or bounded networks, not *.') from None
    try:
        port=int(env.get('PORT',env.get('GRADIO_SERVER_PORT','7861')) if hosted else env.get('GRADIO_SERVER_PORT',env.get('PORT','7861')))
        if not 1<=port<=65535:raise ValueError()
    except ValueError:raise ValueError('Set PORT or GRADIO_SERVER_PORT to a valid TCP port.') from None
    return ServerConfig(mode,env.get('ACCENT_COACH_HOST','127.0.0.1'),port,hosts,data.resolve(),public_url,forwarded)
