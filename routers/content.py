from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from services import content_service
from services.progress_service import get_chapter_progress, get_bookmarks, get_overall_stats, get_last_position

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    stats = get_overall_stats()
    last_pos = get_last_position()
    bookmarks = get_bookmarks()
    phases = content_service.get_all_phases()
    return request.app.state.templates.TemplateResponse("index.html", {
        "request": request,
        "phases": phases,
        "stats": stats,
        "last_pos": last_pos,
        "bookmarks": bookmarks
    })


@router.get("/chapter/{chapter_id}", response_class=HTMLResponse)
async def chapter(request: Request, chapter_id: str):
    chapter_info, phase_info = content_service.get_chapter(chapter_id)
    if not chapter_info:
        return HTMLResponse("Chapter not found", status_code=404)
    prev_id, next_id = content_service.get_prev_next(chapter_id)
    progress_list = get_chapter_progress(chapter_id)
    progress_map = {p["section_id"]: p for p in progress_list}
    bookmarks = get_bookmarks()
    bookmarked_sections = {b["section_id"] for b in bookmarks if b["chapter_id"] == chapter_id}

    sections_with_content = []
    for s in chapter_info["sections"]:
        content = content_service.load_section_content(chapter_info["dir"], s["filename"])
        sections_with_content.append({
            **s,
            "content": content,
            "completed": progress_map.get(s["filename"], {}).get("completed", 0) == 1,
            "score": progress_map.get(s["filename"], {}).get("score", 0),
            "bookmarked": s["filename"] in bookmarked_sections
        })

    return request.app.state.templates.TemplateResponse("chapter.html", {
        "request": request,
        "phase": phase_info,
        "chapter": chapter_info,
        "sections": sections_with_content,
        "prev_id": prev_id,
        "next_id": next_id,
        "exercises": chapter_info.get("exercises", [])
    })


@router.get("/phase/{phase_key}", response_class=HTMLResponse)
async def phase_view(request: Request, phase_key: str):
    phase = content_service.get_phase(phase_key)
    if not phase:
        return HTMLResponse("Phase not found", status_code=404)
    return request.app.state.templates.TemplateResponse("phase.html", {
        "request": request,
        "phase": phase
    })
