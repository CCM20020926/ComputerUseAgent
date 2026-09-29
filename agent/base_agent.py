from langchain_openai import ChatOpenAI
import dotenv
import logging
from action.base_action import ACTION_SPACE, ACTION_SCHEMA
import json
import io
import base64
from PIL import Image
from datetime import datetime

dotenv.load_dotenv()

def execute_action(action_name, **kwargs):
    action = ACTION_SPACE.get(action_name)
    if action is None:
        raise ValueError(f"Invalid action: {action_name}")
    return action(**kwargs)


class BaseAgent:
    def __init__(self, model, base_url=None):
        self.llm = ChatOpenAI(
            model=model,
            base_url=base_url,
            use_responses_api=True
        )

        # Set reasoning effort to low for GPT-5 / GPT-6 series
        if any(model.lower().startswith(prefix) for prefix in ("gpt-5", "gpt-6")):
            self.llm.reasoning_effort = "low"

    def invoke(self, *args, **kwargs):
        raise NotImplementedError

    async def ainvoke(self, *args, **kwargs):
        raise NotImplementedError("暂不支持异步运行！")

    @staticmethod
    def _load_static_memory() -> str:
        """Read agent/memory/CLAUDE.md content."""
        import pathlib
        md_path = pathlib.Path(__file__).parent / "memory" / "CLAUDE.md"
        if md_path.exists():
            return md_path.read_text(encoding="utf-8").strip()
        return ""

    @staticmethod
    def _get_action_schema() -> str:
        action_schema = json.dumps(
            {name: json.loads(doc.strip()) for name, doc in ACTION_SCHEMA.items()},
            indent=2, ensure_ascii=False,
        )

        return action_schema

    @staticmethod
    def _take_screenshot() -> str:
        """Capture the screen and return a base64-encoded data URI."""
        from action.base_action import screenshot as take_screenshot
        img: Image.Image = take_screenshot()
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{b64}"

    @staticmethod
    def _create_logger(name: str = "agent") -> logging.Logger:
        """Create a logger that outputs to both console and a daily log file.

        Log files are stored in ``logs/`` at the project root, named by date
        (e.g. ``logs/2026-09-27.log``).
        """
        import pathlib

        logger = logging.getLogger(name)

        # Avoid duplicate handlers on repeated calls
        if logger.handlers:
            return logger

        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # ── Console handler ──
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # ── File handler (one file per day) ──
        logs_dir = pathlib.Path(__file__).resolve().parent.parent / "logs"
        logs_dir.mkdir(exist_ok=True)

        today = datetime.now().strftime("%Y-%m-%d")
        file_handler = logging.FileHandler(
            logs_dir / f"{today}.log", encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        return logger

