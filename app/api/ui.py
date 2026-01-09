from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from pathlib import Path

router = APIRouter(tags=["ui"])

BASE_DIR = Path(__file__).resolve().parent.parent  # app/api/ui.py 기준
TEMPLATE_DIR = BASE_DIR / "../templates"
STATIC_DIR = BASE_DIR / "../static"


# -----------------------------
# 메인 페이지 (좌측 + iframe)
# -----------------------------
@router.get("/", response_class=HTMLResponse)
def index():
    return Path("templates/index.html").read_text(encoding="utf-8")


# -----------------------------
# iframe 공통 렌더러
# -----------------------------
def render_iframe(title: str, body_html: str) -> HTMLResponse:
    base_path = TEMPLATE_DIR / "iframe_base.html"

    if not base_path.exists():
        return HTMLResponse(
            f"<h1>iframe_base.html not found</h1><pre>{base_path}</pre>",
            status_code=500
        )

    base = base_path.read_text(encoding="utf-8")
    html = base.replace("{{ title }}", title)
    html = html.replace("{{ content | safe }}", body_html)
    return HTMLResponse(html)


# -----------------------------
# iframe 내부 페이지들
# -----------------------------
@router.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    body = (TEMPLATE_DIR / "dashboard.html").read_text(encoding="utf-8")
    return render_iframe("Dashboard", body)


@router.get("/upload", response_class=HTMLResponse)
def upload():
    body = (TEMPLATE_DIR / "upload.html").read_text(encoding="utf-8")
    return render_iframe("Upload", body)


@router.get("/search", response_class=HTMLResponse)
def search():
    body = """
    <h1>🔍 문서 검색</h1>
    <input placeholder="검색어 입력">
    """
    return render_iframe("Search", body)


@router.get("/rag", response_class=HTMLResponse)

def rag():
    body = """
    <h1>🧠 RAG 질의</h1>
    <textarea rows="4" style="width:100%"></textarea>
    """
    return render_iframe("RAG", body)
