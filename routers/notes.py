from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import httpx

from services import progress_service, content_service

router = APIRouter()


class NoteCreate(BaseModel):
    chapter_id: str
    section_id: str
    content: str


class AnnotationCreate(BaseModel):
    chapter_id: str
    section_id: str
    selected_text: str
    comment: str = ""


class SettingsUpdate(BaseModel):
    api_key: str = ""
    model_name: str = ""
    api_base: str = "https://api.openai.com/v1"


class AIQuestion(BaseModel):
    annotation_id: int | None = None
    selected_text: str
    question: str


@router.get("/notes", response_class=HTMLResponse)
async def notes_page(request: Request):
    notes = progress_service.get_notes()
    annotations = progress_service.get_annotations()
    phases = content_service.get_all_phases()
    return request.app.state.templates.TemplateResponse(request=request, name="notes.html", context={
        "request": request,
        "phases": phases,
        "notes": notes,
        "annotations": annotations
    })


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    phases = content_service.get_all_phases()
    settings = progress_service.get_settings()
    return request.app.state.templates.TemplateResponse(request=request, name="settings.html", context={
        "request": request,
        "phases": phases,
        "settings": settings
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


@router.post("/api/annotations")
async def create_annotation(data: AnnotationCreate):
    progress_service.save_annotation(
        data.chapter_id,
        data.section_id,
        data.selected_text,
        data.comment,
    )
    return {"status": "ok"}


@router.get("/api/annotations")
async def annotations_route(chapter_id: str | None = None):
    return progress_service.get_annotations(chapter_id)


@router.delete("/api/annotations/{annotation_id}")
async def delete_annotation_route(annotation_id: int):
    progress_service.delete_annotation(annotation_id)
    return {"status": "ok"}


@router.get("/api/settings")
async def get_settings_route():
    return progress_service.get_settings()


@router.post("/api/settings")
async def save_settings_route(data: SettingsUpdate):
    progress_service.save_settings({
        "api_key": data.api_key,
        "model_name": data.model_name,
        "api_base": data.api_base,
    })
    return {"status": "ok"}


@router.post("/api/ai/ask")
async def ask_ai_route(data: AIQuestion):
    settings = progress_service.get_settings()
    api_key = settings.get("api_key", "").strip()
    model_name = settings.get("model_name", "").strip()
    api_base = settings.get("api_base", "https://api.openai.com/v1").rstrip("/")

    if not api_key or not model_name:
        return JSONResponse(
            {"error": "请先在设置页面填写 API Key 和模型名称。"},
            status_code=400,
        )

    question_text = data.question.strip() or "请解释这段内容，并给我更易懂的说明。"
    prompt = (
        "你是量化交易和 DolphinDB 学习助手。"
        "请根据用户选中的课程内容，用中文给出清晰、结构化、易懂的解答。"
        "如果问题涉及代码，请尽量给出完整可运行示例。\n\n"
        f"课程片段：\n{data.selected_text}\n\n"
        f"用户问题：\n{question_text}"
    )

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{api_base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model_name,
                    "messages": [
                        {"role": "system", "content": "你是专业、耐心的量化交易中文助教。"},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.3,
                },
            )

        if response.status_code >= 400:
            return JSONResponse(
                {"error": f"AI 接口请求失败：{response.status_code} {response.text[:300]}"},
                status_code=500,
            )

        payload = response.json()
        answer = payload["choices"][0]["message"]["content"]

        if data.annotation_id is not None:
            progress_service.save_annotation_ai_answer(data.annotation_id, answer)

        return {"answer": answer}
    except Exception as exc:
        return JSONResponse({"error": f"AI 调用失败：{exc}"}, status_code=500)
