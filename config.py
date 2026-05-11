import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.join(BASE_DIR, "content")
DB_PATH = os.path.join(BASE_DIR, "database", "learning.db")
CHAPTERS_FILE = os.path.join(CONTENT_DIR, "chapters.json")


def load_chapters():
    with open(CHAPTERS_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)
    result = []
    for phase_key in sorted(raw.keys()):
        phase = raw[phase_key]
        phase_chapters = []
        for ch in phase["chapters"]:
            ch_dir = os.path.join(CONTENT_DIR, ch["dir"])
            exercises_path = os.path.join(ch_dir, "exercises.json")
            if os.path.exists(exercises_path):
                with open(exercises_path, "r", encoding="utf-8") as ef:
                    ch["exercises"] = json.load(ef)
            else:
                ch["exercises"] = []
            sections = []
            for s in sorted(os.listdir(ch_dir)):
                if s.endswith(".md"):
                    parts = s.split("_", 1)
                    order = int(parts[0]) if parts[0].isdigit() else 0
                    title = parts[1].replace(".md", "") if len(parts) > 1 else s.replace(".md", "")
                    sections.append({
                        "filename": s,
                        "title": title,
                        "order": order,
                        "exercise_count": sum(1 for e in ch["exercises"] if e.get("section", "") == parts[0])
                    })
            sections.sort(key=lambda x: x["order"])
            ch["sections"] = sections
            ch["total_exercises"] = len(ch["exercises"])
            phase_chapters.append(ch)
        result.append({
            "phase_key": phase_key,
            "phase_title": phase["title"],
            "phase_desc": phase.get("description", ""),
            "chapters": phase_chapters
        })
    return result


CHAPTERS = []


def init_chapters():
    global CHAPTERS
    CHAPTERS = load_chapters()
    return CHAPTERS
