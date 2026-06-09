//
//  Helpers.swift
//  SahamIndo
//

import SwiftUI

// MARK: - IDR Formatter

func formatIDR(_ value: Double, decimals: Int = 0) -> String {
    let f = NumberFormatter()
    f.numberStyle          = .decimal
    f.groupingSeparator    = "."
    f.decimalSeparator     = ","
    f.minimumFractionDigits = decimals
    f.maximumFractionDigits = decimals
    return f.string(from: NSNumber(value: value)) ?? "\(Int(value))"
}

func formatIDRShort(_ value: Double) -> String {
    if value >= 1_000_000_000 { return String(format: "%.1fM",  value / 1_000_000_000) }
    if value >= 1_000_000     { return String(format: "%.1fJt", value / 1_000_000) }
    if value >= 1_000         { return String(format: "%.0fRb", value / 1_000) }
    return String(format: "%.0f", value)
}

// MARK: - Color Extension

extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let r, g, b: UInt64
        switch hex.count {
        case 6: (r, g, b) = ((int >> 16) & 0xff, (int >> 8) & 0xff, int & 0xff)
        default: (r, g, b) = (1, 1, 1)
        }
        self.init(.sRGB,
                  red:     Double(r) / 255,
                  green:   Double(g) / 255,
                  blue:    Double(b) / 255,
                  opacity: 1)
    }

    // Adaptive backgrounds — dark navy in dark mode, system colors in light mode
    static let appBackground = Color(UIColor { tc in
        tc.userInterfaceStyle == .dark
            ? UIColor(red: 18/255, green: 17/255, blue: 46/255, alpha: 1)
            : .systemBackground
    })

    static let appCardBackground = Color(UIColor { tc in
        tc.userInterfaceStyle == .dark
            ? UIColor(red: 28/255, green: 27/255, blue: 53/255, alpha: 1)
            : .secondarySystemBackground
    })

    static let appElevatedBackground = Color(UIColor { tc in
        tc.userInterfaceStyle == .dark
            ? UIColor(red: 30/255, green: 29/255, blue: 64/255, alpha: 1)
            : .tertiarySystemBackground
    })
}

// MARK: - BEI Trading Hours

struct BEITradingHours {

    private static var jakartaCalendar: Calendar {
        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = TimeZone(identifier: "Asia/Jakarta")!
        return cal
    }

    /// Apakah menit `date` termasuk jam sesi BEI (tidak termasuk jam istirahat)
    static func isTradingMinute(_ date: Date) -> Bool {
        let cal     = jakartaCalendar
        let weekday = cal.component(.weekday, from: date)
        guard weekday >= 2 && weekday <= 6 else { return false }

        let h = cal.component(.hour,   from: date)
        let m = cal.component(.minute, from: date)
        let t = h * 60 + m

        let (bS, bE) = breakRange(weekday: weekday)
        guard t >= 9 * 60 && t <= 15 * 60 + 59 else { return false }
        if t >= bS && t < bE { return false }
        return true
    }

    /// Apakah `date` adalah hari bursa (Senin–Jumat)
    static func isTradingDay(_ date: Date) -> Bool {
        let weekday = jakartaCalendar.component(.weekday, from: date)
        return weekday >= 2 && weekday <= 6
    }

    /// Rentang jam istirahat dalam menit sejak tengah malam
    static func breakRange(weekday: Int) -> (start: Int, end: Int) {
        if weekday == 6 {
            return (11 * 60 + 30, 14 * 60)   // Jumat: 11:30–14:00
        } else {
            return (12 * 60, 13 * 60 + 30)   // Senin–Kamis: 12:00–13:30
        }
    }
}
