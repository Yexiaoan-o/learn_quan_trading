from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from services import progress_service, content_service
from pydantic import BaseModel

router = APIRouter()


class ProgressUpdate(BaseModel):
    completed: bool = True


@router.post("/api/progress/{chapter_id}/{section_id}")
async def update_progress(chapter_id: str, section_id: str, data: ProgressUpdate):
    progress_service.mark_section(chapter_id, section_id, data.completed)
    return {"status": "ok"}


@router.get("/progress", response_class=HTMLResponse)
async def progress_page(request: Request):
    all_progress = progress_service.get_progress()
    stats = progress_service.get_overall_stats()
    phases = content_service.get_all_phases()

    phase_stats = []
    for phase in phases:
        total_sections = 0
        completed_sections = 0
        total_exercises = 0
        completed_exercises = 0
        for ch in phase["chapters"]:
            total_sections += len(ch.get("sections", []))
            total_exercises += ch.get("total_exercises", 0)
            for s in ch.get("sections", []):
                for p in all_progress:
                    if p["chapter_id"] == ch["id"] and p["section_id"] == s["filename"]:
                        if p["completed"]:
                            completed_sections += 1
                        break
            for e in ch.get("exercises", []):
                for eh in progress_service.get_exercise_history(ch["id"]):
                    if eh["exercise_id"] == e["id"] and eh["correct"]:
                        completed_exercises += 1
                        break

        phase_stats.append({
            "key": phase["phase_key"],
            "title": phase["phase_title"],
            "total_sections": total_sections,
            "completed_sections": completed_sections,
            "section_pct": round(completed_sections / total_sections * 100) if total_sections > 0 else 0,
            "total_exercises": total_exercises,
            "completed_exercises": completed_exercises,
            "exercise_pct": round(completed_exercises / total_exercises * 100) if total_exercises > 0 else 0
        })

    return request.app.state.templates.TemplateResponse(request=request, name="progress.html", context={
        "request": request,
        "phases": phases,
        "stats": stats,
        "phase_stats": phase_stats
    })


class LearningTime(BaseModel):
    seconds: int


@router.post("/api/learning-time/{chapter_id}")
async def record_time(chapter_id: str, data: LearningTime):
    progress_service.record_learning_time(chapter_id, data.seconds)
    return {"status": "ok"}
