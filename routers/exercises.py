from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from services import content_service, grading_service, progress_service
from pydantic import BaseModel

router = APIRouter()


class ExerciseAnswer(BaseModel):
    answer: str


@router.get("/exercise/{chapter_id}", response_class=HTMLResponse)
async def exercise_page(request: Request, chapter_id: str):
    chapter_info, phase_info = content_service.get_chapter(chapter_id)
    if not chapter_info:
        return HTMLResponse("Chapter not found", status_code=404)
    exercises = chapter_info.get("exercises", [])
    if not exercises:
        return HTMLResponse("No exercises for this chapter", status_code=404)

    rendered_exercises = []
    for ex in exercises:
        ex_copy = dict(ex)
        ex_copy["question"] = content_service.render_markdown(ex.get("question", ""))
        ex_copy["explanation"] = content_service.render_markdown(ex.get("explanation", ""))
        rendered_exercises.append(ex_copy)

    history = progress_service.get_exercise_history(chapter_id)
    history_map = {h["exercise_id"]: h for h in history}

    return request.app.state.templates.TemplateResponse("exercise.html", {
        "request": request,
        "phase": phase_info,
        "chapter": chapter_info,
        "exercises": rendered_exercises,
        "history_map": history_map
    })


@router.post("/api/exercise/{chapter_id}/{exercise_id}")
async def submit_exercise(chapter_id: str, exercise_id: str, data: ExerciseAnswer):
    exercises = chapter_info = None
    for p in content_service.get_all_phases():
        for ch in p["chapters"]:
            if ch["id"] == chapter_id:
                exercises = ch.get("exercises", [])
                break

    if not exercises:
        return JSONResponse({"error": "Chapter not found"}, status_code=404)

    exercise = None
    for ex in exercises:
        if ex["id"] == exercise_id:
            exercise = ex
            break

    if not exercise:
        return JSONResponse({"error": "Exercise not found"}, status_code=404)

    result = grading_service.grade_exercise(exercise, data.answer)
    progress_service.save_exercise_result(
        chapter_id, exercise_id, data.answer, result["correct"], result["score"]
    )

    return {
        "correct": result["correct"],
        "score": result["score"],
        "feedback": result["feedback"],
        "explanation": exercise.get("explanation", ""),
        "answer": exercise.get("answer")
    }


@router.get("/api/exercises/{chapter_id}/history")
async def exercise_history(chapter_id: str):
    history = progress_service.get_exercise_history(chapter_id)
    return history
