import SwiftUI

struct DashboardView: View {
    @Binding var selectedTab: Int
    let chatbotViewModel: ChatbotViewModel
    @State var viewModel: DashboardViewModel
    
    var body: some View {
        NavigationStack {
            Group {
                if viewModel.isLoading && viewModel.rekomendasi.isEmpty {
                    VStack(spacing: 16) {
                        ProgressView()
                            .scaleEffect(1.5)
                        Text("Menganalisis data bursa...")
                            .foregroundColor(.secondary)
                            .font(.subheadline)
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .background(Color(.systemGroupedBackground))
                } else if let error = viewModel.errorMessage, viewModel.rekomendasi.isEmpty {
                    VStack(spacing: 20) {
                        Image(systemName: "wifi.exclamationmark")
                            .font(.system(size: 60))
                            .foregroundColor(.red)
                        Text("Koneksi Bermasalah")
                            .font(.title2)
                            .fontWeight(.bold)
                        Text(error)
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                            .multilineTextAlignment(.center)
                            .padding(.horizontal, 32)
                        Button("Coba Lagi") {
                            Task {
                                await viewModel.loadDashboardData()
                            }
                        }
                        .buttonStyle(.borderedProminent)
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .background(Color(.systemGroupedBackground))
                } else {
                    VStack(alignment: .leading, spacing: 0) {
                        
                        // Header Subtitle (Tanggal Update)
                        Text("Pembaruan terakhir: \(viewModel.rekomendasi.first != nil ? "Hari Ini" : "Belum ada data")")
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                            .padding(.horizontal)
                            .padding(.bottom, 12)
                        
                        // Horizontal Scroll Card Makroekonomi
                        if let makro = viewModel.makro {
                            ScrollView(.horizontal, showsIndicators: false) {
                                HStack(spacing: 12) {
                                    MacroCardView(title: "BI Rate", value: makro.biRate == 0 ? "N/A" : String(format: "%.2f%%", makro.biRate), icon: "percent", color: .red)
                                    MacroCardView(title: "USD / IDR", value: String(format: "Rp %.0f", makro.usdIdr), icon: "dollarsign.circle.fill", color: .green)
                                    MacroCardView(title: "Inflasi YoY", value: String(format: "%.2f%%", makro.inflasi), icon: "arrow.up.forward.circle.fill", color: .orange)
                                    MacroCardView(title: "IHSG", value: String(format: "%.2f", makro.ihsg), icon: "chart.line.uptrend.xyaxis", color: .blue)
                                }
                                .padding(.horizontal)
                            }
                            .padding(.bottom, 16)
                        }
                        
                        // List Rekomendasi Saham
                        List {
                            Section(header: Text("Daftar Emiten Teratas").font(.caption).fontWeight(.bold)) {
                                ForEach(viewModel.rekomendasi) { stock in
                                    NavigationLink(destination: DetailSahamView(
                                        kodeSaham: stock.kodeSaham,
                                        selectedTab: $selectedTab,
                                        chatbotViewModel: chatbotViewModel
                                    )) {
                                        SahamRowView(stock: stock)
                                    }
                                }
                            }
                        }
                        .listStyle(.insetGrouped)
                        .refreshable {
                            await viewModel.loadDashboardData()
                        }
                    }
                    .background(Color(.systemGroupedBackground))
                }
            }
            .navigationTitle("Rekomendasi Minggu Ini")
            .task {
                await viewModel.loadDashboardData()
            }
        }
    }
}

// Subview: Card Makroekonomi
struct MacroCardView: View {
    let title: String
    let value: String
    let icon: String
    let color: Color
    
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Image(systemName: icon)
                    .foregroundColor(color)
                    .font(.headline)
                Spacer()
            }
            
            Text(value)
                .font(.headline)
                .fontWeight(.bold)
                .foregroundColor(Color(.label))
            
            Text(title)
                .font(.system(size: 11))
                .foregroundColor(.secondary)
        }
        .padding(12)
        .frame(width: 120, height: 85)
        .background(Color(.secondarySystemGroupedBackground))
        .cornerRadius(12)
        .shadow(color: Color.black.opacity(0.03), radius: 4, x: 0, y: 2)
    }
}

// Subview: Baris List Rekomendasi Saham (SahamRowView)
struct SahamRowView: View {
    let stock: Rekomendasi
    
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .center) {
                // Ticker dan Nama
                VStack(alignment: .leading, spacing: 2) {
                    Text(stock.kodeSaham)
                        .font(.system(size: 18, weight: .bold, design: .rounded))
                        .foregroundColor(Color(.label))
                    if let name = stock.namaPerusahaan {
                        Text(name)
                            .font(.system(size: 12))
                            .foregroundColor(.secondary)
                            .lineLimit(1)
                    }
                }
                
                Spacer()
                
                // Badge BUY/HOLD/SELL
                Text(stock.rekomendasi)
                    .font(.system(size: 11, weight: .black))
                    .foregroundColor(.white)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 5)
                    .background(badgeColor(stock.rekomendasi))
                    .cornerRadius(8)
            }
            
            // Score Bar & Angka Skor
            HStack(spacing: 12) {
                ProgressView(value: stock.skorTotal, total: 100.0)
                    .tint(.blue)
                    .frame(height: 6)
                
                Text(String(format: "%.1f", stock.skorTotal))
                    .font(.system(size: 13, weight: .bold, design: .rounded))
                    .foregroundColor(.blue)
            }
            
            // Alasan Singkat (1 baris, truncated)
            if let alasan = stock.alasan {
                Text(alasan)
                    .font(.system(size: 11))
                    .foregroundColor(.secondary)
                    .lineLimit(1)
            }
        }
        .padding(.vertical, 4)
    }
    
    private func badgeColor(_ type: String) -> Color {
        switch type.uppercased() {
        case "BUY":
            return .green
        case "HOLD":
            return .orange
        case "SELL":
            return .red
        default:
            return .gray
        }
    }
}
