// ─────────────────────────────────────────────────────────────
//  Services+StockDetail.swift

import Foundation

// MARK: - Response DTO

struct StockDetailDTO: Decodable {
    let symbol:               String
    let name:                 String?
    let sector:               String?
    let sentiment:            String          // "RECOMMENDED" | "NEUTRAL" | "NEGATIVE"
    let emitent_ai_summarize: String
    let price:                Double
    let change:               Double
    let pct_change:           Double
    let score:                Double?

    enum CodingKeys: String, CodingKey {
        case symbol = "kode_saham"
        case name = "nama_perusahaan"
        case sector = "sektor"
        case sentiment = "rekomendasi"
        case emitent_ai_summarize = "alasan"
        case price = "price"
        case change = "change"
        case pct_change = "pct_change"
        case score = "skor_total"
    }
}

// MARK: - Domain Model

struct StockDetail {
    let symbol:      String
    let name:        String?
    let sector:      String?
    let sentiment:   StockSentiment
    let aiSummary:   String
    let price:       Double
    let change:      Double
    let pctChange:   Double
    let score:       Double

    init(
        symbol: String,
        name: String?,
        sector: String?,
        sentiment: StockSentiment,
        aiSummary: String,
        price: Double,
        change: Double,
        pctChange: Double,
        score: Double = 50.0
    ) {
        self.symbol = symbol
        self.name = name
        self.sector = sector
        self.sentiment = sentiment
        self.aiSummary = aiSummary
        self.price = price
        self.change = change
        self.pctChange = pctChange
        self.score = score
    }
}

enum StockSentiment: String {
    case recommended = "Recommended"
    case neutral     = "Neutral"
    case caution     = "Caution"

    /// Label singkat untuk UI badge
    var label: String { rawValue }

    /// Warna sesuai palette SahamIndo
    var hexColor: String {
        switch self {
        case .recommended: return "22C55E"   // green-500
        case .neutral:     return "EAB308"   // yellow-500
        case .caution:     return "EF4444"   // red-500
        }
    }

    /// SF Symbol yang merepresentasikan kondisi
    var icon: String {
        switch self {
        case .recommended: return "arrow.up.circle.fill"
        case .neutral:     return "minus.circle.fill"
        case .caution:     return "exclamationmark.circle.fill"
        }
    }
}

// MARK: - Service Extension

extension RealStockService {

    /// GET /rekomendasi/saham/{symbol}
    /// Mengembalikan StockDetail lengkap termasuk sentiment dan AI summary.
    func fetchDetail(symbol: String) async throws -> StockDetail {
        let dto = try await APIClient.get(
            "/rekomendasi/saham/\(symbol)",
            as: StockDetailDTO.self
        )

        let mappedSentiment: StockSentiment
        switch dto.sentiment.uppercased() {
        case "RECOMMENDED", "BUY":
            mappedSentiment = .recommended
        case "NEGATIVE", "CAUTION", "SELL":
            mappedSentiment = .caution
        default:
            mappedSentiment = .neutral
        }

        return StockDetail(
            symbol:    dto.symbol,
            name:      dto.name,
            sector:    dto.sector,
            sentiment: mappedSentiment,
            aiSummary: dto.emitent_ai_summarize,
            price:     dto.price,
            change:    dto.change,
            pctChange: dto.pct_change,
            score:     dto.score ?? 50.0
        )
    }
}
