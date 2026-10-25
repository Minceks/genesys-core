from frontend_host import create_app


def test_standalone_frontend_routes_and_assets(tmp_path):
    (tmp_path / 'index.html').write_text('<html>Genesys</html>')
    (tmp_path / 'assets').mkdir()
    (tmp_path / 'assets' / 'app-123.js').write_text('console.log("Genesys")')
    client = create_app(tmp_path).test_client()
    assert client.get('/health').status_code == 200
    for path in ('/', '/build', '/projects/example'):
        result = client.get(path)
        assert result.status_code == 200
        assert b'Genesys' in result.data
        assert result.headers['Cache-Control'] == 'no-cache'
    asset = client.get('/assets/app-123.js')
    assert asset.mimetype in ('text/javascript', 'application/javascript')
    assert 'immutable' in asset.headers['Cache-Control']
    assert asset.headers['X-Content-Type-Options'] == 'nosniff'
    for path in ('/assets/missing.js', '/missing.css', '/.env', '/..%2Fsecret', '/foo%5Csecret'):
        assert client.get(path).status_code == 404


def test_missing_build_is_not_healthy(tmp_path):
    client = create_app(tmp_path).test_client()
    assert client.get('/health').status_code == 503
    assert client.get('/build').status_code == 503
