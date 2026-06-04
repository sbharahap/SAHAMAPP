import asyncio
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
import time

async def run_test(model_name):
    print(f"\n--- Testing model: {model_name} ---")
    llm = ChatOllama(
        model=model_name,
        base_url="http://localhost:11434",
        temperature=0.0,
        timeout=30
    )
    messages = [
        SystemMessage(content="You are a helpful assistant."),
        HumanMessage(content="Reply with exactly 'Hello World'")
    ]
    try:
        print("Sending message...")
        start_time = time.time()
        response = await llm.ainvoke(messages)
        elapsed = time.time() - start_time
        print(f"Success! Elapsed: {elapsed:.2f}s")
        print("Response:", response.content)
    except Exception as e:
        print("Error:", e)

async def main():
    await run_test("gemma3:1b")
    await run_test("qwen2.5:3b")
    await run_test("qwen3:8b")

if __name__ == "__main__":
    asyncio.run(main())
