import httpx
import urllib.parse
import xml.etree.ElementTree as ET
import json
import os
import time
from datetime import datetime
from email.utils import parsedate_to_datetime

from backend.data.preprocessors.data_cleaner import hitung_sentimen_sederhana

SAHAM_LIST_20 = [
    "BBCA", "BBRI", "BMRI", "BBNI", "TLKM", "ASII", "UNVR", "ADRO", "GOTO", "KLBF",
    "ANTM", "PGAS", "UNTR", "PTBA", "MEDC", "BRIS", "AMRT", "MDKA", "ICBP", "INDF"
]

def parse_pubdate(pubdate_str):
    try:
        dt = parsedate_to_datetime(pubdate_str)
        return dt.isoformat()
    except Exception:
        return pubdate_str

def main():
    print("=" * 60)
    print("📰 DOWNLOAD & SENTIMENT ANALYSIS BERITA UNTUK BACKTEST (2022 - 2025)")
    print("=" * 60)
    
    news_db = {}
    years = [2022, 2023, 2024, 2025]
    
    for i, kode in enumerate(SAHAM_LIST_20):
        print(f"\n({i+1}/{len(SAHAM_LIST_20)}) 🔍 Fetching news for {kode}...")
        news_db[kode] = []
        
        for year in years:
            # Query per tahun agar mendapatkan max 100 per tahun (total max 400 per saham)
            query = f"{kode} before:{year}-12-31 after:{year}-01-01"
            encoded_query = urllib.parse.quote(query)
            url = f"https://news.google.com/rss/search?q={encoded_query}&hl=id&gl=ID&ceid=ID:id"
            
            try:
                r = httpx.get(url, headers={"User-Agent": "Mozilla/5.0"}, follow_redirects=True, timeout=20)
                if r.status_code == 200:
                    root = ET.fromstring(r.text)
                    items = root.findall(".//item")
                    print(f"   - Year {year}: Found {len(items)} news articles.")
                    
                    for item in items:
                        title = item.find("title").text
                        link = item.find("link").text
                        pub_date_raw = item.find("pubDate").text
                        pub_date = parse_pubdate(pub_date_raw)
                        
                        skor = hitung_sentimen_sederhana(title)
                        
                        news_db[kode].append({
                            "judul": title,
                            "url": link,
                            "tanggal_publish": pub_date,
                            "skor_sentimen": skor
                        })
                else:
                    print(f"   - Year {year}: ❌ Failed to fetch. HTTP Status: {r.status_code}")
            except Exception as e:
                print(f"   - Year {year}: ❌ Error: {e}")
                
            # Delay minimal agar tidak di-ban Google
            time.sleep(1.2)
            
        print(f"   Total news articles for {kode} (2022-2025): {len(news_db[kode])}")
        
    out_dir = "/Users/satriabaladewaharahap/Downloads/SAHAMAPP/backend/scratch"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "backtest_news.json")
    
    print(f"\n💾 Menyimpan data berita ke {out_path}...")
    with open(out_path, "w") as f:
        json.dump(news_db, f, indent=2)
        
    print("✅ DOWNLOAD & ANALISIS SENTIMENT SELESAI DENGAN SUKSES!")

if __name__ == "__main__":
    main()
