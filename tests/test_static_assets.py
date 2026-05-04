from app.templates import _static_asset_url


def test_static_asset_url_adds_content_version() -> None:
    url = _static_asset_url("/static/css/styles.css")
    assert url.startswith("/static/css/styles.css?v=")
    assert len(url.rsplit("=", 1)[1]) == 12


def test_static_asset_url_preserves_existing_query_separator() -> None:
    url = _static_asset_url("/static/css/styles.css?theme=default")
    assert "&v=" in url
