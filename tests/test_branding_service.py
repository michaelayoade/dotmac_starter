from __future__ import annotations

from unittest.mock import patch

import app.services.branding as branding_service
from app.services.branding import (
    generate_css,
    get_branding,
    save_branding,
    validate_logo_url,
)


def test_get_branding_returns_defaults(db_session) -> None:
    branding = get_branding(db_session)
    assert branding["display_name"]
    assert branding["primary_color"].startswith("#")
    assert branding["accent_color"].startswith("#")


def test_get_branding_validates_default_logo_url(db_session) -> None:
    with patch.object(
        branding_service.settings,
        "brand_logo_url",
        "javascript:alert(1)",
        create=True,
    ):
        branding = get_branding(db_session)
    assert branding["logo_url"] is None


def test_save_branding_persists_values(db_session) -> None:
    save_branding(
        db_session,
        {
            "display_name": "Acme Starter",
            "primary_color": "#112233",
            "accent_color": "#445566",
            "font_family_display": "Outfit",
            "font_family_body": "Inter",
        },
    )
    branding = get_branding(db_session)
    assert branding["display_name"] == "Acme Starter"
    assert branding["primary_color"] == "#112233"
    assert branding["accent_color"] == "#445566"


def test_generate_css_contains_brand_variables() -> None:
    css = generate_css(
        {
            "primary_color": "#123456",
            "accent_color": "#ABCDEF",
            "font_family_display": "Outfit",
            "font_family_body": "Plus Jakarta Sans",
            "custom_css": ".demo { color: red; }",
        }
    )
    assert "--brand-primary: #123456;" in css
    assert "--brand-accent: #ABCDEF;" in css
    assert ".demo { color: red; }" in css


def test_validate_logo_url_allows_https_and_root_relative_paths() -> None:
    assert validate_logo_url("https://example.com/logo.png") == (
        "https://example.com/logo.png"
    )
    assert validate_logo_url("/static/branding/logo.png") == (
        "/static/branding/logo.png"
    )


def test_validate_logo_url_rejects_disallowed_schemes() -> None:
    assert validate_logo_url("javascript:alert(1)") is None
    assert validate_logo_url("data:image/png;base64,aaa") is None
    assert validate_logo_url("http://example.com/logo.png") is None
    assert validate_logo_url("ftp://example.com/logo.png") is None


def test_save_branding_validates_logo_urls_before_persist(db_session) -> None:
    save_branding(
        db_session,
        {
            "logo_url": "javascript:alert(1)",
            "logo_dark_url": "data:image/png;base64,aaa",
        },
    )
    branding = get_branding(db_session)
    assert branding["logo_url"] is None
    assert branding["logo_dark_url"] is None
