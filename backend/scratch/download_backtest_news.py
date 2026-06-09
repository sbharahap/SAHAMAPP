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
    "BBCA", "BBRI", "BMRI", "BBNI", "TLKM", "ASII", "UNVR", "ADRO", "GGRM", "KLBF",
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
    print("📰 DOWNLOAD & SENTIMENT ANALYSIS BERITA UNTUK LIVE (SEMINGGU TERAKHIR)")
    print("=" * 60)
    
    out_dir = "/Users/satriabaladewaharahap/Downloads/SAHAMAPP/backend/scratch"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "backtest_news.json")
    
    # Load checkpoint data if exists
    news_db = {}
    if os.path.exists(out_path):
        try:
            with open(out_path, "r") as f:
                news_db = json.load(f)
            
            # Cek apakah file ini berisi data historis (misal 2022-2025)
            is_historical = False
            for ticker, articles in news_db.items():
                if isinstance(articles, list):
                    for art in articles:
                        tp = art.get("tanggal_publish", "")
                        # Jika tanggal artikel sebelum Mei 2026, itu adalah data historis
                        if tp and tp < "2026-05-01":
                            is_historical = True
                            break
                if is_historical:
                    break
            
            if is_historical:
                backup_path = os.path.join(out_dir, "backtest_news_historical.json")
                print(f"📦 Terdeteksi data historis lama (2022-2025). Mengubah nama ke {backup_path}...")
                os.rename(out_path, backup_path)
                news_db = {}
            else:
                print(f"🔄 Checkpoint ditemukan. Memuat data untuk {len(news_db.keys())} emiten.")
        except Exception as e:
            print(f"⚠️ Gagal membaca checkpoint: {e}. Mengulang dari awal.")
            news_db = {}
            
    for i, kode in enumerate(SAHAM_LIST_20):
        # RESUME CHECK: Lewati jika emiten sudah berhasil di-scrape sebelumnya
        if kode in news_db and isinstance(news_db[kode], list) and len(news_db[kode]) > 0:
            print(f"\n({i+1}/{len(SAHAM_LIST_20)}) ⏩ {kode} sudah ada di database ({len(news_db[kode])} artikel). Lewati.")
            continue
            
        print(f"\n({i+1}/{len(SAHAM_LIST_20)}) 🔍 Fetching news for {kode} (last 7 days)...")
        news_db[kode] = []
        
        # Query untuk 7 hari terakhir menggunakan when:7d
        query = f"{kode} when:7d"
        encoded_query = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={encoded_query}&hl=id&gl=ID&ceid=ID:id"
        
        try:
            r = httpx.get(url, headers={"User-Agent": "Mozilla/5.0"}, follow_redirects=True, timeout=20)
            if r.status_code == 200:
                root = ET.fromstring(r.text)
                items = root.findall(".//item")
                print(f"   - Found {len(items)} news articles.")
                
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
                print(f"   - ❌ Failed to fetch. HTTP Status: {r.status_code}")
        except Exception as e:
            print(f"   - ❌ Error: {e}")
            
        # Delay minimal agar tidak di-ban Google
        time.sleep(1.2)
            
        print(f"   Total news articles for {kode} (last 7 days): {len(news_db[kode])}")
        
        # SAVE CHECKPOINT: Simpan berkala setiap selesai satu emiten
        try:
            with open(out_path, "w") as f:
                json.dump(news_db, f, indent=2)
            print(f"   💾 Checkpoint tersimpan untuk {kode} ke {out_path}.")
        except Exception as e:
            print(f"   ⚠️ Gagal menyimpan checkpoint untuk {kode}: {e}")
        
    print("\n✅ DOWNLOAD & ANALISIS SENTIMENT SELESAI DENGAN SUKSES!")

if __name__ == "__main__":
    main()
