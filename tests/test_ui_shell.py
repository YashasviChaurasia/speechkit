from pathlib import Path


def test_editorial_shell_has_navigation_and_stable_render_targets():
    html = Path("static/index.html").read_text()
    for target in ("upload-panel", "overview", "speakers", "search-panel", "transcript", "artifact"):
        assert f'id="{target}"' in html
        assert f'href="#{target}"' in html
    for element_id in ("upload", "status", "result", "media", "filename", "facts", "speaker-cards", "query", "mode", "search", "results", "segments", "raw", "export"):
        assert f'id="{element_id}"' in html
