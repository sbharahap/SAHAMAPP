//
//  Models.swift
//  SahamIndo
//

import SwiftUI

// MARK: - Stock Market Data

struct StockMarketData {
    let symbol:        String
    let name:          String?
    let logo:          String?
    let price:         Double
    let change:        Double
    let percentChange: Double
}

// MARK: - Holding (persisted)

struct Holding: Identifiable, Codable, Equatable {
    var id:             UUID   = UUID()
    var symbol:         String
    var quantity:       Double  // lembar
    var totalCostBasis: Double  // IDR

    init(id: UUID = UUID(), symbol: String, quantity: Double, totalCostBasis: Double) {
        self.id             = id
        self.symbol         = symbol
        self.quantity       = quantity
        self.totalCostBasis = totalCostBasis
    }
}

// MARK: - Portfolio Item (computed, tidak di-persist)

struct PortfolioItem: Identifiable, Hashable {
    let id            = UUID()
    let symbol:        String
    let name:          String?
    let logo:          String?
    let price:         Double
    let change:        Double
    let percentChange: Double
    let quantity:      Double
    let sentiment:     Sentiment

    var value: Double { price * quantity }
}

// MARK: - Sentiment

struct Sentiment: Hashable {
    let buy:  Double
    let hold: Double
    let sell: Double
    var score: Double

    init(buy: Double, hold: Double, sell: Double, score: Double = 50.0) {
        self.buy = buy
        self.hold = hold
        self.sell = sell
        self.score = score
    }

    var label: String {
        if score >= 70.0 { return "Recommended" }
        if score <= 40.0 { return "Caution" }
        return "Neutral"
    }

    var color: Color {
        switch label {
        case "Recommended": return Color(hex: "22C55E")
        case "Caution": return Color(hex: "EF4444")
        default:         return Color(hex: "EAB308")
        }
    }

    static func from(dbValue: String, score: Double = 50.0) -> Sentiment {
        switch dbValue.uppercased() {
        case "RECOMMENDED", "BUY": return Sentiment(buy: 0.65, hold: 0.25, sell: 0.10, score: score)
        case "CAUTION", "NEGATIVE", "SELL": return Sentiment(buy: 0.15, hold: 0.25, sell: 0.60, score: score)
        default:            return Sentiment(buy: 0.35, hold: 0.40, sell: 0.25, score: score)
        }
    }
}

// MARK: - Chart Data Point

struct StockDataPoint: Identifiable, Equatable {
    let id     = UUID()
    let date:   Date
    let close:  Double
    let open:   Double
    let high:   Double
    let low:    Double
    let volume: Double
}

// MARK: - Stock Alert (persisted notification)

struct StockAlert: Identifiable, Codable {
    var id:        UUID         = UUID()
    var date:      Date
    var symbol:    String
    var stockName: String?
    var sector:    String?
    var alertType: AlertType
    var score:     Double
    var aiSummary: String
    var isRead:    Bool         = false

    enum AlertType: String, Codable {
        case strongBuy  = "strongBuy"
        case strongSell = "strongSell"
    }
}

// MARK: - Portfolio Value Point (chart history)

struct PortfolioValuePoint: Identifiable {
    let id    = UUID()
    let date:  Date
    let value: Double   // IDR
}

// MARK: - Time Range

enum TimeRange: String, CaseIterable {
    case oneDay     = "1D"
    case oneWeek    = "1W"
    case oneMonth   = "1M"
    case threeMonth = "3M"
    case ytd        = "YTD"
    case oneYear    = "1Y"
    case fiveYear   = "5Y"

    var isIntraday: Bool {
        self == .oneDay || self == .oneWeek
    }

    // MARK: - X-axis spacing exponent (Data Morphing effect)
    var xSpacingExponent: CGFloat {
        switch self {
        case .oneDay:     return 1.0
        case .oneWeek:    return 1.0
        case .oneMonth:   return 0.88
        case .threeMonth: return 0.78
        case .ytd:        return 0.72
        case .oneYear:    return 0.65
        case .fiveYear:   return 0.55
        }
    }
    
}
