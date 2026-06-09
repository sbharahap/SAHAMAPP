//
//  PortfolioHistoryChart.swift
//  SahamIndo
//

import SwiftUI

// MARK: - Dummy History Generator

extension PortfolioValuePoint {

    // Generates daily value history for a single holding from purchaseDate to today.
    static func generateForHolding(
        item: PortfolioItem,
        purchaseDate: Date,
        costBasis: Double
    ) -> [PortfolioValuePoint] {
        let cal   = Calendar.current
        let today = cal.startOfDay(for: Date())
        let start = cal.startOfDay(for: purchaseDate)

        let diffDays = cal.dateComponents([.day], from: start, to: today).day ?? 0
        let totalDays = max(diffDays + 1, 2)

        let endValue   = max(item.price * item.quantity, 1)
        let startValue = max(costBasis, 1)

        var values = Array(repeating: 0.0, count: totalDays)
        values[totalDays - 1] = endValue

        var rng = SystemRandomNumberGenerator()
        let vol = endValue * 0.012

        // Random walk backwards from today
        for i in stride(from: totalDays - 2, through: 0, by: -1) {
            let change = Double.random(in: -vol...vol, using: &rng)
            values[i] = max(values[i + 1] - change, 1)
        }

        // Blend to anchor first point at costBasis
        let generatedStart = values[0]
        for i in 0..<totalDays {
            let t = Double(i) / Double(totalDays - 1)
            values[i] += (startValue - generatedStart) * (1.0 - t)
        }
        values[0] = startValue
        values[totalDays - 1] = endValue

        return (0..<totalDays).map { i in
            let date = cal.date(byAdding: .day, value: i, to: start)!
            return PortfolioValuePoint(date: date, value: max(values[i], 1))
        }
    }

    static func generate(from items: [PortfolioItem], days: Int = 360) -> [PortfolioValuePoint] {
        guard !items.isEmpty else { return [] }

        let cal   = Calendar.current
        let today = cal.startOfDay(for: Date())
        var totals = Array(repeating: 0.0, count: days)

        for item in items {
            guard item.quantity > 0 else { continue }
            var prices = Array(repeating: 0.0, count: days)
            prices[days - 1] = item.price
            var rng = SystemRandomNumberGenerator()
            for i in stride(from: days - 2, through: 0, by: -1) {
                let vol    = item.price * 0.015
                let change = Double.random(in: -vol...vol, using: &rng)
                prices[i]  = max(prices[i + 1] - change, 50)
            }
            for i in 0..<days { totals[i] += prices[i] * item.quantity }
        }

        return (0..<days).map { i in
            let date = cal.date(byAdding: .day, value: i - (days - 1), to: today)!
            return PortfolioValuePoint(date: date, value: totals[i])
        }
    }
}

// MARK: - Portfolio History Chart

struct PortfolioHistoryChart: View {

    let data: [PortfolioValuePoint]

    @State private var selectedPoint: PortfolioValuePoint? = nil
    @State private var isDragging     = false
    @State private var chartSize: CGSize = .zero

    private let chartHeight: CGFloat = 160

    private var minValue:   Double { data.map(\.value).min() ?? 0 }
    private var maxValue:   Double { data.map(\.value).max() ?? 1 }
    private var valueRange: Double { maxValue - minValue }
    private var startValue: Double { data.first?.value ?? 0 }

    private var displayValue:    Double { selectedPoint?.value ?? data.last?.value ?? 0 }
    private var isPositive:      Bool   { displayValue >= startValue }
    private var changePercent:   Double {
        guard startValue != 0 else { return 0 }
        return ((displayValue - startValue) / startValue) * 100
    }
    private var changeAbsolute:  Double { displayValue - startValue }
    private var accentColor:     Color  {
        isPositive ? Color(hex: "00D4AA") : Color(hex: "FF4757")
    }

    var body: some View {
        VStack(spacing: 0) {
            HistoryInfoRow(
                displayValue:   displayValue,
                changePercent:  changePercent,
                changeAbsolute: changeAbsolute,
                isPositive:     isPositive,
                accentColor:    accentColor,
                selectedPoint:  selectedPoint,
                isDragging:     isDragging
            )
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
            .animation(.easeInOut(duration: 0.15), value: isDragging)

            historyCanvas
                .frame(height: chartHeight)
                .background(
                    GeometryReader { geo in
                        Color.clear
                            .onAppear { chartSize = geo.size }
                            .onChange(of: geo.size) { _, s in chartSize = s }
                    }
                )
        }
    }

    // MARK: - Canvas

    private var historyCanvas: some View {
        ZStack {
            if chartSize.height > 0 {
                gradientArea.animation(.easeInOut(duration: 0.25), value: isPositive)
                lineStroke.animation(.easeInOut(duration: 0.25), value: isPositive)

                if isDragging, let point = selectedPoint {
                    let x = xPos(for: point)
                    let y = yPos(for: point.value)

                    DashLine(from: CGPoint(x: x, y: 0), to: CGPoint(x: x, y: chartSize.height))
                        .stroke(Color.primary.opacity(0.2), style: StrokeStyle(lineWidth: 1, dash: [4, 4]))
                    DashLine(from: CGPoint(x: 0, y: y), to: CGPoint(x: chartSize.width, y: y))
                        .stroke(Color.primary.opacity(0.12), style: StrokeStyle(lineWidth: 1, dash: [4, 4]))

                    Circle().fill(accentColor)
                        .frame(width: 12, height: 12)
                        .shadow(color: accentColor.opacity(0.6), radius: 5)
                        .position(x: x, y: y)
                    Circle().fill(Color.white)
                        .frame(width: 5, height: 5)
                        .position(x: x, y: y)

                    historyTooltip(point: point, x: x, y: y)
                }
            }
        }
        .contentShape(Rectangle())
        .gesture(
            DragGesture(minimumDistance: 0)
                .onChanged { val in
                    isDragging = true
                    let i      = Int((val.location.x / chartSize.width) * CGFloat(data.count - 1) + 0.5)
                    let nearest = data[max(0, min(i, data.count - 1))]
                    if nearest.id != selectedPoint?.id {
                        selectedPoint = nearest
                        UIImpactFeedbackGenerator(style: .light).impactOccurred()
                    }
                }
                .onEnded { _ in
                    withAnimation(.easeOut(duration: 0.3)) {
                        isDragging    = false
                        selectedPoint = nil
                    }
                }
        )
    }

    private var gradientArea: some View {
        gradientAreaPath()
            .fill(
                LinearGradient(
                    stops: [
                        .init(color: accentColor.opacity(0.3),  location: 0),
                        .init(color: accentColor.opacity(0.05), location: 0.7),
                        .init(color: .clear,                    location: 1),
                    ],
                    startPoint: .top, endPoint: .bottom
                )
            )
    }

    private var lineStroke: some View {
        linePath()
            .stroke(accentColor, style: StrokeStyle(lineWidth: 2, lineCap: .round, lineJoin: .round))
    }

    // MARK: - Tooltip

    private func historyTooltip(point: PortfolioValuePoint, x: CGFloat, y: CGFloat) -> some View {
        let w: CGFloat = 150, h: CGFloat = 50, pad: CGFloat = 8
        var tx = x - w / 2
        tx = max(pad, min(tx, chartSize.width - w - pad))
        var ty = y - h - 12
        if ty < 4 { ty = y + 14 }

        return VStack(spacing: 2) {
            Text(formatDate(point.date))
                .font(.system(size: 10, weight: .medium))
                .foregroundColor(.secondary)
            Text(formatIDR(point.value))
                .font(.system(size: 13, weight: .bold, design: .monospaced))
        }
        .padding(.horizontal, 12).padding(.vertical, 8)
        .frame(width: w, height: h)
        .background(
            RoundedRectangle(cornerRadius: 9)
                .fill(Color(.systemBackground))
                .overlay(RoundedRectangle(cornerRadius: 9).stroke(Color.primary.opacity(0.08), lineWidth: 1))
                .shadow(color: .black.opacity(0.15), radius: 8, x: 0, y: 4)
        )
        .position(x: tx + w / 2, y: ty + h / 2)
        .transition(.opacity)
    }

    // MARK: - Paths

    private func linePath() -> Path {
        guard data.count > 1, chartSize.height > 0 else { return Path() }
        var path = Path()
        for (i, pt) in data.enumerated() {
            let x = xPos(for: pt)
            let y = yPos(for: pt.value)
            if i == 0 {
                path.move(to: CGPoint(x: x, y: y))
            } else {
                let prev = data[i - 1]
                let px   = xPos(for: prev)
                let py   = yPos(for: prev.value)
                path.addCurve(to: CGPoint(x: x, y: y),
                              control1: CGPoint(x: px + (x - px) * 0.5, y: py),
                              control2: CGPoint(x: px + (x - px) * 0.5, y: y))
            }
        }
        return path
    }

    private func gradientAreaPath() -> Path {
        var path = linePath()
        guard let last = data.last else { return path }
        path.addLine(to: CGPoint(x: xPos(for: last),    y: chartSize.height))
        path.addLine(to: CGPoint(x: xPos(for: data[0]), y: chartSize.height))
        path.closeSubpath()
        return path
    }

    private func xPos(for point: PortfolioValuePoint) -> CGFloat {
        guard let i = data.firstIndex(where: { $0.id == point.id }) else { return 0 }
        return CGFloat(i) / CGFloat(max(data.count - 1, 1)) * chartSize.width
    }

    private func yPos(for value: Double) -> CGFloat {
        let topPad: CGFloat = 12, bottomPad: CGFloat = 12
        let usable = chartSize.height - topPad - bottomPad
        guard usable > 0 else { return chartSize.height / 2 }
        let norm = (value - minValue) / max(valueRange, 1)
        return topPad + usable * (1 - norm)
    }

    private func formatDate(_ date: Date) -> String {
        let f = DateFormatter()
        f.dateFormat = "d MMM yyyy"
        f.locale     = Locale(identifier: "id_ID")
        return f.string(from: date)
    }
}

// MARK: - History Info Row

struct HistoryInfoRow: View {

    let displayValue:   Double
    let changePercent:  Double
    let changeAbsolute: Double
    let isPositive:     Bool
    let accentColor:    Color
    let selectedPoint:  PortfolioValuePoint?
    let isDragging:     Bool

    var body: some View {
        HStack(alignment: .bottom) {
            VStack(alignment: .leading, spacing: 4) {
                Text(formatIDR(displayValue))
                    .font(.system(size: 26, weight: .bold, design: .rounded))
                    .animation(.none, value: displayValue)

                HStack(spacing: 5) {
                    Image(systemName: isPositive ? "arrow.up.right" : "arrow.down.right")
                        .font(.system(size: 10, weight: .bold))
                    Text(String(format: "%+.2f%%", changePercent))
                        .font(.system(size: 12, weight: .semibold))
                    Text("(\(isPositive ? "+" : "")\(formatIDR(changeAbsolute)))")
                        .font(.system(size: 11, weight: .medium))
                        .opacity(0.8)
                }
                .foregroundColor(accentColor)
                .padding(.horizontal, 8).padding(.vertical, 4)
                .background(accentColor.opacity(0.12))
                .cornerRadius(6)
            }

            Spacer()

            if isDragging, let point = selectedPoint {
                VStack(alignment: .trailing, spacing: 2) {
                    Text(formatDate(point.date))
                        .font(.system(size: 11, weight: .medium))
                        .foregroundColor(.secondary)
                    Text(formatIDR(point.value))
                        .font(.system(size: 13, weight: .semibold))
                }
                .transition(.opacity.combined(with: .scale(scale: 0.95)))
            }
        }
    }

    private func formatDate(_ date: Date) -> String {
        let f = DateFormatter()
        f.dateFormat = "d MMM yyyy"
        f.locale     = Locale(identifier: "id_ID")
        return f.string(from: date)
    }
}
