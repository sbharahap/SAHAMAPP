//
//  StockChartViewModel.swift
//  SahamIndo
//
//  Perubahan: fetchData() sekarang hit RealChartService → FastAPI
//

import SwiftUI
import Combine

@MainActor
final class StockChartViewModel: ObservableObject {

    @Published private(set) var dataPoints:  [StockDataPoint] = []
    @Published private(set) var isLoading:   Bool             = false
    @Published private(set) var errorMessage: String?         = nil
    @Published var selectedRange: TimeRange = .oneDay
    @Published var cacheState: CacheState = .live  // tambahkan ini

    var symbol: String = ""

    private let chartService = RealChartService()

    // MARK: - 1D slot constants
    // 87 slot: 09:00–16:10 inklusif, interval 5 menit (Yahoo Finance)
    static let oneDayTotalSlots  = 87
    static let oneDayOpenHour    = 9
    static let oneDayOpenMinute  = 0
    static let oneDayOpenMinutes = 9 * 60      // 540 menit sejak tengah malam

    // MARK: - Computed
    var minPrice:    Double { dataPoints.map(\.close).min() ?? 0 }
    var maxPrice:    Double { dataPoints.map(\.close).max() ?? 0 }
    var startPrice:  Double { dataPoints.first?.close ?? 0 }
    var latestPrice: Double { dataPoints.last?.close  ?? 0 }

    var isPositive: Bool {
        guard let first = dataPoints.first?.close,
              let last  = dataPoints.last?.close else { return true }
        return last >= first
    }

    var changeAmount: Double {
        guard !dataPoints.isEmpty else { return 0 }
        return latestPrice - startPrice
    }

    var changePercent: Double {
        guard startPrice != 0 else { return 0 }
        return (changeAmount / startPrice) * 100
    }

    func oneDaySlotIndex(for date: Date) -> Int {
        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = TimeZone(identifier: "Asia/Jakarta")!
        let h = cal.component(.hour,   from: date)
        let m = cal.component(.minute, from: date)
        let minutesSinceOpen = (h * 60 + m) - Self.oneDayOpenMinutes
        return max(0, min(minutesSinceOpen / 5, Self.oneDayTotalSlots - 1))
    }

    // MARK: - Fetch dari API
    func fetchData() async {
        await fetchDataWithCache()
    }

    // MARK: - 1D Slot Normalization
    //
    // Memetakan candle dari API ke 87 slot tetap (09:00–16:10, interval 5 menit).
    // Slot yang tidak ada datanya (jam istirahat / gap) di-forward-fill dengan
    // harga close slot valid terakhir — sehingga garis chart tidak "loop balik".
    //
    // Slot index = (jam * 60 + menit - 540) / 5
    //   Slot  0 = 09:00
    //   Slot 86 = 16:10
    //
    // Jam istirahat (forward-fill otomatis karena slot nil):
    //   Senin–Kamis: 12:00–13:25 → slot 36–53
    //   Jumat:       11:30–13:55 → slot 30–59

    private func normalizeToSlots(_ candles: [StockDataPoint]) -> [StockDataPoint] {
        guard !candles.isEmpty else { return [] }

        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = TimeZone(identifier: "Asia/Jakarta")!

        let now        = Date()
        let totalSlots = Self.oneDayTotalSlots   // 87
        let refDate    = cal.startOfDay(for: candles[0].date)

        var slots: [StockDataPoint?] = Array(repeating: nil, count: totalSlots)

        for candle in candles {
            let h = cal.component(.hour,   from: candle.date)
            let m = cal.component(.minute, from: candle.date)
            let minutesSinceOpen = h * 60 + m - Self.oneDayOpenMinutes
            guard minutesSinceOpen >= 0 else { continue }
            let idx = minutesSinceOpen / 5
            guard idx < totalSlots else { continue }
            slots[idx] = candle
        }

        // ── Hitung slot terakhir yang boleh ditampilkan (≤ now) ──────────────
        let nowH = cal.component(.hour,   from: now)
        let nowM = cal.component(.minute, from: now)
        let nowMinutesSinceOpen = nowH * 60 + nowM - Self.oneDayOpenMinutes
        // Slot index sekarang, dibulatkan ke bawah (belum tentu ada candlenya)
        let currentSlotIdx = max(0, min(nowMinutesSinceOpen / 5, totalSlots - 1))

        // Forward-fill hanya sampai currentSlotIdx
        for i in 1...currentSlotIdx {
            if slots[i] == nil, let prev = slots[i - 1] {
                let slotMinutes = Self.oneDayOpenMinutes + i * 5
                let slotDate = cal.date(
                    bySettingHour:  slotMinutes / 60,
                    minute:         slotMinutes % 60,
                    second:         0,
                    of:             refDate
                ) ?? prev.date

                slots[i] = StockDataPoint(
                    date:   slotDate,
                    close:  prev.close,
                    open:   prev.close,
                    high:   prev.close,
                    low:    prev.close,
                    volume: 0
                )
            }
        }

        // Ambil slot 0...currentSlotIdx saja — slot masa depan tidak dirender
        return slots[0...currentSlotIdx].compactMap { $0 }
    }
}

extension StockChartViewModel {

    /// Versi baru fetchData() — pakai cache otomatis saat offline.
    /// Salin isi function ini ke fetchData() di StockChartViewModel.swift.
    func fetchDataWithCache() async {
        guard !symbol.isEmpty else { return }
        isLoading    = true
        errorMessage = nil

        let (points, state) = await chartService.fetchCandlesCached(symbol: symbol, range: selectedRange)
        cacheState   = state

        if points.isEmpty {
            errorMessage = "Tidak ada data untuk \(symbol) (\(selectedRange.rawValue))"
        } else {
            dataPoints = selectedRange == .oneDay ? normalizeToSlots(points) : points
        }

        isLoading = false
    }
}
