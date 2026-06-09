//
//  AIInsightCard.swift
//  SahamIndo
//
//  Cara pakai di StockDetailView:
//
//      AIInsightCard(symbol: item.symbol)
//          .padding(.horizontal)
//
//  Taruh setelah TimeRangeSelectorView / Divider di body StockDetailView.
//

import SwiftUI
import Combine

// MARK: - ViewModel

@MainActor
final class AIInsightViewModel: ObservableObject {

    @Published private(set) var detail:      StockDetail? = nil
    @Published private(set) var isLoading:   Bool         = true
    @Published private(set) var errorMessage: String?     = nil
    @Published private(set) var cacheState:  CacheState   = .live

    private let service = RealStockService()

    func load(symbol: String) async {
        guard !symbol.isEmpty else {
            print("[AIInsight] symbol kosong")
            return
        }
        isLoading    = true
        errorMessage = nil

        do {
            detail     = try await service.fetchDetail(symbol: symbol)
            cacheState = .live
            print("[AIInsight] OK:", detail?.sentiment.label ?? "-")
        } catch {
            print("[AIInsight] ERROR:", error)

            // Fallback 1: DummyData (data lokal hardcoded)
            if let dummy = DummyData.stockDetails[symbol] {
                detail     = dummy
                cacheState = .noData
                print("[AIInsight] fallback dummy OK:", symbol)
            } else {
                errorMessage = "Gagal memuat insight"
            }
        }

        isLoading = false
    }
}

// MARK: - AIInsightCard

struct AIInsightCard: View {

    let symbol: String

    @StateObject private var vm = AIInsightViewModel()
    @EnvironmentObject private var router: Router
    @EnvironmentObject private var chatbotVM: ChatbotViewModel

    var body: some View {
        VStack(spacing: 0) {
            if vm.isLoading {
                loadingView
            } else if let detail = vm.detail {
                cardContent(detail: detail)
            } else if let err = vm.errorMessage {
                errorView(message: err)
            } else {
                loadingView
            }
        }
        .task { await vm.load(symbol: symbol) }
    }

    // MARK: - Card Content

    private func cardContent(detail: StockDetail) -> some View {
        VStack(alignment: .leading, spacing: 14) {

            // ── Header: judul + sentiment badge ──
            HStack(alignment: .center, spacing: 8) {
                Image(systemName: "sparkles")
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundColor(Color(hex: "818CF8"))

                Text("AI Insight")
                    .font(.system(size: 14, weight: .bold))
                    .foregroundColor(.primary)

                Spacer()

                // Tampilkan badge offline kalau data dari dummy
                if vm.cacheState == .noData {
                    HStack(spacing: 4) {
                        Image(systemName: "wifi.slash")
                            .font(.system(size: 9, weight: .semibold))
                        Text("Offline")
                            .font(.system(size: 9, weight: .bold))
                    }
                    .foregroundColor(Color(hex: "EAB308"))
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Color(hex: "EAB308").opacity(0.12))
                    .clipShape(Capsule())
                } else {
                    Text("Updated: Today at 07:00 WIB")
                        .font(.system(size: 10, weight: .bold))
                        .foregroundColor(.secondary)
                        .kerning(0.8)
                }
            }

            // ── Divider ──
            Rectangle()
                .fill(Color.primary.opacity(0.08))
                .frame(height: 1)

            // ── AI Summary text ──
            Text(detail.aiSummary)
                .font(.system(size: 13, weight: .regular))
                .foregroundColor(Color.primary.opacity(0.85))
                .lineSpacing(4)
                .fixedSize(horizontal: false, vertical: true)

            // ── Divider ──
            Rectangle()
                .fill(Color.primary.opacity(0.08))
                .frame(height: 1)

            // ── Button: Tanya Chatbot ──
            Button(action: {
                chatbotVM.inputText = "Bagaimana analisis fundamental dan sentimen terbaru untuk saham \(detail.symbol)?"
                router.selectedTab = "assets"
            }) {
                HStack(spacing: 6) {
                    Image(systemName: "sparkles")
                    Text("Tanya chatbot tentang saham ini")
                }
                .font(.system(size: 12, weight: .bold))
                .foregroundColor(.white)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 10)
                .background(Color(hex: "FFA500"))
                .cornerRadius(10)
            }
            .buttonStyle(.plain)

        }
        .padding(16)
        .background(
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .fill(Color.appCardBackground)
                .overlay(
                    RoundedRectangle(cornerRadius: 16, style: .continuous)
                        .strokeBorder(
                            LinearGradient(
                                colors: [
                                    Color(hex: "818CF8").opacity(0.35),
                                    Color(hex: "818CF8").opacity(0.08)
                                ],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            ),
                            lineWidth: 1
                        )
                )
        )
        .transition(.opacity.combined(with: .scale(scale: 0.97)))
    }

    // MARK: - Loading Skeleton

    private var loadingView: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                RoundedRectangle(cornerRadius: 4).fill(Color.primary.opacity(0.08)).frame(width: 90, height: 14)
                Spacer()
                RoundedRectangle(cornerRadius: 20).fill(Color.white.opacity(0.07)).frame(width: 100, height: 24)
            }
            RoundedRectangle(cornerRadius: 4).fill(Color.primary.opacity(0.06)).frame(maxWidth: .infinity).frame(height: 12)
            RoundedRectangle(cornerRadius: 4).fill(Color.primary.opacity(0.06)).frame(maxWidth: .infinity).frame(height: 12)
            RoundedRectangle(cornerRadius: 4).fill(Color.primary.opacity(0.06)).frame(width: 200, height: 12)
        }
        .padding(16)
        .background(RoundedRectangle(cornerRadius: 16).fill(Color.appCardBackground))
        .redacted(reason: .placeholder)
    }

    // MARK: - Error State

    private func errorView(message: String) -> some View {
        HStack(spacing: 8) {
            Image(systemName: "exclamationmark.triangle")
                .font(.system(size: 12))
                .foregroundColor(Color(hex: "EF4444"))
            Text(message)
                .font(.system(size: 12))
                .foregroundColor(.secondary)
        }
        .padding(12)
        .background(RoundedRectangle(cornerRadius: 12).fill(Color(hex: "1E1D3F")))
    }
}

// SentimentPill dipindah ke SentimentPill.swift — gunakan SentimentPill(stockSentiment:)

// MARK: - Preview

#Preview {
    ZStack {
        Color(hex: "12112e").ignoresSafeArea()

        VStack(spacing: 16) {
            // Contoh Recommended
            cardPreview(
                sentiment: .recommended,
                summary: "BBCA mempertahankan NIM 5,6% dengan kualitas kredit terjaga. Pertumbuhan DPK 11% YoY dan CASA ratio 81% memberikan cost of fund terendah di industri. Dividen payout ratio 60% menarik bagi investor income.",
                sector: "Perbankan"
            )

            // Contoh Caution
            cardPreview(
                sentiment: .caution,
                summary: "BBRI menghadapi tekanan NIM akibat kenaikan biaya dana. NPL segmen mikro naik tipis ke 3,1%. Restrukturisasi kredit UMKM pasca-pandemi masih berjalan.",
                sector: "Perbankan"
            )

            // Contoh Neutral
            cardPreview(
                sentiment: .neutral,
                summary: "TLKM menghadapi tekanan ARPU IndiHome di tengah persaingan fixed broadband. Telkomsel masih solid dengan market share 53%.",
                sector: "Telekomunikasi"
            )
        }
        .padding()
    }
}

private func cardPreview(sentiment: StockSentiment, summary: String, sector: String) -> some View {
    VStack(alignment: .leading, spacing: 14) {
        HStack {
            Image(systemName: "sparkles").font(.system(size: 13, weight: .semibold)).foregroundColor(Color(hex: "818CF8"))
            Text("AI Insight").font(.system(size: 14, weight: .bold)).foregroundColor(.primary)
            Spacer()
            SentimentPill(stockSentiment: sentiment)
        }
        Rectangle().fill(Color.primary.opacity(0.08)).frame(height: 1)
        Text(summary).font(.system(size: 13)).foregroundColor(Color.primary.opacity(0.85)).lineSpacing(4)
        HStack(spacing: 4) {
            Image(systemName: "building.2").font(.system(size: 10)).foregroundColor(.secondary)
            Text(sector).font(.system(size: 11, weight: .medium)).foregroundColor(.secondary)
        }
    }
    .padding(16)
    .background(
        RoundedRectangle(cornerRadius: 16, style: .continuous).fill(Color.appCardBackground)
            .overlay(RoundedRectangle(cornerRadius: 16, style: .continuous)
                .strokeBorder(LinearGradient(colors: [Color(hex: "818CF8").opacity(0.35), Color(hex: "818CF8").opacity(0.08)], startPoint: .topLeading, endPoint: .bottomTrailing), lineWidth: 1))
    )
}
