import base64
import json
import time
from datetime import datetime
from pathlib import Path

from langchain_core.messages import HumanMessage
from langchain_core.prompts import PromptTemplate

from .base_agent import BaseAgent, execute_action
from schema import CUAOutput, ContextMemoryEntry


# ── Prompt Template ──────────────────────────────────────────────────
# Variables: task, static_memory, action_history, action_schema
_PROMPT_TEMPLATE = PromptTemplate(
    input_variables=["task", "static_memory", "action_history", "action_schema"],
    template=(
        "You are a GUI automation agent. Observe the current screenshot "
        "and select an action to accomplish the task.\n\n"
        "## Task\n{task}\n\n"
        "## User Instructions (ABSOLUTE PRIORITY)\n"
        "{static_memory}\n\n"
        "## Action History\n"
        "{action_history}\n\n"
        "## Available Actions\n"
        "You MUST select the action from the following schema only. "
        "Do NOT fabricate action names.\n\n"
        "{action_schema}\n\n"
        "## Response Format\n"
        "- thought: your reasoning about the current screen and next step\n"
        "- step: a brief description of the action you are about to take\n"
        "- action: the exact action name from the schema above\n"
        "- arguments: the parameters for that action, matching its schema"
    ),
)

# Actions that signal the agent should stop
_TERMINAL_ACTIONS = {"finish", "error_env", "call_user"}

_MAX_ITERATIONS = 20


class CUAReActAgent(BaseAgent):
    def __init__(self, model, base_url=None):
        super().__init__(model, base_url)
        self.static_memory = self._load_static_memory()
        self.model = model

        self.llm = self.llm.with_structured_output(CUAOutput, method='function_calling')
        self.action_schema = self._get_action_schema()
        self.logger = self._create_logger()
        self.type = 'react'
    # ------------------------------------------------------------------ #
    #  Public API                                                         #
    # ------------------------------------------------------------------ #

    def invoke(self, task: str):
        """Run the ReAct loop for GUI automation.

        Parameters
        ----------
        task : str, optional
            The task description.  If *None*, the content of
            ``agent/memory/CLAUDE.md`` is used instead.
        """

        self.logger.info("-----------------------")
        self.logger.info(f'Task: {task}, Agent type: {self.type}, Model: {self.model}')
        self.logger.info("-----------------------")

        # Context memory – action history
        context_memory: list[ContextMemoryEntry] = []

        # Structured Trajectory Log
        trajectory_log = {}
        trajectory_log.update({"task": task, "agent_type": self.type, "model": self.model})
        trajectory_log["trajectory"] = []

        # 在 logs 目录下创建一个文件夹，记录本组任务的图文轨迹记录
        task_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.trajectory_dir = Path(__file__).resolve().parent.parent / "logs" / task_tag
        self.trajectory_dir.mkdir(parents=True, exist_ok=True)

        # ReAct loop
        t1 = time.time()

        iteration = 0

        while True:
            # Take current screenshot
            screenshot = self._take_screenshot()
            # 保存图像到文件夹
            img_data = base64.b64decode(screenshot.split(",", 1)[1])
            (self.trajectory_dir / f"{iteration}.png").write_bytes(img_data)

            if iteration >= _MAX_ITERATIONS:
                self.logger.info("Reached maximum iterations: %d", _MAX_ITERATIONS)
                break

            # Build complete prompt (template + all context)
            prompt_text = self._build_prompt(
                task, self.static_memory, context_memory, self.action_schema,
            )

            # Call LLM – only prompt text + screenshot, no history
            output: CUAOutput = self.llm.invoke([
                    HumanMessage(content=[
                        {"type": "text", "text": prompt_text},
                        {"type": "image_url", "image_url": {"url": screenshot}},
                    ])
                ]
            )

            action_name: str = output.action
            arguments: dict = output.arguments
            thought: str = output.thought
            step: str = output.step

            self._log_step(thought, step, action_name, arguments)

            # Record into context memory
            context_memory.append(
                ContextMemoryEntry(thought=thought, step=step)
            )

            # Execute the chosen action
            execute_action(action_name, **arguments)
            time.sleep(1)

            # Check terminal actions
            if action_name in _TERMINAL_ACTIONS:
                trajectory_log["trajectory"].append(
                    {
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "thought": thought,
                        "step": step,
                        "action": action_name,
                        "arguments": arguments,
                        "image": ""
                    }
                )

                break

            # 将当前动作时间（Y%-m%-D% H%:%M:%S）、thought、action_name、arguments、执行后的关联图片保存
            trajectory_log["trajectory"].append(
                {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "thought": thought,
                    "step": step,
                    "action": action_name,
                    "arguments": arguments,
                    "image": f"{iteration + 1}.png"
                }
            )

            iteration += 1

        t2 = time.time()

        # 保存 trajectory_log 到轨迹目录
        (self.trajectory_dir / "trajectory.json").write_text(
            json.dumps(trajectory_log, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        self.logger.info(f"Trajectory saved to {self.trajectory_dir}")

        self.logger.info(f"Task completed in {t2 - t1} seconds")

        return context_memory

    # ------------------------------------------------------------------ #
    #  Private helpers                                                    #
    # ------------------------------------------------------------------ #
    def _log_step(self, thought: str, step: str, action: str, arguments: dict):
        self.logger.info(
            f"Thought: {thought}"
            f" | Step: {step}"
            f" | Action: {action}"
            f" | Arguments: {arguments}"
        )

    @staticmethod
    def _build_prompt(
        task: str,
        static_memory: str,
        context_memory: list[ContextMemoryEntry],
        action_schema: str,
    ) -> str:
        """Build the complete prompt via _PROMPT_TEMPLATE."""
        # Serialize action history
        if context_memory:
            lines = []
            for idx, entry in enumerate(context_memory, 1):
                lines.append(f"- Step {idx}\n  Thought: {entry.thought}\n  Action: {entry.step}")
            action_history = "\n".join(lines)
        else:
            action_history = "(none)"

        return _PROMPT_TEMPLATE.format(
            task=task,
            static_memory=static_memory or "(no additional instructions)",
            action_history=action_history,
            action_schema=action_schema,
        )
