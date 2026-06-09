//
//  IDXDummyPriceGenerator+AllRanges.swift
//  SahamIndo

import Foundation

struct IDXDummyPriceGenerator {

    // MARK: - Stock base data (hanya dipakai kalau cache 1D kosong)

    private static let stockInfo: [String: (base: Double, vol: Double, trend: Double)] = [
        "BREN":  (5_025,   80,  0.00025),
        "BBCA":  (9_950,   85,  0.00020),
        "DSSA":  (55_750, 620,  0.00035),
        "BBRI":  (4_150,   55,  0.00015),
        "TPIA":  (8_650,  125,  0.00030),
        "AMMN":  (9_200,  135,  0.00040),
        "BYAN":  (18_500, 260,  0.00020),
        "DCII":  (43_000, 520,  0.00045),
        "BMRI":  (5_675,   72,  0.00020),
        "TLKM":  (3_020,   42,  0.00010),
    ]

    private static var jakartaCal: Calendar {
        var c = Calendar(identifier: .gregorian)
        c.timeZone = TimeZone(identifier: "Asia/Jakarta")!
        return c
    }

    // MARK: - Harga hari ini (anchor semua range)
    //
    // Prioritas:
    //   1. Harga close terakhir dari cache 1D (StockCacheManager)
    //   2. info.base (hardcoded fallback)

    private static func currentPrice(symbol: String,
                                     info: (base: Double, vol: Double, trend: Double)) -> Double {
        if let cached = StockCacheManager.shared.loadCandles(symbol: symbol, range: .oneDay),
           let last   = cached.data.last {
            return last.close
        }
        return info.base
    }

    // MARK: - Public entry point

    static func generate(symbol: String, range: TimeRange) -> [StockDataPoint] {
        let info  = stockInfo[symbol] ?? (base: 1_000, vol: 20, trend: 0.0002)
        let price = currentPrice(symbol: symbol, info: info)   // ← anchor harga hari ini

        switch range {
        case .oneDay:     return generateOneDay(info: info, currentPrice: price)
        case .oneWeek:    return generateMultiDay(info: info, currentPrice: price, tradingDays: 5,   intervalMinutes: 60)
        case .oneMonth:   return generateDailyCandles(info: info, currentPrice: price, tradingDays: 22)
        case .threeMonth: return generateDailyCandles(info: info, currentPrice: price, tradingDays: 66)
        case .ytd:        return generateYTD(info: info, currentPrice: price)
        case .oneYear:    return generateDailyCandles(info: info, currentPrice: price, tradingDays: 252)
        case .fiveYear:   return generateWeeklyCandles(info: info, currentPrice: price, weeks: 260)
        }
    }

    // MARK: - 1D  (slot 5 menit, jam bursa BEI)

    private static func generateOneDay(
        info: (base: Double, vol: Double, trend: Double),
        currentPrice: Double
    ) -> [StockDataPoint] {
        let cal = jakartaCal
        let now = Date()
        var rng = SeededRNG(seed: 42)

        var startDay = cal.startOfDay(for: now)
        while !BEITradingHours.isTradingDay(startDay) {
            startDay = cal.date(byAdding: .day, value: -1, to: startDay)!
        }

        let open9    = cal.date(bySettingHour: 9,  minute: 0,  second: 0, of: startDay)!
        let close16  = cal.date(bySettingHour: 15, minute: 55, second: 0, of: startDay)!

        var slots: [Date] = []
        var cursor = open9
        while cursor <= close16 {
            slots.append(cursor)
            cursor = cal.date(byAdding: .minute, value: 5, to: cursor)!
        }

        // Simulasi mundur dari currentPrice supaya titik terakhir = currentPrice
        let validSlots = slots.filter { $0 <= now }
        guard !validSlots.isEmpty else { return [] }

        let prices = simulateBackward(base: currentPrice, vol: info.vol * 0.18,
                                      trend: 0, steps: validSlots.count, rng: &rng)

        return validSlots.enumerated().compactMap { (i, slot) in
            let h    = cal.component(.hour,   from: slot)
            let m    = cal.component(.minute, from: slot)
            let t    = h * 60 + m
            let wday = cal.component(.weekday, from: slot)
            let (bS, bE) = BEITradingHours.breakRange(weekday: wday)
            // Jam istirahat: tahan harga (forward-fill)
            let p = (t >= bS && t < bE) ? (i > 0 ? prices[i - 1] : prices[i]) : prices[i]
            return makePoint(date: slot, price: p, vol: info.vol, rng: &rng)
        }
    }

    // MARK: - 1W  (slot 1 jam, 5 hari bursa)

    private static func generateMultiDay(
        info: (base: Double, vol: Double, trend: Double),
        currentPrice: Double,
        tradingDays: Int,
        intervalMinutes: Int
    ) -> [StockDataPoint] {
        let cal = jakartaCal
        let now = Date()
        var rng = SeededRNG(seed: 7)

        let days = lastTradingDays(count: tradingDays, before: now, cal: cal)

        // Hitung total slot, simulasi mundur dari currentPrice
        var allSlots: [(date: Date, dayIdx: Int)] = []
        for (di, day) in days.enumerated() {
            let open9   = cal.date(bySettingHour: 9,  minute: 0, second: 0, of: day)!
            let close15 = cal.date(bySettingHour: 15, minute: 0, second: 0, of: day)!
            var c = open9
            while c <= min(close15, now) {
                allSlots.append((c, di))
                c = cal.date(byAdding: .minute, value: intervalMinutes, to: c)!
            }
        }
        guard !allSlots.isEmpty else { return [] }

        let prices = simulateBackward(base: currentPrice, vol: info.vol * 0.04,
                                      trend: info.trend, steps: allSlots.count, rng: &rng)

        return allSlots.enumerated().map { (i, slot) in
            makePoint(date: slot.date, price: prices[i], vol: info.vol, rng: &rng)
        }
    }

    // MARK: - 1M / 3M / 1Y  (1 candle per hari bursa)

    private static func generateDailyCandles(
        info: (base: Double, vol: Double, trend: Double),
        currentPrice: Double,
        tradingDays: Int
    ) -> [StockDataPoint] {
        let cal = jakartaCal
        let now = Date()
        var rng = SeededRNG(seed: 13)

        let days   = lastTradingDays(count: tradingDays, before: now, cal: cal)
        let prices = simulateBackward(base: currentPrice, vol: info.vol,
                                      trend: info.trend, steps: tradingDays, rng: &rng)

        return days.enumerated().map { (i, day) in
            let closeTime = cal.date(bySettingHour: 15, minute: 50, second: 0, of: day)!
            return makePoint(date: closeTime, price: prices[i], vol: info.vol, rng: &rng)
        }
    }

    // MARK: - YTD

    private static func generateYTD(
        info: (base: Double, vol: Double, trend: Double),
        currentPrice: Double
    ) -> [StockDataPoint] {
        let cal  = jakartaCal
        let now  = Date()
        var rng  = SeededRNG(seed: 99)

        let year  = cal.component(.year, from: now)
        var comps = DateComponents(); comps.year = year; comps.month = 1; comps.day = 1
        let jan1  = cal.date(from: comps)!

        var days: [Date] = []
        var cursor = jan1
        while cursor <= now {
            if BEITradingHours.isTradingDay(cursor) { days.append(cursor) }
            cursor = cal.date(byAdding: .day, value: 1, to: cursor)!
        }
        guard !days.isEmpty else { return [] }

        let prices = simulateBackward(base: currentPrice, vol: info.vol,
                                      trend: info.trend, steps: days.count, rng: &rng)

        return days.enumerated().map { (i, day) in
            let closeTime = cal.date(bySettingHour: 15, minute: 50, second: 0, of: day)!
            return makePoint(date: closeTime, price: prices[i], vol: info.vol, rng: &rng)
        }
    }

    // MARK: - 5Y  (1 candle per minggu)

    private static func generateWeeklyCandles(
        info: (base: Double, vol: Double, trend: Double),
        currentPrice: Double,
        weeks: Int
    ) -> [StockDataPoint] {
        let cal = jakartaCal
        let now = Date()
        var rng = SeededRNG(seed: 31)

        // Simulasi mundur dari currentPrice — prices[last] = currentPrice
        let prices = simulateBackward(base: currentPrice, vol: info.vol * 3,
                                      trend: info.trend, steps: weeks, rng: &rng)

        return (0..<weeks).compactMap { i in
            let daysAgo   = (weeks - 1 - i) * 7
            guard let day = cal.date(byAdding: .day, value: -daysAgo, to: now) else { return nil }
            let closeTime = cal.date(bySettingHour: 15, minute: 50, second: 0, of: day) ?? day
            return makePoint(date: closeTime, price: prices[i], vol: info.vol, rng: &rng)
        }
    }

    // MARK: - Core: simulateBackward
    //
    // Menghasilkan array harga ASCENDING (index 0 = paling lama).
    // prices[steps-1] dijamin = base (= harga hari ini).
    // Simulasi berjalan MUNDUR dari titik akhir ke titik awal,
    // sehingga titik terakhir selalu tepat = currentPrice.

    private static func simulateBackward(
        base: Double,
        vol: Double,
        trend: Double,
        steps: Int,
        rng: inout SeededRNG
    ) -> [Double] {
        guard steps > 0 else { return [] }
        var prices = Array(repeating: 0.0, count: steps)
        prices[steps - 1] = base                           // ← titik terakhir = harga hari ini
        for i in stride(from: steps - 2, through: 0, by: -1) {
            let trendAdj = prices[i + 1] * trend
            let noise    = rng.nextDouble(in: -vol ... vol)
            prices[i]    = max(prices[i + 1] - trendAdj + noise, 50)
        }
        return prices
    }

    // MARK: - Helpers

    private static func lastTradingDays(count: Int, before date: Date, cal: Calendar) -> [Date] {
        var result: [Date] = []
        var cursor = cal.startOfDay(for: date)
        while result.count < count {
            if BEITradingHours.isTradingDay(cursor) { result.insert(cursor, at: 0) }
            cursor = cal.date(byAdding: .day, value: -1, to: cursor)!
        }
        return result
    }

    private static func makePoint(
        date: Date,
        price: Double,
        vol: Double,
        rng: inout SeededRNG
    ) -> StockDataPoint {
        let spread = vol * 0.3
        let open   = max(price + rng.nextDouble(in: -spread ... spread), 50)
        let high   = max(price, open) + abs(rng.nextDouble(in: 0 ... spread))
        let low    = min(price, open) - abs(rng.nextDouble(in: 0 ... spread))
        let volume = Double(Int.random(in: 1_000_000 ... 50_000_000))
        return StockDataPoint(date: date, close: price, open: open,
                              high: high, low: low, volume: volume)
    }
}

// ─────────────────────────────────────────────────────────────
// MARK: - SeededRNG (deterministik, konsisten saat offline)
// ─────────────────────────────────────────────────────────────

private struct SeededRNG {
    private var state: UInt64

    init(seed: UInt64) { self.state = seed == 0 ? 1 : seed }

    mutating func next() -> UInt64 {
        state ^= state << 13
        state ^= state >> 7
        state ^= state << 17
        return state
    }

    mutating func nextDouble(in range: ClosedRange<Double>) -> Double {
        let raw = Double(next()) / Double(UInt64.max)
        return range.lowerBound + raw * (range.upperBound - range.lowerBound)
    }
}
