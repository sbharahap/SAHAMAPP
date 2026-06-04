import asyncio
from backend.data.collectors.makro_collector import _get_bi_rate_from_news

async def main():
    res = await _get_bi_rate_from_news()
    print("Result:", res)

if __name__ == "__main__":
    asyncio.run(main())
