import os
import json
from markdown_it import MarkdownIt
import config

md_renderer = MarkdownIt("commonmark", {"html": True, "typographer": True}).enable(["table", "strikethrough"])


def get_all_phases():
    return config.CHAPTERS


def get_phase(phase_key):
    for p in config.CHAPTERS:
        if p["phase_key"] == phase_key:
            return p
    return None


def get_chapter(chapter_id):
    for p in config.CHAPTERS:
        for ch in p["chapters"]:
            if ch["id"] == chapter_id:
                return ch, p
    return None, None


def get_prev_next(chapter_id):
    all_chapters = []
    for p in config.CHAPTERS:
        for ch in p["chapters"]:
            all_chapters.append(ch["id"])
    if chapter_id not in all_chapters:
        return None, None
    idx = all_chapters.index(chapter_id)
    prev_id = all_chapters[idx - 1] if idx > 0 else None
    next_id = all_chapters[idx + 1] if idx < len(all_chapters) - 1 else None
    return prev_id, next_id


def render_markdown(text):
    if text is None:
        return ""
    return md_renderer.render(text)


def load_section_content(chapter_dir, filename, as_html=True):
    filepath = os.path.join(config.CONTENT_DIR, chapter_dir, filename)
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        raw = f.read()
    return render_markdown(raw) if as_html else raw


def load_exercises(chapter_dir):
    filepath = os.path.join(config.CONTENT_DIR, chapter_dir, "exercises.json")
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def search_content(query):
    results = []
    query_lower = query.lower()
    for p in config.CHAPTERS:
        for ch in p["chapters"]:
            for s in ch.get("sections", []):
                content = load_section_content(ch["dir"], s["filename"])
                if content and query_lower in content.lower():
                    lines = content.split("\n")
                    snippet = ""
                    for i, line in enumerate(lines):
                        if query_lower in line.lower():
                            start = max(0, i - 1)
                            end = min(len(lines), i + 3)
                            snippet = "\n".join(lines[start:end])
                            break
                    results.append({
                        "phase_title": p["phase_title"],
                        "chapter_id": ch["id"],
                        "chapter_title": ch["title"],
                        "section_title": s["title"],
                        "section_filename": s["filename"],
                        "snippet": snippet[:300]
                    })
    return results
