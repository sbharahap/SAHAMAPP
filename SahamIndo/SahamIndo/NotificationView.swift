//
//  NotificationView.swift
//  SahamIndo
//

import SwiftUI

// MARK: - Notification List View

struct NotificationView: View {

    @EnvironmentObject private var notifVM:   NotificationViewModel
    @EnvironmentObject private var router:    Router
    @EnvironmentObject private var chatbotVM: ChatbotViewModel

    @State private var selectedAlert: StockAlert? = nil

    var body: some View {
        Group {
            if notifVM.isChecking && notifVM.alerts.isEmpty {
                loadingState
            } else if notifVM.alerts.isEmpty {
                emptyState
            } else {
                alertsList
            }
        }
        .background(Color.appBackground.ignoresSafeArea())
        .navigationTitle("Notifikasi Sinyal")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            if !notifVM.alerts.isEmpty {
                ToolbarItem(placement: .topBarTrailing) {
                    Menu {
                        Button {
                            notifVM.markAllRead()
                        } label: {
                            Label("Tandai Semua Dibaca", systemImage: "checkmark.circle")
                        }
                        Button(role: .destructive) {
                            notifVM.clearAll()
                        } label: {
                            Label("Hapus Semua", systemImage: "trash")
                        }
                    } label: {
                        Image(systemName: "ellipsis.circle").foregroundColor(.primary)
                    }
                }
            }
        }
        .sheet(item: $selectedAlert) { alert in
            NotificationDetailView(alert: alert)
                .environmentObject(router)
                .environmentObject(chatbotVM)
        }
        .task { await notifVM.checkForAlerts() }
    }

    // MARK: - States

    private var loadingState: some View {
        VStack(spacing: 16) {
            ProgressView().tint(Color(hex: "FFA500")).scaleEffect(1.2)
            Text("Memeriksa sinyal pasar dari database…")
                .font(.system(size: 13))
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 32)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private var emptyState: some View {
        VStack(spacing: 14) {
            Image(systemName: "bell.slash")
                .font(.system(size: 44))
                .foregroundColor(.secondary)
                .padding(.bottom, 4)
            Text("Belum Ada Sinyal")
                .font(.system(size: 16, weight: .bold))
                .foregroundColor(.primary)
            Text("Sistem memantau sentimen \(notifVM.isChecking ? "saat ini…" : "setiap jam"). Notifikasi akan muncul ketika ada sinyal bullish atau bearish kuat dari database.")
                .font(.system(size: 12))
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 40)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private var alertsList: some View {
        ScrollView {
            VStack(spacing: 0) {
                if notifVM.isChecking {
                    HStack(spacing: 8) {
                        ProgressView().scaleEffect(0.75).tint(.secondary)
                        Text("Memperbarui dari database…")
                            .font(.system(size: 11))
                            .foregroundColor(.secondary)
                    }
                    .padding(.vertical, 10)
                }

                VStack(spacing: 8) {
                    ForEach(notifVM.alerts) { alert in
                        AlertRowView(alert: alert)
                            .onTapGesture {
                                notifVM.markRead(alert.id)
                                selectedAlert = alert
                            }
                    }
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 12)
            }
        }
    }
}

// MARK: - Alert Row

struct AlertRowView: View {

    let alert: StockAlert

    private let green  = Color(hex: "22C55E")
    private let red    = Color(hex: "EF4444")
    private let cardBg = Color.appCardBackground

    private var signalColor: Color { alert.alertType == .strongBuy ? green : red }

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            Image(systemName: alert.alertType == .strongBuy
                  ? "arrow.up.circle.fill"
                  : "exclamationmark.circle.fill")
                .font(.system(size: 30))
                .foregroundColor(signalColor)

            VStack(alignment: .leading, spacing: 4) {
                HStack(spacing: 6) {
                    Text(alert.symbol)
                        .font(.system(size: 14, weight: .bold))
                        .foregroundColor(.primary)

                    Text(alert.alertType == .strongBuy ? "STRONG BUY" : "STRONG SELL")
                        .font(.system(size: 9, weight: .bold))
                        .foregroundColor(alert.alertType == .strongBuy ? .black : .white)
                        .padding(.horizontal, 6).padding(.vertical, 2)
                        .background(signalColor)
                        .clipShape(Capsule())

                    Spacer()

                    Text("Score \(Int(alert.score))")
                        .font(.system(size: 10, weight: .bold))
                        .foregroundColor(signalColor)
                }

                if let name = alert.stockName {
                    Text(name)
                        .font(.system(size: 11))
                        .foregroundColor(.secondary)
                        .lineLimit(1)
                }

                Text(String(alert.aiSummary.prefix(100)) + "…")
                    .font(.system(size: 11))
                    .foregroundColor(Color.primary.opacity(0.7))
                    .lineLimit(2)

                Text(relativeDate(alert.date))
                    .font(.system(size: 9))
                    .foregroundColor(.secondary)
                    .padding(.top, 1)
            }

            if !alert.isRead {
                Circle().fill(Color.blue).frame(width: 8, height: 8).padding(.top, 6)
            }
        }
        .padding(12)
        .background(cardBg)
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(alert.isRead ? Color.primary.opacity(0.06) : signalColor.opacity(0.3),
                        lineWidth: 1)
        )
        .opacity(alert.isRead ? 0.75 : 1.0)
    }

    private func relativeDate(_ date: Date) -> String {
        let diff = Date().timeIntervalSince(date)
        if diff < 60    { return "Baru saja" }
        if diff < 3600  { return "\(Int(diff / 60)) menit lalu" }
        if diff < 86400 { return "\(Int(diff / 3600)) jam lalu" }
        let f = DateFormatter()
        f.dateFormat = "d MMM yyyy, HH:mm"
        f.locale = Locale(identifier: "id_ID")
        return f.string(from: date)
    }
}

// MARK: - Notification Detail View

struct NotificationDetailView: View {

    let alert: StockAlert

    @EnvironmentObject private var router:    Router
    @EnvironmentObject private var chatbotVM: ChatbotViewModel
    @Environment(\.dismiss) private var dismiss

    private let green   = Color(hex: "22C55E")
    private let red     = Color(hex: "EF4444")
    private let accent  = Color(hex: "FFA500")
    private let indigo  = Color(hex: "818CF8")
    private let cardBg  = Color.appCardBackground
    private let bgColor = Color.appBackground

    private var signalColor: Color { alert.alertType == .strongBuy ? green : red }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 16) {
                    headerCard
                    scoreCard
                    aiSummaryCard
                    askAgentButton
                }
                .padding(16)
                .padding(.bottom, 32)
            }
            .background(bgColor.ignoresSafeArea())
            .navigationTitle(alert.symbol)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Tutup") { dismiss() }.foregroundColor(.secondary)
                }
            }
        }
    }

    // MARK: - Header Card

    private var headerCard: some View {
        VStack(spacing: 12) {
            HStack(alignment: .top, spacing: 12) {
                Image(systemName: alert.alertType == .strongBuy
                      ? "arrow.up.circle.fill"
                      : "exclamationmark.circle.fill")
                    .font(.system(size: 40))
                    .foregroundColor(signalColor)

                VStack(alignment: .leading, spacing: 4) {
                    HStack(spacing: 6) {
                        Text(alert.symbol)
                            .font(.system(size: 20, weight: .bold))
                            .foregroundColor(.primary)

                        Text(alert.alertType == .strongBuy ? "STRONG BUY" : "STRONG SELL")
                            .font(.system(size: 10, weight: .bold))
                            .foregroundColor(alert.alertType == .strongBuy ? .black : .white)
                            .padding(.horizontal, 8).padding(.vertical, 3)
                            .background(signalColor)
                            .clipShape(Capsule())
                    }

                    if let name = alert.stockName {
                        Text(name).font(.system(size: 12)).foregroundColor(.secondary)
                    }

                    if let sector = alert.sector {
                        HStack(spacing: 4) {
                            Image(systemName: "building.2").font(.system(size: 9))
                            Text(sector).font(.system(size: 10))
                        }
                        .foregroundColor(.secondary)
                    }
                }
                Spacer()
            }

            Rectangle().fill(Color.primary.opacity(0.08)).frame(height: 1)

            HStack {
                HStack(spacing: 4) {
                    Circle().fill(Color(hex: "22C55E")).frame(width: 6, height: 6)
                    Text("Data live dari database")
                        .font(.system(size: 10, weight: .medium))
                        .foregroundColor(.secondary)
                }
                Spacer()
                Text(fullDate(alert.date)).font(.system(size: 10)).foregroundColor(.secondary)
            }
        }
        .padding(16)
        .background(cardBg)
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .overlay(RoundedRectangle(cornerRadius: 16).stroke(signalColor.opacity(0.3), lineWidth: 1))
    }

    // MARK: - Score Card

    private var scoreCard: some View {
        VStack(spacing: 10) {
            HStack {
                Text("Skor Sentimen")
                    .font(.system(size: 14, weight: .bold)).foregroundColor(.primary)
                Spacer()
                Text(String(format: "%.1f / 100", alert.score))
                    .font(.system(size: 14, weight: .bold, design: .rounded))
                    .foregroundColor(signalColor)
            }

            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    RoundedRectangle(cornerRadius: 4)
                        .fill(Color.primary.opacity(0.08)).frame(height: 10)
                    RoundedRectangle(cornerRadius: 4)
                        .fill(LinearGradient(
                            colors: [signalColor.opacity(0.6), signalColor],
                            startPoint: .leading, endPoint: .trailing))
                        .frame(width: geo.size.width * CGFloat(min(alert.score / 100.0, 1.0)),
                               height: 10)
                }
            }
            .frame(height: 10)

            HStack {
                Text("Bearish Kuat").font(.system(size: 9, weight: .medium)).foregroundColor(red)
                Spacer()
                Text("Bullish Kuat").font(.system(size: 9, weight: .medium)).foregroundColor(green)
            }
        }
        .padding(16)
        .background(cardBg)
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .overlay(RoundedRectangle(cornerRadius: 16).stroke(Color.primary.opacity(0.08), lineWidth: 1))
    }

    // MARK: - AI Summary Card

    private var aiSummaryCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 6) {
                Image(systemName: "sparkles")
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundColor(indigo)
                Text("Analisis AI dari Database")
                    .font(.system(size: 14, weight: .bold)).foregroundColor(.primary)
                Spacer()
            }

            Rectangle().fill(Color.primary.opacity(0.08)).frame(height: 1)

            Text(alert.aiSummary)
                .font(.system(size: 13))
                .foregroundColor(Color.primary.opacity(0.85))
                .lineSpacing(5)
                .fixedSize(horizontal: false, vertical: true)

            if let sector = alert.sector {
                Rectangle().fill(Color.primary.opacity(0.08)).frame(height: 1)
                HStack(spacing: 5) {
                    Image(systemName: "building.2").font(.system(size: 10))
                    Text("Sektor: \(sector)").font(.system(size: 11, weight: .medium))
                }
                .foregroundColor(.secondary)
            }
        }
        .padding(16)
        .background(
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .fill(cardBg)
                .overlay(
                    RoundedRectangle(cornerRadius: 16, style: .continuous)
                        .strokeBorder(
                            LinearGradient(
                                colors: [indigo.opacity(0.35), indigo.opacity(0.08)],
                                startPoint: .topLeading, endPoint: .bottomTrailing),
                            lineWidth: 1)
                )
        )
    }

    // MARK: - Ask AI Agent Button

    private var askAgentButton: some View {
        Button(action: askAIAgent) {
            HStack(spacing: 10) {
                Image(systemName: "sparkles").font(.system(size: 16, weight: .semibold))
                VStack(alignment: .leading, spacing: 1) {
                    Text("Tanya AI Agent tentang \(alert.symbol)")
                        .font(.system(size: 14, weight: .bold))
                    Text("Analisis mendalam + sumber & rekomendasi konkret")
                        .font(.system(size: 10)).opacity(0.82)
                }
                Spacer()
                Image(systemName: "chevron.right").font(.system(size: 11, weight: .semibold))
            }
            .foregroundColor(.white)
            .padding(16)
            .background(accent)
            .cornerRadius(14)
        }
        .buttonStyle(.plain)
    }

    // MARK: - Helpers

    private func askAIAgent() {
        let signalType = alert.alertType == .strongBuy
            ? "bullish kuat (Strong Buy)"
            : "bearish kuat (Strong Sell)"
        let sectorPart = alert.sector.map { " di sektor \($0)" } ?? ""
        let namePart   = alert.stockName.map { " (\($0))" } ?? ""
        chatbotVM.inputText = """
        Berikan analisis mendalam tentang saham \(alert.symbol)\(namePart)\(sectorPart) yang memiliki sinyal \(signalType) dengan skor sentimen \(Int(alert.score))/100. \
        Jelaskan: (1) faktor utama yang mendorong sinyal ini, (2) risiko yang perlu diperhatikan, \
        (3) potensi target harga jangka pendek & menengah, dan (4) rekomendasi tindakan konkret dengan sumber referensinya.
        """
        router.selectedTab = "assets"
        dismiss()
    }

    private func fullDate(_ date: Date) -> String {
        let f = DateFormatter()
        f.dateFormat = "d MMM yyyy, HH:mm"
        f.locale = Locale(identifier: "id_ID")
        return f.string(from: date)
    }
}
