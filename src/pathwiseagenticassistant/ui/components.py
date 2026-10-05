import gradio as gr

from pathwiseagenticassistant.agents.compilation.ui_component import UIComponent


# Must be called inside a gr.Blocks() (or gr.render) context
def render(component: UIComponent):

    if component.type == "markdown":
        return gr.Markdown(component.content or "")

    if component.type == "text":
        return gr.Textbox(
            value=component.content or "",
            interactive=False,
            show_label=False,
        )

    if component.type == "textbox":
        return gr.Textbox(
            label=component.label or "",
        )

    if component.type == "code":
        # gr.Code only highlights a fixed set of languages; fall back to plain text otherwise
        language = component.language.lower() if component.language else None
        return gr.Code(
            value=component.content or "",
            language=language if language in gr.Code.languages else None,
            interactive=False,
        )

    if component.type == "quiz":
        return render_quiz(component)

    if component.type == "accordion":
        with gr.Accordion(component.label or "Details", open=False):
            for child in component.children:
                render(child)

        return

    if component.type == "column":
        with gr.Column():
            for child in component.children:
                render(child)

        return

    if component.type == "row":
        with gr.Row():
            for child in component.children:
                render(child)

        return

    raise ValueError(f"Unknown component type: {component.type}")


def render_quiz(component: UIComponent):
    with gr.Group():
        choice = gr.Radio(component.options, label=component.content or "Quiz")
        check = gr.Button("Check")
        result = gr.Markdown()

    def grade(selected):
        if selected is None:
            return "Pick an answer first."
        verdict = "✅ Correct!" if selected == component.answer else f"❌ Not quite. The answer is **{component.answer}**."
        return f"{verdict}\n\n{component.explanation}" if component.explanation else verdict

    check.click(grade, inputs=choice, outputs=result)
