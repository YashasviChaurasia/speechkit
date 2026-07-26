from pathlib import Path


def test_editorial_shell_has_navigation_and_stable_render_targets():
    html = Path("static/index.html").read_text()
    for target in ("upload-panel", "overview", "speakers", "search-panel", "transcript", "artifact"):
        assert f'id="{target}"' in html
        assert f'href="#{target}"' in html
    for element_id in ("upload", "status", "result", "media", "filename", "facts", "speaker-cards", "query", "mode", "search", "results", "segments", "raw", "export"):
        assert f'id="{element_id}"' in html


def test_hero_positions_speechlens_as_intelligence_layer():
    html = Path("static/index.html").read_text()

    assert "Speech Intelligence Layer" in html
    assert 'id="intelligence-benefits"' in html
    assert "Agentic Video Editor" in html


def test_editorial_styles_define_workspace_accessibility_and_mobile_layout():
    css = Path("static/styles.css").read_text()
    for selector in (".rail", ".workspace", ".section-marker", ":focus-visible", "prefers-reduced-motion", "@media(max-width:820px)"):
        assert selector in css


def test_intelligence_hero_uses_a_wider_balanced_desktop_measure():
    css = Path("static/styles.css").read_text()

    assert ".intro { max-width: 1120px" in css
    assert "font-size: clamp(2.8rem, 4.4vw, 4.9rem)" in css


def test_ui_script_uses_safe_error_messages_and_rail_navigation_state():
    script = Path("static/app.js").read_text()
    assert "data.error?.message" in script
    assert "rail-link" in script
    assert "IntersectionObserver" in script


def test_ui_exposes_provider_configuration_without_retaining_keys():
    html = Path("static/index.html").read_text()
    script = Path("static/app.js").read_text()

    assert 'id="provider-config"' in html
    assert 'id="api-key"' in html
    assert 'type="password"' in html
    assert 'id="analyse"' in html
    assert '"/api/provider/config"' in script
    assert 'apiKey.value = ""' in script
