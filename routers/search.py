from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from services import content_service

router = APIRouter()


@router.get("/search", response_class=HTMLResponse)
async def search_page(request: Request, q: str = ""):
    phases = content_service.get_all_phases()
    results = content_service.search_content(q) if q else []
    return request.app.state.templates.TemplateResponse(request=request, name="search.html", context={
        "request": request,
        "phases": phases,
        "query": q,
        "results": results
    })
