from langchain_core.tools import tool
from memory_manager import memory_manager
from agent.skill_agent import CUASkillAgent
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import HumanMessage
import uuid

def generate_uuid() -> str:
    """生成一个标准 UUID4 字符串。"""
    return str(uuid.uuid4())

chat_model = ChatOpenAI(model="gpt-6-luna")
chat_model.reasoning_effort = 'low'

cua_skill_agent = CUASkillAgent(model="gpt-6-luna")

@tool
def add_memory(category: str, query: str):
    """Store user's personal preference or local environment configuration into long-term memory.

    Use this tool ONLY when the user explicitly states one of the following:
    - **Preference**: personal habits, tool preferences, workflow preferences,
      e.g. "I prefer using WPS Office", "I like dark theme", "I usually use Chrome".
    - **Local Config**: local file paths, folder locations, environment settings,
      e.g. "My documents folder is D:\\Docs", "My project root is E:\\Projects".

    Args:
        category: Must be exactly one of ['preference', 'local_config'].
                  Use 'preference' for user habits and tool preferences.
                  Use 'local_config' for local file paths and environment settings.
        query: The concrete information to remember, e.g. "习惯使用 WPS Office" or "常用办公文件夹路径为 D:\\OfficeFiles".
    """
    try:
        memory_manager.add(category, query)
        return "写入成功！"
    except Exception as e:
        print(e)
        return str(e)

@tool
def call_cua(task: str):
    """Delegate a GUI automation task to the Computer Use Agent.

    Use this tool when the user requests any operation that involves interacting
    with the graphical user interface, including but not limited to:
    - File operations: open, move, rename, delete files or folders
    - Browser operations: navigate to a URL, search the web, fill forms, click buttons
    - Application control: launch apps, switch windows, type text, use keyboard shortcuts
    - Any task that requires seeing the screen and performing mouse/keyboard actions

    Args:
        task: A clear, self-contained description of the GUI task to perform.
              Include all necessary context so the CUA agent can execute independently.
    """
    try:
        context_memory = cua_skill_agent.invoke(task)
        return context_memory[-1]
    except Exception as e:
        return str(e)

def main():
    saver = InMemorySaver()

    # System prompt: guide the agent on when to use each tool
    system_prompt = (
        "You are a helpful conversational assistant that coordinates with "
        "specialized tools to serve the user.\n\n"
        "You have access to two tools:\n"
        "1. **add_memory** — Save the user's stated preferences or local "
        "environment configuration (file paths, folder locations) into "
        "long-term memory.\n"
        "2. **call_cua** — Delegate a GUI automation task (file operations, "
        "browser control, app launching, etc.) to the Computer Use Agent.\n\n"
        "## Decision Rules\n"
        "- If the user expresses a **personal preference** (e.g. preferred "
        "software, habits, workflow style), call **add_memory** with "
        "category='preference'.\n"
        "- If the user mentions a **local configuration** (e.g. file paths, "
        "folder locations, environment settings), call **add_memory** with "
        "category='local_config'.\n"
        "- If the user requests a **GUI operation** (opening files, browsing "
        "the web, controlling applications, etc.), call **call_cua** with a "
        "clear task description.\n"
        "- If the user's message contains **both** memory-worthy information "
        "AND a GUI operation request, you MUST call **add_memory** first to "
        "save the information, and **then** call **call_cua** to execute the "
        "GUI task. Do NOT combine them into a single tool call.\n"
        "- If the message is a general conversation (greetings, questions, "
        "chit-chat), respond directly in a friendly and helpful manner "
        "without calling any tool.\n\n"
        "## Important\n"
        "- Always confirm to the user when memory has been saved.\n"
        "- When calling call_cua, include all relevant context in the task "
        "description so the GUI agent can act independently.\n"
        "- Reply in the same language the user uses."
    )

    chat_agent = create_agent(
        model=chat_model,
        tools=[add_memory, call_cua],
        checkpointer=saver,
        system_prompt=system_prompt
    )

    while True:
        print("user> ", end='')
        query = input()

        if query == "exit":
            break

        if query.strip() == '':
            continue

        state = chat_agent.invoke(
            input={"messages": [HumanMessage(content=query)]},
            config={"configurable": {"thread_id": "default"}}
        )

        print(state["messages"][-1].content)

if __name__ == '__main__':
    main()