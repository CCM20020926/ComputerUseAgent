# CUA — Computer Use Agent

**声明：** 此 README.md 内容主体由 AI 生成，部分代码由 AI 编写

<span style="color: red;"> （2026/9/29） 当前 docx SKILL 只能创建新文档（creating documents），功能存在一定不稳定性；edit documents 功能存在 bug，尚不能正常运行 </span>

## 项目概述

基于 **ReAct（Reasoning + Acting）** 范式的 GUI 自动化 Agent 系统。通过观察屏幕截图进行多模态理解与多步推理，从预定义动作集中选择并执行 GUI 操作，循环迭代直至任务完成。

核心技术栈：**LangChain + LangGraph + OpenAI 兼容接口 + mem0 + ChromaDB**

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     main.py — 多 Agent 协同 Shell                │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │          意图路由 Agent（LangGraph + checkpointer）        │   │
│  │                                                          │   │
│  │  ┌─────────────┐              ┌────────────────────┐     │   │
│  │  │ add_memory   │              │ call_cua           │     │   │
│  │  │ (记忆写入)   │              │ (GUI 任务委派)     │     │   │
│  │  └──────┬───────┘              └────────┬───────────┘     │   │
│  └─────────┼───────────────────────────────┼─────────────────┘   │
│            │                               │                      │
│            ▼                               ▼                      │
│  ┌──────────────────┐          ┌──────────────────────────┐      │
│  │  MemoryManager   │          │   CUASkillAgent          │      │
│  │  (mem0+ChromaDB) │          │   (Skill 渐进式披露)     │      │
│  └──────────────────┘          └──────────────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

系统由三层构成：
1. **对话 Shell（main.py）** — 多 Agent 协同入口，负责意图路由与任务分发
2. **Computer Use Agent（skill_agent.py）** — 核心 GUI 自动化 Agent，具备 Skill 加载与动态记忆检索能力
3. **基础 ReAct Agent（react_agent.py）** — 精简版 Agent，仅依赖截图与静态记忆进行推理

---

## 一、CUAReActAgent — 基础 ReAct 循环

> 文件：`agent/react_agent.py`

### 架构

```
┌─────────────────────────────────────────────────┐
│                  CUAReActAgent                   │
│                                                  │
│  ┌──────────┐   ┌──────────┐   ┌─────────────┐  │
│  │  Screen   │──▶│   LLM    │──▶│  Structured  │  │
│  │ Screenshot│   │ (ReAct)  │   │   Output     │  │
│  └──────────┘   └──────────┘   └──────┬──────┘  │
│       ▲                                │         │
│       │          ┌─────────────┐       │         │
│       └──────────│  Execute &  │◀──────┘         │
│                  │  Wait 1s    │                  │
│                  └─────────────┘                  │
│                                                  │
│  ┌──────────────────────────────────────────┐    │
│  │        短期工作记忆（Context Memory）      │    │
│  │  list[ContextMemoryEntry]                │    │
│  │  - Step 1: Thought → Action              │    │
│  │  - Step 2: Thought → Action              │    │
│  │  - ...                                   │    │
│  └──────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘
```

### 核心机制

**1. 动作选择 — Function Call + Structured Output**

使用 `llm.with_structured_output(CUAOutput, method='function_calling')` 强制 LLM 通过 Function Call 返回结构化响应，保证输出格式可靠。`CUAOutput` 定义如下：

```python
class CUAOutput(BaseModel):
    thought: str              # 思考过程（Self-Reflection）
    step: str                 # 当前步骤描述
    action: str               # 选择的动作名称
    arguments: Dict[str, Any] # 动作参数
```

**2. 屏幕观测 — 多模态感知循环**

每轮迭代截取当前屏幕，转换为 base64 PNG data URI，与提示词文本一起封装为单条 `HumanMessage` 发送给 LLM。Agent 仅基于**当前提示词 + 当前截图**推理，不依赖历史消息累积，实现无状态调用。

**3. 上下文压缩 — Self-Reflection 提取关键信息**

通过 `thought` 字段，Agent 在每步执行后进行自我反思，将视觉观察压缩为文本形式的思考摘要，存入 `ContextMemoryEntry`。后续轮次仅将压缩后的文本历史注入提示词，而非重复传递完整截图，从而有效压缩上下文 Token。

**4. 提示词模板 — PromptTemplate 无状态调用**

模块级 `_PROMPT_TEMPLATE` 封装完整提示词，包含任务、静态记忆、动作历史、动作 Schema 四个变量，每次调用时由 `_build_prompt()` 填充。

**5. 迭代控制**

| 控制项 | 设定 |
|--------|------|
| 最大迭代次数 | **20 回合**，达到后强制退出 |
| 提前退出条件 | Agent 选择 `finish`、`error_env`、`call_user` 动作时 |
| 动作执行后延时 | **1 秒**，等待 GUI 响应 |

---

## 二、CUASkillAgent — Skill 渐进式披露 + 层次化记忆

> 文件：`agent/skill_agent.py`

### 架构

```
┌───────────────────────────────────────────────────────────────┐
│                      CUASkillAgent                             │
│                                                                │
│  ┌──────────┐   ┌──────────────────────────────────────────┐  │
│  │  Screen   │──▶│              LLM (ReAct)                │  │
│  │ Screenshot│   │                                          │  │
│  └──────────┘   │  注入上下文:                              │  │
│                 │  - 静态长期记忆 (CLAUDE.md)                │  │
│                 │  - 动态长期记忆 (search_memory 结果)       │  │
│                 │  - 短期工作记忆 (context_memory)           │  │
│                 │  - Skill 索引 (按需加载)                   │  │
│                 │  - 已加载 Skill 内容                       │  │
│                 │  - 动作 Schema                             │  │
│                 └───────────────┬──────────────────────────┘  │
│                                 │                              │
│            ┌────────────────────┼────────────────────┐         │
│            ▼                    ▼                     ▼         │
│  ┌──────────────┐   ┌────────────────┐   ┌──────────────┐     │
│  │ load_skill   │   │ search_memory  │   │ 其他 GUI 动作 │     │
│  │ (按需加载)   │   │ (动态记忆检索) │   │              │     │
│  └──────────────┘   └────────────────┘   └──────────────┘     │
└───────────────────────────────────────────────────────────────┘
```

### 核心机制

**1. Skill 渐进式披露（Progressive Disclosure）**

为解决 Skill 文档全量加载导致 Token 浪费的问题，设计两阶段披露机制：

- **阶段一：Skill 索引** — 初始化时扫描 `skills/` 目录，解析每个 `SKILL.md` 的 YAML frontmatter，仅提取 `name` 和 `description`，构建轻量索引注入提示词
- **阶段二：按需加载** — Agent 根据索引判断需要某个 Skill 时，调用 `load_skill` 动作加载完整 `SKILL.md` 内容，存入 `self.loaded_skills` 字典，后续轮次自动注入

```python
# 索引示例（注入提示词）
- **launch_app**: Search and launch Windows applications via Start Menu
- **docx**: Create and edit .docx documents using LibreOffice
```

**2. 层次化记忆体系**

| 层级 | 名称 | 存储位置 | 生命周期 | 用途 |
|------|------|----------|----------|------|
| L1 | 静态长期记忆 | `agent/memory/CLAUDE.md` | 永久 | 用户指令、偏好、环境配置 |
| L2 | 动态长期记忆 | `mem0 + ChromaDB` | 永久 | 对话中检索到的用户偏好、历史经验 |
| L3 | 短期工作记忆 | `context_memory` 列表 | 单次任务 | 当前任务的步骤历史与思考摘要 |

- **L1 静态记忆**：直接读取文件内容，以最高优先级注入提示词
- **L2 动态记忆**：Agent 通过 `search_memory` 动作主动检索 mem0 向量数据库，检索结果经 `qa_llm` 精简后存入 `dynamic_memory` 字典，按类别组织注入提示词
- **L3 工作记忆**：每步的 `thought` + `step` 记录，通过 Self-Reflection 压缩视觉信息为文本

**3. 动态记忆检索流程**

```
Agent 判断需要历史信息
  → 调用 search_memory(category, query)
    → mem0.search() 向量检索 top-5
      → qa_llm 精简回答（去除冗余）
        → 结果存入 dynamic_memory[category]
          → 下一轮提示词注入
```

**4. 扩展提示词模板**

相比 `react_agent.py`，`skill_agent.py` 的 `_PROMPT_TEMPLATE` 新增三个变量：

```
## Dynamic Memory
{dynamic_memory}          ← L2 动态长期记忆

## Available Skills
{skill_index}             ← Skill 轻量索引

## Loaded Skill Instructions
{loaded_skill_content}    ← 已加载的完整 Skill 文档
```

---

## 三、多 Agent 协同 Shell — main.py

> 文件：`main.py`

### 架构

```
┌─────────────────────────────────────────────────────────┐
│                    对话 Shell (main.py)                  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │         意图路由 Agent (LangGraph)                │   │
│  │         model: gpt-6-luna                        │   │
│  │         checkpointer: InMemorySaver              │   │
│  │                                                   │   │
│  │  System Prompt:                                   │   │
│  │  - 偏好/配置 → add_memory                         │   │
│  │  - GUI 操作  → call_cua                           │   │
│  │  - 闲聊      → 直接回复                           │   │
│  │  - 混合意图  → 先 add_memory 再 call_cua          │   │
│  └──────────┬───────────────────────┬───────────────┘   │
│             │                       │                    │
│             ▼                       ▼                    │
│  ┌─────────────────┐    ┌────────────────────────┐      │
│  │  add_memory     │    │  call_cua              │      │
│  │  MemoryManager  │    │  CUASkillAgent         │      │
│  │  .add(category) │    │  .invoke(task)         │      │
│  └─────────────────┘    └────────────────────────┘      │
└─────────────────────────────────────────────────────────┘
```

### 核心机制

**1. 意图路由**

主对话 Agent 基于 System Prompt 中的决策规则，对用户输入进行意图分类：

| 意图类型 | 路由目标 | 示例 |
|----------|----------|------|
| 个人偏好 | `add_memory(category='preference')` | "我喜欢用 WPS Office" |
| 环境配置 | `add_memory(category='local_config')` | "我的文档在 D:\\Docs" |
| GUI 操作 | `call_cua(task)` | "打开 Chrome 搜索天气" |
| 混合意图 | 先 `add_memory` 再 `call_cua` | "记住我喜欢暗色主题，然后帮我把 Word 设为暗色" |
| 普通闲聊 | 直接回复 | "你好" |

**2. 状态管理 — LangGraph Checkpointer**

使用 `InMemorySaver` 作为 checkpointer，维护对话状态。同一 `thread_id` 下的多轮对话共享上下文，支持连续交互。

**3. 工具封装**

- `add_memory` — 封装 `MemoryManager.add()`，将用户偏好/配置写入 mem0 向量数据库，记忆管理委托 MemoryManger Agent 进行
- `call_cua` — 封装 `CUASkillAgent.invoke()`，将 GUI 任务委派给 Computer Use Agent

---

## 四、动作空间

共 **16 个动作**，分为以下类别：

| 类别 | 动作 |
|------|------|
| 鼠标操作 | `single_click`, `double_click`, `triple_click`, `right_click`, `move_to`, `drag_to`, `scroll` |
| 键盘操作 | `type_text`, `press_key`, `key_down`, `key_up`, `hot_key` |
| 截图 | `screenshot` |
| 剪贴板 | `copy_selected_text`, `paste_text` |
| 系统 | `switch_window`, `wait` |
| 控制流 | `finish`, `error_env`, `call_user`, `do_nothing` |
| Skill/记忆 | `run_script`, `search_memory`, `load_skill` |

所有动作的 Schema 以 OpenAI Tool 格式定义在 `action/base_action.py` 的函数文档字符串中，运行时由 `_get_action_schema()` 聚合为 JSON 注入提示词。 **调用方式本质上是 Function Call**

---

## 五、文件结构

```
ComputerUse/
├── agent/
│   ├── memory/
│   │   ├── CLAUDE.md              # 静态长期记忆（用户指令）
│   │   └── chroma_db/             # ChromaDB 向量存储
│   ├── base_agent.py              # Agent 基类 + execute_action
│   ├── react_agent.py             # 基础 ReAct Agent
│   └── skill_agent.py             # Skill Agent（渐进式披露 + 层次化记忆）
├── action/
│   └── base_action.py             # 动作定义 + ACTION_SCHEMA + ACTION_SPACE
├── skills/
│   ├── launch_app/                # 应用启动 Skill
│   ├── web_search_or_navigation/  # 网页搜索/导航 Skill
│   ├── docx/                      # Word 文档编辑 Skill
│   └── add_city_to_world_clock/   # 世界时钟 Skill
├── memory_manager.py              # mem0 记忆管理器
├── schema.py                      # CUAOutput, ContextMemoryEntry
├── settings.py                    # Pydantic Settings 配置
├── main.py                        # 多 Agent 协同对话 Shell
└── demo.py                        # 快速演示入口
```

---

## 六、模型配置

- 若使用 **GPT-5 / GPT-6** 系列模型，自动设置 `reasoning_effort = "low"`
- `CUAOutput` 通过 Function Call 结构化输出，保证动作选择的可靠性
- 记忆系统使用独立的 `qa_llm` 进行检索结果精简，与主推理模型解耦
