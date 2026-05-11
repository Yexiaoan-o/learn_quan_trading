from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from services import progress_service, content_service
from pydantic import BaseModel

router = APIRouter()


class NoteCreate(BaseModel):
    chapter_id: str
    section_id: str
    content: str


@router.get("/notes", response_class=HTMLResponse)
async def notes_page(request: Request):
    notes = progress_service.get_notes()
    phases = content_service.get_all_phases()
    return request.app.state.templates.TemplateResponse("notes.html", {
        "request": request,
        "phases": phases,
        "notes": notes
    })


@router.post("/api/notes")
async def create_note(data: NoteCreate):
    progress_service.save_note(data.chapter_id, data.section_id, data.content)
    return {"status": "ok"}


@router.delete("/api/notes/{note_id}")
async def delete_note_route(note_id: int):
    progress_service.delete_note(note_id)
    return {"status": "ok"}


@router.get("/api/notes")
async def get_notes(chapter_id: str | None = None):
    return progress_service.get_notes(chapter_id)


@router.post("/api/bookmark/{chapter_id}/{section_id}")
async def toggle_bookmark_route(chapter_id: str, section_id: str):
    action = progress_service.toggle_bookmark(chapter_id, section_id)
    return {"action": action}


@router.get("/api/bookmarks")
async def get_bookmarks_route():
    return progress_service.get_bookmarks()
