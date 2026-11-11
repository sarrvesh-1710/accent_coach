"""Private stdio worker, launched only with the configured isolated interpreter."""
import contextlib
import json
import sys

from .generator import _failure, TARGET_ACCENT
from .runtime import valid_text


def serve(source, sink, factory=None):
    generator = None
    for line in source:
        try:
            request = json.loads(line)
            if not isinstance(request, dict) or not valid_text(request.get('text')):
                result = _failure('UNSUPPORTED_TEXT', 'Use 1–12 words and at most 200 characters.')
            elif request.get('target_accent') != TARGET_ACCENT:
                result = _failure('UNSUPPORTED_ACCENT', 'Only General American examples are available.')
            else:
                with contextlib.redirect_stdout(sys.stderr):
                    if generator is None:
                        if factory is None:
                            from .kokoro_backend import KokoroGenerator
                            factory = KokoroGenerator
                        generator = factory()
                    result = generator.generate_audio(request['text'], request['target_accent'], output_dir=request['output_dir'])
        except Exception:
            generator = None
            result = _failure('MODEL_UNAVAILABLE', 'The optional neural voice could not finish. Please retry.', True)
        sink.write(json.dumps(result, allow_nan=False) + '\n'); sink.flush()


if __name__ == '__main__':
    serve(sys.stdin, sys.stdout)
