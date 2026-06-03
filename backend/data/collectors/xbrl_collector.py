"""
AI Saham Indonesia — IDX XBRL Financial Report Collector

Mengambil laporan keuangan resmi emiten dari IDX (Indonesia Stock Exchange) API,
mengunduh file ZIP XBRL (instance.zip), dan mengekstrak metrik keuangan utama:
- Total Aset
- Total Liabilitas
- Total Ekuitas
- Laba Bersih (Profit/Loss Attributable to Parent)
- EPS (Earnings Per Share)

Rasio yang dihitung:
- ROE (Return on Equity) = Laba Bersih / Total Ekuitas * 100
- DER (Debt to Equity) = Total Liabilitas / Total Ekuitas
"""

import asyncio
import io
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Dict
import httpx
from loguru import logger

# User Agent dan headers realistis untuk menghindari Cloudflare 403
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.idx.co.id/id/perusahaan-tercatat/laporan-keuangan-dan-tahunan",
    "Origin": "https://www.idx.co.id",
    "Connection": "keep-alive"
}

async def fetch_xbrl_file_url(kode_saham: str, year: int, period: str = "Audit") -> str | None:
    """
    Mencari URL download instance.zip dari API IDX untuk kode saham, tahun, dan periode tertentu.
    """
    url = "https://www.idx.co.id/primary/ListedCompany/GetFinancialReport"
    params = {
        "indexFrom": 0,
        "pageSize": 5,
        "kodeEmiten": kode_saham.upper(),
        "year": str(year),
        "periode": period,
        "reportType": "rdf"
    }
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, params=params, headers=_HEADERS)
            if response.status_code == 200:
                data = response.json()
                results = data.get("Results", [])
                if results:
                    attachments = results[0].get("Attachments", [])
                    # Cari instance.zip
                    instance_attachment = next((a for a in attachments if a.get("File_Name") == "instance.zip"), None)
                    if instance_attachment:
                        return instance_attachment["File_Path"]
            else:
                logger.warning(f"⚠️ GetFinancialReport HTTP {response.status_code} untuk {kode_saham} ({year})")
    except Exception as e:
        logger.error(f"❌ Gagal mengambil file URL laporan keuangan untuk {kode_saham}: {e}")
    
    return None

async def download_and_parse_xbrl(file_path: str) -> Dict[str, float] | None:
    """
    Mengunduh file zip dari path, mengekstrak file xbrl/xml di dalamnya,
    dan memparsing nilai-nilai laporan keuangan utama.
    """
    download_url = f"https://www.idx.co.id{file_path}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(download_url, headers=_HEADERS)
            if response.status_code != 200:
                logger.error(f"🚫 Gagal download zip dari {download_url}: HTTP {response.status_code}")
                return None
                
            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                # Cari file xbrl atau xml
                target_file = next((name for name in z.namelist() if name.endswith(".xbrl") or name.endswith(".xml")), None)
                if not target_file:
                    logger.warning(f"⚠️ Tidak ditemukan file .xbrl atau .xml di dalam {file_path}")
                    return None
                    
                xml_content = z.read(target_file)
                root = ET.fromstring(xml_content)
                
                # Variabel penampung nilai mentah
                assets = None
                liabilities = None
                equity = None
                net_profit = None
                eps = None
                
                # Context yang sah untuk data tahun berjalan (Instant untuk Balance Sheet, Duration untuk Income Statement)
                instant_contexts = {"CurrentYearInstant", "CurrentPeriodInstant"}
                duration_contexts = {"CurrentYearDuration", "CurrentPeriodDuration"}
                
                for elem in root.iter():
                    tag_name = elem.tag
                    local_name = tag_name.split("}")[-1] if "}" in tag_name else tag_name
                    context_ref = elem.get("contextRef")
                    
                    try:
                        val = float(elem.text) if elem.text else None
                    except (ValueError, TypeError):
                        val = None
                        
                    if val is None:
                        continue
                        
                    # 1. Total Assets
                    if local_name in ["Assets", "TotalAssets"] and context_ref in instant_contexts:
                        assets = val
                    # 2. Total Liabilities
                    elif local_name in ["Liabilities", "TotalLiabilities"] and context_ref in instant_contexts:
                        liabilities = val
                    # 3. Total Equity
                    elif local_name in ["Equity", "TotalEquity", "EquityPositionEndOfThePeriod"] and context_ref in instant_contexts:
                        equity = val
                    # 4. Net Profit (Laba Bersih yang diatribusikan ke pemilik entitas induk)
                    elif local_name == "ProfitLossAttributableToParentEntity" and context_ref in duration_contexts:
                        net_profit = val
                    elif local_name == "ProfitLoss" and context_ref in duration_contexts and net_profit is None:
                        net_profit = val
                    # 5. Earnings Per Share
                    elif local_name in ["BasicEarningsLossPerShareFromContinuingOperations", "BasicEarningsLossPerShare"] and context_ref in duration_contexts:
                        eps = val
                
                # Hitung rasio finansial
                roe = None
                der = None
                
                if net_profit is not None and equity is not None and equity != 0:
                    roe = (net_profit / equity) * 100.0
                    
                if liabilities is not None and equity is not None and equity != 0:
                    der = liabilities / equity
                    
                return {
                    "total_assets": assets,
                    "total_liabilities": liabilities,
                    "total_equity": equity,
                    "net_profit": net_profit,
                    "roe": round(roe, 2) if roe is not None else None,
                    "der": round(der, 2) if der is not None else None,
                    "eps": round(eps, 2) if eps is not None else None,
                }
    except Exception as e:
        logger.error(f"❌ Gagal memproses data XBRL untuk {file_path}: {e}")
        
    return None

async def collect_xbrl_fundamental(kode_saham: str, period: str = "Audit") -> Dict[str, Any] | None:
    """
    Mengambil data fundamental keuangan dari IDX XBRL.
    Memiliki mekanisme fallback tahun: jika tahun sekarang belum terbit,
    akan mundur ke 1 tahun lalu, dan maksimal 2 tahun lalu.
    """
    current_year = datetime.today().year
    kode_clean = kode_saham.strip().upper()
    
    # Cari di tahun berjalan, tahun lalu, atau 2 tahun lalu
    for year_offset in [0, 1, 2]:
        target_year = current_year - year_offset
        logger.info(f"🔍 Mencari laporan keuangan {kode_clean} untuk tahun {target_year}...")
        
        file_path = await fetch_xbrl_file_url(kode_clean, target_year, period)
        if file_path:
            logger.info(f"📥 Ditemukan file path: {file_path}. Mendownload dan memparsing...")
            parsed_data = await download_and_parse_xbrl(file_path)
            if parsed_data:
                parsed_data["kode_saham"] = kode_clean
                parsed_data["tahun"] = target_year
                parsed_data["periode"] = period
                logger.info(f"✅ Berhasil memproses XBRL {kode_clean} {target_year}: ROE={parsed_data['roe']}%, DER={parsed_data['der']}x, EPS={parsed_data['eps']}")
                return parsed_data
                
        # Delay kecil antar request pencarian tahun
        await asyncio.sleep(1.0)
        
    logger.warning(f"⚠️ Tidak ditemukan laporan keuangan XBRL untuk {kode_clean} dalam 3 tahun terakhir")
    return None

async def collect_xbrl_fundamental_batch(kode_saham_list: list[str], period: str = "Audit") -> list[dict[str, Any]]:
    """
    Mengambil data fundamental XBRL untuk daftar emiten secara berurutan dengan rate-limiting.
    """
    logger.info(f"📊 Mulai mengumpulkan data XBRL IDX untuk {len(kode_saham_list)} saham...")
    results = []
    
    for i, kode in enumerate(kode_saham_list):
        try:
            data = await collect_xbrl_fundamental(kode, period)
            if data:
                results.append(data)
        except Exception as e:
            logger.error(f"❌ Error batch XBRL untuk {kode}: {e}")
            
        # Rate limit delay
        if i < len(kode_saham_list) - 1:
            await asyncio.sleep(2.0)
            
    logger.info(f"📊 Selesai batch XBRL: {len(results)}/{len(kode_saham_list)} emiten berhasil.")
    return results
