//
//  Services.swift
//  SahamIndo
//

import Foundation

// MARK: - Stock Service Protocol

protocol StockServiceProtocol {
    func fetchStock(symbol: String) async throws -> StockMarketData
}

// ─────────────────────────────────────────────────────────────
// MARK: - API Client
// ─────────────────────────────────────────────────────────────

struct APIClient {

    // Cache the verified URL once resolved
    private static var verifiedBaseURL: String? = nil

    static func getBaseURL() async -> String {
        if let verified = verifiedBaseURL {
            return verified
        }
        
        let candidates = [
            "http://100.121.215.111:8080",
            "http://100.118.29.16:8080",
            "http://100.70.203.11:8080",
        ]
        
        let resolved = await withTaskGroup(of: String?.self, returning: String?.self) { group in
            for candidate in candidates {
                group.addTask {
                    guard let url = URL(string: "\(candidate)/api/status") else { return nil }
                    var request = URLRequest(url: url)
                    request.timeoutInterval = 1.0 // fast timeout
                    do {
                        let (_, response) = try await URLSession.shared.data(for: request)
                        if let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode) {
                            return candidate
                        }
                    } catch {}
                    return nil
                }
            }
            for await res in group {
                if let url = res {
                    group.cancelAll()
                    return url
                }
            }
            return nil
        }
        
        //let finalBase = resolved ?? "http://MacBook-Pro-Satria.local:8080"
        let finalBase = resolved ?? "http://10.67.51.0:8080"

        verifiedBaseURL = finalBase
        print("[APIClient] Resolved baseURL: \(finalBase)")
        return finalBase
    }

    enum APIError: Error, LocalizedError {
        case invalidURL
        case httpError(Int)
        case decodingError(Error)

        var errorDescription: String? {
            switch self {
            case .invalidURL:             return "URL tidak valid"
            case .httpError(let code):    return "HTTP error: \(code)"
            case .decodingError(let e):   return "Decode error: \(e.localizedDescription)"
            }
        }
    }

    /// JSONDecoder dengan multi-format date strategy.
    /// Mencoba beberapa format secara berurutan karena
    /// FastAPI/PostgreSQL bisa kembalikan berbagai bentuk timestamp.
    static var decoder: JSONDecoder {
        let d = JSONDecoder()

        // 1. ISO8601 dengan fractional seconds: "2026-06-06T09:00:00.000000+07:00"
        let isoFrac = ISO8601DateFormatter()
        isoFrac.formatOptions = [.withInternetDateTime, .withFractionalSeconds]

        // 2. ISO8601 tanpa fractional: "2026-06-06T09:00:00+07:00"
        let isoPlain = ISO8601DateFormatter()
        isoPlain.formatOptions = [.withInternetDateTime]

        // 3. Format PostgreSQL tanpa timezone: "2026-06-06T09:00:00"
        let dfJKT = DateFormatter()
        dfJKT.locale     = Locale(identifier: "en_US_POSIX")
        dfJKT.timeZone   = TimeZone(identifier: "Asia/Jakarta")
        dfJKT.dateFormat = "yyyy-MM-dd'T'HH:mm:ss"

        // 4. Sama tapi dengan titik desimal: "2026-06-06T09:00:00.000000"
        let dfJKTFrac = DateFormatter()
        dfJKTFrac.locale     = Locale(identifier: "en_US_POSIX")
        dfJKTFrac.timeZone   = TimeZone(identifier: "Asia/Jakarta")
        dfJKTFrac.dateFormat = "yyyy-MM-dd'T'HH:mm:ss.SSSSSS"

        d.dateDecodingStrategy = .custom { decoder in
            let container = try decoder.singleValueContainer()
            let str       = try container.decode(String.self)

            if let date = isoFrac.date(from: str)    { return date }
            if let date = isoPlain.date(from: str)   { return date }
            if let date = dfJKTFrac.date(from: str)  { return date }
            if let date = dfJKT.date(from: str)      { return date }

            throw DecodingError.dataCorruptedError(
                in: container,
                debugDescription: "Cannot parse date string: \(str)"
            )
        }

        return d
    }

    static func get<T: Decodable>(_ path: String, as type: T.Type) async throws -> T {
        let base = await getBaseURL()
        guard let url = URL(string: base + path) else { throw APIError.invalidURL }

        let (data, response) = try await URLSession.shared.data(from: url)

        if let http = response as? HTTPURLResponse, !(200...299).contains(http.statusCode) {
            throw APIError.httpError(http.statusCode)
        }

        do {
            return try decoder.decode(T.self, from: data)
        } catch {
            // Print raw response untuk bantu debug
            if let raw = String(data: data, encoding: .utf8) {
                print("[APIClient] Raw response (300 char):", raw.prefix(300))
            }
            throw APIError.decodingError(error)
        }
    }

    static func sendChatMessageStream(pertanyaan: String, riwayat: [ChatHistoryItem]) async throws -> AsyncThrowingStream<String, Error> {
        let base = await getBaseURL()
        guard let url = URL(string: "\(base)/chat") else {
            throw APIError.invalidURL
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.timeoutInterval = 240.0
        
        let payload = ChatPayload(pertanyaan: pertanyaan, riwayat: riwayat)
        request.httpBody = try JSONEncoder().encode(payload)
        
        let (bytes, response) = try await URLSession.shared.bytes(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse, (200...299).contains(httpResponse.statusCode) else {
            throw APIError.httpError((response as? HTTPURLResponse)?.statusCode ?? 500)
        }
        
        return AsyncThrowingStream { continuation in
            Task {
                do {
                    var buffer = Data()
                    var iterator = bytes.makeAsyncIterator()
                    
                    while let byte = try await iterator.next() {
                        buffer.append(byte)
                        if let decodedString = String(data: buffer, encoding: .utf8) {
                            continuation.yield(decodedString)
                            buffer.removeAll()
                        }
                    }
                    continuation.finish()
                } catch {
                    continuation.finish(throwing: error)
                }
            }
        }
    }
}

// ─────────────────────────────────────────────────────────────
// MARK: - Response DTOs
// ─────────────────────────────────────────────────────────────

private struct StockSummaryDTO: Decodable {
    let symbol:     String
    let name:       String?
    let price:      Double
    let change:     Double
    let pct_change: Double
}

struct CandleDTO: Decodable {
    let ts:     Date
    let open:   Double?
    let high:   Double?
    let low:    Double?
    let close:  Double
    let volume: Int
}

struct AlertDTO: Decodable {
    let id: Int
    let kode_saham: String
    let pesan: String
    let delta: Double
    let tanggal: String
}

struct MakroIndicatorDTO: Decodable {
    let nilai: Double
    let satuan: String
    let tanggal: String
    let sumber: String?
}

struct MakroResponseDTO: Decodable {
    let tanggal_fetch: String
    let indikator: [String: MakroIndicatorDTO]
}

struct RekomendasiItemDTO: Decodable {
    let rank: Int
    let kode_saham: String
    let nama_perusahaan: String?
    let sektor: String?
    let rekomendasi: String
    let alasan: String?
}

struct RekomendasiResponseDTO: Decodable {
    let tanggal: String?
    let rekomendasi: [RekomendasiItemDTO]
}

struct AIMarketInsightDTO: Decodable {
    let text: String
    let updatedAt: String?

    enum CodingKeys: String, CodingKey {
        case text
        case updatedAt = "updated_at"
    }
}

// ─────────────────────────────────────────────────────────────
// MARK: - Real Stock Service
// ─────────────────────────────────────────────────────────────

final class RealStockService: StockServiceProtocol {

    func fetchStock(symbol: String) async throws -> StockMarketData {
        let dto = try await APIClient.get("/stocks/\(symbol)", as: StockSummaryDTO.self)
        return StockMarketData(
            symbol:        dto.symbol,
            name:          dto.name,
            logo:          nil,
            price:         dto.price,
            change:        dto.change,
            percentChange: dto.pct_change
        )
    }

    func fetchAllStocks() async throws -> [StockMarketData] {
        let dtos = try await APIClient.get("/stocks", as: [StockSummaryDTO].self)
        return dtos.map {
            StockMarketData(
                symbol:        $0.symbol,
                name:          $0.name,
                logo:          nil,
                price:         $0.price,
                change:        $0.change,
                percentChange: $0.pct_change
            )
        }
    }

    func fetchAlerts() async throws -> [AlertDTO] {
        return try await APIClient.get("/alerts", as: [AlertDTO].self)
    }

    func fetchMakro() async throws -> MakroResponseDTO {
        return try await APIClient.get("/makro/terbaru", as: MakroResponseDTO.self)
    }

    func fetchRekomendasiMingguan() async throws -> RekomendasiResponseDTO {
        return try await APIClient.get("/rekomendasi/mingguan", as: RekomendasiResponseDTO.self)
    }

    func fetchSentimenBeritaInsight() async throws -> AIMarketInsightDTO {
        return try await APIClient.get("/ai/insights/sentimen-berita", as: AIMarketInsightDTO.self)
    }

    func fetchAsingNetBuyInsight() async throws -> AIMarketInsightDTO {
        return try await APIClient.get("/ai/insights/asing-net-buy", as: AIMarketInsightDTO.self)
    }

    func fetchMakroIDRInsight() async throws -> AIMarketInsightDTO {
        return try await APIClient.get("/ai/insights/makro-idr", as: AIMarketInsightDTO.self)
    }
}

// ─────────────────────────────────────────────────────────────
// MARK: - Real Chart Service
// ─────────────────────────────────────────────────────────────

final class RealChartService {

    func fetchCandles(symbol: String, range: TimeRange) async throws -> [StockDataPoint] {
        let dtos = try await APIClient.get(
            "/stocks/\(symbol)/candles?range=\(range.rawValue)",
            as: [CandleDTO].self
        )
        return dtos.map {
            StockDataPoint(
                date:   $0.ts,
                close:  $0.close,
                open:   $0.open  ?? $0.close,
                high:   $0.high  ?? $0.close,
                low:    $0.low   ?? $0.close,
                volume: Double($0.volume)
            )
        }
    }
}

// ─────────────────────────────────────────────────────────────
// MARK: - Dummy Stock Service (fallback / preview)
// ─────────────────────────────────────────────────────────────

final class DummyStockService: StockServiceProtocol {

    private let data: [String: (price: Double, change: Double, pct: Double, name: String)] = [
        "BREN": (5_025,   +50,  +1.01, "Barito Renewables Energy"),
        "BBCA": (9_950,   -25,  -0.25, "Bank Central Asia"),
        "DSSA": (55_750, +750,  +1.36, "Dian Swastatika Sentosa"),
        "BBRI": (4_150,   -40,  -0.95, "Bank Rakyat Indonesia"),
        "TPIA": (8_650,  +150,  +1.76, "Chandra Asri Pacific"),
        "AMMN": (9_200,  +100,  +1.10, "Amman Mineral Internasional"),
        "BYAN": (18_500, +250,  +1.37, "Bayan Resources"),
        "DCII": (43_000, -500,  -1.15, "DCI Indonesia"),
        "BMRI": (5_675,   +75,  +1.34, "Bank Mandiri"),
        "TLKM": (3_020,   -30,  -0.98, "Telkom Indonesia"),
    ]

    func fetchStock(symbol: String) async throws -> StockMarketData {
        try await Task.sleep(nanoseconds: 50_000_000)
        if let d = data[symbol] {
            return StockMarketData(symbol: symbol, name: d.name, logo: nil,
                                   price: d.price, change: d.change, percentChange: d.pct)
        }
        return StockMarketData(symbol: symbol, name: symbol, logo: nil,
                               price: 1_000, change: 0, percentChange: 0)
    }
}
