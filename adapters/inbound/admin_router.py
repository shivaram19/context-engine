"""
Admin and testing router — UI endpoints for the Context Engine.

GET /chat - test chat interface (same QueryService as WhatsApp)
"""

from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["admin"])

# Template directory
TEMPLATES_DIR = Path("adapters/inbound/templates")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/chat")
async def chat_ui(request: Request):
    """
    Test chat interface — no WhatsApp needed.
    Same QueryService as the WhatsApp handler.
    Access at: http://localhost:8000/chat
    """
    template = templates.get_template("chat.html")
    return HTMLResponse(content=template.render(request=request))
