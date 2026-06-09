//
//  SentimentPill.swift

import SwiftUI

// MARK: - SentimentPill

struct SentimentPill: View {

    enum Size {
        case regular   // default — dipakai di StockDetailHeaderView, AIInsightCard
        case small     // dipakai di StockRowView (list item)

        var fontSize:   CGFloat { self == .small ? 9  : 11 }
        var iconSize:   CGFloat { self == .small ? 9  : 11 }
        var hPadding:   CGFloat { self == .small ? 6  : 10 }
        var vPadding:   CGFloat { self == .small ? 2  : 5  }
        var spacing:    CGFloat { self == .small ? 3  : 5  }
    }

    // ── Internal representation ───────────────────────────────
    private let label:    String
    private let hexColor: String
    private let icon:     String
    private let size:     Size

    // MARK: Init — StockSentiment  (dari Services+StockDetail, dipakai di AIInsightCard)
    init(stockSentiment: StockSentiment, size: Size = .regular) {
        self.label    = stockSentiment.label
        self.hexColor = stockSentiment.hexColor
        self.icon     = stockSentiment.icon
        self.size     = size
    }

    // MARK: Init — Sentiment  (dari Models.swift, dipakai di HomeView / StockDetailHeaderView)
    init(sentiment: Sentiment, size: Size = .regular) {
        switch sentiment.label {
        case "Recommended":
            self.label    = "Recommended"
            self.hexColor = "22C55E"
            self.icon     = "arrow.up.circle.fill"
        case "Caution":
            self.label    = "Caution"
            self.hexColor = "EF4444"
            self.icon     = "exclamationmark.circle.fill"
        default:
            self.label    = "Neutral"
            self.hexColor = "EAB308"
            self.icon     = "minus.circle.fill"
        }
        self.size = size
    }

    // MARK: Body

    var body: some View {
        HStack(spacing: size.spacing) {
            Image(systemName: icon)
                .font(.system(size: size.iconSize, weight: .semibold))
            Text(label)
                .font(.system(size: size.fontSize, weight: .bold))
                .tracking(0.3)
        }
        .foregroundColor(Color(hex: hexColor))
        .padding(.horizontal, size.hPadding)
        .padding(.vertical, size.vPadding)
        .background(Color(hex: hexColor).opacity(0.14))
        .clipShape(Capsule())
        .overlay(
            Capsule()
                .strokeBorder(Color(hex: hexColor).opacity(0.3), lineWidth: 0.8)
        )
    }
}

// MARK: - Preview

#Preview {
    ZStack {
        Color(hex: "12112e").ignoresSafeArea()
        VStack(alignment: .leading, spacing: 16) {

            Text(".regular (default)").font(.caption).foregroundColor(.secondary)
            HStack(spacing: 8) {
                SentimentPill(stockSentiment: .recommended)
                SentimentPill(stockSentiment: .neutral)
                SentimentPill(stockSentiment: .caution)
            }

            Text(".small — untuk StockRowView").font(.caption).foregroundColor(.secondary)
            HStack(spacing: 8) {
                SentimentPill(sentiment: Sentiment(buy: 0.65, hold: 0.25, sell: 0.10), size: .small)
                SentimentPill(sentiment: Sentiment(buy: 0.35, hold: 0.40, sell: 0.25), size: .small)
                SentimentPill(sentiment: Sentiment(buy: 0.15, hold: 0.25, sell: 0.60), size: .small)
            }
        }
        .padding()
    }
}
