from mem0 import Memory
import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

MEM0_CONFIG = {
    "vector_store": {
        "provider": "chroma",
        "config": {
            "collection_name": "latency_test_chroma",
            "path": "agent/memory/chroma_db"
        },
    },
    "llm": {
        "provider": "openai",
        "config": {
            "model": "qwen-plus",
            "openai_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "api_key": os.environ["DASHSCOPE_API_KEY"],
            "temperature": 0,
            "max_tokens": 2000,
        },
    },
    "embedder": {
        "provider": "openai",
        "config": {
            "model": "text-embedding-v4",
            "openai_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "api_key": os.environ["DASHSCOPE_API_KEY"],
        },
    },
    "history_db_path": "agent/memory/mem0_history_chroma.db",
}

class MemoryManager:
    def __init__(self):
        self.memory = Memory.from_config(MEM0_CONFIG)
        self.qa_llm = ChatOpenAI(model='gpt-6-luna')
        self.qa_llm.reasoning_effort = 'low'

    def add(self, category, content, agent_id='cua'):
        messages = [
            {"role": "user", "content": content}
        ]

        response = self.memory.add(messages,  agent_id=agent_id, metadata={"category": category})
        results = response.get("results", [])
        return results

    def search(self, category, query, agent_id='cua') -> str:
        response = self.memory.search(
            query,
            filters={"category": category, "agent_id": agent_id},
            top_k=5
        )

        results = response.get("results", [])

        if not results:
            return "No relevant memory found."

        # Extract memory text from results
        memories = []
        for r in results:
            mem_text = r.get("memory", r.get("id", ""))
            if mem_text:
                memories.append(mem_text)

        context = "\n".join(f"- {m}" for m in memories)

        # Use qa_llm to produce a concise answer

        answer = self.qa_llm.invoke([
            SystemMessage(content=(
                "You are a memory retrieval assistant. You will be given "
                "retrieved memory entries and a query. Answer the query "
                "using ONLY the information from the memory entries. "
                "Be extremely concise and direct — return only the answer, "
                "no explanations, no extra words. If the memory entries "
                "do not contain relevant information, reply: "
                "\"No relevant memory found.\""
            )),
            HumanMessage(content=(
                f"## Retrieved Memories\n{context}\n\n"
                f"## Query\n{query}"
            )),
        ])

        return answer.content

memory_manager = MemoryManager()


