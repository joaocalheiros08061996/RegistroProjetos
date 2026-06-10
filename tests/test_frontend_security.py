from pathlib import Path
import re


FRONTEND_DIR = Path("frontend")
HTML_FILES = tuple(sorted(FRONTEND_DIR.glob("*.html")))
INLINE_SCRIPT_RE = re.compile(r"<script(?![^>]*\bsrc=)[^>]*>", re.IGNORECASE)
INLINE_HANDLER_RE = re.compile(r"\son[a-z]+\s*=", re.IGNORECASE)
SCRIPT_SRC_RE = re.compile(r'<script[^>]+\bsrc="([^"]+)"', re.IGNORECASE)


def test_frontend_has_no_inline_scripts_or_event_handlers():
    for path in HTML_FILES:
        html = path.read_text(encoding="utf-8")
        assert not INLINE_SCRIPT_RE.search(html), f"Script inline encontrado em {path}"
        assert not INLINE_HANDLER_RE.search(html), f"Handler HTML inline encontrado em {path}"


def test_frontend_external_scripts_exist_or_use_allowed_plotly_cdn():
    external_sources: set[str] = set()

    for path in HTML_FILES:
        html = path.read_text(encoding="utf-8")
        for raw_source in SCRIPT_SRC_RE.findall(html):
            source = raw_source.split("?", 1)[0]
            if source.startswith("https://"):
                external_sources.add(source)
                continue
            assert (FRONTEND_DIR / source).is_file(), f"Script ausente: {source}"

    assert external_sources == {"https://cdn.plot.ly/plotly-2.35.2.min.js"}


def test_register_requires_privacy_notice_acknowledgement():
    html = (FRONTEND_DIR / "register.html").read_text(encoding="utf-8")

    assert 'id="privacy-notice-acknowledged"' in html
    assert 'type="checkbox"' in html
    assert "required" in html
    assert 'href="privacy.html"' in html


def test_project_task_form_has_description_field():
    html = (FRONTEND_DIR / "project.html").read_text(encoding="utf-8")

    assert 'id="task_description"' in html
    assert 'maxlength="150"' in html
    assert 'src="pages/project.js?v=20260609"' in html


def test_project_page_explains_large_task_lists_are_filtered():
    html = (FRONTEND_DIR / "project.html").read_text(encoding="utf-8")

    assert "Projetos com mais de 10 tarefas exibem nesta lista somente tarefas não concluídas." in html


def test_projects_form_has_project_description_field():
    html = (FRONTEND_DIR / "projects.html").read_text(encoding="utf-8")

    assert 'id="description"' in html
    assert 'maxlength="150"' in html
    assert 'src="pages/projects.js?v=20260609"' in html


def test_privacy_notice_uses_external_script():
    html = (FRONTEND_DIR / "privacy.html").read_text(encoding="utf-8")

    assert 'src="pages/privacy.js?v=20260603"' in html
    assert not INLINE_SCRIPT_RE.search(html)
