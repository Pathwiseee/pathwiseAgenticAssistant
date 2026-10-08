import json
import sqlite3
import uuid
from pathlib import Path

from agents import SQLiteSession
from pydantic import BaseModel

from pathwiseagenticassistant.schemas import Answer, CompiledLesson, LearningRequest

# Overview Description: Local storage for chats and compiled lessons
#
#   chats ──(lesson_id)──> lessons
#     │
#     └──(id = session_id)──> agent_sessions / agent_messages  (managed by SQLiteSession)
#
# Everything lives in one SQLite file so a chat's metadata, its lesson and its
# agent history can be picked up together by chat id.

DB_PATH = Path("data/pathwise.db")


class Chat(BaseModel):
    id: str
    title: str
    topic: str
    lesson_id: str | None = None
    created_at: str


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chats (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                topic TEXT NOT NULL,
                lesson_id TEXT REFERENCES lessons (id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS lessons (
                id TEXT PRIMARY KEY,
                topic TEXT NOT NULL,
                compiled_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


# ---------- chats ----------

def create_chat(topic: str) -> str:
    # uuid instead of "latest id + 1": SQLiteSession only writes a row on the first
    # message, so counting rows would hand out the same id to two empty chats
    chat_id = uuid.uuid4().hex
    with _connect() as conn:
        conn.execute("INSERT INTO chats (id, title, topic) VALUES (?, ?, ?)", (chat_id, topic, topic))
    return chat_id


def list_chats() -> list[Chat]:
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM chats ORDER BY created_at DESC").fetchall()
    return [Chat(**dict(row)) for row in rows]


def get_chat(chat_id: str) -> Chat:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM chats WHERE id = ?", (chat_id,)).fetchone()
    if row is None:
        raise KeyError(f"no chat with id {chat_id}")
    return Chat(**dict(row))


def get_chat_for_lesson(lesson_id: str) -> Chat | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM chats WHERE lesson_id = ?", (lesson_id,)).fetchone()
    return Chat(**dict(row)) if row else None


def attach_lesson_to_chat(chat_id: str, lesson_id: str) -> None:
    with _connect() as conn:
        conn.execute("UPDATE chats SET lesson_id = ? WHERE id = ?", (lesson_id, chat_id))


def get_chat_session(chat_id: str) -> SQLiteSession:
    return SQLiteSession(chat_id, DB_PATH)


async def get_chat_messages(chat_id: str) -> list[dict[str, str]]:
    """The chat as {role, content} messages for gr.Chatbot.

    The session stores what the model saw, not what the user saw: intake prompts carry a
    "Topic: ..." prefix and agent replies are JSON (LearningRequest or Answer).
    """
    intake_prefix = f"Topic: {get_chat(chat_id).topic}, User Prompt: "  # as built by intake_user_request
    messages = []
    for item in await get_chat_session(chat_id).get_items():
        if item.get("role") == "user":
            messages.append({"role": "user", "content": item["content"].removeprefix(intake_prefix)})
        elif item.get("role") == "assistant":  # reasoning and tool items have no role
            reply = json.loads(item["content"][0]["text"])
            text = Answer(**reply).as_markdown() if "answer" in reply else LearningRequest(**reply).summary()
            messages.append({"role": "assistant", "content": text})
    return messages


# ---------- lessons ----------

def save_lesson(lesson: CompiledLesson) -> str:
    lesson_id = uuid.uuid4().hex
    with _connect() as conn:
        conn.execute(
            "INSERT INTO lessons (id, topic, compiled_json) VALUES (?, ?, ?)",
            (lesson_id, lesson.research_pack.topic, lesson.model_dump_json()),
        )
    return lesson_id


def list_lessons() -> list[tuple[str, str]]:
    """(id, topic) pairs for the lesson directory, newest first."""
    with _connect() as conn:
        rows = conn.execute("SELECT id, topic FROM lessons ORDER BY created_at DESC").fetchall()
    return [(row["id"], row["topic"]) for row in rows]


def get_lesson(lesson_id: str) -> CompiledLesson:
    with _connect() as conn:
        row = conn.execute("SELECT compiled_json FROM lessons WHERE id = ?", (lesson_id,)).fetchone()
    if row is None:
        raise KeyError(f"no lesson with id {lesson_id}")
    return CompiledLesson.model_validate_json(row["compiled_json"])
