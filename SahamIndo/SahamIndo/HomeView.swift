//
//  HomeView.swift
//  SahamIndo
//

import SwiftUI

// MARK: - HomeView

struct HomeView: View {

    @EnvironmentObject private var vm:      PortfolioViewModel
    @EnvironmentObject private var router:  Router
    @EnvironmentObject private var notifVM: NotificationViewModel

    var body: some View {
        ScrollView {
            
            VStack(spacing: 0) {
                
                AIInsightCardView()
                    .padding(.vertical, 12)
                
                AIFeatureCardsView()
                
                Divider()
                
                StockListView(
                    items: vm.items,
                    onTap: { router.push(.stockDetail($0)) }
                )
            }
        }
       .background(Color.appBackground.ignoresSafeArea())
        .navigationTitle("")
        .navigationBarTitleDisplayMode(.inline)
        .safeAreaInset(edge: .top) {
            HStack {
                HStack(spacing: 0) {
                    Text("SAHAM")
                        .font(.title)
                        .fontWeight(.bold)
                        .foregroundColor(.primary)
                    Text(".AI")
                        .font(.title)
                        .fontWeight(.bold)
                        .foregroundColor(Color(hex: "EAB308"))
                }
                Spacer()
                NotificationButton(unreadCount: notifVM.unreadCount) { router.push(.notification) }
            }
            .padding(.horizontal)
            .padding(.vertical, 8)
            .background(Color.appBackground)
        }
        .toolbar(.hidden, for: .navigationBar)
        .task { await vm.fetchData() }
        .task { await notifVM.checkForAlerts() }
        .onAppear {
            UISegmentedControl.appearance().selectedSegmentTintColor = UIColor(Color(hex: "FFA500"))
            UISegmentedControl.appearance().setTitleTextAttributes(
                [.foregroundColor: UIColor.black], for: .selected
            )
            UISegmentedControl.appearance().setTitleTextAttributes(
                [.foregroundColor: UIColor.secondaryLabel], for: .normal
            )
        }
    }
    
}

// MARK: - Portfolio Header

struct PortfolioHeaderView: View {

    let totalValue:     Double
    let totalProfitIDR: Double
    let totalCost:      Double

    private var profitPct: Double {
        guard totalCost > 0 else { return 0 }
        return (totalProfitIDR / totalCost) * 100
    }

    private var isPositive: Bool { totalProfitIDR >= 0 }
    private var accentColor: Color { isPositive ? Color(hex: "22C55E") : Color(hex: "EF4444") }

    var body: some View {
        VStack(spacing: 4) {
            Text("Total Portofolio")
                .font(.caption)
                .foregroundColor(.secondary)

            Text(formatIDR(totalValue))
                .font(.system(size: 32, weight: .bold, design: .rounded))

            HStack(spacing: 6) {
                Text("\(isPositive ? "+ " : "- ")\(formatIDR(abs(totalProfitIDR)))")
                    .font(.system(size: 13, weight: .semibold))
                if totalCost > 0 {
                    Text("(\(profitPct >= 0 ? "+" : "")\(profitPct, specifier: "%.2f")%)")
                        .font(.caption)
                }
            }
            .foregroundColor(accentColor)
            .padding(.horizontal, 10)
            .padding(.vertical, 4)
            .background(accentColor.opacity(0.1))
            .clipShape(Capsule())
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
    }
}

// MARK: - Stock List

struct StockListView: View {

    let items:  [PortfolioItem]
    let onTap:  (PortfolioItem) -> Void

    var body: some View {
        //ScrollView {
            LazyVStack(spacing: 0) {
                ForEach(items) { item in
                    VStack(spacing: 0) {
                        StockRowView(stock: item)
                            .padding(.horizontal, 16)
                            .padding(.vertical, 6)
                        Divider()
                            .padding(.horizontal, 16)
                    }
                    .contentShape(Rectangle())
                    .onTapGesture { onTap(item) }
                }
            }
        //}
    }
}

// MARK: - Stock Row

struct StockRowView: View {

    let stock: PortfolioItem

    var body: some View {
        HStack(spacing: 8) {
            StockAvatarView(symbol: stock.symbol)

            VStack(alignment: .leading, spacing: 2) {
                HStack(spacing: 6) {
                    Text(stock.symbol)
                        .font(.system(size: 15, weight: .bold))

                    SentimentPill(sentiment: stock.sentiment, size: .small)
                }
                Text(stock.name ?? "-")
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .lineLimit(1)

                SentimentBarView(sentiment: stock.sentiment)
                    .frame(width: 160)
            }
            .layoutPriority(1)

            Spacer(minLength: 0)

            MiniSparklineView(symbol: stock.symbol, isPositive: stock.change >= 0)
                .frame(width: 70, height: 34)
                .padding(.trailing, 8)

            VStack(alignment: .trailing, spacing: 2) {
                Text(formatIDR(stock.price))
                    .font(.system(size: 16, weight: .semibold))
                    .lineLimit(1)
                    .fixedSize(horizontal: true, vertical: false)

                HStack(spacing: 2) {
                    Image(systemName: stock.change >= 0 ? "arrow.up.right" : "arrow.down.forward")
                        .font(.system(size: 8, weight: .bold))
                    Text("\(abs(stock.percentChange), specifier: "%.2f")%")
                        .font(.system(size: 10, weight: .medium))
                        .lineLimit(1)
                        .fixedSize(horizontal: true, vertical: false)
                }
                .foregroundColor(stock.change >= 0 ? Color(hex: "22C55E") : Color(hex: "EF4444"))
                .padding(.horizontal, 6)
                .padding(.vertical, 3)
                .background((stock.change >= 0 ? Color(hex: "22C55E") : Color(hex: "EF4444")).opacity(0.1))
                .clipShape(Capsule())
            }
            .fixedSize(horizontal: true, vertical: false)
        }
        .padding(.vertical, 6)
    }
}

// MARK: - Stock Avatar

struct StockAvatarView: View {
    
    let symbol: String
    
    private var gradientColors: [Color] {
        let hash = abs(symbol.hashValue)
        let choices: [[Color]] = [
            [Color(hex: "3B82F6"), Color(hex: "1D4ED8")], // Blue
            [Color(hex: "EC4899"), Color(hex: "BE185D")], // Pink
            [Color(hex: "8B5CF6"), Color(hex: "6D28D9")], // Purple
            [Color(hex: "10B981"), Color(hex: "047857")], // Teal
            [Color(hex: "F59E0B"), Color(hex: "D97706")], // Amber
            [Color(hex: "EF4444"), Color(hex: "B91C1C")], // Red
            [Color(hex: "06B6D4"), Color(hex: "0891B2")]  // Cyan
        ]
        return choices[hash % choices.count]
    }
    
    var body: some View {
        if UIImage(named: symbol) != nil {
            Image(symbol)
                .resizable()
                .scaledToFit()
                .frame(width: 42, height: 42)
                .clipShape(Circle())
        } else {
            let initials = String(symbol.prefix(2))
            Circle()
                .fill(LinearGradient(
                    colors: gradientColors,
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                ))
                .frame(width: 42, height: 42)
                .overlay(
                    Text(initials)
                        .font(.system(size: 14, weight: .bold, design: .rounded))
                        .foregroundColor(.white)
                )
                .shadow(color: Color.black.opacity(0.15), radius: 3, x: 0, y: 1)
        }
    }
}

// MARK: - Sentiment Badge

//struct SentimentBadgeView: View {
//
//    let sentiment: Sentiment
//
//    var body: some View {
//        Text(sentiment.label)
//            .font(.system(size: 10, weight: .semibold))
//            .padding(.horizontal, 6)
//            .padding(.vertical, 2)
//            .background(sentiment.color.opacity(0.15))
//            .foregroundColor(sentiment.color)
//            .clipShape(Capsule())
//    }
//}

// MARK: - Sentiment Bar

struct SentimentBarView: View {

    let sentiment: Sentiment

    var body: some View {
        HStack(spacing: 6) {
            ZStack(alignment: .leading) {
                // Background track
                RoundedRectangle(cornerRadius: 3)
                    .fill(Color.primary.opacity(0.12))
                    .frame(width: 110, height: 5)
                
                // Filled track based on score
                RoundedRectangle(cornerRadius: 3)
                    .fill(sentiment.color)
                    .frame(width: 110 * CGFloat(sentiment.score / 100.0), height: 5)
            }
            
            Text(String(format: "%.1f%%", sentiment.score))
                .font(.system(size: 10, weight: .bold, design: .rounded))
                .foregroundColor(sentiment.color)
        }
    }
}

// MARK: - Mini Sparkline Chart (1D)
//
// Menggunakan StockChartViewModel yang sama dengan StockDetailView:
//   • Data dari RealChartService (FastAPI) → normalizeToSlots (87 slot tetap)
//   • Fallback ke IDXDummyPriceGenerator jika API tidak bisa diakses
// Hasilnya konsisten dengan chart 1D di halaman detail saham.

struct MiniSparklineView: View {

    let symbol:     String
    let isPositive: Bool

    @StateObject private var chartVM = StockChartViewModel()

    private let green = Color(hex: "22C55E")
    private let red   = Color(hex: "EF4444")

    private var points: [StockDataPoint] { chartVM.dataPoints }

    var body: some View {
        Canvas { ctx, size in
            guard points.count > 1 else { return }

            let closes   = points.map(\.close)
            let startVal = closes[0]
            let minVal   = closes.min()!
            let maxVal   = closes.max()!
            let range    = max(maxVal - minVal, 1)
            let w        = size.width
            let h        = size.height
            let padV:    CGFloat = 4
            let usableH  = h - padV * 2

            func xFor(_ i: Int) -> CGFloat {
                CGFloat(i) / CGFloat(closes.count - 1) * w
            }
            func yFor(_ v: Double) -> CGFloat {
                padV + usableH * (1 - (v - minVal) / range)
            }

            let startY = yFor(startVal)

            // ── Helper: build area path closing to a given baseline Y ──
            func buildAreaPath(closeY: CGFloat) -> Path {
                var p = Path()
                p.move(to: CGPoint(x: xFor(0), y: closeY))
                for i in 0..<closes.count {
                    let x = xFor(i); let y = yFor(closes[i])
                    if i == 0 {
                        p.addLine(to: CGPoint(x: x, y: y))
                    } else {
                        let px = xFor(i - 1); let py = yFor(closes[i - 1])
                        p.addCurve(to: CGPoint(x: x, y: y),
                                   control1: CGPoint(x: px + (x - px) * 0.5, y: py),
                                   control2: CGPoint(x: px + (x - px) * 0.5, y: y))
                    }
                }
                p.addLine(to: CGPoint(x: xFor(closes.count - 1), y: closeY))
                p.closeSubpath()
                return p
            }

            // ── Helper: build full line path ──
            func buildLinePath() -> Path {
                var p = Path()
                for i in 0..<closes.count {
                    let x = xFor(i); let y = yFor(closes[i])
                    if i == 0 { p.move(to: CGPoint(x: x, y: y)) }
                    else {
                        let px = xFor(i - 1); let py = yFor(closes[i - 1])
                        p.addCurve(to: CGPoint(x: x, y: y),
                                   control1: CGPoint(x: px + (x - px) * 0.5, y: py),
                                   control2: CGPoint(x: px + (x - px) * 0.5, y: y))
                    }
                }
                return p
            }

            let greenAreaPath = buildAreaPath(closeY: startY)
            let redAreaPath   = buildAreaPath(closeY: h)
            let linePath      = buildLinePath()

            // ── Area & line: green above startY, red below startY ──
            let lineStyle = StrokeStyle(lineWidth: 1.2, lineCap: .round, lineJoin: .round)

            // Green: fade dari startY ke atas
            ctx.drawLayer { layer in
                layer.clip(to: Path(CGRect(x: 0, y: 0, width: w, height: startY)))
                layer.fill(greenAreaPath, with: .linearGradient(
                    Gradient(stops: [
                        .init(color: green.opacity(0.18), location: 0),
                        .init(color: green.opacity(0.06), location: 1),
                    ]),
                    startPoint: CGPoint(x: 0, y: 0),
                    endPoint:   CGPoint(x: 0, y: startY)
                ))
                layer.stroke(linePath, with: .color(green), style: lineStyle)
            }

            // Red: fade dari startY ke bawah
            ctx.drawLayer { layer in
                layer.clip(to: Path(CGRect(x: 0, y: startY, width: w, height: h - startY)))
                layer.fill(redAreaPath, with: .linearGradient(
                    Gradient(stops: [
                        .init(color: red.opacity(0.18), location: 0),
                        .init(color: red.opacity(0.04), location: 1),
                    ]),
                    startPoint: CGPoint(x: 0, y: startY),
                    endPoint:   CGPoint(x: 0, y: h)
                ))
                layer.stroke(linePath, with: .color(red), style: lineStyle)
            }

            // ── Baseline dashed line at startY ──
            var basePath = Path()
            basePath.move(to: CGPoint(x: 0, y: startY))
            basePath.addLine(to: CGPoint(x: w, y: startY))
            ctx.stroke(basePath,
                       with: .color(Color.primary.opacity(0.15)),
                       style: StrokeStyle(lineWidth: 0.5, dash: [2, 3]))

            // ── Dashed last-price horizontal line ──
            let lastY = yFor(closes.last!)
            let lastColor = closes.last! >= startVal ? green : red
            var dashPath = Path()
            dashPath.move(to: CGPoint(x: 0, y: lastY))
            dashPath.addLine(to: CGPoint(x: w, y: lastY))
            ctx.stroke(dashPath,
                       with: .color(lastColor.opacity(0.5)),
                       style: StrokeStyle(lineWidth: 0.75, dash: [3, 3]))

            // ── Last-price dot ──
            let dotX = xFor(closes.count - 1)
            let dotR: CGFloat = 2.5
            ctx.fill(Path(ellipseIn: CGRect(x: dotX - dotR, y: lastY - dotR,
                                            width: dotR * 2, height: dotR * 2)),
                     with: .color(lastColor))
        }
        .task(id: symbol) {
            chartVM.symbol      = symbol
            chartVM.selectedRange = .oneDay
            await chartVM.fetchData()
        }
    }
}

// MARK: - Reset Button

//struct ResetButton: View {
//
//    let action: () -> Void
//
//    var body: some View {
//        Button(role: .destructive, action: action) {
//            Image(systemName: "trash")
//                .foregroundColor(.red)
//        }
//    }
//}
struct NotificationButton: View {

    let unreadCount: Int
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            ZStack(alignment: .topTrailing) {
                Image(systemName: "bell.fill")
                    .font(.system(size: 20))
                    .foregroundColor(.primary)

                if unreadCount > 0 {
                    ZStack {
                        Circle()
                            .fill(Color(hex: "EF4444"))
                            .frame(width: 16, height: 16)
                        Text(unreadCount > 9 ? "9+" : "\(unreadCount)")
                            .font(.system(size: 8, weight: .bold))
                            .foregroundColor(.white)
                    }
                    .offset(x: 6, y: -6)
                }
            }
        }
    }
}

// MARK: - AI Feature Cards

struct AIFeatureCardsView: View {

    struct AIFeature: Identifiable {
        let id = UUID()
        let icon: String
        let title: String
        let description: String
    }

    private let features: [AIFeature] = [
        AIFeature(icon: "sparkle.text.clipboard.fill", title: "AI News Summary",   description: "Rangkuman berita makroekonomi dan emiten pilihan hari ini."),
        AIFeature(icon: "sparkles.square.filled.on.square",      title: "Tanya Emiten", description: "Diskusikan kesehatan finansial, hitungan valuasi, dan potensi bisnis emiten secara interaktif."),
        AIFeature(icon: "exclamationmark.shield.fill",               title: "Sinyal Risiko",description: "Notifikasi instan jika sentimen fundamental atau berita emiten Anda mendadak berbalik arah."),
    ]

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .center, spacing: 8) {
                Image(systemName: "sparkles")
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundColor(Color(hex: "818CF8"))

                Text("AI Features")
                    .font(.system(size: 16, weight: .bold))
                    .foregroundColor(.primary)
            }
            .padding(.horizontal, 16)
            
            HStack(spacing: 6) {
                ForEach(features) { feature in
                    AIFeatureCardItem(feature: feature)
                }
            }
            .padding(.horizontal, 16)
        }
    }
}

// MARK: - AI Feature Card Item

private struct AIFeatureCardItem: View {

    let feature: AIFeatureCardsView.AIFeature

    private let accent = Color(hex: "EAB308")

    var body: some View {
        VStack(alignment: .center, spacing: 6) {
            ZStack {
                RoundedRectangle(cornerRadius: 8)
                    .fill(accent.opacity(0.12))
                    .frame(width: 36, height: 40)
                Image(systemName: feature.icon)
                    .font(.system(size: 24, weight: .semibold))
                    .foregroundColor(accent)
            }

            VStack(alignment: .center, spacing: 2) {
                Text(feature.title)
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundColor(.primary)
                    .fixedSize(horizontal: false, vertical: true)
                Text(feature.description)
                    .font(.system(size: 9, weight: .regular))
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .padding(8)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .background(Color.appCardBackground)
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .strokeBorder(accent.opacity(0.18), lineWidth: 0.5)
        )
    }
}

// MARK: - AI Insight Card
// Fix glitch: anchor pakai teks plain TERPANJANG dari semua chip (tidak pernah resize).

struct AIInsightCardView: View {

    struct InsightChip: Identifiable, Equatable {
        let id    = UUID()
        let label: String
        let text:  String
        var plainText: String { text.replacingOccurrences(of: "**", with: "") }

        static func == (lhs: InsightChip, rhs: InsightChip) -> Bool {
            lhs.label == rhs.label && lhs.text == rhs.text
        }
    }

    private let accent = Color(hex: "EAB308")

    @State private var chips: [InsightChip] = [
        InsightChip(
            label: "Analisis Teknikal",
            text:  "Sektor **perbankan** menunjukkan momentum positif pasca data inflasi. **BBCA & BBRI** berpotensi retest resistance minggu ini."
        ),
        InsightChip(
            label: "Sentimen Berita",
            text:  "Sentimen media sosial terhadap **GGRM** meningkat signifikan. Buzz positif naik **34%** dalam 48 jam terakhir."
        ),
        InsightChip(
            label: "Asing Net Buy",
            text:  "Investor asing net buy **Rp 1,2 triliun** hari ini. Sektor **energi & infrastruktur** jadi pilihan utama."
        ),
        InsightChip(
            label: "Makro IDR",
            text:  "Rupiah menguat ke **Rp 15.820/USD** didukung surplus neraca dagang. **BI** diprediksi tahan suku bunga bulan ini."
        ),
    ]

    // Threshold: teks dianggap "panjang" jika lebih dari N kata
    private let readMoreThreshold = 30

    @State private var selectedChip: InsightChip
    @State private var isPulsing:    Bool     = false
    @State private var wordIndex:    Int      = 0
    @State private var targetWords:  [String] = []
    @State private var timer:        Timer?   = nil
    @State private var selectedIndex  = 0
    @State private var isExpanded:    Bool     = false
    @State private var showReadMore:  Bool     = false
    @State private var lastUpdated:   Date?    = nil
    init() {
        let first = InsightChip(
            label: "Analisis Teknikal",
            text:  "Sektor **perbankan** menunjukkan momentum positif pasca data inflasi. **BBCA & BBRI** berpotensi retest resistance minggu ini."
        )
        _selectedChip = State(initialValue: first)
    }

    private var displayedText: String {
        targetWords.prefix(wordIndex).joined(separator: " ")
    }

    var body: some View {
        VStack(spacing: 0) {

            // ── Card Content ──
            VStack(alignment: .leading, spacing: 12) {

                // ── Header badge ──
                HStack {
                    HStack(spacing: 6) {
                        Circle()
                            .fill(accent)
                            .frame(width: 7, height: 7)
                            .scaleEffect(isPulsing ? 0.7 : 1.0)
                            .animation(.easeInOut(duration: 1).repeatForever(), value: isPulsing)
                        
                        Text("AI LIVE")
                            .font(.system(size: 10, weight: .bold))
                            .foregroundColor(accent)
                            .kerning(0.8)
                    }
                    .padding(.horizontal, 10)
                    .padding(.vertical, 5)
                    .background(accent.opacity(0.12))
                    .clipShape(Capsule())
                    .overlay(Capsule().strokeBorder(accent.opacity(0.35), lineWidth: 0.5))
                    .onAppear {
                        isPulsing = true
                        startTyping(text: selectedChip.text)
                    }
                    
                    Spacer()
                    if let date = lastUpdated {
                        TimelineView(.periodic(from: Date(), by: 60)) { context in
                            Text("Last updated: \(timeAgoString(from: date, now: context.date))")
                                .font(.system(size: 10, weight: .bold))
                                .foregroundColor(accent)
                                .kerning(0.8)
                        }
                    }
                }

                // ── Insight text ──
                let isLongText = targetWords.count > readMoreThreshold

                VStack(alignment: .leading, spacing: 8) {
                    // Teks animasi — dipotong jika belum di-expand dan teks panjang
                    buildAttributedText(from: displayedText)
                        .font(.system(size: 14))
                        .foregroundColor(Color.primary.opacity(0.85))
                        .lineSpacing(4)
                        .fixedSize(horizontal: false, vertical: true)
                        .lineLimit(isLongText && !isExpanded ? 3 : nil)
                        .frame(maxWidth: .infinity, alignment: .topLeading)
                        .transaction { $0.animation = nil }

                    // Tombol "Baca selengkapnya" — muncul 2 detik setelah chip dipilih, hanya jika teks panjang
                    if isLongText && showReadMore {
                        Button(action: {
                            withAnimation(.easeInOut(duration: 0.25)) {
                                isExpanded.toggle()
                            }
                        }) {
                            HStack(spacing: 4) {
                                Text(isExpanded ? "Sembunyikan" : "Baca selengkapnya")
                                    .font(.system(size: 11, weight: .semibold))
                                Image(systemName: isExpanded ? "chevron.up" : "chevron.down")
                                    .font(.system(size: 9, weight: .bold))
                            }
                            .foregroundColor(accent)
                        }
                        .buttonStyle(.plain)
                        .transition(.opacity)
                    }
                }
                .frame(maxWidth: .infinity, minHeight: 80, alignment: .topLeading)

            }
            .padding(12)
            .frame(maxWidth: .infinity)

            // ── Chips — selalu tampil, tidak ikut di-clip ──
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 6) {
                    ForEach(Array(chips.enumerated()), id: \.element.id) { index, chip in
                        InsightChipView(
                            label: chip.label,
                            isActive: selectedIndex == index,
                            accent: accent
                        ) {
                            selectedIndex = index
                            selectedChip = chip
                            isExpanded = false
                            startTyping(text: chip.text)
                        }
                    }
                }
                .padding(.horizontal, 12)
            }
            .padding(.bottom, 10)

        }
        .frame(minHeight: 150, alignment: .top)
        .background(Color(hex: "EAB308").opacity(0.05))
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .overlay(
            RoundedRectangle(cornerRadius: 16)
                .strokeBorder(accent.opacity(0.25), lineWidth: 0.5)
        )
        .padding(.horizontal, 16)
        .task {
            await loadLiveInsights()
        }
        .onDisappear { stopTimer() }
    }

    // MARK: - Live Loader

    private func loadLiveInsights() async {
        let service = RealStockService()

        // Fetch all sources in parallel; AI endpoints take priority, real data used as fallback
        async let sentimenAIFetch = service.fetchSentimenBeritaInsight()
        async let asingAIFetch    = service.fetchAsingNetBuyInsight()
        async let makroAIFetch    = service.fetchMakroIDRInsight()
        async let makroFetch      = service.fetchMakro()
        async let alertsFetch     = service.fetchAlerts()
        async let rekFetch        = service.fetchRekomendasiMingguan()

        let sentimenAI = try? await sentimenAIFetch
        let asingAI    = try? await asingAIFetch
        let makroAI    = try? await makroAIFetch
        let makroData  = try? await makroFetch
        let alertsData = try? await alertsFetch
        let rekData    = try? await rekFetch

        // ── Analisis Teknikal: AI via /rekomendasi/mingguan ──
        let teknikalText: String
        if let top = rekData?.rekomendasi.first {
            let alasan = (top.alasan ?? "")
                .components(separatedBy: "⚠️Catatan:").first?
                .trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
            teknikalText = "Rekomendasi utama minggu ini: **\(top.kode_saham)** (\(top.rekomendasi)). \(alasan)"
        } else {
            teknikalText = "Data rekomendasi teknikal sedang diperbarui."
        }

        // ── Sentimen Berita: AI → aggregate alerts → rekomendasi distribution → unavailable ──
        let sentimenText: String
        if let aiText = sentimenAI?.text, !aiText.isEmpty {
            sentimenText = aiText
        } else if let alerts = alertsData, !alerts.isEmpty {
            let positives = alerts.filter { $0.delta > 0 }.count
            let negatives = alerts.filter { $0.delta < 0 }.count
            let topNames  = alerts.prefix(3).map { "**\($0.kode_saham)**" }.joined(separator: ", ")
            sentimenText = "Terdeteksi **\(alerts.count) sinyal** perubahan sentimen hari ini — **\(positives) positif**, **\(negatives) negatif**. Saham terpantau: \(topNames)."
        } else if let rek = rekData, !rek.rekomendasi.isEmpty {
            let buy     = rek.rekomendasi.filter { ["RECOMMENDED","BUY"].contains($0.rekomendasi.uppercased()) }.count
            let caution = rek.rekomendasi.filter { ["CAUTION","SELL","NEGATIVE"].contains($0.rekomendasi.uppercased()) }.count
            let neutral = rek.rekomendasi.count - buy - caution
            sentimenText = "Sentimen pasar minggu ini: **\(buy) saham** direkomendasikan beli, **\(caution)** caution, **\(neutral)** netral."
        } else {
            sentimenText = "Data sentimen berita sedang diperbarui."
        }

        // ── Asing Net Buy: AI → macro asing_net_buy key → IHSG+kurs proxy → unavailable ──
        let asingText: String
        if let aiText = asingAI?.text, !aiText.isEmpty {
            asingText = aiText
        } else if let asingObj = makroData?.indikator["asing_net_buy"] {
            let val = asingObj.nilai
            asingText = val < 0
                ? "Investor asing mencatatkan net sell sebesar **Rp \(String(format: "%.1f", abs(val))) triliun** hari ini di pasar saham Indonesia."
                : "Investor asing mencatatkan net buy sebesar **Rp \(String(format: "%.1f", val)) triliun** hari ini di pasar saham Indonesia."
        } else if let makro = makroData,
                  let ihsg = makro.indikator["ihsg"]?.nilai,
                  let usd  = makro.indikator["kurs_usd_idr"]?.nilai {
            asingText = "IHSG saat ini di level **\(String(format: "%.1f", ihsg))** dengan kurs USD/IDR **Rp \(String(format: "%.0f", usd))**. Data aliran dana asing sedang diperbarui."
        } else {
            asingText = "Data aliran dana asing sedang diperbarui."
        }

        // ── Makro IDR: AI → real indicators (only show keys that exist) → unavailable ──
        let makroText: String
        if let aiText = makroAI?.text, !aiText.isEmpty {
            makroText = aiText
        } else if let makro = makroData {
            var parts: [String] = []
            if let v = makro.indikator["ihsg"]?.nilai         { parts.append("IHSG di level **\(String(format: "%.1f", v))**") }
            if let v = makro.indikator["kurs_usd_idr"]?.nilai { parts.append("kurs USD/IDR **Rp \(String(format: "%.0f", v))**") }
            if let v = makro.indikator["bi_rate"]?.nilai      { parts.append("BI Rate **\(String(format: "%.2f", v))%**") }
            if let v = makro.indikator["inflasi_yoy"]?.nilai  { parts.append("inflasi YoY **\(String(format: "%.2f", v))%**") }
            makroText = parts.isEmpty ? "Data makro sedang diperbarui." : parts.joined(separator: ", ") + "."
        } else {
            makroText = "Data makro sedang diperbarui."
        }

        let newChips = [
            InsightChip(label: "Analisis Teknikal", text: teknikalText),
            InsightChip(label: "Sentimen Berita",   text: sentimenText),
            InsightChip(label: "Asing Net Buy",     text: asingText),
            InsightChip(label: "Makro IDR",         text: makroText)
        ]

        await MainActor.run {
            self.chips       = newChips
            self.lastUpdated = Date()
            if selectedIndex < chips.count {
                selectedChip = chips[selectedIndex]
                startTyping(text: selectedChip.text)
            }
        }
    }

    // MARK: - Typing Engine

    private func startTyping(text: String) {
        stopTimer()
        showReadMore  = false
        targetWords   = text.components(separatedBy: " ")
        wordIndex     = 0

        timer = Timer.scheduledTimer(withTimeInterval: 0.07, repeats: true) { t in
            if wordIndex < targetWords.count {
                wordIndex += 1

                // Tampilkan tombol tepat saat kata ke-readMoreThreshold terketik
                // (artinya teks sudah memenuhi minHeight container)
                if wordIndex == readMoreThreshold && !showReadMore {
                    DispatchQueue.main.async {
                        withAnimation(.easeIn(duration: 0.3)) {
                            showReadMore = true
                        }
                    }
                }
            } else {
                // Teks pendek (tidak sampai threshold) — tetap munculkan tombol saat selesai
                if !showReadMore {
                    DispatchQueue.main.async {
                        withAnimation(.easeIn(duration: 0.3)) {
                            showReadMore = true
                        }
                    }
                }
                t.invalidate()
                timer = nil
            }
        }
    }

    private func stopTimer() {
        timer?.invalidate()
        timer = nil
    }

    // MARK: - Relative time helper

    private func timeAgoString(from date: Date, now: Date = Date()) -> String {
        let diff = Int(now.timeIntervalSince(date))
        if diff < 60 { return "baru saja" }
        let mins = diff / 60
        if mins < 60 { return "\(mins) mnt lalu" }
        let hours = mins / 60
        return "\(hours) jam lalu"
    }

    // MARK: - Bold keyword helper

    private func buildAttributedText(from raw: String) -> Text {
        var attrStr = AttributedString("")
        let parts  = raw.components(separatedBy: "**")
        for (i, part) in parts.enumerated() {
            var temp = AttributedString(part)
            if i % 2 == 1 {
                temp.font = .system(size: 14).weight(.semibold)
                temp.foregroundColor = accent
            } else {
                temp.font = .system(size: 14)
                temp.foregroundColor = Color.primary.opacity(0.85)
            }
            attrStr.append(temp)
        }
        return Text(attrStr)
    }
}
// MARK: - Insight Chip

private struct InsightChipView: View {

    let label:    String
    let isActive: Bool
    let accent:   Color
    let onTap:    () -> Void

    var body: some View {
        Button(action: onTap) {
            Text(label)
                .font(.system(size: 10, weight: .medium))
                .foregroundColor(isActive ? accent : .secondary)
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .background(isActive ? accent.opacity(0.12) : Color.primary.opacity(0.05))
                .clipShape(Capsule())
                .overlay(
                    Capsule().strokeBorder(
                        isActive ? accent.opacity(0.45) : Color.primary.opacity(0.1),
                        lineWidth: 0.5
                    )
                )
        }
        .buttonStyle(.plain)
    }
}

#Preview {
    NavigationStack {
        HomeView()
            .environmentObject(PortfolioViewModel())
            .environmentObject(Router())
            .environmentObject(NotificationViewModel())
    }
}
