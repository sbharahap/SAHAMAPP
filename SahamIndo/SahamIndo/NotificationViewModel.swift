//
//  NotificationViewModel.swift
//  SahamIndo
//

import SwiftUI
import Combine
import UserNotifications

@MainActor
final class NotificationViewModel: ObservableObject {

    // MARK: - Published

    @Published private(set) var alerts:     [StockAlert] = []
    @Published private(set) var isChecking: Bool         = false

    // MARK: - Computed

    var unreadCount: Int { alerts.filter { !$0.isRead }.count }

    // MARK: - Private

    private let service      = RealStockService()
    private let alertsKey    = "stock_alerts_v1"
    private let lastCheckKey = "stock_alerts_last_check"

    // Major IDX symbols to monitor for sentiment signals
    private let watchSymbols = [
        "BBCA", "BBRI", "BMRI", "BBNI", "TLKM",
        "ASII", "UNVR", "ADRO", "GGRM", "KLBF",
        "ANTM", "PGAS", "ICBP", "INDF", "UNTR",
        "PTBA", "MEDC", "BRIS", "AMRT", "MDKA"
    ]

    // Thresholds for triggering an alert
    private let bullishThreshold: Double = 75.0
    private let bearishThreshold: Double = 30.0

    // MARK: - Init

    init() {
        loadAlerts()
    }

    // MARK: - Public

    /// Fetch latest sentiment from database and create alerts for strong signals.
    /// Rate-limited to once per hour; always runs if no previous check exists.
    func checkForAlerts() async {
        guard !isChecking else { return }

        if let lastCheck = UserDefaults.standard.object(forKey: lastCheckKey) as? Date,
           Date().timeIntervalSince(lastCheck) < 3600 { return }

        isChecking = true
        await requestNotificationPermission()

        // Skip symbols already alerted today to avoid duplicates
        let alertedToday = Set(
            alerts
                .filter { Calendar.current.isDateInToday($0.date) }
                .map { $0.symbol }
        )

        for symbol in watchSymbols where !alertedToday.contains(symbol) {
            guard let detail = try? await service.fetchDetail(symbol: symbol) else { continue }

            let isStrongBuy  = detail.score >= bullishThreshold && detail.sentiment == .recommended
            let isStrongSell = detail.score <= bearishThreshold && detail.sentiment == .caution
            guard isStrongBuy || isStrongSell else { continue }

            let alert = StockAlert(
                date:      Date(),
                symbol:    detail.symbol,
                stockName: detail.name,
                sector:    detail.sector,
                alertType: isStrongBuy ? .strongBuy : .strongSell,
                score:     detail.score,
                aiSummary: detail.aiSummary
            )
            alerts.insert(alert, at: 0)
            await schedulePushNotification(for: alert)
        }

        // Keep only the 50 most recent alerts
        if alerts.count > 50 { alerts = Array(alerts.prefix(50)) }

        saveAlerts()
        UserDefaults.standard.set(Date(), forKey: lastCheckKey)
        isChecking = false
    }

    func markRead(_ id: UUID) {
        guard let idx = alerts.firstIndex(where: { $0.id == id }) else { return }
        alerts[idx].isRead = true
        saveAlerts()
    }

    func markAllRead() {
        alerts = alerts.map { var a = $0; a.isRead = true; return a }
        saveAlerts()
    }

    func clearAll() {
        alerts = []
        saveAlerts()
    }

    // MARK: - Push Notifications

    private func requestNotificationPermission() async {
        _ = try? await UNUserNotificationCenter.current()
            .requestAuthorization(options: [.alert, .badge, .sound])
    }

    private func schedulePushNotification(for alert: StockAlert) async {
        let content = UNMutableNotificationContent()
        content.title  = alert.alertType == .strongBuy ? "📈 Sinyal Bullish Kuat" : "📉 Sinyal Bearish Kuat"
        let name       = alert.stockName ?? alert.symbol
        let preview    = String(alert.aiSummary.prefix(100))
        content.body   = "\(alert.symbol) (\(name)) — Score \(Int(alert.score))\n\(preview)..."
        content.sound  = .default

        let trigger = UNTimeIntervalNotificationTrigger(timeInterval: 1, repeats: false)
        let request  = UNNotificationRequest(identifier: alert.id.uuidString,
                                             content: content,
                                             trigger: trigger)
        try? await UNUserNotificationCenter.current().add(request)
    }

    // MARK: - Persistence

    private func saveAlerts() {
        guard let encoded = try? JSONEncoder().encode(alerts) else { return }
        UserDefaults.standard.set(encoded, forKey: alertsKey)
    }

    private func loadAlerts() {
        guard let data    = UserDefaults.standard.data(forKey: alertsKey),
              let decoded = try? JSONDecoder().decode([StockAlert].self, from: data)
        else { return }
        alerts = decoded
    }
}
