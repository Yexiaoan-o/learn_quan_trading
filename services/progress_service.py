import os
import json
import sqlite3
from database.init_db import get_db


def mark_section(chapter_id, section_id, completed=True):
    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO progress (chapter_id, section_id, completed, last_accessed)
            VALUES (?, ?, ?, datetime('now','localtime'))
            ON CONFLICT(chapter_id, section_id) DO UPDATE SET
                completed = ?,
                last_accessed = datetime('now','localtime')
        """, (chapter_id, section_id, 1 if completed else 0, 1 if completed else 0))
        conn.commit()
    finally:
        conn.close()


def get_progress():
    conn = get_db()
    try:
        rows = conn.execute("SELECT chapter_id, section_id, completed, score, last_accessed FROM progress").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_chapter_progress(chapter_id):
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM progress WHERE chapter_id = ?", (chapter_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def save_exercise_result(chapter_id, exercise_id, user_answer, correct, score):
    conn = get_db()
    try:
        existing = conn.execute(
            "SELECT attempts FROM exercises WHERE chapter_id = ? AND exercise_id = ?",
            (chapter_id, exercise_id)
        ).fetchone()
        if existing:
            attempts = existing["attempts"] + 1
            conn.execute("""
                UPDATE exercises SET user_answer = ?, correct = ?, score = ?,
                    attempts = ?, completed_at = datetime('now','localtime')
                WHERE chapter_id = ? AND exercise_id = ?
            """, (user_answer, 1 if correct else 0, score, attempts, chapter_id, exercise_id))
        else:
            conn.execute("""
                INSERT INTO exercises (chapter_id, exercise_id, user_answer, correct, score, attempts, completed_at)
                VALUES (?, ?, ?, ?, ?, 1, datetime('now','localtime'))
            """, (chapter_id, exercise_id, user_answer, 1 if correct else 0, score))
        conn.commit()
    finally:
        conn.close()


def get_exercise_history(chapter_id):
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM exercises WHERE chapter_id = ? ORDER BY completed_at DESC",
            (chapter_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_overall_stats():
    conn = get_db()
    try:
        total_progress = conn.execute("SELECT COUNT(DISTINCT chapter_id || '-' || section_id) FROM progress WHERE completed = 1").fetchone()[0]
        total_exercises = conn.execute("SELECT COUNT(*) FROM exercises").fetchone()[0]
        correct_exercises = conn.execute("SELECT COUNT(*) FROM exercises WHERE correct = 1").fetchone()[0]
        accuracy = (correct_exercises / total_exercises * 100) if total_exercises > 0 else 0
        last_accessed = conn.execute(
            "SELECT chapter_id, section_id, last_accessed FROM progress ORDER BY last_accessed DESC LIMIT 1"
        ).fetchone()
        total_learning_seconds = conn.execute("SELECT COALESCE(SUM(seconds), 0) FROM learning_time").fetchone()[0]
        return {
            "completed_sections": total_progress,
            "total_exercises_attempted": total_exercises,
            "correct_exercises": correct_exercises,
            "accuracy": round(accuracy, 1),
            "last_chapter": last_accessed["chapter_id"] if last_accessed else None,
            "last_section": last_accessed["section_id"] if last_accessed else None,
            "total_learning_minutes": round(total_learning_seconds / 60, 1)
        }
    finally:
        conn.close()


def get_last_position():
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT chapter_id, section_id FROM progress ORDER BY last_accessed DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def save_note(chapter_id, section_id, content):
    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO notes (chapter_id, section_id, content, created_at, updated_at)
            VALUES (?, ?, ?, datetime('now','localtime'), datetime('now','localtime'))
        """, (chapter_id, section_id, content))
        conn.commit()
    finally:
        conn.close()


def get_notes(chapter_id=None):
    conn = get_db()
    try:
        if chapter_id:
            rows = conn.execute(
                "SELECT * FROM notes WHERE chapter_id = ? ORDER BY updated_at DESC",
                (chapter_id,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM notes ORDER BY updated_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def delete_note(note_id):
    conn = get_db()
    try:
        conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        conn.commit()
    finally:
        conn.close()


def toggle_bookmark(chapter_id, section_id):
    conn = get_db()
    try:
        existing = conn.execute(
            "SELECT id FROM bookmarks WHERE chapter_id = ? AND section_id = ?",
            (chapter_id, section_id)
        ).fetchone()
        if existing:
            conn.execute("DELETE FROM bookmarks WHERE chapter_id = ? AND section_id = ?",
                         (chapter_id, section_id))
            action = "removed"
        else:
            conn.execute(
                "INSERT INTO bookmarks (chapter_id, section_id, created_at) VALUES (?, ?, datetime('now','localtime'))",
                (chapter_id, section_id))
            action = "added"
        conn.commit()
        return action
    finally:
        conn.close()


def get_bookmarks():
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM bookmarks ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def record_learning_time(chapter_id, seconds):
    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO learning_time (chapter_id, date, seconds)
            VALUES (?, date('now','localtime'), ?)
            ON CONFLICT(chapter_id, date) DO UPDATE SET seconds = seconds + ?
        """, (chapter_id, seconds, seconds))
        conn.commit()
    finally:
        conn.close()
