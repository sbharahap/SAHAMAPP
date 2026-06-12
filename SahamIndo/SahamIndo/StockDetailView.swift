//
//  StockDetailView.swift
//  SahamIndo
//

import SwiftUI
import Combine

// MARK: - StockDetailView

struct StockDetailView: View {

    let item: PortfolioItem

    @EnvironmentObject private var portfolioVM: PortfolioViewModel
    @StateObject private var chartVM = StockChartViewModel()

    // Crosshair
    @State private var selectedPoint: StockDataPoint? = nil
    @State private var isDragging    = false
    @State private var chartSize: CGSize = .zero

    // Sheets
    @State private var showTradeSheet = false

    // MARK: - Computed display values (berubah saat drag)

    private var displayPrice: Double  { selectedPoint?.close ?? chartVM.latestPrice }
    private var displayChange: Double {
        guard isDragging else { return item.change }
        return displayPrice - chartVM.startPrice
    }
    private var displayChangePct: Double {
        guard isDragging else { return item.percentChange }
        guard chartVM.startPrice != 0 else { return 0 }
        return (displayChange / chartVM.startPrice) * 100
    }
    private var displayIsPositive: Bool { displayPrice >= chartVM.startPrice }
    private var accentColor: Color {
        displayIsPositive ? Color(hex: "00D4AA") : Color(hex: "FF4757")
    }
    // Warna crosshair dot mengikuti posisi vs startPrice (untuk konsistensi visual)
    private var crosshairColor: Color {
        guard let pt = selectedPoint else { return accentColor }
        return pt.close >= chartVM.startPrice ? Color(hex: "00D4AA") : Color(hex: "FF4757")
    }

    // Holding terkini dari portfolioVM
    private var currentHolding: Holding? {
        portfolioVM.holdings.first { $0.symbol == item.symbol }
    }
    private var currentQty: Double { currentHolding?.quantity ?? 0 }

    // MARK: - Body

    var body: some View {
        VStack(spacing: 0) {
            ScrollView {
                VStack(spacing: 12) {
                    StockDetailHeaderView(item: item)
                        .padding(.horizontal)

                    PriceInfoView(
                        displayPrice:      displayPrice,
                        displayChange:     displayChange,
                        displayChangePct:  displayChangePct,
                        displayIsPositive: displayIsPositive,
                        accentColor:       accentColor,
                        selectedRange:     chartVM.selectedRange,
                        selectedPoint:     selectedPoint,
                        isDragging:        isDragging
                    )
                    .padding(.horizontal)
                    .animation(.easeInOut(duration: 0.1), value: isDragging)

                    ChartCanvasView(
                        chartVM:       chartVM,
                        selectedPoint: $selectedPoint,
                        isDragging:    $isDragging,
                        chartSize:     $chartSize,
                        accentColor:   accentColor,
                        displayIsPositive: displayIsPositive
                    )
                    .frame(height: 230)
                    .background(
                        GeometryReader { geo in
                            Color.clear
                                .onAppear { chartSize = geo.size }
                                .onChange(of: geo.size) { _, s in chartSize = s }
                        }
                    )
                    .padding(.horizontal, 8)

                    if !chartVM.dataPoints.isEmpty {
                        XAxisAnimatedLabels(
                            chartVM:   chartVM,
                            chartSize: chartSize
                        )
                        .padding(.horizontal, 8)
                        .padding(.top, -16)
                        .padding(.vertical, 6)
                    }

                    TimeRangeSelectorView(chartVM: chartVM) {
                        selectedPoint = nil
                        isDragging    = false
                    }
                    .padding(.horizontal)
                    .padding(.top, -16)
                    Divider()
                    .padding(.horizontal)

                    // ── AI Insight Card ──────────────────────────
                    AIInsightCard(symbol: item.symbol)
                        .padding(.horizontal)
                        .animation(.easeInOut(duration: 0.3), value: item.symbol)
                    // ─────────────────────────────────────────────
              
                    Spacer(minLength: 20)
                }
                .padding(.vertical, 12)
            }
            
            // Sticky Trade Button Bar
            tradeButtonBar
        }
        .background(Color.appBackground.ignoresSafeArea())
        .navigationTitle(item.symbol)
        .navigationBarTitleDisplayMode(.inline)
        .toolbar(.hidden, for: .tabBar)
        .sheet(isPresented: $showTradeSheet) {
            TradeSheetView(stock: item)
                .presentationDetents([.large])
                .environmentObject(portfolioVM)
        }
        .task {
            chartVM.symbol = item.symbol
            await chartVM.fetchData()
        }
        .onReceive(
            Timer.publish(every: 5 * 60, on: .main, in: .common).autoconnect()
        ) { _ in
            guard chartVM.selectedRange == .oneDay else { return }
            Task { await chartVM.fetchData() }
        }
    }
    
    private var tradeButtonBar: some View {
        VStack(spacing: 0) {
            Divider()
                .background(Color.primary.opacity(0.08))

            HStack(spacing: 16) {
                VStack(alignment: .leading, spacing: 3) {
                    Text("Posisi Kepemilikan")
                        .font(.system(size: 10, weight: .semibold))
                        .foregroundColor(.secondary)

                    Text("\(Int(currentQty)) lembar (\(Int(currentQty / 100)) Lot)")
                        .font(.system(size: 13, weight: .bold, design: .rounded))
                        .foregroundColor(.primary)
                }
                
                Spacer()
                
                Button(action: {
                    showTradeSheet = true
                }) {
                    HStack(spacing: 6) {
                        Image(systemName: "arrow.left.arrow.right")
                            .font(.system(size: 15))
                        Text("Trade")
                            .font(.system(size: 14, weight: .bold))
                    }
                    .foregroundColor(.black)
                    .padding(.horizontal, 28)
                    .padding(.vertical, 11)
                    .background(Color(hex: "FFA500"))
                    .cornerRadius(8)
                    .shadow(color: Color(hex: "FFA500").opacity(0.25), radius: 4, x: 0, y: 2)
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
            .background(Color.appCardBackground)
        }
    }
}

// MARK: - Stock Detail Header

struct StockDetailHeaderView: View {

    let item: PortfolioItem

    var body: some View {
        HStack(spacing: 10) {
            StockAvatarView(symbol: item.symbol)
                .scaleEffect(1.1)

            VStack(alignment: .leading, spacing: 2) {
                Text(item.symbol)
                    .font(.system(size: 20, weight: .bold, design: .rounded))
                Text(item.name ?? "-")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            Spacer()
            SentimentPill(sentiment: item.sentiment)
        }
        .padding(.top, 6)
    }
}

// MARK: - Price Info

struct PriceInfoView: View {

    let displayPrice:      Double
    let displayChange:     Double
    let displayChangePct:  Double
    let displayIsPositive: Bool
    let accentColor:       Color
    let selectedRange:     TimeRange
    let selectedPoint:     StockDataPoint?
    let isDragging:        Bool

    var body: some View {
        HStack(alignment: .bottom) {
            VStack(alignment: .leading, spacing: 6) {
                RollingPriceView(price: displayPrice, fontSize: 34, isInteractive: isDragging)
                    .frame(height: 34 * 1.25)   // clip container = digitHeight
                HStack(spacing: 6) {
                    
                    
                    HStack(spacing: 5) {
                        Image(systemName: displayIsPositive ? "arrow.up.right" : "arrow.down.right")
                            .font(.system(size: 11, weight: .bold))
                        Text("\(displayIsPositive ? "+" : "")\(formatIDR(displayChange))")
                            .font(.system(size: 13, weight: .semibold))
                        Text("(\(String(format: "%+.2f%%", displayChangePct)))")
                            .font(.system(size: 12, weight: .medium))
                            .opacity(0.85)
                    }
                    .foregroundColor(accentColor)
                    .padding(.horizontal, 8).padding(.vertical, 4)
                    .background(accentColor.opacity(0.12))
                    .cornerRadius(6)
                    
                    Text(selectedRange.rawValue)
                            .font(.system(size: 14, weight: .bold))
                }
            }

            Spacer()

            if isDragging, let point = selectedPoint {
                VStack(alignment: .trailing, spacing: 3) {
                    Text(formatDragDate(point.date, range: selectedRange))
                        .font(.system(size: 11, weight: .medium))
                        .foregroundColor(.secondary)
                    Text(formatIDR(point.close))
                        .font(.system(size: 13, weight: .semibold))
                }
                .transition(.opacity.combined(with: .scale(scale: 0.95)))
            }
        }
    }

    private func formatDragDate(_ date: Date, range: TimeRange) -> String {
        let df = DateFormatter()
        df.locale     = Locale(identifier: "id_ID")
        df.timeZone   = TimeZone(identifier: "Asia/Jakarta")!
        df.dateFormat = range.isIntraday ? "d MMM 'pukul' HH:mm" : "d MMM yyyy"
        return df.string(from: date)
    }
}

// MARK: - Animated Chart Path (untuk morphing antar range)

// MARK: - MorphPoint  (X + Y dalam satu vektor animatable)
// Menggabungkan efek:
// 1. X Spacing Morph — pow(t, exponent) * width  → titik bergeser kiri/kanan
// 2. Path Tweening   — padded(to:) clone titik terakhir → garis tumbuh/menyusut dari kanan

struct MorphPoint: VectorArithmetic, Sendable {
    var x: CGFloat
    var y: CGFloat

    static var zero: MorphPoint { .init(x: 0, y: 0) }

    static func + (lhs: Self, rhs: Self) -> Self { .init(x: lhs.x + rhs.x, y: lhs.y + rhs.y) }
    static func - (lhs: Self, rhs: Self) -> Self { .init(x: lhs.x - rhs.x, y: lhs.y - rhs.y) }

    mutating func scale(by rhs: Double) { x *= CGFloat(rhs); y *= CGFloat(rhs) }

    var magnitudeSquared: Double { Double(x * x + y * y) }
}

// MARK: - AnimatableChartData  (array MorphPoint, VectorArithmetic)

struct AnimatableChartData: VectorArithmetic, Equatable, Sendable {

    var points: [MorphPoint]

    static var zero: Self { .init(points: []) }

    static func + (lhs: Self, rhs: Self) -> Self {
        let n = max(lhs.points.count, rhs.points.count)
        let lp = lhs.padded(to: n)
        let rp = rhs.padded(to: n)
        var resultPoints: [MorphPoint] = []
        resultPoints.reserveCapacity(n)
        for i in 0..<n {
            resultPoints.append(lp[i] + rp[i])
        }
        return .init(points: resultPoints)
    }

    static func - (lhs: Self, rhs: Self) -> Self {
        let n = max(lhs.points.count, rhs.points.count)
        let lp = lhs.padded(to: n)
        let rp = rhs.padded(to: n)
        var resultPoints: [MorphPoint] = []
        resultPoints.reserveCapacity(n)
        for i in 0..<n {
            resultPoints.append(lp[i] - rp[i])
        }
        return .init(points: resultPoints)
    }

    mutating func scale(by rhs: Double) {
        for i in points.indices { points[i].scale(by: rhs) }
    }

    var magnitudeSquared: Double {
        points.reduce(0) { $0 + $1.magnitudeSquared }
    }

    // Path Tweening: titik tambahan tumbuh dari titik terakhir lama
    private func padded(to count: Int) -> [MorphPoint] {
        guard let last = points.last else {
            return Array(repeating: .zero, count: count)
        }
        if points.count >= count { return points }
        return points + Array(repeating: last, count: count - points.count)
    }
}

// MARK: - NormalizedChartData  (alias lama — dipertahankan untuk NormalizedChartData-only shape)
// Dipakai oleh MorphingLineShape & MorphingAreaShape (lama, masih digunakan)
// tetapi sekarang dibungkus AnimatableChartData di ChartCanvasView.
struct NormalizedChartData: VectorArithmetic, Equatable, Sendable {
    var values: [Double]

    static var zero: NormalizedChartData { .init(values: []) }

    static func + (lhs: NormalizedChartData, rhs: NormalizedChartData) -> NormalizedChartData {
        let n = max(lhs.values.count, rhs.values.count)
        guard n > 0 else { return .zero }
        return .init(values: (0..<n).map { i in
            let l = i < lhs.values.count ? lhs.values[i] : (lhs.values.last ?? 0)
            let r = i < rhs.values.count ? rhs.values[i] : (rhs.values.last ?? 0)
            return l + r
        })
    }

    static func - (lhs: NormalizedChartData, rhs: NormalizedChartData) -> NormalizedChartData {
        let n = max(lhs.values.count, rhs.values.count)
        guard n > 0 else { return .zero }
        return .init(values: (0..<n).map { i in
            let l = i < lhs.values.count ? lhs.values[i] : (lhs.values.last ?? 0)
            let r = i < rhs.values.count ? rhs.values[i] : (rhs.values.last ?? 0)
            return l - r
        })
    }

    mutating func scale(by rhs: Double) { values = values.map { $0 * rhs } }

    var magnitudeSquared: Double { values.reduce(0) { $0 + $1 * $1 } }
}

// MARK: - Chart Canvas

struct ChartCanvasView: View {

    @ObservedObject var chartVM: StockChartViewModel
    @Binding var selectedPoint:  StockDataPoint?
    @Binding var isDragging:     Bool
    @Binding var chartSize:      CGSize

    let accentColor:       Color
    let displayIsPositive: Bool

    // State untuk animasi morphing (non-1D ranges)
    // AnimatableChartData membawa MorphPoint(x, y) — kedua efek berjalan dalam satu pass:
    // • Efek 1: X Spacing Morph  — pow(t, exponent) berbeda per TimeRange
    // • Efek 2: Path Tweening    — padded(to:) clone titik terakhir saat count berbeda
    @State private var animatedData: AnimatableChartData = .zero

    // State untuk 1H: data siap render + clip width yang dianimasikan
    @State private var oneDayReady:        Bool    = false
    @State private var oneDayClipWidth:    CGFloat = 0
    /// true setelah 1H pernah ditampilkan — membedakan "pertama buka" vs "transisi dari range lain"
    @State private var hasEverLoadedOneDay: Bool   = false

    private let resampleCount = 300   // resolusi tinggi — chart tetap tajam di retina

    var body: some View {
        ZStack {
            // Render condition:
            // • 1H + pertama buka (oneDayReady=true)  → pakai renderer 1H + AnimatableClipRect
            // • 1H + transisi dari range lain (oneDayReady=false) → pakai MorphingXYLineShape seperti range lain
            // • range lain → animatedData sudah terisi
            let shouldShow = chartSize.height > 0 &&
                (oneDayReady || !animatedData.points.isEmpty)

            if shouldShow {
                chartContent
            } else if chartVM.dataPoints.isEmpty && !chartVM.isLoading {
                Text("Data tidak tersedia")
                    .font(.caption).foregroundColor(.secondary)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
        }
        .frame(maxWidth: .infinity)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color.appCardBackground)

        )
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .contentShape(Rectangle().inset(by: -40))
        .gesture(dragGesture)
        // Trigger morphing / draw: isLoading false → data baru siap
        .onChange(of: chartVM.isLoading) { _, isLoading in
            guard !isLoading, !chartVM.dataPoints.isEmpty else { return }

            if chartVM.selectedRange == .oneDay {
                // ── Masuk ke 1H ──────────────────────────────────────────────────
                // Hitung target MorphPoints untuk 1H: titik berhenti di xLast,
                // sisanya di-pad dengan titik terakhir (garis flat ke kanan).
                let oneDayTarget = buildMorphPoints(chartVM.dataPoints,
                                                   range: chartVM.selectedRange,
                                                   size: chartSize)

                // Hitung xLast (pixel) agar kita tahu clip final-nya
                let lastSlotIdx = chartVM.oneDaySlotIndex(for: chartVM.dataPoints.last!.date)
                let innerW      = chartSize.width - 8
                let xLast       = 4 + CGFloat(lastSlotIdx) / CGFloat(StockChartViewModel.oneDayTotalSlots - 1) * innerW
                let targetClip  = min(xLast + 4, chartSize.width)

                if !hasEverLoadedOneDay {
                    // ── Pertama kali 1H ditampilkan sejak view dibuka → grow kiri ke kanan ──
                    animatedData        = oneDayTarget
                    hasEverLoadedOneDay = true
                    oneDayReady         = true
                    oneDayClipWidth     = 0
                    DispatchQueue.main.async {
                        withAnimation(.easeInOut(duration: 1.2)) {
                            oneDayClipWidth = targetClip
                        }
                    }
                } else {
                    // ── Datang dari range lain → spring morph menyusut ke xLast ──
                    // Tidak ada handoff: chart tetap pakai MorphingXYLineShape (oneDayReady = false).
                    // Setelah spring selesai chart sudah berhenti di xLast — tidak perlu switch renderer.
                    oneDayReady = false
                    withAnimation(.spring(response: 1.2, dampingFraction: 1.0)) {
                        animatedData = oneDayTarget
                    }
                }
            } else {
                // ── Masuk ke range lain (termasuk keluar dari 1H) ────────────────
                // animatedData harus sudah mencerminkan posisi 1H aktual
                // (di-set saat masuk ke 1H) sehingga garis "tumbuh" dari titik terakhir 1H.
                oneDayReady = false
                let target = buildMorphPoints(chartVM.dataPoints,
                                             range: chartVM.selectedRange,
                                             size: chartSize)
                // Jika belum ada data sebelumnya, mulai dari garis flat tengah
                if animatedData.points.isEmpty {
                    let flatPoints = (0..<resampleCount).map { i -> MorphPoint in
                        let t  = CGFloat(i) / CGFloat(resampleCount - 1)
                        return MorphPoint(x: t * chartSize.width, y: chartSize.height / 2)
                    }
                    animatedData = AnimatableChartData(points: flatPoints)
                }
                withAnimation(.spring(response: 1.55, dampingFraction: 1.0)) {
                    animatedData = target
                }
            }
        }
    }

    // MARK: Chart Content

    private var chartContent: some View {
        let data   = chartVM.dataPoints
        let minP   = chartVM.minPrice
        let maxP   = chartVM.maxPrice
        let startP = chartVM.startPrice
        let lastP  = chartVM.latestPrice
        let isOneDay = chartVM.selectedRange == .oneDay && oneDayReady

        let yMax      = yPos(for: maxP,   in: chartSize)
        let yMin      = yPos(for: minP,   in: chartSize)
        let yBaseline = yPos(for: startP, in: chartSize)
        let yLast     = yPos(for: lastP,  in: chartSize)

        let greenColor = Color(hex: "00D4AA")
        let redColor   = Color(hex: "FF4757")

        // ── 1H: bangun OneDayLineShape.Point dari slot index ──
        let oneDayPoints: [OneDayLineShape.Point] = isOneDay ? {
            let closes = data.map(\.close)
            let minV   = closes.min() ?? minP
            let maxV   = closes.max() ?? maxP
            let range  = maxV - minV
            return data.map { pt in
                OneDayLineShape.Point(
                    slotIndex: chartVM.oneDaySlotIndex(for: pt.date),
                    normY: range > 0 ? (pt.close - minV) / range : 0.5
                )
            }
        }() : []

        return ZStack {
            // ── Grid lines max & min ─────────────────────────────────────────
            DashLine(from: CGPoint(x: 0, y: yMax), to: CGPoint(x: chartSize.width, y: yMax))
                .stroke(Color.secondary.opacity(0.25), style: StrokeStyle(lineWidth: 1, dash: [4, 3]))
            DashLine(from: CGPoint(x: 0, y: yMin), to: CGPoint(x: chartSize.width, y: yMin))
                .stroke(Color.secondary.opacity(0.25), style: StrokeStyle(lineWidth: 1, dash: [4, 3]))

            // ── Baseline (startPrice) — kuning tipis ─────────────────────────
//            DashLine(from: CGPoint(x: 0, y: yBaseline),
//                     to:   CGPoint(x: chartSize.width, y: yBaseline))
//                .stroke(Color(hex: "EAB308").opacity(0.50),
//                        style: StrokeStyle(lineWidth: 1, dash: [6, 4]))
            AnimatableHDashLine(y: yBaseline)
                .stroke(Color(hex: "EAB308").opacity(0.50),
                        style: StrokeStyle(lineWidth: 1, dash: [6, 4]))
                .animation(.spring(response: 1.55, dampingFraction: 1.0), value: yBaseline)

            if isOneDay {
                // ── 1H: semua layer (shadow + line + dot) dibungkus dalam satu ZStack ──
                // lalu di-clip oleh AnimatableClipRect yang lebarnya tumbuh kiri→kanan.
                // Karena clip-nya satu dan animatable, shadow, line, dan dot selalu sinkron.

                // Hitung posisi X dot dari slot index (sama dengan cara targetClip dihitung)
                let lastSlotIdx = data.isEmpty ? 0 : chartVM.oneDaySlotIndex(for: data.last!.date)
                let innerW      = chartSize.width - 8
                let dotX        = 4 + CGFloat(lastSlotIdx) / CGFloat(StockChartViewModel.oneDayTotalSlots - 1) * innerW
                let dotColor    = lastP >= startP ? greenColor : redColor

                ZStack {
                    // Shadow hijau (atas baseline)
                    OneDayAreaShape(points: oneDayPoints,
                                    totalSlots: StockChartViewModel.oneDayTotalSlots,
                                    hPad: 4, closingY: yBaseline)
                        .fill(LinearGradient(
                            stops: [
                                .init(color: greenColor.opacity(0.38), location: 0.0),  // tebal di atas
                                .init(color: greenColor.opacity(0.18), location: 0.5),
                                .init(color: greenColor.opacity(0.0),  location: 1.0),  // transparan di bawah
                            ],
                            startPoint: .top, endPoint: .bottom
                        ))
                        .clipShape(Rectangle().path(in: CGRect(
                            x: 0, y: 0, width: chartSize.width, height: yBaseline)))

                    // Shadow merah (bawah baseline)
                    OneDayAreaShape(points: oneDayPoints,
                                    totalSlots: StockChartViewModel.oneDayTotalSlots,
                                    hPad: 4, closingY: yBaseline)
                        .fill(LinearGradient(
                            stops: [
                                .init(color: redColor.opacity(0.38), location: 0.0),
                                .init(color: redColor.opacity(0.18), location: 0.5),
                                .init(color: redColor.opacity(0.0),  location: 1.0),
                            ],
                            startPoint: .bottom, endPoint: .top
                        ))
                        .clipShape(Rectangle().path(in: CGRect(
                            x: 0, y: yBaseline,
                            width: chartSize.width, height: chartSize.height - yBaseline)))

                    // Line hijau (atas baseline)
                    OneDayLineShape(points: oneDayPoints,
                                    totalSlots: StockChartViewModel.oneDayTotalSlots,
                                    hPad: 4)
                        .stroke(greenColor, style: StrokeStyle(lineWidth: 2.2, lineCap: .round, lineJoin: .round))
                        .clipShape(Rectangle().path(in: CGRect(
                            x: 0, y: 0, width: chartSize.width, height: yBaseline)))

                    // Line merah (bawah baseline)
                    OneDayLineShape(points: oneDayPoints,
                                    totalSlots: StockChartViewModel.oneDayTotalSlots,
                                    hPad: 4)
                        .stroke(redColor, style: StrokeStyle(lineWidth: 2.2, lineCap: .round, lineJoin: .round))
                        .clipShape(Rectangle().path(in: CGRect(
                            x: 0, y: yBaseline,
                            width: chartSize.width, height: chartSize.height - yBaseline)))

                    // ── Last price dot & dashed line — di dalam clip agar muncul
                    //    bersama ujung garis saat animasi grow kiri→kanan ──────────
                    if !isDragging {
                        AnimatableHDashLine(y: yLast)
                            .stroke(dotColor.opacity(0.70),
                                    style: StrokeStyle(lineWidth: 1.5, dash: [5, 3]))

                        Circle().fill(dotColor)
                            .frame(width: 9, height: 9)
                            .shadow(color: dotColor.opacity(0.7), radius: 5)
                            .position(x: dotX, y: yLast)
                        Circle().fill(Color.white)
                            .frame(width: 4, height: 4)
                            .position(x: dotX, y: yLast)
                    }
                }
                // Satu AnimatableClipRect mengontrol semua layer — shadow, line, dan dot tumbuh bersama
                .clipShape(AnimatableClipRect(clipWidth: oneDayClipWidth))

            } else {
                // ── Range lain: MorphingXYAreaShape + MorphingXYLineShape (spring morphing) ──
                // Kedua shape membaca MorphPoint(x, y) langsung — tidak perlu konversi Y lagi.

                MorphingXYAreaShape(data: animatedData, closingY: yBaseline)
                    .fill(LinearGradient(
                        stops: [
                            .init(color: greenColor.opacity(0.38), location: 0.0),  // tebal di atas
                            .init(color: greenColor.opacity(0.18), location: 0.5),
                            .init(color: greenColor.opacity(0.0),  location: 1.0),  // transparan di bawah
                        ],
                        startPoint: .top, endPoint: .bottom
                    ))
                    .clipShape(AnimatableClipAbove(cutY: yBaseline))
                    .animation(.spring(response: 1.55, dampingFraction: 1.0), value: yBaseline)

                MorphingXYAreaShape(data: animatedData, closingY: yBaseline)
                    .fill(LinearGradient(
                        stops: [
                            .init(color: redColor.opacity(0.38), location: 0.0),
                            .init(color: redColor.opacity(0.18), location: 0.5),
                            .init(color: redColor.opacity(0.0),  location: 1.0),
                        ],
                        startPoint: .bottom, endPoint: .top
                    ))
                    .clipShape(AnimatableClipBelow(cutY: yBaseline, totalHeight: chartSize.height))
                    .animation(.spring(response: 1.55, dampingFraction: 1.0), value: yBaseline)

                MorphingXYLineShape(data: animatedData)
                    .stroke(greenColor, style: StrokeStyle(lineWidth: 2.2, lineCap: .round, lineJoin: .round))
                    .clipShape(AnimatableClipAbove(cutY: yBaseline))
                    .animation(.spring(response: 1.55, dampingFraction: 1.0), value: yBaseline)

                MorphingXYLineShape(data: animatedData)
                    .stroke(redColor, style: StrokeStyle(lineWidth: 2.2, lineCap: .round, lineJoin: .round))
                    .clipShape(AnimatableClipBelow(cutY: yBaseline, totalHeight: chartSize.height))
                    .animation(.spring(response: 1.55, dampingFraction: 1.0), value: yBaseline)
            }

            // ── Label max & min ──────────────────────────────────────────────
            Text("Max \(formatIDR(maxP))")
                .font(.system(size: 9, weight: .semibold))
                .foregroundColor(.secondary)
                .padding(.horizontal, 4).padding(.vertical, 2)
            // .background(Color(.systemBackground).opacity(0.85))
                .background(Color(hex: "1e1d40").opacity(0.85))
                .cornerRadius(4)
                .position(x: chartSize.width - 34, y: yMax - 10)

            Text("Min \(formatIDR(minP))")
                .font(.system(size: 9, weight: .semibold))
                .foregroundColor(.secondary)
                .padding(.horizontal, 4).padding(.vertical, 2)
                .background(Color.appCardBackground.opacity(0.85))

                .cornerRadius(4)
                .position(x: chartSize.width - 34, y: yMin + 10)

            // ── Last price line & dot (non-1D ranges) ───────────────────────
            // Untuk isOneDay: dot sudah dirender di dalam ZStack yang di-clip
            // AnimatableClipRect, sehingga muncul bersama ujung garis.
            // Untuk range lain: dot ikut spring morph via animatedData.
            if !isDragging && !isOneDay {
                let dotColor = lastP >= startP ? greenColor : redColor

                // Ambil posisi dari animatedData agar dot & dashed line ikut morph
                let animX = animatedData.points.last.map { $0.x } ?? xFor(index: data.count - 1, count: data.count, width: chartSize.width)
                let animY = animatedData.points.last.map { $0.y } ?? yLast

                // AnimatableHDashLine: Y ikut diinterpolasi SwiftUI frame-by-frame
                // dengan spring yang sama → garis bergerak mulus bersama dot
                AnimatableHDashLine(y: animY)
                    .stroke(dotColor.opacity(0.70),
                            style: StrokeStyle(lineWidth: 1.5, dash: [5, 3]))
                    .animation(.spring(response: 1.55, dampingFraction: 1.0), value: animY)

                Circle().fill(dotColor)
                    .frame(width: 9, height: 9)
                    .shadow(color: dotColor.opacity(0.7), radius: 5)
                    .position(x: animX, y: animY)
                Circle().fill(Color.white)
                    .frame(width: 4, height: 4)
                    .position(x: animX, y: animY)
            }

            // ── Crosshair saat drag ──────────────────────────────────────────
            if isDragging, let point = selectedPoint {
                let ptColor = point.close >= startP ? greenColor : redColor
                CrosshairView(
                    point:      point,
                    chartVM:    chartVM,
                    chartSize:  chartSize,
                    accentColor: ptColor,
                    xPos: xFor(index: data.firstIndex(where: { $0.id == point.id }) ?? 0,
                               count: data.count, width: chartSize.width),
                    yPos: yPos(for: point.close, in: chartSize)
                )
            }
        }
    }

    // MARK: - Drag Gesture

    private var dragGesture: some Gesture {
        DragGesture(minimumDistance: 0)
            .onChanged { val in
                isDragging = true
                let data = chartVM.dataPoints
                guard !data.isEmpty, chartSize.width > 0 else { return }

                let innerWidth = chartSize.width - 8   // hPad 8 kiri & kanan
                let clampedX   = max(0, min(val.location.x - 4, innerWidth))

                let nearest: StockDataPoint

                if chartVM.selectedRange == .oneDay {
                    // 1H: X berdasarkan slot index di antara 81 total slot
                    let totalSlots = StockChartViewModel.oneDayTotalSlots
                    let slotFrac   = clampedX / innerWidth * CGFloat(totalSlots - 1)
                    let targetSlot = Int(slotFrac.rounded())
                    // Cari data point dengan slot index terdekat
                    nearest = data.min(by: {
                        abs(chartVM.oneDaySlotIndex(for: $0.date) - targetSlot) <
                        abs(chartVM.oneDaySlotIndex(for: $1.date) - targetSlot)
                    }) ?? data[0]
                } else {
                    // Range lain (1M, 3M, YTD, 1Y, 5Y):
                    // Titik di chart diposisikan dengan pow(t, xSpacingExponent) — non-linear.
                    // animatedData.points menyimpan X aktual setiap titik (sudah ter-morph).
                    // Cari titik yang X-nya paling dekat dengan posisi jari untuk akurasi penuh.
                    let touchX = clampedX + 4  // kompensasi hPad=4 (chart mulai dari x=4)
                    if !animatedData.points.isEmpty {
                        let bestMorphIdx = animatedData.points.indices.min(by: {
                            abs(animatedData.points[$0].x - touchX) <
                            abs(animatedData.points[$1].x - touchX)
                        }) ?? 0
                        // Map morph index (0..<resampleCount) ke data index (0..<data.count)
                        let dataFrac = CGFloat(bestMorphIdx) / CGFloat(max(animatedData.points.count - 1, 1))
                        let i = max(0, min(Int((dataFrac * CGFloat(data.count - 1)).rounded()), data.count - 1))
                        nearest = data[i]
                    } else {
                        // Fallback linear jika animatedData belum siap
                        let denominator = CGFloat(max(data.count - 1, 1))
                        let rawIndex    = (clampedX / innerWidth) * denominator
                        let i           = max(0, min(Int(rawIndex.rounded()), data.count - 1))
                        nearest = data[i]
                    }
                }

                if nearest.id != selectedPoint?.id {
                    selectedPoint = nearest
                    UIImpactFeedbackGenerator(style: .light).impactOccurred()
                }
            }
            .onEnded { _ in
                withAnimation(.easeOut(duration: 0.25)) {
                    isDragging    = false
                    selectedPoint = nil
                }
            }
    }

    // MARK: - Build MorphPoints (Efek 1 + Efek 2 sekaligus)
    //
    // Menghasilkan AnimatableChartData dengan MorphPoint(x, y) dimana:
    // • x = pow(t, exponent) * width   → X Spacing Morph per TimeRange
    // • y = normalized vertical position
    //
    // Untuk .oneDay: titik diresample hanya sampai xLast (slot terakhir),
    // lalu sisa slot di-pad dengan titik terakhir → garis flat ke kanan.
    // Ini memungkinkan tweening "tumbuh" (1H → range lain) dan "menyusut"
    // (range lain → 1H): AnimatableChartData.padded(to:) mengklone titik
    // terakhir sehingga garis bergerak dari/ke ujung xLast secara mulus.
    //
    // Untuk range lain: sama seperti sebelumnya (resampleCount titik penuh).

    private func buildMorphPoints(
        _ data: [StockDataPoint],
        range: TimeRange,
        size: CGSize
    ) -> AnimatableChartData {
        guard data.count > 1, size.width > 0, size.height > 0 else {
            return .zero
        }

        let closes  = data.map(\.close)
        let minV    = closes.min()!
        let maxV    = closes.max()!
        let vRange  = maxV - minV

        let topPad: CGFloat    = 20
        let bottomPad: CGFloat = 20
        let hPad: CGFloat      = 4
        let usable    = size.height - topPad - bottomPad
        let innerW    = size.width  - hPad * 2

        if range == .oneDay {
            // ── 1H: bangun titik berdasarkan slot index, bukan resampleCount ──
            // Titik aktual: slot 0…lastSlotIdx; slot sisanya di-pad titik terakhir.
            // Dengan begitu AnimatableChartData.padded(to: resampleCount) identik
            // dengan resampleCount titik yang dipakai range lain → tweening mulus.

            let totalSlots = StockChartViewModel.oneDayTotalSlots  // 81
            let lastSlotIdx = chartVM.oneDaySlotIndex(for: data.last!.date)

            // Resample nilai Y ke resampleCount titik, tapi hanya untuk area
            // 0…lastSlotIdx; titik setelah itu dikopi dari titik terakhir.
            // X dihitung dari slot index → sesuai dengan spacing 1H sebenarnya.

            var morphPoints: [MorphPoint] = []
            morphPoints.reserveCapacity(resampleCount)

            for i in 0..<resampleCount {
                let slotFrac = CGFloat(i) / CGFloat(resampleCount - 1) * CGFloat(totalSlots - 1)
                let slot     = Int(slotFrac)   // slot index 0…80 yang di-map ke titik ini

                let x: CGFloat
                let y: CGFloat

                if slot <= lastSlotIdx {
                    // Interpolasi nilai Y: skala i ke rentang data aktual saja
                    let activeFrac = CGFloat(lastSlotIdx) / CGFloat(totalSlots - 1)
                    let dataFrac   = (slotFrac / CGFloat(totalSlots - 1)) / max(activeFrac, 1e-6) * CGFloat(data.count - 1)
//                    let lo   = Int(dataFrac)
//                    let hi   = min(lo + 1, data.count - 1)
//                    let frac = dataFrac - CGFloat(lo)
//                    let val  = closes[lo] * Double(1 - frac) + closes[hi] * Double(frac)
                    let lo   = max(0, min(Int(dataFrac), data.count - 1))  // ← clamp lo juga
                    let hi   = min(lo + 1, data.count - 1)
                    let frac = dataFrac - CGFloat(lo)
                    let val  = closes[lo] * Double(1 - frac) + closes[hi] * Double(frac)

                    let normY = vRange > 0 ? (val - minV) / vRange : 0.5
                    y = topPad + usable * CGFloat(1.0 - normY)
                    x = hPad + slotFrac / CGFloat(totalSlots - 1) * innerW
                } else {
                    // Di luar data aktual: semua titik menumpuk TEPAT di xLast.
                    // Keluar dari 1H → titik ini "tumbuh" ke kanan saat spring morph.
                    // Masuk ke 1H   → titik dari kanan "menyusut" kembali ke xLast.
                    let lastVal = closes.last!
                    let normY   = vRange > 0 ? (lastVal - minV) / vRange : 0.5
                    y = topPad + usable * CGFloat(1.0 - normY)
                    x = hPad + CGFloat(lastSlotIdx) / CGFloat(totalSlots - 1) * innerW
                }

                morphPoints.append(MorphPoint(x: x, y: y))
            }

            return AnimatableChartData(points: morphPoints)

        } else {
            // ── Range lain: resample penuh ke resampleCount (tidak berubah) ──
            let exponent = range.xSpacingExponent

            let points: [MorphPoint] = (0..<resampleCount).map { i in
                let tData = Double(i) / Double(resampleCount - 1) * Double(data.count - 1)
                //let lo    = Int(tData)
                //let hi    = min(lo + 1, data.count - 1)
                let lo    = max(0, min(Int(tData), data.count - 1))  // ← clamp lo
                let hi    = min(lo + 1, data.count - 1)
                let frac  = tData - Double(lo)
                let val   = closes[lo] * (1 - frac) + closes[hi] * frac

                let normY = vRange > 0 ? (val - minV) / vRange : 0.5
                let y     = topPad + usable * CGFloat(1.0 - normY)

                let t = CGFloat(i) / CGFloat(resampleCount - 1)
                let x = hPad + pow(t, exponent) * innerW

                return MorphPoint(x: x, y: y)
            }

            return AnimatableChartData(points: points)
        }
    }

    private func padOrTrim(_ nd: NormalizedChartData, to count: Int) -> NormalizedChartData {
        var vals = nd.values
        if vals.count < count {
            vals += Array(repeating: vals.last ?? 0.5, count: count - vals.count)
        } else if vals.count > count {
            vals = Array(vals.prefix(count))
        }
        return NormalizedChartData(values: vals)
    }

    // MARK: - Coordinate Helpers

    private func xFor(index: Int, count: Int, width: CGFloat) -> CGFloat {
        let innerWidth = width - 8  // hPad 4 kiri & kanan
        if chartVM.selectedRange == .oneDay {
            // 1H: posisi X berdasarkan slot index di antara 81 total slot
            let data = chartVM.dataPoints
            guard index < data.count else {
                return 4 + CGFloat(index) / CGFloat(max(count - 1, 1)) * innerWidth
            }
            let slotIdx = chartVM.oneDaySlotIndex(for: data[index].date)
            return 4 + CGFloat(slotIdx) / CGFloat(StockChartViewModel.oneDayTotalSlots - 1) * innerWidth
        }
        // Non-1D: gunakan X yang sudah termorphing dari animatedData
        // Cari titik di animatedData yang paling mendekati index yang diminta
        guard !animatedData.points.isEmpty else {
            return 4 + CGFloat(index) / CGFloat(max(count - 1, 1)) * innerWidth
        }
        let fraction = CGFloat(index) / CGFloat(max(count - 1, 1))
        let ptIndex  = Int((fraction * CGFloat(animatedData.points.count - 1)).rounded())
            .clamped(to: 0...(animatedData.points.count - 1))
        return animatedData.points[ptIndex].x
    }

    private func yPos(for value: Double, in size: CGSize) -> CGFloat {
        let topPad: CGFloat = 20, bottomPad: CGFloat = 20
        let usable = size.height - topPad - bottomPad
        guard usable > 0 else { return size.height / 2 }
        let range = chartVM.maxPrice - chartVM.minPrice
        let norm  = range > 0 ? (value - chartVM.minPrice) / range : 0.5
        return topPad + usable * (1 - norm)
    }
}

// MARK: - Dash Line Shape

struct DashLine: Shape {
    let from: CGPoint
    let to:   CGPoint

    func path(in rect: CGRect) -> Path {
        var p = Path()
        p.move(to: from)
        p.addLine(to: to)
        return p
    }
}

/// Horizontal dashed line dengan Y yang animatable — ikut morph bersama dot.
struct AnimatableHDashLine: Shape {
    var y: CGFloat

    var animatableData: CGFloat {
        get { y }
        set { y = newValue }
    }

    func path(in rect: CGRect) -> Path {
        var p = Path()
        p.move(to: CGPoint(x: 0, y: y))
        p.addLine(to: CGPoint(x: rect.width, y: y))
        return p
    }
}


// MARK: - One Day Line Shape
// Menggambar line chart 1H dengan X berdasarkan slot index (0-80 dari 81 total slot).
// Mendukung .trim(from:to:) untuk animasi left-to-right.

struct OneDayLineShape: Shape {
    /// Titik data: (slotIndex 0-80, normalizedY 0-1)
    struct Point {
        let slotIndex: Int   // posisi di antara 81 slot
        let normY:     Double // Y ternormalisasi [0…1]
    }

    var points:      [Point]
    var totalSlots:  Int     // 81
    var hPad:        CGFloat // 12

    func path(in rect: CGRect) -> Path {
        guard points.count > 1 else { return Path() }

        let topPad: CGFloat    = 20, bottomPad: CGFloat = 20
        let usable: CGFloat    = rect.height - topPad - bottomPad
        let innerWidth: CGFloat = rect.width - hPad * 2
        guard usable > 0, innerWidth > 0 else { return Path() }

        func cgPoint(_ p: Point) -> CGPoint {
            CGPoint(
                x: hPad + CGFloat(p.slotIndex) / CGFloat(totalSlots - 1) * innerWidth,
                y: topPad + usable * CGFloat(1.0 - p.normY)
            )
        }

        var path = Path()
        path.move(to: cgPoint(points[0]))

        // Polyline lurus — data 1D sudah di-forward-fill ke slot seragam,
        // sehingga garis lurus sudah akurat. Catmull-Rom tidak dipakai di sini
        // karena titik-titik slot bisa tidak merata (gap jam istirahat) sehingga
        // kurva menjadi "melengkung palsu" yang tidak mencerminkan data asli.
        for i in 1..<points.count {
            path.addLine(to: cgPoint(points[i]))
        }
        return path
    }
}

/// Shape yang bisa dianimasikan — clip rectangle dari x=0 hingga x=clipWidth
struct AnimatableClipRect: Shape {
    var clipWidth: CGFloat

    var animatableData: CGFloat {
        get { clipWidth }
        set { clipWidth = newValue }
    }

    func path(in rect: CGRect) -> Path {
        Path(CGRect(x: 0, y: 0, width: max(0, clipWidth), height: rect.height))
    }
}

/// Clip mask: semua area dari y=0 hingga y=cutY (area di atas garis baseline — untuk shadow hijau)
struct AnimatableClipAbove: Shape {
    var cutY: CGFloat

    var animatableData: CGFloat {
        get { cutY }
        set { cutY = newValue }
    }

    func path(in rect: CGRect) -> Path {
        Path(CGRect(x: 0, y: 0, width: rect.width, height: max(0, cutY)))
    }
}

/// Clip mask: semua area dari y=cutY hingga bawah (area di bawah garis baseline — untuk shadow merah)
struct AnimatableClipBelow: Shape {
    var cutY: CGFloat
    var totalHeight: CGFloat

    var animatableData: AnimatablePair<CGFloat, CGFloat> {
        get { AnimatablePair(cutY, totalHeight) }
        set { cutY = newValue.first; totalHeight = newValue.second }
    }

    func path(in rect: CGRect) -> Path {
        let h = max(0, totalHeight - cutY)
        return Path(CGRect(x: 0, y: cutY, width: rect.width, height: h))
    }
}

/// Area fill untuk 1H — sama seperti OneDayLineShape tapi ditutup ke closingY
struct OneDayAreaShape: Shape {
    var points:     [OneDayLineShape.Point]
    var totalSlots: Int
    var hPad:       CGFloat
    var closingY:   CGFloat

    func path(in rect: CGRect) -> Path {
        guard points.count > 1 else { return Path() }

        let topPad: CGFloat    = 20, bottomPad: CGFloat = 20
        let usable: CGFloat    = rect.height - topPad - bottomPad
        let innerWidth: CGFloat = rect.width - hPad * 2
        guard usable > 0, innerWidth > 0 else { return Path() }

        func cgPoint(_ p: OneDayLineShape.Point) -> CGPoint {
            CGPoint(
                x: hPad + CGFloat(p.slotIndex) / CGFloat(totalSlots - 1) * innerWidth,
                y: topPad + usable * CGFloat(1.0 - p.normY)
            )
        }

        var path = Path()
        path.move(to: cgPoint(points[0]))

        // Polyline lurus — konsisten dengan OneDayLineShape.
        // Catmull-Rom dihindari karena interval slot tidak selalu seragam
        // (ada gap jam istirahat) sehingga kurva Catmull-Rom melengkung tidak wajar.
        for i in 1..<points.count {
            path.addLine(to: cgPoint(points[i]))
        }

        let lastX = hPad + CGFloat(points.last!.slotIndex) / CGFloat(totalSlots - 1) * innerWidth
        let firstX = hPad + CGFloat(points.first!.slotIndex) / CGFloat(totalSlots - 1) * innerWidth
        path.addLine(to: CGPoint(x: lastX,  y: closingY))
        path.addLine(to: CGPoint(x: firstX, y: closingY))
        path.closeSubpath()
        return path
    }
}

// MARK: - Crosshair View

struct CrosshairView: View {

    let point:       StockDataPoint
    let chartVM:     StockChartViewModel
    let chartSize:   CGSize
    let accentColor: Color
    let xPos:        CGFloat
    let yPos:        CGFloat

    var body: some View {
        ZStack {
            // Horizontal drag line
            DashLine(from: CGPoint(x: 0, y: yPos),
                     to:   CGPoint(x: chartSize.width, y: yPos))
                .stroke(accentColor.opacity(0.6),
                        style: StrokeStyle(lineWidth: 2, dash: [5, 3]))

            // Vertical line
            DashLine(from: CGPoint(x: xPos, y: 0),
                     to:   CGPoint(x: xPos, y: chartSize.height))
                .stroke(Color.primary.opacity(0.25),
                        style: StrokeStyle(lineWidth: 1, dash: [4, 4]))

            // Dot
            Circle().fill(accentColor)
                .frame(width: 13, height: 13)
                .shadow(color: accentColor.opacity(0.7), radius: 6)
                .position(x: xPos, y: yPos)
            Circle().fill(Color.white)
                .frame(width: 5, height: 5)
                .position(x: xPos, y: yPos)

            // Tooltip (hanya tanggal, di atas chart)
            TooltipView(
                date:       point.date,
                range:      chartVM.selectedRange,
                xPos:       xPos,
                chartWidth: chartSize.width
            )
        }
    }
}

// MARK: - Tooltip View

struct TooltipView: View {

    let date:       Date
    let range:      TimeRange
    let xPos:       CGFloat
    let chartWidth: CGFloat

    private let h: CGFloat   = 26
    private let pad: CGFloat = 4

    private var text: String {
        let df = DateFormatter()
        df.locale     = Locale(identifier: "id_ID")
        df.timeZone   = TimeZone(identifier: "Asia/Jakarta")!
        df.dateFormat = range.isIntraday ? "d MMM 'at' HH:mm" : "d MMM yyyy"
        return df.string(from: date)
    }

    private var estimatedWidth: CGFloat {
        CGFloat(text.count) * 7.5 + 20
    }

    private var clampedX: CGFloat {
        var x = xPos - estimatedWidth / 2
        x = max(pad, min(x, chartWidth - estimatedWidth - pad))
        return x + estimatedWidth / 2
    }

    var body: some View {
        Text(text)
            .font(.system(size: 11, weight: .semibold))
            .foregroundColor(.primary)
            .padding(.horizontal, 0).padding(.vertical, 4)
            .frame(height: h)
            .background(
                RoundedRectangle(cornerRadius: 6)
                    .fill(Color(.systemBackground))
                    .overlay(
                        RoundedRectangle(cornerRadius: 6)
                            .stroke(Color.primary.opacity(0.08), lineWidth: 1)
                    )
                    .shadow(color: .black.opacity(0.12), radius: 4, x: 0, y: 2)
            )
            .position(x: clampedX, y: h / 2 + 4)
            .transition(.opacity)
    }
}

import SwiftUI

// MARK: - Axis Tick Model

/// A single tick on the X-axis.
/// `id` is stable across range changes when the same logical position
/// (e.g. "first label", "second label") survives a transition.
/// We assign IDs 0…(maxTicks-1) so the same ordinal position maps to
/// the same SwiftUI identity — enabling matched-geometry-style diffing.
struct AxisTick: Identifiable, Equatable {
    /// Ordinal index within the tick set (0-based).  Used as SwiftUI identity.
    let id:         Int
    /// Normalised X position [0…1] where 0 = left edge, 1 = right edge of inner chart.
    let normX:      Double
    /// Display label string.
    let label:      String
}

// MARK: - Tick Generator

enum AxisTickGenerator {

    private static var jakartaCal: Calendar = {
        var c = Calendar(identifier: .gregorian)
        c.timeZone = TimeZone(identifier: "Asia/Jakarta")!
        return c
    }()

    // MARK: - Public entry point

    static func ticks(for data: [StockDataPoint],
                      range: TimeRange,
                      chartVM: StockChartViewModel) -> [AxisTick] {
        guard !data.isEmpty else { return [] }
        switch range {
        case .oneDay:     return oneDayTicks(data: data, chartVM: chartVM)
        case .oneWeek:    return oneWeekTicks(data: data)
        case .oneMonth:   return oneMonthTicks(data: data)
        case .threeMonth: return threeMonthTicks(data: data)
        case .ytd:        return ytdTicks(data: data)
        case .oneYear:    return oneYearTicks(data: data)
        case .fiveYear:   return fiveYearTicks(data: data)
        }
    }

    // MARK: - Helpers

    /// Kumpulkan index pertama setiap hari kalender (WIB) dalam array data.
    private static func firstIndexPerDay(_ data: [StockDataPoint]) -> [(index: Int, date: Date)] {
        var seen = Set<String>()
        var result: [(Int, Date)] = []
        let df = DateFormatter()
        df.timeZone   = TimeZone(identifier: "Asia/Jakarta")!
        df.dateFormat = "yyyy-MM-dd"
        for (i, pt) in data.enumerated() {
            let key = df.string(from: pt.date)
            if !seen.contains(key) { seen.insert(key); result.append((i, pt.date)) }
        }
        return result
    }

    /// Kumpulkan index pertama setiap bulan kalender (WIB) dalam array data.
    /// Mengembalikan dict "yyyy-MM" → first index, diurutkan.
    private static func firstIndexPerMonth(_ data: [StockDataPoint]) -> [(key: String, index: Int, date: Date)] {
        var buckets: [String: (Int, Date)] = [:]
        let df = DateFormatter()
        df.timeZone   = TimeZone(identifier: "Asia/Jakarta")!
        df.dateFormat = "yyyy-MM"
        for (i, pt) in data.enumerated() {
            let key = df.string(from: pt.date)
            if buckets[key] == nil { buckets[key] = (i, pt.date) }
        }
        return buckets.keys.sorted().compactMap { k in
            buckets[k].map { (k, $0.0, $0.1) }
        }
    }

    /// Cari index data point terdekat dengan `targetDate`.
    private static func nearestIndex(in data: [StockDataPoint], to targetDate: Date) -> Int? {
        data.enumerated().min(by: {
            abs($0.element.date.timeIntervalSince(targetDate)) <
            abs($1.element.date.timeIntervalSince(targetDate))
        })?.offset
    }

    // MARK: - 1D ───────────────────────────────────────────────────────────────

    private static func oneDayTicks(data: [StockDataPoint],
                                    chartVM: StockChartViewModel) -> [AxisTick] {
        guard let firstDate = data.first?.date else { return [] }
        let weekday = jakartaCal.component(.weekday, from: firstDate)
        let totalSlots = StockChartViewModel.oneDayTotalSlots  // 81

        let lastSlotIndex: Int = {
            guard let lastPt = data.last else { return 0 }
            let h = jakartaCal.component(.hour,   from: lastPt.date)
            let m = jakartaCal.component(.minute, from: lastPt.date)
            let mins = (h * 60 + m) - (StockChartViewModel.oneDayOpenHour * 60
                                        + StockChartViewModel.oneDayOpenMinute)
            return max(0, min(mins / 5, totalSlots - 1))
        }()

        let candidates: [(hour: Int, minute: Int, label: String)] = weekday == 6
            ? [(9,30,"09:30"),(10,30,"10:30"),(11,30,"11:30"),(14,0,"14:00"),(15,0,"15:00")]
            : [(10,0,"10:00"),(11,0,"11:00"),(12,0,"12:00"),(13,30,"13:30"),(14,30,"14:30"),(15,30,"15:30")]

        let openMins = StockChartViewModel.oneDayOpenHour * 60 + StockChartViewModel.oneDayOpenMinute
        var result: [AxisTick] = []
        var ordinal = 0
        for slot in candidates {
            let slotIndex = (slot.hour * 60 + slot.minute - openMins) / 5
            guard slotIndex >= 0, slotIndex <= lastSlotIndex else { continue }
            result.append(AxisTick(id: ordinal,
                                   normX: Double(slotIndex) / Double(totalSlots - 1),
                                   label: slot.label))
            ordinal += 1
        }
        return result
    }

    // MARK: - 1W ───────────────────────────────────────────────────────────────
    // Data: intraday per-jam, 7 hari ke belakang dari hari ini (5 Jun 2026).
    // Hari aktif bursa 7 hari ke belakang: 29 Mei, 30 Mei, 2 Jun, 3 Jun, 4 Jun, 5 Jun
    // (Sabtu 31 Mei & Minggu 1 Jun libur).
    //
    // Label yang diinginkan:
    //   • Titik paling awal per hari → tanggal saja ("29", "30", "2", "3", "4", "5")
    //   TAPI: jika hari pertama bulan baru masuk dalam rentang → ganti labelnya dengan
    //   singkatan bulan + tanggal, misal "Jun 2" supaya transisi bulan jelas.
    //   Dalam kasus 7 hari ke belakang dari 5 Jun: hari 2 Jun adalah hari pertama
    //   Juni yang muncul → label "Jun".
    //
    // Implementasi: label = tanggal saja, kecuali hari pertama suatu bulan baru
    // (bulan berbeda dari hari sebelumnya) → label = "MMM" (nama bulan).

    private static func oneWeekTicks(data: [StockDataPoint]) -> [AxisTick] {
        let days  = firstIndexPerDay(data)
        let total = max(data.count - 1, 1)
        let cal   = jakartaCal

        let dayDF = DateFormatter()
        dayDF.timeZone   = TimeZone(identifier: "Asia/Jakarta")!
        dayDF.dateFormat = "d"   // tanggal saja: "29", "2", dst

        let monDF = DateFormatter()
        monDF.locale     = Locale(identifier: "en_US")
        monDF.timeZone   = TimeZone(identifier: "Asia/Jakarta")!
        monDF.dateFormat = "MMM"  // "Jun", "May", dst

        var ticks: [AxisTick] = []
        var prevMonth = -1

        for (ordinal, pair) in days.enumerated() {
            let month = cal.component(.month, from: pair.date)
            let isNewMonth = (prevMonth != -1 && month != prevMonth)

            // Label: nama bulan jika hari pertama bulan baru muncul, otherwise tanggal
            let label = isNewMonth ? monDF.string(from: pair.date) : dayDF.string(from: pair.date)
            let normX = Double(pair.index) / Double(total)
            ticks.append(AxisTick(id: ordinal, normX: normX, label: label))
            prevMonth = month
        }
        return ticks
    }

    // MARK: - 1M ───────────────────────────────────────────────────────────────
    // Data: intraday per-jam, 30 hari ke belakang.
    // Label:
    //   • Hari pertama setiap bulan baru yang muncul dalam data → nama bulan ("Jun", "May")
    //   • Selain itu → tanggal saja ("5", "12", "19", "26", dst)
    //   • Target ~5-6 label merata; ambil satu perwakilan per hari, lalu pilih
    //     evenly-spaced + paksa semua "bulan baru" selalu tampil.

    private static func oneMonthTicks(data: [StockDataPoint]) -> [AxisTick] {
        let days  = firstIndexPerDay(data)
        let total = max(data.count - 1, 1)
        let cal   = jakartaCal

        let dayDF = DateFormatter()
        dayDF.timeZone   = TimeZone(identifier: "Asia/Jakarta")!
        dayDF.dateFormat = "d"

        let monDF = DateFormatter()
        monDF.locale     = Locale(identifier: "en_US")
        monDF.timeZone   = TimeZone(identifier: "Asia/Jakarta")!
        monDF.dateFormat = "MMM"

        // Tandai setiap hari yang merupakan hari pertama bulan baru
        var prevMonth = -1
        var isNewMonthDay = [Bool]()
        for pair in days {
            let m = cal.component(.month, from: pair.date)
            isNewMonthDay.append(prevMonth != -1 && m != prevMonth)
            prevMonth = m
        }

        // Pilih sekitar 5 label evenly-spaced dari array days
        let maxLabels = min(5, days.count)
        var selectedIndices = Set<Int>()

        if days.count <= maxLabels {
            days.indices.forEach { selectedIndices.insert($0) }
        } else {
            let step = Double(days.count - 1) / Double(maxLabels - 1)
            for k in 0..<maxLabels {
                selectedIndices.insert(min(Int(Double(k) * step + 0.5), days.count - 1))
            }
        }

        // Tambahkan semua hari "bulan baru" agar transisi bulan selalu terlihat
        for (k, isNew) in isNewMonthDay.enumerated() {
            if isNew { selectedIndices.insert(k) }
        }

        // Hapus label tanggal yang terlalu dekat dengan label bulan baru
        // supaya angka seperti "29" tidak mepet di sebelah "Jun".
        let newMonthPositions = isNewMonthDay.indices.filter { isNewMonthDay[$0] }
        let minGap = 2
        let filtered = selectedIndices.filter { k in
            guard !isNewMonthDay[k] else { return true }
            return !newMonthPositions.contains(where: { abs($0 - k) < minGap })
        }

        let sortedSel = filtered.sorted()
        return sortedSel.enumerated().map { ordinal, k in
            let pair  = days[k]
            let label = isNewMonthDay[k]
                        ? monDF.string(from: pair.date)
                        : dayDF.string(from: pair.date)
            return AxisTick(id: ordinal,
                            normX: Double(pair.index) / Double(total),
                            label: label)
        }
    }

    // MARK: - 3M ───────────────────────────────────────────────────────────────
    // Data: harian (per hari bursa), 90 hari ke belakang → sekitar Mar–Jun 2026.
    // Label:
    //   • Titik data paling awal (tanggal saja, misal "5" jika hari ini 5 Jun)
    //   • Awal setiap bulan baru → nama bulan ("Apr", "May", "Jun")
    //   Dengan demikian label akan seperti: "5  Apr  May  Jun"

    private static func threeMonthTicks(data: [StockDataPoint]) -> [AxisTick] {
        guard !data.isEmpty else { return [] }
        let total = max(data.count - 1, 1)
        let cal   = jakartaCal

        let dayDF = DateFormatter()
        dayDF.timeZone   = TimeZone(identifier: "Asia/Jakarta")!
        dayDF.dateFormat = "d"   // tanggal saja untuk titik pertama

        let monDF = DateFormatter()
        monDF.locale     = Locale(identifier: "en_US")
        monDF.timeZone   = TimeZone(identifier: "Asia/Jakarta")!
        monDF.dateFormat = "MMM"

        var ticks: [AxisTick] = []
        var ordinal = 0

        // 1. Titik paling awal → tanggal saja
        ticks.append(AxisTick(id: ordinal,
                              normX: 0.0,
                              label: dayDF.string(from: data[0].date)))
        ordinal += 1

        // 2. Awal setiap bulan baru
        let months = firstIndexPerMonth(data)
        let firstMonth = cal.component(.month, from: data[0].date)
        for m in months {
            let month = cal.component(.month, from: m.date)
            guard month != firstMonth else { continue }   // skip bulan data paling awal
            let normX = Double(m.index) / Double(total)
            ticks.append(AxisTick(id: ordinal, normX: normX, label: monDF.string(from: m.date)))
            ordinal += 1
        }

        return ticks
    }

    // MARK: - YTD ──────────────────────────────────────────────────────────────
    // Data: harian dari 1 Jan 2026 hingga hari ini.
    // Label tetap: "2026" (paling kiri / 1 Jan), "Feb", "Mar", "Apr", "May", "Jun"
    // Setiap label diposisikan di data point awal bulan yang bersangkutan.

    private static func ytdTicks(data: [StockDataPoint]) -> [AxisTick] {
        guard !data.isEmpty else { return [] }
        let total = max(data.count - 1, 1)
        let cal   = jakartaCal

        let monDF = DateFormatter()
        monDF.locale     = Locale(identifier: "en_US")
        monDF.timeZone   = TimeZone(identifier: "Asia/Jakarta")!
        monDF.dateFormat = "MMM"

        var ticks: [AxisTick] = []
        var ordinal = 0

        // Titik paling kiri → "2026"
        ticks.append(AxisTick(id: ordinal, normX: 0.0, label: "2026"))
        ordinal += 1

        // Satu label per awal bulan (Feb, Mar, Apr, May, Jun, dst)
        let firstMonth = cal.component(.month, from: data[0].date)
        let months = firstIndexPerMonth(data)
        for m in months {
            let month = cal.component(.month, from: m.date)
            guard month != firstMonth else { continue }
            let normX = Double(m.index) / Double(total)
            ticks.append(AxisTick(id: ordinal, normX: normX, label: monDF.string(from: m.date)))
            ordinal += 1
        }

        return ticks
    }

    // MARK: - 1Y ───────────────────────────────────────────────────────────────
    // Data: mingguan, 52 minggu ke belakang → Jun 2025–Jun 2026.
    // Label: "2025" di kiri, lalu awal setiap kuartal/bulan signifikan:
    //   Sep, "2026", Apr, Jun  (sesuai permintaan)

    private static func oneYearTicks(data: [StockDataPoint]) -> [AxisTick] {
        guard !data.isEmpty else { return [] }
        let total = max(data.count - 1, 1)
        let cal   = jakartaCal

        // Label tetap yang diinginkan, dicari data point terdekat
        struct Target { let year: Int; let month: Int; let label: String }
        let targets: [Target] = [
            Target(year: 2025, month: 6,  label: "2025"),
            Target(year: 2025, month: 9,  label: "Sep"),
            Target(year: 2026, month: 1,  label: "2026"),
            Target(year: 2026, month: 4,  label: "Apr"),
        ]

        var ticks: [AxisTick] = []
        var ordinal = 0
        for t in targets {
            var comps      = DateComponents()
            comps.year     = t.year
            comps.month    = t.month
            comps.day      = 1
            comps.timeZone = cal.timeZone
            guard let targetDate = cal.date(from: comps),
                  let idx = nearestIndex(in: data, to: targetDate) else { continue }
            // "Jun" di ujung: gunakan normX aktual (jangan paksa 1.0) ─ offset diurus AnimatedTickView
            let normX = Double(idx) / Double(total)
            ticks.append(AxisTick(id: ordinal, normX: normX, label: t.label))
            ordinal += 1
        }
        return ticks
    }

    // MARK: - 5Y ───────────────────────────────────────────────────────────────
    // Data: mingguan, 260 minggu ke belakang → awal 2021–Jun 2026.
    // Label: satu per tahun, ditempatkan di data point terdekat 1 Januari tahun tsb.
    // "2026" diposisikan di awal Januari 2026 (BUKAN last point).

    private static func fiveYearTicks(data: [StockDataPoint]) -> [AxisTick] {
        guard !data.isEmpty else { return [] }
        let total = max(data.count - 1, 1)
        let cal   = jakartaCal

        // Mulai dari 2022 (skip 2021 yang muncul di ujung kiri data 5Y)
        let lastYear  = cal.component(.year, from: data.last!.date)
        let startYear = 2022

        var ticks: [AxisTick] = []
        var ordinal = 0

        for year in startYear...lastYear {
            var comps      = DateComponents()
            comps.year     = year
            comps.month    = 1
            comps.day      = 1
            comps.timeZone = cal.timeZone
            guard let targetDate = cal.date(from: comps),
                  let idx = nearestIndex(in: data, to: targetDate) else { continue }
            // normX dari posisi aktual di data — TIDAK di-snap ke 1.0
            let normX = Double(idx) / Double(total)
            ticks.append(AxisTick(id: ordinal, normX: normX, label: "\(year)"))
            ordinal += 1
        }
        return ticks
    }
}

// MARK: - Animated Axis Tick View

/// A single animated tick (dot + label).
/// `targetX` is the final pixel position.
/// On appear the tick starts at `exitX` (right edge) and springs to `targetX`.
/// On disappear it springs back to `exitX`.
///
/// Label alignment shifts so left-edge labels don't clip left and right-edge
/// labels don't clip right.  The rule:
///   • normX ≤ 0.15  → leading alignment (text grows right)
///   • normX ≥ 0.85  → trailing alignment (text grows left)
///   • otherwise     → centre alignment
//private struct AnimatedTickView: View {
//
//    let tick:      AxisTick
//    let targetX:   CGFloat    // final pixel X
//    let exitX:     CGFloat    // off-screen right edge (for enter/exit)
//    let hPad:      CGFloat
//    let innerWidth: CGFloat   // chartSize.width − 2*hPad, used for normX check
//
//    @State private var appeared = false
//
//    /// The spring used for line-chart morphing — must match ChartCanvasView exactly.
//    private let spring: Animation = .spring(response: 3.0, dampingFraction: 1.0)
//
//    // Offset so the label "hugs" the correct edge instead of centring on targetX
//    private var labelOffset: CGFloat {
//        if tick.normX <= 0.10 { return 14 }   // shift right — label kiri
//        if tick.normX >= 0.90 { return -14 }  // shift left  — label kanan
//        return 0
//    }
//
//    var body: some View {
//        VStack(spacing: 2) {
//            // Tick dot
//
//            // Label — shifted so edge labels stay inside view
//            Text(tick.label)
//                .font(.system(size: 9, weight: .medium))
//                .foregroundColor(.secondary)
//                .fixedSize()
//                .lineLimit(1)
//                .offset(x: labelOffset)
//        }
//        // Position horizontally; vertical centre is fixed (frame height = 20)
//        .position(x: targetX, y: 10)
//        .opacity(1)
//        .onAppear {
//            appeared = true
//        }
//    }
//}
// AFTER
private struct AnimatedTickView: View {

    let tick:      AxisTick
    let targetX:   CGFloat
    let exitX:     CGFloat
    let hPad:      CGFloat
    let innerWidth: CGFloat
    let isEntering: Bool    // ← tambahkan parameter ini

    @State private var currentX: CGFloat? = nil   // nil = belum .onAppear

    private let spring: Animation = .spring(response: 0.55, dampingFraction: 0.80)

    private var labelOffset: CGFloat {
        if tick.normX <= 0.10 { return 8 }
        if tick.normX >= 0.90 { return -8 }
        return 0
    }

    var body: some View {
        VStack(spacing: 2) {
            Text(tick.label)
                .font(.system(size: 9, weight: .medium))
                .foregroundColor(.secondary)
                .fixedSize()
                .lineLimit(1)
                .offset(x: labelOffset)
        }
        .position(x: currentX ?? (isEntering ? exitX : targetX), y: 10)
        .opacity(currentX == nil ? 0 : 1)
        .onAppear {
            if isEntering {
                // mulai dari kanan, spring ke posisi final
                currentX = exitX
                DispatchQueue.main.async {
                    withAnimation(spring) {
                        currentX = targetX
                    }
                }
            } else {
                // tick lama yang tetap ada — langsung ke posisi, tanpa animasi enter
                currentX = targetX
            }
        }
        .onChange(of: targetX) { _, newX in
            withAnimation(spring) {
                currentX = newX
            }
        }
    }
}

// MARK: - XAxisAnimatedLabels (public, replaces XAxisLabelsView)

public struct XAxisAnimatedLabels: View {

    @ObservedObject var chartVM: StockChartViewModel
    let chartSize: CGSize

    /// Inner horizontal padding that matches the chart canvas (hPad = 8 on each side).
    private let hPad: CGFloat = 4

    /// Tracks the *previous* tick set so we can animate exits for removed ticks.
    @State private var renderedTicks: [AxisTick] = []

    /// Ticks that are currently animating OUT (slide to right + fade).
    @State private var exitingTicks: [AxisTick] = []

    /// Maps tick.id → current pixel X so exiting ticks start from their last known position.
    @State private var lastKnownX: [Int: CGFloat] = [:]

    private var innerWidth: CGFloat { max(chartSize.width - hPad * 2, 1) }
    private var exitX:      CGFloat { chartSize.width + 40 }

    public var body: some View {
        ZStack {
            // ── Entering / staying ticks ──────────────────────────────────

            ForEach(renderedTicks) { tick in
                // let targetX   = hPad + CGFloat(tick.normX) * innerWidth
                let exponent = chartVM.selectedRange.xSpacingExponent
                let targetX  = hPad + pow(CGFloat(tick.normX), exponent) * innerWidth
                
                let isNew     = lastKnownX[tick.id] == nil   // belum pernah dirender
                AnimatedTickView(
                    tick:       tick,
                    targetX:    targetX,
                    exitX:      exitX,
                    hPad:       hPad,
                    innerWidth: innerWidth,
                    isEntering: isNew
                )
                // onAppear tidak lagi update lastKnownX di sini — sudah dipindah ke updateTicks
            }

            // ── Exiting ticks (slide right → disappear) ───────────────────
            ForEach(exitingTicks) { tick in
                ExitingTickView(
                    tick:    tick,
                    startX:  lastKnownX[tick.id] ?? exitX,
                    exitX:   exitX,
                    spring:  .spring(response: 0.6, dampingFraction: 0.78)
                )
            }
        }
        .frame(height: 20)
        .clipped()
        // ── React to new data ─────────────────────────────────────────────
        .onChange(of: chartVM.dataPoints) { _, newData in
            updateTicks(from: newData)
        }
        .onChange(of: chartVM.selectedRange) { _, _ in
            // Range changed but data may not have arrived yet; handled by dataPoints change.
            // However, if data is already present (cached), handle immediately.
            if !chartVM.dataPoints.isEmpty {
                updateTicks(from: chartVM.dataPoints)
            }
        }
        .onAppear {
            if !chartVM.dataPoints.isEmpty {
                // Silent first render — no slide-in on initial appear
                renderedTicks = AxisTickGenerator.ticks(for: chartVM.dataPoints,
                                                        range: chartVM.selectedRange,
                                                        chartVM: chartVM)
            }
        }
    }

    // MARK: - Diff & animate

    private func updateTicks(from data: [StockDataPoint]) {
        guard chartSize.width > 0 else { return }

        let newTicks = AxisTickGenerator.ticks(for: data,
                                               range: chartVM.selectedRange,
                                               chartVM: chartVM)

        // Find ticks that are leaving
        let newIDs   = Set(newTicks.map(\.id))
        let leaving  = renderedTicks.filter { !newIDs.contains($0.id) }

        // Stage exiting ticks (they animate themselves out)
        if !leaving.isEmpty {
            exitingTicks = leaving
            // Remove them from exitingTicks after the spring settles (~0.9 s)
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.95) {
                exitingTicks = exitingTicks.filter { t in !leaving.contains(t) }
            }
        }

        // Record pixel X for any tick that is staying so exit starts from correct pos
//        for tick in newTicks {
//            let x = hPad + CGFloat(tick.normX) * innerWidth
//            lastKnownX[tick.id] = x
//        }
        let stayingIDs = Set(renderedTicks.map(\.id)).intersection(newIDs)
        for tick in newTicks where stayingIDs.contains(tick.id) {
            // hanya update lastKnownX untuk tick yang sudah ada (staying)
            lastKnownX[tick.id] = hPad + CGFloat(tick.normX) * innerWidth
        }

        // Update rendered set — new ticks will be inserted and AnimatedTickView.onAppear fires
        renderedTicks = newTicks
    }
}

// MARK: - Exiting Tick View

/// A tick that has been removed from the set.
/// It starts at `startX`, then springs to `exitX` and fades out.
private struct ExitingTickView: View {

    let tick:   AxisTick
    let startX: CGFloat
    let exitX:  CGFloat
    let spring: Animation

    @State private var gone = false

    private var labelOffset: CGFloat {
        if tick.normX <= 0.10 { return 14 }
        if tick.normX >= 0.90 { return -14 }
        return 0
    }

    var body: some View {
        VStack(spacing: 2) {

            Text(tick.label)
                .font(.system(size: 9, weight: .medium))
                .foregroundColor(.secondary)
                .fixedSize()
                .lineLimit(1)
                .offset(x: labelOffset)
        }
        .position(x: gone ? exitX : startX, y: 10)
        .opacity(gone ? 0 : 1)
        .onAppear {
            withAnimation(spring) { gone = true }
        }
    }
}

struct TimeRangeSelectorView: View {

    @ObservedObject var chartVM: StockChartViewModel
    let onRangeChange: () -> Void

    var body: some View {
        Picker("Range", selection: $chartVM.selectedRange) {
            ForEach(TimeRange.allCases, id: \.self) { range in
                Text(range.rawValue).tag(range)
            }
        }
        .pickerStyle(.segmented)
        .tint(Color(hex: "FFA500"))
        .onChange(of: chartVM.selectedRange) { _, _ in
            onRangeChange()
            Task { await chartVM.fetchData() }
        }
    }
}

// MARK: - Position Summary

struct PositionSummaryView: View {

    let item:       PortfolioItem
    let holding:    Holding?
    let currentQty: Double

    private var costBasis: Double { holding?.totalCostBasis ?? 0 }
    private var avgPrice:  Double { currentQty > 0 ? costBasis / currentQty : 0 }
    private var pl:        Double { item.value - costBasis }

    var body: some View {
        VStack(spacing: 12) {
            HStack {
                LabelValueView(
                    label: "Kepemilikan",
                    value: "\(Int(currentQty)) lembar (\(Int(currentQty / 100)) lot)"
                )
                Spacer()
                LabelValueView(
                    label: "Nilai Pasar",
                    value: formatIDR(item.value),
                    alignment: .trailing
                )
            }
            .padding()
            .background(Color(.secondarySystemBackground))
            .cornerRadius(12)

            if currentQty > 0 {
                HStack {
                    LabelValueView(
                        label: "Harga Rata-rata",
                        value: formatIDR(avgPrice)
                    )
                    Spacer()
                    LabelValueView(
                        label: "Untung/Rugi",
                        value: "\(pl >= 0 ? "+" : "")\(formatIDR(pl))",
                        valueColor: pl >= 0 ? Color(hex: "22C55E") : Color(hex: "EF4444"),
                        alignment: .trailing
                    )
                }
                .padding()
                .background(Color(.secondarySystemBackground))
                .cornerRadius(12)
            }
        }
    }
}

struct LabelValueView: View {

    let label:      String
    let value:      String
    var valueColor: Color     = .primary
    var alignment:  HorizontalAlignment = .leading

    var body: some View {
        VStack(alignment: alignment, spacing: 4) {
            Text(label)
                .font(.caption)
                .foregroundColor(.secondary)
            Text(value)
                .font(.headline)
                .foregroundColor(valueColor)
        }
    }
}

// MARK: - Bottom Action Bar

struct BottomActionBarView: View {

    let symbol:      String
    let hasPosition: Bool
    let onBuy:       () -> Void
    let onSell:      () -> Void

    var body: some View {
        HStack(spacing: 12) {
            ActionButton(
                title:    "Jual",
                color:    Color(hex: "EF4444"),
                disabled: !hasPosition,
                action:   onSell
            )
            ActionButton(
                title:    "Beli",
                color:    Color(hex: "22C55E"),
                disabled: false,
                action:   onBuy
            )
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
        .background(.ultraThinMaterial)
    }
}

struct ActionButton: View {

    let title:    String
    let color:    Color
    let disabled: Bool
    let action:   () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.system(size: 16, weight: .bold))
                .foregroundColor(.white)
                .frame(maxWidth: .infinity, minHeight: 50)
                .background(color)
                .cornerRadius(14)
        }
        .opacity(disabled ? 0.4 : 1.0)
        .disabled(disabled)
    }
}

// MARK: - Buy Sheet

struct BuySheetView: View {

    let item:        PortfolioItem
    let portfolioVM: PortfolioViewModel

    @Environment(\.dismiss) private var dismiss
    @State private var buyAmount  = ""
    @State private var slideOffset = CGFloat.zero

    private var idrVal:   Double  { Double(buyAmount) ?? 0 }
    private var lots:     Double  { idrVal > 0 ? floor(idrVal / (item.price * 100)) : 0 }
    private var realQty:  Double  { lots * 100 }
    private var realCost: Double  { realQty * item.price }
    private var canBuy:   Bool    { idrVal > 0 && lots >= 1 }

    var body: some View {
        NavigationStack {
            VStack(spacing: 24) {
                SheetStockHeaderView(
                    symbol:   item.symbol,
                    price:    item.price,
                    subtitle: "per lembar"
                )

                Divider()

                IDRInputView(
                    label:  "Jumlah Investasi (IDR)",
                    amount: $buyAmount
                )

                if idrVal > 0 {
                    BuySummaryView(
                        lots:     lots,
                        realQty:  realQty,
                        realCost: realCost,
                        price:    item.price
                    )
                }

                Spacer()

                SlideToConfirmView(
                    label:    "Geser untuk Beli",
                    color:    Color(hex: "22C55E"),
                    disabled: !canBuy,
                    onConfirm: {
                        portfolioVM.buy(symbol: item.symbol, amountIDR: idrVal, price: item.price)
                        dismiss()
                    }
                )
                .padding(.bottom, 8)
            }
            .padding(.horizontal, 20)
            .navigationTitle("Beli \(item.symbol)")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Batal") { dismiss() }
                }
            }
        }
        .presentationDetents([.medium, .large])
        .presentationDragIndicator(.visible)
    }
}

// MARK: - Sell Sheet

struct SellSheetView: View {

    let item:        PortfolioItem
    let currentQty:  Double
    let portfolioVM: PortfolioViewModel

    @Environment(\.dismiss) private var dismiss
    @State private var sellAmount = ""

    private var qty:      Double { Double(sellAmount) ?? 0 }
    private var proceeds: Double { qty * item.price }
    private var avgPrice: Double {
        let h = portfolioVM.holdings.first { $0.symbol == item.symbol }
        return currentQty > 0 ? (h?.totalCostBasis ?? 0) / currentQty : 0
    }
    private var pl:       Double { proceeds - (qty * avgPrice) }
    private var canSell:  Bool   { qty > 0 && qty <= currentQty }

    var body: some View {
        NavigationStack {
            VStack(spacing: 24) {
                SheetStockHeaderView(
                    symbol:   item.symbol,
                    price:    item.price,
                    subtitle: "Kepemilikan: \(Int(currentQty)) lembar"
                )

                Divider()

                LembarInputView(
                    label:     "Jumlah Lembar yang Dijual",
                    amount:    $sellAmount,
                    maxAmount: currentQty
                )

                if qty > 0 {
                    SellSummaryView(proceeds: proceeds, pl: pl)
                }

                Spacer()

                SlideToConfirmView(
                    label:    "Geser untuk Jual",
                    color:    Color(hex: "EF4444"),
                    disabled: !canSell,
                    onConfirm: {
                        portfolioVM.sell(symbol: item.symbol, quantity: qty)
                        dismiss()
                    }
                )
                .padding(.bottom, 8)
            }
            .padding(.horizontal, 20)
            .navigationTitle("Jual \(item.symbol)")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Batal") { dismiss() }
                }
            }
        }
        .presentationDetents([.medium, .large])
        .presentationDragIndicator(.visible)
    }
}

// MARK: - Sheet Sub-Views

struct SheetStockHeaderView: View {
    let symbol:   String
    let price:    Double
    let subtitle: String

    var body: some View {
        VStack(spacing: 4) {
            Text(symbol)
                .font(.system(size: 15, weight: .semibold))
                .foregroundColor(.secondary)
            Text(formatIDR(price))
                .font(.system(size: 28, weight: .bold, design: .rounded))
            Text(subtitle)
                .font(.caption)
                .foregroundColor(.secondary)
        }
        .padding(.top, 8)
    }
}

struct IDRInputView: View {
    let label:  String
    @Binding var amount: String

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(label)
                .font(.caption)
                .foregroundColor(.secondary)
            HStack {
                Text("Rp")
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundColor(.secondary)
                TextField("0", text: $amount)
                    .font(.system(size: 22, weight: .bold, design: .rounded))
                    .keyboardType(.numberPad)
                    .onChange(of: amount) { _, v in
                        let filtered = v.filter { $0.isNumber }
                        if filtered != v { amount = filtered }
                    }
            }
            .padding()
            .background(Color(.secondarySystemBackground))
            .cornerRadius(12)
        }
    }
}

struct LembarInputView: View {
    let label:     String
    @Binding var amount: String
    let maxAmount: Double

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(label)
                .font(.caption)
                .foregroundColor(.secondary)
            HStack {
                TextField("0", text: $amount)
                    .font(.system(size: 22, weight: .bold, design: .rounded))
                    .keyboardType(.numberPad)
                    .onChange(of: amount) { _, v in
                        let filtered = v.filter { $0.isNumber }
                        if filtered != v { amount = filtered }
                        if let val = Double(filtered), val > maxAmount {
                            amount = "\(Int(maxAmount))"
                        }
                    }
                Text("lembar")
                    .font(.system(size: 14))
                    .foregroundColor(.secondary)
            }
            .padding()
            .background(Color(.secondarySystemBackground))
            .cornerRadius(12)
        }
    }
}

struct BuySummaryView: View {
    let lots:     Double
    let realQty:  Double
    let realCost: Double
    let price:    Double

    var body: some View {
        VStack(spacing: 10) {
            SummaryRowView(label: "Estimasi Lembar",
                           value: "\(Int(realQty)) lembar (\(Int(lots)) lot)")
            SummaryRowView(label: "Total Biaya",
                           value: "Rp \(formatIDR(realCost))")
            SummaryRowView(label: "Harga per Lembar",
                           value: "Rp \(formatIDR(price))")
        }
        .padding()
        .background(Color(.secondarySystemBackground))
        .cornerRadius(12)
    }
}

struct SellSummaryView: View {
    let proceeds: Double
    let pl:       Double

    var body: some View {
        VStack(spacing: 10) {
            SummaryRowView(label: "Hasil Penjualan",
                           value: "Rp \(formatIDR(proceeds))")
            SummaryRowView(label: "Untung/Rugi",
                           value: "\(pl >= 0 ? "+" : "")Rp \(formatIDR(pl))",
                           valueColor: pl >= 0 ? Color(hex: "22C55E") : Color(hex: "EF4444"))
        }
        .padding()
        .background(Color(.secondarySystemBackground))
        .cornerRadius(12)
    }
}

struct SummaryRowView: View {
    let label:      String
    let value:      String
    var valueColor: Color = .primary

    var body: some View {
        HStack {
            Text(label)
                .font(.system(size: 13))
                .foregroundColor(.secondary)
            Spacer()
            Text(value)
                .font(.system(size: 13, weight: .semibold))
                .foregroundColor(valueColor)
        }
    }
}

// MARK: - Slide to Confirm

struct SlideToConfirmView: View {

    let label:     String
    let color:     Color
    let disabled:  Bool
    let onConfirm: () -> Void

    @State private var slideOffset = CGFloat.zero

    private let thumbSize: CGFloat = 54

    var body: some View {
        GeometryReader { geo in
            let maxSlide = geo.size.width - thumbSize - 8

            ZStack(alignment: .leading) {
                // Track
                RoundedRectangle(cornerRadius: 16)
                    .fill(color.opacity(0.15))
                    .frame(height: thumbSize)

                // Fill progress
                RoundedRectangle(cornerRadius: 16)
                    .fill(color.opacity(0.25))
                    .frame(width: max(thumbSize, slideOffset + thumbSize), height: thumbSize)
                    .animation(.interactiveSpring(), value: slideOffset)

                // Label
                Text(label)
                    .font(.system(size: 15, weight: .semibold))
                    .foregroundColor(color.opacity(0.8))
                    .frame(maxWidth: .infinity)

                // Thumb
                RoundedRectangle(cornerRadius: 13)
                    .fill(color)
                    .frame(width: thumbSize, height: thumbSize - 8)
                    .overlay(
                        Image(systemName: "chevron.right.2")
                            .font(.system(size: 16, weight: .bold))
                            .foregroundColor(.white)
                    )
                    .shadow(color: color.opacity(0.4), radius: 6, x: 0, y: 3)
                    .offset(x: 4 + slideOffset)
                    .gesture(
                        DragGesture()
                            .onChanged { val in
                                slideOffset = max(0, min(val.translation.width, maxSlide))
                            }
                            .onEnded { _ in
                                if slideOffset >= maxSlide * 0.85 {
                                    slideOffset = maxSlide
                                    UINotificationFeedbackGenerator().notificationOccurred(.success)
                                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.2) {
                                        onConfirm()
                                        slideOffset = .zero
                                    }
                                } else {
                                    withAnimation(.spring()) { slideOffset = .zero }
                                }
                            }
                    )
            }
        }
        .frame(height: thumbSize)
        .opacity(disabled ? 0.4 : 1.0)
        .disabled(disabled)
    }
}

// MARK: - Preview

#Preview {
    NavigationStack {
        StockDetailView(
            item: PortfolioItem(
                symbol:        "BBCA",
                name:          "Bank Central Asia",
                logo:          nil,
                price:         9_950,
                change:        -25,
                percentChange: -0.25,
                quantity:      500,
                sentiment:     Sentiment(buy: 0.4, hold: 0.40, sell: 0.25)
            )
        )
        .environmentObject(PortfolioViewModel())
        .environmentObject(Router())
        .environmentObject(ChatbotViewModel())
    }
}

struct MorphingLineShape: Shape {
 
    var normalized: NormalizedChartData
 
    var animatableData: NormalizedChartData {
        get { normalized }
        set { normalized = newValue }
    }
 
    func path(in rect: CGRect) -> Path {
        let vals = normalized.values
        guard vals.count > 1 else { return Path() }
 
        let topPad: CGFloat    = 20
        let bottomPad: CGFloat = 20
        let usable             = rect.height - topPad - bottomPad
        guard usable > 0 else { return Path() }
 
        let hPad: CGFloat       = 4
        let innerWidth: CGFloat = rect.width - hPad * 2
        let xMin = hPad
        let xMax = hPad + innerWidth
 
        // Clamp v to a slightly wider-than-unit range so a spring overshoot
        // stays inside the padded chart area rather than leaving the frame.
        let pts: [CGPoint] = vals.enumerated().map { i, v in
            let vc = v.clamped(to: -0.05...1.05)
            return CGPoint(
                x: hPad + CGFloat(i) / CGFloat(vals.count - 1) * innerWidth,
                y: topPad + usable * CGFloat(1.0 - vc)
            )
        }
 
        var path = Path()
        path.move(to: pts[0])
 
        let tension: CGFloat = 0.4
        for i in 1..<pts.count {
            let p0 = pts[max(i - 2, 0)]
            let p1 = pts[i - 1]
            let p2 = pts[i]
            let p3 = pts[min(i + 1, pts.count - 1)]
 
            // ── KEY FIX: clamp control-point X so bezier handles never leave
            //             the chart's horizontal bounds during interpolation. ──
            let cp1 = CGPoint(
                x: (p1.x + (p2.x - p0.x) * tension).clamped(to: xMin...xMax),
                y:  p1.y + (p2.y - p0.y) * tension
            )
            let cp2 = CGPoint(
                x: (p2.x - (p3.x - p1.x) * tension).clamped(to: xMin...xMax),
                y:  p2.y - (p3.y - p1.y) * tension
            )
            path.addCurve(to: p2, control1: cp1, control2: cp2)
        }
        return path
    }
}
 
// MARK: - Fixed Morphing Area Shape
 
struct MorphingAreaShape: Shape {
 
    var normalized: NormalizedChartData
    /// Y coordinate where the area is closed (typically yBaseline or yLastPrice).
    var closingY: CGFloat
 
    var animatableData: NormalizedChartData {
        get { normalized }
        set { normalized = newValue }
    }
 
    func path(in rect: CGRect) -> Path {
        let vals = normalized.values
        guard vals.count > 1 else { return Path() }
 
        let topPad: CGFloat    = 20
        let bottomPad: CGFloat = 20
        let usable             = rect.height - topPad - bottomPad
        guard usable > 0 else { return Path() }
 
        let hPad: CGFloat       = 4
        let innerWidth: CGFloat = rect.width - hPad * 2
        let xMin = hPad
        let xMax = hPad + innerWidth
 
        let pts: [CGPoint] = vals.enumerated().map { i, v in
            let vc = v.clamped(to: -0.05...1.05)
            return CGPoint(
                x: hPad + CGFloat(i) / CGFloat(vals.count - 1) * innerWidth,
                y: topPad + usable * CGFloat(1.0 - vc)
            )
        }
 
        var path = Path()
        path.move(to: pts[0])
 
        let tension: CGFloat = 0.4
        for i in 1..<pts.count {
            let p0 = pts[max(i - 2, 0)]
            let p1 = pts[i - 1]
            let p2 = pts[i]
            let p3 = pts[min(i + 1, pts.count - 1)]
 
            let cp1 = CGPoint(
                x: (p1.x + (p2.x - p0.x) * tension).clamped(to: xMin...xMax),
                y:  p1.y + (p2.y - p0.y) * tension
            )
            let cp2 = CGPoint(
                x: (p2.x - (p3.x - p1.x) * tension).clamped(to: xMin...xMax),
                y:  p2.y - (p3.y - p1.y) * tension
            )
            path.addCurve(to: p2, control1: cp1, control2: cp2)
        }
 
        // Close the area back to closingY
        path.addLine(to: CGPoint(x: xMax, y: closingY))
        path.addLine(to: CGPoint(x: xMin, y: closingY))
        path.closeSubpath()
        return path
    }
}
 
// MARK: - MorphingXYLineShape
// Shape animatable yang membaca MorphPoint(x, y) langsung dari AnimatableChartData.
// X sudah termorphing oleh pow(t, exponent), Y sudah ternormalisasi.
// Kedua efek (X Spacing Morph + Path Tweening) berjalan dalam satu SwiftUI animation pass.

struct MorphingXYLineShape: Shape {

    var data: AnimatableChartData

    var animatableData: AnimatableChartData {
        get { data }
        set { data = newValue }
    }

    func path(in rect: CGRect) -> Path {
        let pts = data.points
        guard pts.count > 1 else { return Path() }

        var path = Path()
        path.move(to: CGPoint(x: pts[0].x, y: pts[0].y))

        let tension: CGFloat = 0.4
        for i in 1..<pts.count {
            let p0 = pts[max(i - 2, 0)]
            let p1 = pts[i - 1]
            let p2 = pts[i]
            let p3 = pts[min(i + 1, pts.count - 1)]

            let cp1 = CGPoint(
                x: (p1.x + (p2.x - p0.x) * tension).clamped(to: 0...rect.width),
                y:  p1.y + (p2.y - p0.y) * tension
            )
            let cp2 = CGPoint(
                x: (p2.x - (p3.x - p1.x) * tension).clamped(to: 0...rect.width),
                y:  p2.y - (p3.y - p1.y) * tension
            )
            path.addCurve(to: CGPoint(x: p2.x, y: p2.y), control1: cp1, control2: cp2)
        }
        return path
    }
}

// MARK: - MorphingXYAreaShape
// Area fill dari MorphingXYLineShape — ditutup ke closingY (baseline harga awal).

struct MorphingXYAreaShape: Shape {

    var data:     AnimatableChartData
    var closingY: CGFloat

    var animatableData: AnimatablePair<AnimatableChartData, CGFloat> {
        get { AnimatablePair(data, closingY) }
        set { data = newValue.first; closingY = newValue.second }
    }

    func path(in rect: CGRect) -> Path {
        let pts = data.points
        guard pts.count > 1 else { return Path() }

        var path = Path()
        path.move(to: CGPoint(x: pts[0].x, y: pts[0].y))

        let tension: CGFloat = 0.4
        for i in 1..<pts.count {
            let p0 = pts[max(i - 2, 0)]
            let p1 = pts[i - 1]
            let p2 = pts[i]
            let p3 = pts[min(i + 1, pts.count - 1)]

            let cp1 = CGPoint(
                x: (p1.x + (p2.x - p0.x) * tension).clamped(to: 0...rect.width),
                y:  p1.y + (p2.y - p0.y) * tension
            )
            let cp2 = CGPoint(
                x: (p2.x - (p3.x - p1.x) * tension).clamped(to: 0...rect.width),
                y:  p2.y - (p3.y - p1.y) * tension
            )
            path.addCurve(to: CGPoint(x: p2.x, y: p2.y), control1: cp1, control2: cp2)
        }

        path.addLine(to: CGPoint(x: pts.last!.x,  y: closingY))
        path.addLine(to: CGPoint(x: pts.first!.x, y: closingY))
        path.closeSubpath()
        return path
    }
}

// MARK: - Comparable clamp helper (private to this file)

private extension Comparable {
    func clamped(to range: ClosedRange<Self>) -> Self {
        min(max(self, range.lowerBound), range.upperBound)
    }
}


// MARK: - Rolling Price View

/// Memecah string format IDR menjadi karakter-karakter,
/// lalu digit 0–9 di-roll ala SpeedometerAnimation.
struct RollingPriceView: View {

    let price: Double
    let fontSize: CGFloat
    var isInteractive: Bool = false  // ← tambah ini


    private var formatted: String { formatIDR(price) }

    // Setiap karakter dimodelkan sebagai token
    private var tokens: [(id: Int, char: Character)] {
        Array(formatted.enumerated()).map { ($0.offset, $0.element) }
    }

    var body: some View {
        HStack(spacing: 1) {
            ForEach(tokens, id: \.id) { token in
                if let digit = token.char.wholeNumberValue {
                    RollingPriceDigit(digit: digit, delay: Double(token.id) * 0.04, fontSize: fontSize)
                } else {
                    // "Rp", ".", spasi — tampil statis
                    Text(String(token.char))
                        .font(.system(size: fontSize, weight: .bold, design: .rounded))
                }
            }
        }
    }
}

/// Satu digit yang scroll vertikal (0–9).
struct RollingPriceDigit: View {

    let digit: Int
    let delay: Double
    let fontSize: CGFloat
    var isInteractive: Bool = false  // ← tambah ini


    private var digitHeight: CGFloat { fontSize * 1.25 }

    var body: some View {
        GeometryReader { _ in
            VStack(spacing: 0) {
                ForEach(0..<10) { n in
                    Text("\(n)")
                        .font(.system(size: fontSize, weight: .bold, design: .rounded))
                        .frame(height: digitHeight)
                }
            }
            .offset(y: -CGFloat(digit) * digitHeight)
            .animation(
                    isInteractive
                        ? .interpolatingSpring(stiffness: 40, damping: 20)
                        : .interpolatingSpring(stiffness: 120, damping: 28).delay(delay),
                    value: digit
                )
        }
        .frame(width: fontSize * 0.65, height: digitHeight)
        .clipped()
    }
}

#Preview {
    let item = PortfolioItem(
        symbol:        "BBCA",
        name:          "Bank Central Asia Tbk",
        logo:          nil,
        price:         9500,
        change:        75,
        percentChange: 0.80,
        quantity:      100,
        sentiment:     Sentiment(buy: 60, hold: 30, sell: 10)
    )

    NavigationStack {
        StockDetailView(item: item)
            .environmentObject(PortfolioViewModel())
            .environmentObject(Router())
            .environmentObject(ChatbotViewModel())
    }
}
