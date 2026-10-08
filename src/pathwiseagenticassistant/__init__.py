def main() -> None:
    from dotenv import load_dotenv

    from pathwiseagenticassistant.ui.app import build_app

    load_dotenv()
    build_app().launch()
