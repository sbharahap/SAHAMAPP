//
//  StockCache.swift
//  SahamIndo
//
//  Layer cache UserDefaults untuk data saham & candle.
//  Dipakai otomatis oleh Services.swift saat baseURL offline.
//
//  Arsitektur:
//  ┌─────────────────────────────────────────────────────┐
//  │  RealStockService / RealChartService                │
//  │  1. Coba hit API                                    │
//  │  2. Berhasil → simpan ke cache → return data        │
//  │  3. Gagal    → baca cache     → return data (stale) │
//  └─────────────────────────────────────────────────────┘
//
//  Tidak ada perubahan ke Model, Router, atau View.
//

import Foundation

// ─────────────────────────────────────────────────────────────
// MARK: - Cache Keys
// ─────────────────────────────────────────────────────────────

private enum CacheKey {
    /// Semua saham: JSON [StockSummaryCache]
    static let allStocks = "cache_all_stocks_v1"

    /// Candle per saham per range: "cache_candles_BBCA_1D_v1"
    static func candles(symbol: String, range: String) -> String {
        "cache_candles_\(symbol)_\(range)_v1"
    }

    /// Timestamp cache terakhir (Double / timeIntervalSince1970)
    static let allStocksTimestamp = "cache_all_stocks_ts_v1"
    static func candlesTimestamp(symbol: String, range: String) -> String {
        "cache_candles_\(symbol)_\(range)_ts_v1"
    }
}

// ─────────────────────────────────────────────────────────────
// MARK: - Codable wrappers (internal, tidak expose ke luar)
// ─────────────────────────────────────────────────────────────

private struct StockSummaryCache: Codable {
    let symbol:     String
    let name:       String?
    let price:      Double
    let change:     Double
    let pctChange:  Double
}

private struct CandleCache: Codable {
    let ts:     Date
    let open:   Double
    let high:   Double
    let low:    Double
    let close:  Double
    let volume: Double
}

// ─────────────────────────────────────────────────────────────
// MARK: - StockCacheManager
// ─────────────────────────────────────────────────────────────

/// Singleton sederhana. Semua operasi sinkron (UserDefaults sudah thread-safe
/// untuk read/write nilai primitif & Data).
final class StockCacheManager {

    static let shared = StockCacheManager()
    private init() {}

    // Berapa lama cache dianggap "segar" (bukan stale) — untuk info UI saja.
    // Kita tetap pakai cache lama kalau API mati, berapa pun umurnya.
    private let freshnessInterval: TimeInterval = 5 * 60   // 5 menit

    private let defaults = UserDefaults.standard

    // MARK: - All Stocks

    func saveAllStocks(_ data: [StockMarketData]) {
        let list = data.map {
            StockSummaryCache(
                symbol:    $0.symbol,
                name:      $0.name,
                price:     $0.price,
                change:    $0.change,
                pctChange: $0.percentChange
            )
        }
        guard let encoded = try? JSONEncoder().encode(list) else { return }
        defaults.set(encoded, forKey: CacheKey.allStocks)
        defaults.set(Date().timeIntervalSince1970, forKey: CacheKey.allStocksTimestamp)
    }

    func loadAllStocks() -> (data: [StockMarketData], isStale: Bool)? {
        guard
            let raw     = defaults.data(forKey: CacheKey.allStocks),
            let list    = try? JSONDecoder().decode([StockSummaryCache].self, from: raw)
        else { return nil }

        let ts    = defaults.double(forKey: CacheKey.allStocksTimestamp)
        let age   = Date().timeIntervalSince1970 - ts
        let stale = age > freshnessInterval

        let result = list.map {
            StockMarketData(
                symbol:        $0.symbol,
                name:          $0.name,
                logo:          nil,
                price:         $0.price,
                change:        $0.change,
                percentChange: $0.pctChange
            )
        }
        return (result, stale)
    }

    // MARK: - Candles

    func saveCandles(_ points: [StockDataPoint], symbol: String, range: TimeRange) {
        let list = points.map {
            CandleCache(
                ts:     $0.date,
                open:   $0.open,
                high:   $0.high,
                low:    $0.low,
                close:  $0.close,
                volume: $0.volume
            )
        }
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .secondsSince1970
        guard let encoded = try? encoder.encode(list) else { return }

        let key    = CacheKey.candles(symbol: symbol, range: range.rawValue)
        let tsKey  = CacheKey.candlesTimestamp(symbol: symbol, range: range.rawValue)
        defaults.set(encoded, forKey: key)
        defaults.set(Date().timeIntervalSince1970, forKey: tsKey)
    }

    func loadCandles(symbol: String, range: TimeRange) -> (data: [StockDataPoint], isStale: Bool)? {
        let key = CacheKey.candles(symbol: symbol, range: range.rawValue)
        guard let raw = defaults.data(forKey: key) else { return nil }

        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .secondsSince1970
        guard let list = try? decoder.decode([CandleCache].self, from: raw) else { return nil }

        let tsKey = CacheKey.candlesTimestamp(symbol: symbol, range: range.rawValue)
        let ts    = defaults.double(forKey: tsKey)
        let age   = Date().timeIntervalSince1970 - ts
        let stale = age > freshnessInterval

        let result = list.map {
            StockDataPoint(
                date:   $0.ts,
                close:  $0.close,
                open:   $0.open,
                high:   $0.high,
                low:    $0.low,
                volume: $0.volume
            )
        }
        return (result, stale)
    }

    // MARK: - Cache Age Helper

    /// Kembalikan string seperti "3 menit lalu" untuk ditampilkan di UI.
    func cacheAgeString(symbol: String? = nil, range: TimeRange? = nil) -> String? {
        let ts: Double
        if let sym = symbol, let rng = range {
            ts = defaults.double(forKey: CacheKey.candlesTimestamp(symbol: sym, range: rng.rawValue))
        } else {
            ts = defaults.double(forKey: CacheKey.allStocksTimestamp)
        }
        guard ts > 0 else { return nil }

        let age = Int(Date().timeIntervalSince1970 - ts)
        if age < 60    { return "\(age) detik lalu" }
        if age < 3600  { return "\(age / 60) menit lalu" }
        if age < 86400 { return "\(age / 3600) jam lalu" }
        return "\(age / 86400) hari lalu"
    }

    // MARK: - Clear Cache

    func clearAllCache() {
        let keys = defaults.dictionaryRepresentation().keys.filter {
            $0.hasPrefix("cache_")
        }
        keys.forEach { defaults.removeObject(forKey: $0) }
    }
}

// ─────────────────────────────────────────────────────────────
// MARK: - CacheState (untuk UI feedback)
// ─────────────────────────────────────────────────────────────

enum CacheState: Equatable {
    case live               // data langsung dari API
    case cached(age: String)  // data dari cache, tampilkan usia
    case noData             // tidak ada data sama sekali (API mati + cache kosong)
}

// ─────────────────────────────────────────────────────────────
// MARK: - RealStockService + Cache  (tambah ke Services.swift)
// ─────────────────────────────────────────────────────────────
//
// Ganti implementasi fetchAllStocks() & fetchStock() di Services.swift
// dengan versi di bawah ini, atau salin ekstensi ini ke Services.swift.
//

extension RealStockService {

    /// Fetch semua saham; simpan ke cache jika berhasil; baca cache jika gagal.
    /// Returns: (data, cacheState)
    func fetchAllStocksCached() async -> (data: [StockMarketData], state: CacheState) {
        do {
            // 1. Coba API
            let data = try await fetchAllStocks()
            // 2. Simpan ke cache
            StockCacheManager.shared.saveAllStocks(data)
            return (data, .live)
        } catch {
            print("[RealStockService] offline, membaca cache:", error.localizedDescription)
            // 3. Baca cache
            if let cached = StockCacheManager.shared.loadAllStocks() {
                let age = StockCacheManager.shared.cacheAgeString() ?? "?"
                return (cached.data, .cached(age: age))
            }
            return ([], .noData)
        }
    }
}

// ─────────────────────────────────────────────────────────────
// MARK: - RealChartService + Cache
// ─────────────────────────────────────────────────────────────

extension RealChartService {

    /// Fetch candle; simpan ke cache jika berhasil; baca cache jika gagal.
    func fetchCandlesCached(symbol: String, range: TimeRange) async -> (data: [StockDataPoint], state: CacheState) {
        do {
            // 1. Coba API
            let data = try await fetchCandles(symbol: symbol, range: range)
            // 2. Simpan ke cache
            StockCacheManager.shared.saveCandles(data, symbol: symbol, range: range)
            return (data, .live)
        } catch {
            print("[RealChartService] offline (\(symbol)/\(range.rawValue)), membaca cache:", error.localizedDescription)
            // 3. Baca cache
            if let cached = StockCacheManager.shared.loadCandles(symbol: symbol, range: range) {
                let age = StockCacheManager.shared.cacheAgeString(symbol: symbol, range: range) ?? "?"
                return (cached.data, .cached(age: age))
            }
            // 4. Fallback ke dummy generator (sudah ada di IDXDummyPriceGenerator)
            let dummy = IDXDummyPriceGenerator.generate(symbol: symbol, range: range)
            return (dummy, .noData)
        }
    }
}

