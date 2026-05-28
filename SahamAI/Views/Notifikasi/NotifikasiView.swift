import SwiftUI

struct NotifikasiView: View {
    @Binding var badgeCount: Int
    
    @State private var alerts: [AlertModel] = []
    @State private var isLoading = false
    @State private var errorMessage: String? = nil
    
    var body: some View {
        NavigationStack {
            Group {
                if isLoading && alerts.isEmpty {
                    VStack(spacing: 16) {
                        ProgressView()
                        Text("Memuat data notifikasi...")
                            .foregroundColor(.secondary)
                            .font(.subheadline)
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .background(Color(.systemGroupedBackground))
                } else if let error = errorMessage {
                    VStack(spacing: 16) {
                        Image(systemName: "wifi.slash")
                            .font(.system(size: 50))
                            .foregroundColor(.red)
                        Text("Gagal memuat notifikasi")
                            .font(.headline)
                        Text(error)
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                            .multilineTextAlignment(.center)
                        Button("Coba Lagi") {
                            Task {
                                await loadAlerts()
                            }
                        }
                        .buttonStyle(.borderedProminent)
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .background(Color(.systemGroupedBackground))
                    .padding()
                } else if alerts.isEmpty {
                    // Empty State Kustom
                    VStack(spacing: 24) {
                        Image(systemName: "bell.and.waves.left.and.right")
                            .font(.system(size: 80))
                            .foregroundColor(.secondary)
                            .symbolEffect(.bounce.up.byLayer, options: .repeating)
                        
                        VStack(spacing: 8) {
                            Text("Belum Ada Alert")
                                .font(.title3)
                                .fontWeight(.bold)
                            Text("Sistem memantau saham Anda setiap 30 menit.")
                                .font(.subheadline)
                                .foregroundColor(.secondary)
                                .multilineTextAlignment(.center)
                                .padding(.horizontal, 32)
                        }
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .background(Color(.systemGroupedBackground))
                } else {
                    List {
                        Section(header: Text("Riwayat Alert Sentimen").font(.caption).fontWeight(.bold)) {
                            ForEach(alerts) { alert in
                                AlertCustomRow(alert: alert)
                            }
                        }
                    }
                    .listStyle(.insetGrouped)
                    .refreshable {
                        await loadAlerts()
                    }
                }
            }
            .navigationTitle("Notifikasi")
            .task {
                await loadAlerts()
            }
        }
    }
    
    private func loadAlerts() async {
        isLoading = true
        errorMessage = nil
        do {
            let fetchedAlerts = try await NetworkManager.shared.fetchAlerts()
            self.alerts = fetchedAlerts
            
            // Perbarui jumlah badge dengan total notifikasi baru
            self.badgeCount = fetchedAlerts.count
        } catch {
            self.errorMessage = error.localizedDescription
        }
        isLoading = false
    }
}

// Subview: Baris Alert Notifikasi (AlertCustomRow)
struct AlertCustomRow: View {
    let alert: AlertModel
    
    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            // Dot Warna: Hijau jika positif, Merah jika negatif
            Circle()
                .fill(alert.delta >= 0 ? Color.green : Color.red)
                .frame(width: 10, height: 10)
                .padding(.top, 6)
            
            VStack(alignment: .leading, spacing: 6) {
                HStack {
                    Text(alert.kodeSaham)
                        .font(.system(size: 16, weight: .bold, design: .rounded))
                        .foregroundColor(Color(.label))
                    
                    Spacer()
                    
                    Text(formatISODate(alert.tanggal))
                        .font(.system(size: 10))
                        .foregroundColor(.secondary)
                }
                
                Text(alert.pesan)
                    .font(.system(size: 13))
                    .foregroundColor(Color(.label))
                    .lineLimit(4)
                
                Text(String(format: "Perubahan: %+.1f poin", alert.delta))
                    .font(.system(size: 11, weight: .bold))
                    .foregroundColor(alert.delta >= 0 ? .green : .red)
            }
        }
        .padding(.vertical, 4)
    }
    
    private func formatISODate(_ dateStr: String) -> String {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        
        let fallbackFormatter = ISO8601DateFormatter()
        fallbackFormatter.formatOptions = [.withInternetDateTime]
        
        if let date = formatter.date(from: dateStr) ?? fallbackFormatter.date(from: dateStr) {
            let displayFormatter = DateFormatter()
            displayFormatter.dateFormat = "dd MMM, HH:mm"
            return displayFormatter.string(from: date)
        }
        return dateStr
    }
}
