import logging

import gradio as gr

from pathwiseagenticassistant.chat.chat_service import respond_to_message
from pathwiseagenticassistant.schemas import Answer
from pathwiseagenticassistant.storage.db import (
    attach_lesson_to_chat,
    create_chat,
    get_chat,
    get_chat_for_lesson,
    get_chat_messages,
    get_lesson,
    init_db,
    list_chats,
    list_lessons,
)
from pathwiseagenticassistant.ui.renderer import lesson_panel

# Overview Description: Local chat app. The UI only talks to chat_service and storage.
#
#   sidebar (chats, lessons) ──> show_chat(chat_id) ──> chatbot + lesson panel, read from SQLite
#   message box ──> respond_to_message(chat_id, text) ──> ChatEvents ──> chatbot (+ lesson panel)
#
# Only the active chat id is kept in gr.State; everything else is read from SQLite.


logger = logging.getLogger(__name__)


def _message(role: str, content: str) -> dict[str, str]:
    return {"role": role, "content": content}


def build_app() -> gr.Blocks:
    init_db()
    with gr.Blocks() as app:
        active_chat = gr.State(None)

        with gr.Sidebar():
            topic = gr.Textbox(label="Topic for a new chat")
            new_chat = gr.Button("+ New chat")
            chats = gr.Radio(label="Chats")
            lessons = gr.Radio(label="Lessons")

        with gr.Row():
            with gr.Column(scale=2):
                chatbot = gr.Chatbot()
                msg = gr.Textbox(show_label=False, placeholder="Message", submit_btn=True)
                show_lesson = gr.Checkbox(label="Show lesson")
            with gr.Column(scale=3, visible=False) as lesson_column:
                lesson_state = lesson_panel()

        view = [active_chat, chats, lessons, chatbot, lesson_state]
        controls = [msg, topic, new_chat, chats, lessons]  # locked while a message is being answered

        def set_locked(locked: bool) -> dict:
            return {control: gr.update(interactive=not locked) for control in controls}

        async def show_chat(chat_id: str | None) -> dict:
            chat = get_chat(chat_id) if chat_id else None
            lesson = get_lesson(chat.lesson_id) if chat and chat.lesson_id else None
            return {
                active_chat: chat_id,
                chats: gr.Radio(choices=[(c.title, c.id) for c in list_chats()], value=chat_id),
                lessons: gr.Radio(
                    choices=[(lesson_topic, lesson_id) for lesson_id, lesson_topic in list_lessons()],
                    value=chat.lesson_id if chat else None,
                ),
                chatbot: await get_chat_messages(chat_id) if chat_id else [],
                lesson_state: lesson.model_dump() if lesson else None,
            }

        async def start_chat(topic: str) -> dict:
            if not topic.strip():
                raise gr.Error("Enter a topic for the new chat first.")
            return await show_chat(create_chat(topic.strip()))

        async def open_lesson(lesson_id: str) -> dict:
            chat = get_chat_for_lesson(lesson_id)
            if chat is None:  # lesson saved but never attached, e.g. the app stopped in between
                chat_id = create_chat(get_lesson(lesson_id).research_pack.topic)
                attach_lesson_to_chat(chat_id, lesson_id)
                return await show_chat(chat_id)
            return await show_chat(chat.id)

        async def send(message: str, chat_id: str | None, history: list[dict]):
            if chat_id is None:
                raise gr.Error("Start a new chat or pick one first.")
            if not message.strip():
                return
            history = [*history, _message("user", message)]
            yield {**set_locked(True), msg: gr.Textbox(value="", interactive=False), chatbot: history}
            try:
                async for event in respond_to_message(chat_id, message):
                    if event.kind == "status":  # temporary line, replaced by the next event
                        yield {chatbot: [*history, _message("assistant", f"⏳ {event.message}")]}
                        continue
                    if event.kind == "answer":
                        history.append(_message("assistant", Answer(answer=event.message, sources=event.sources).as_markdown()))
                        yield {chatbot: history}
                        continue
                    history.append(_message("assistant", "Lesson ready. Tick 'Show lesson' to open it."))
                    yield {**await show_chat(chat_id), chatbot: history}
            except Exception:  # keep the app usable: an exception would leave the controls locked
                logger.exception("Failed to respond in chat %s", chat_id)
                history.append(_message("assistant", "⚠️ Something went wrong. Please try again."))
            yield {**set_locked(False), chatbot: history}

        gr.on([new_chat.click, topic.submit], start_chat, topic, view)
        chats.input(show_chat, chats, view)
        lessons.input(open_lesson, lessons, view)
        msg.submit(send, [msg, active_chat, chatbot], list(dict.fromkeys([*view, *controls])))
        show_lesson.change(lambda visible: gr.Column(visible=visible), show_lesson, lesson_column)
        app.load(show_chat, active_chat, view)

    return app
