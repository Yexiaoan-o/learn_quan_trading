import sys
import os
from contextlib import asynccontextmanager

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from database.init_db import init_db
from config import init_chapters
from routers import content, progress, exercises, notes, search


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    init_chapters()
    print("[App] 量化交易学习平台已启动！访问 http://127.0.0.1:8000")
    yield


app = FastAPI(title="量化交易学习平台", version="1.0.0", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")
app.state.templates = templates

app.include_router(content.router)
app.include_router(progress.router)
app.include_router(exercises.router)
app.include_router(notes.router)
app.include_router(search.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
