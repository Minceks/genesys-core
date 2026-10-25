"""Standalone host for the built Genesys interface, independent of site builders."""
from pathlib import Path
import os

from flask import Flask, abort, send_from_directory


def create_app(dist_dir=None):
    root = Path(dist_dir or Path(__file__).parent / 'dist').resolve()
    app = Flask(__name__, static_folder=None)

    @app.get('/health')
    def health():
        ready = (root / 'index.html').is_file()
        return {'status': 'ok' if ready else 'missing_frontend_build',
                'deploymentId': os.getenv('RAILWAY_DEPLOYMENT_ID', '')}, 200 if ready else 503

    @app.get('/')
    @app.get('/<path:filename>')
    def frontend(filename=''):
        parts = filename.split('/')
        if any(part.startswith('.') or '\\' in part for part in parts):
            abort(404)
        target = (root / filename).resolve()
        if not target.is_relative_to(root):
            abort(404)
        if target.is_file():
            response = send_from_directory(root, filename)
            response.headers['Cache-Control'] = (
                'public, max-age=31536000, immutable'
                if filename.startswith('assets/') else 'no-cache'
            )
        else:
            # Missing assets must return 404, rather than HTML with a script MIME error.
            if filename.startswith('assets/') or '.' in parts[-1]:
                abort(404)
            if not (root / 'index.html').is_file():
                abort(503)
            response = send_from_directory(root, 'index.html')
            response.headers['Cache-Control'] = 'no-cache'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response

    from deployment_notify import notify_deployment
    notify_deployment()
    return app


app = create_app()
