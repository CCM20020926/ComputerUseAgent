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
# Variables: task, static_memory, dynamic_memory, action_history,
#            action_schema, skill_index, loaded_skill_content
_PROMPT_TEMPLATE = PromptTemplate(
    input_variables=[
        "task", "static_memory", "dynamic_memory", "action_history",
        "action_schema", "skill_index", "loaded_skill_content",
    ],
    template=(
        "You are a GUI automation agent. Observe the current screenshot "
        "and select an action to accomplish the task.\n\n"
        "## Task\n{task}\n\n"
        "## User Instructions (ABSOLUTE PRIORITY)\n"
        "{static_memory}\n\n"
        "## Dynamic Memory\n"
        "{dynamic_memory}\n\n"
        "## Action History\n"
        "{action_history}\n\n"
        "## Available Actions\n"
        "You MUST select the action from the following schema only. "
        "Do NOT fabricate action names.\n\n"
        "{action_schema}\n\n"
        "## Available Skills\n"
        "The following skills provide specialized multi-step workflows. "
        "When a skill matches the current task, use the `load_skill` action "
        "to load its detailed instructions BEFORE executing the workflow.\n\n"
        "{skill_index}\n\n"
        "## Loaded Skill Instructions\n"
        "{loaded_skill_content}\n\n"
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


class CUASkillAgent(BaseAgent):
    def __init__(self, model, base_url=None):
        super().__init__(model, base_url)
        self.static_memory = self._load_static_memory()
        self.model = model

        self.llm = self.llm.with_structured_output(CUAOutput, method='function_calling')
        self.action_schema = self._get_action_schema()
        self.skill_index = self._build_skill_index()
        self.loaded_skills: dict[str, str] = {}
        self.logger = self._create_logger()
        self.type = 'skill'

    # ------------------------------------------------------------------ #
    #  Public API                                                         #
    # ------------------------------------------------------------------ #

    def invoke(self, task: str):
        """Run the skill-based ReAct loop for GUI automation.

        Parameters
        ----------
        task : str
            The task description.
        """

        self.logger.info("-----------------------")
        self.logger.info(f'Task: {task}, Agent type: {self.type}, Model: {self.model}')
        self.logger.info("-----------------------")

        # Context memory – action history
        context_memory: list[ContextMemoryEntry] = []

        # Dynamic memory – search_memory results (progressive disclosure)
        dynamic_memory: dict[str, list[str]] = {}

        # Structured Trajectory Log
        trajectory_log = {}
        trajectory_log.update({"task": task, "agent_type": self.type, "model": self.model})
        trajectory_log["trajectory"] = []

        # Trajectory directory
        task_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.trajectory_dir = Path(__file__).resolve().parent.parent / "logs" / task_tag
        self.trajectory_dir.mkdir(parents=True, exist_ok=True)

        # ReAct loop
        t1 = time.time()

        iteration = 0

        while True:
            # Take current screenshot
            screenshot = self._take_screenshot()
            img_data = base64.b64decode(screenshot.split(",", 1)[1])
            (self.trajectory_dir / f"{iteration}.png").write_bytes(img_data)

            if iteration >= _MAX_ITERATIONS:
                self.logger.info("Reached maximum iterations: %d", _MAX_ITERATIONS)
                break

            # Build complete prompt (template + all context)
            prompt_text = self._build_prompt(
                task, self.static_memory, dynamic_memory,
                context_memory, self.action_schema,
                self.skill_index, self.loaded_skills,
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
            result = execute_action(action_name, **arguments)

            # ── Progressive disclosure: capture load_skill result ──
            if action_name == "load_skill" and result:
                skill_name = arguments.get("skill_name", "")
                self.loaded_skills[skill_name] = result
                self.logger.info(f"Loaded skill: {skill_name}")

            # ── Progressive disclosure: capture search_memory result ──
            if action_name == "search_memory" and result:
                category = arguments.get("category", "Others")
                self.logger.info(f"Searched memory [{category}], results: {result}")

                if result != "No relevant memory found.":
                    dynamic_memory.setdefault(category, []).append(result)

                else:
                    context_memory.append(
                        ContextMemoryEntry(
                            thought='',
                            step=f'Searched memory about \'{arguments.get('query')}\', but No relevant memory found.'
                        )
                    )



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

            # Record trajectory
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

        # Save trajectory log
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
    def _build_skill_index() -> str:
        """Scan the ``skills/`` directory and build a lightweight index
        from each SKILL.md frontmatter (name + description only).
        """
        skills_dir = Path(__file__).resolve().parent.parent / "skills"
        if not skills_dir.exists():
            return "(no skills available)"

        entries = []
        for skill_dir in sorted(skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue

            content = skill_md.read_text(encoding="utf-8")
            name = skill_dir.name
            description = _parse_skill_description(content)
            entries.append(f"- **{name}**: {description}")

        if not entries:
            return "(no skills available)"

        return "\n".join(entries)

    @staticmethod
    def _build_prompt(
        task: str,
        static_memory: str,
        dynamic_memory: dict[str, list[str]],
        context_memory: list[ContextMemoryEntry],
        action_schema: str,
        skill_index: str,
        loaded_skills: dict[str, str],
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

        # Serialize loaded skill content
        if loaded_skills:
            sections = []
            for skill_name, content in loaded_skills.items():
                sections.append(f"### Skill: {skill_name}\n{content}")
            loaded_skill_content = "\n\n".join(sections)
        else:
            loaded_skill_content = "(no skills loaded yet — use `load_skill` to load a skill when needed)"

        # Serialize dynamic memory from search_memory results
        if dynamic_memory:
            sections = []
            for category, answers in dynamic_memory.items():
                sections.append(f"### [{category}]")
                for answer in answers:
                    sections.append(f"- {answer}")
            dynamic_memory_str = "\n".join(sections)
        else:
            dynamic_memory_str = (
                "(no dynamic memories retrieved yet — use `search_memory` "
                "action to look up user preferences or local configurations "
                "before starting the task if needed)"
            )

        return _PROMPT_TEMPLATE.format(
            task=task,
            static_memory=static_memory or "(no additional instructions)",
            dynamic_memory=dynamic_memory_str,
            action_history=action_history,
            action_schema=action_schema,
            skill_index=skill_index,
            loaded_skill_content=loaded_skill_content,
        )


# ── Module-level helpers ─────────────────────────────────────────────

def _parse_skill_description(content: str) -> str:
    """Extract the ``description`` field from YAML frontmatter."""
    if not content.startswith("---"):
        return ""
    parts = content.split("---", 2)
    if len(parts) < 3:
        return ""
    frontmatter = parts[1].strip()
    for line in frontmatter.split("\n"):
        if line.strip().startswith("description:"):
            return line.split(":", 1)[1].strip()
    return ""
