import asyncio
import feedparser
import httpx
import re
import base64
from backend.data.collectors.berita_collector import _fetch_rss_feed, decode_google_news_url

async def main():
    url = "https://news.google.com/rss/search?q=saham+BBCA+IDX&hl=id&gl=ID&ceid=ID:id"
    entries = await _fetch_rss_feed(url)
    print("Entries count:", len(entries))
    for entry in entries[:5]:
        link = entry.get("link", "")
        print("\nOriginal link:", link)
        decoded = decode_google_news_url(link)
        print("Decoded link:", decoded)

if __name__ == "__main__":
    asyncio.run(main())
