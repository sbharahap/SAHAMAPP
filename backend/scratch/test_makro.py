import asyncio
from backend.data.collectors.makro_collector import collect_makro

async def main():
    print("Testing collect_makro...")
    res = await collect_makro()
    print("Result:", res)

if __name__ == "__main__":
    asyncio.run(main())
