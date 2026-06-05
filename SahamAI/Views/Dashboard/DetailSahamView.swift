import SwiftUI

struct DetailSahamView: View {
    let kodeSaham: String
    @Binding var selectedTab: Int
    let chatbotViewModel: ChatbotViewModel
    
    @State private var detail: RekomendasiDetail? = nil
    @State private var isLoading = false
    @State private var errorMessage: String? = nil
    
    @Environment(\.dismiss) private var dismiss
    
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                if isLoading {
                    VStack {
                        Spacer()
                        ProgressView()
                            .scaleEffect(1.3)
                        Text("Menganalisis data emiten...")
                            .foregroundColor(.secondary)
                            .font(.subheadline)
                            .padding(.top)
                        Spacer()
                    }
                    .frame(maxWidth: .infinity, minHeight: 300)
                } else if let error = errorMessage {
                    VStack(spacing: 16) {
                        Image(systemName: "exclamationmark.octagon.fill")
                            .font(.system(size: 50))
                            .foregroundColor(.red)
                        Text("Gagal memuat detail")
                            .font(.headline)
                        Text(error)
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                            .multilineTextAlignment(.center)
                        Button("Coba Lagi") {
                            Task {
                                await loadDetail()
                            }
                        }
                        .buttonStyle(.borderedProminent)
                    }
                    .frame(maxWidth: .infinity, minHeight: 300)
                    .padding()
                } else if let d = detail {
                    
                    // Header Card
                    VStack(alignment: .leading, spacing: 12) {
                        HStack {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(d.kodeSaham)
                                    .font(.system(size: 34, weight: .black, design: .rounded))
                                    .foregroundColor(Color(.label))
                                if let name = d.namaPerusahaan {
                                    Text(name)
                                        .font(.subheadline)
                                        .foregroundColor(.secondary)
                                }
                            }
                            Spacer()
                            
                            VStack(alignment: .trailing, spacing: 6) {
                                Text(d.rekomendasi)
                                    .font(.system(size: 13, weight: .black))
                                    .foregroundColor(.white)
                                    .padding(.horizontal, 14)
                                    .padding(.vertical, 6)
                                    .background(badgeColor(d.rekomendasi))
                                    .cornerRadius(8)
                                
                                Text(String(format: "%.1f", d.skorTotal))
                                    .font(.system(size: 28, weight: .bold, design: .rounded))
                                    .foregroundColor(.blue)
                            }
                        }
                    }
                    .padding()
                    .background(Color(.secondarySystemGroupedBackground))
                    .cornerRadius(16)
                    .shadow(color: Color.black.opacity(0.03), radius: 6, x: 0, y: 3)
                    
                    if d.dataTerbatas == true {
                        HStack(spacing: 12) {
                            Image(systemName: "exclamationmark.triangle.fill")
                                .font(.title3)
                                .foregroundColor(.orange)
                            VStack(alignment: .leading, spacing: 4) {
                                Text("Data Kurang Lengkap")
                                    .font(.system(size: 14, weight: .bold))
                                    .foregroundColor(.orange)
                                Text(d.catatanData ?? "Data fundamental atau berita pendukung kurang lengkap di database.")
                                    .font(.system(size: 12))
                                    .foregroundColor(.secondary)
                            }
                            Spacer()
                        }
                        .padding()
                        .background(Color.orange.opacity(0.1))
                        .cornerRadius(12)
                        .overlay(
                            RoundedRectangle(cornerRadius: 12)
                                .stroke(Color.orange.opacity(0.3), lineWidth: 1)
                        )
                        .padding(.horizontal, 4)
                    }
                    
                    // 4 Kartu Breakdown Skor
                    Text("Breakdown Skor AI")
                        .font(.headline)
                        .fontWeight(.bold)
                        .padding(.horizontal, 4)
                    
                    VStack(spacing: 12) {
                        ScoreComponentCard(title: "Fundamental", score: d.skorFundamental ?? 0.0, icon: "doc.text.fill", color: .blue)
                        ScoreComponentCard(title: "Sentimen Pasar", score: d.skorSentimen ?? 0.0, icon: "bubble.left.and.bubble.right.fill", color: .orange)
                        ScoreComponentCard(title: "Makroekonomi", score: d.skorMakro ?? 0.0, icon: "globe.asia.australia.fill", color: .teal)
                        ScoreComponentCard(title: "Tingkat Risiko", score: d.skorRisiko ?? 0.0, icon: "exclamationmark.shield.fill", color: .red)
                    }
                    
                    // Kartu Bobot Minggu Ini
                    VStack(alignment: .leading, spacing: 12) {
                        Text("Bobot Adaptif Minggu Ini")
                            .font(.headline)
                            .fontWeight(.bold)
                        
                        VStack(alignment: .leading, spacing: 8) {
                            if let b = d.bobot {
                                BobotRowView(label: "Fundamental", weight: b.fundamental ?? 0.30)
                                BobotRowView(label: "Sentimen", weight: b.sentimen ?? 0.25)
                                BobotRowView(label: "Sektor Industri", weight: b.sektor ?? 0.20)
                                BobotRowView(label: "Makroekonomi", weight: b.makro ?? 0.15)
                                BobotRowView(label: "Risiko Keamanan", weight: b.risiko ?? 0.10)
                            } else {
                                Text("Bobot default: F(30%) · S(25%) · K(20%) · M(15%) · R(10%)")
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                            }
                            
                            Text("💡 Bobot disesuaikan otomatis oleh AI Agent berdasarkan perilisan laporan keuangan baru atau perubahan suku bunga acuan.")
                                .font(.system(size: 11))
                                .foregroundColor(.secondary)
                                .padding(.top, 4)
                        }
                        .padding()
                        .background(Color(.secondarySystemGroupedBackground))
                        .cornerRadius(16)
                        .shadow(color: Color.black.opacity(0.03), radius: 6, x: 0, y: 3)
                    }
                    .padding(.top, 8)
                    
                    // Analisis Tertulis AI
                    VStack(alignment: .leading, spacing: 12) {
                        Text("Analisis Alasan AI")
                            .font(.headline)
                            .fontWeight(.bold)
                        
                        Text(d.alasan ?? "Tidak ada analisis tertulis.")
                            .font(.subheadline)
                            .foregroundColor(Color(.label))
                            .lineSpacing(6)
                    }
                    .padding()
                    .background(Color(.secondarySystemGroupedBackground))
                    .cornerRadius(16)
                    .shadow(color: Color.black.opacity(0.03), radius: 6, x: 0, y: 3)
                    .padding(.top, 8)
                    
                    // Tombol Tanya Chatbot
                    Button(action: {
                        chatbotViewModel.inputText = "Bagaimana analisis fundamental dan sentimen terbaru untuk saham \(d.kodeSaham)?"
                        selectedTab = 1 // Pindah ke tab Chatbot
                        dismiss()      // Tutup halaman detail kembali ke tabview root
                    }) {
                        HStack {
                            Image(systemName: "bubble.left.and.bubble.right.fill")
                            Text("Tanya chatbot tentang saham ini")
                                .fontWeight(.bold)
                        }
                        .foregroundColor(.white)
                        .padding()
                        .frame(maxWidth: .infinity)
                        .background(Color.blue)
                        .cornerRadius(14)
                    }
                    .padding(.top, 16)
                    .padding(.bottom, 24)
                }
            }
            .padding()
        }
        .navigationTitle(kodeSaham)
        .navigationBarTitleDisplayMode(.inline)
        .background(Color(.systemGroupedBackground))
        .task {
            await loadDetail()
        }
    }
    
    private func loadDetail() async {
        isLoading = true
        errorMessage = nil
        do {
            self.detail = try await NetworkManager.shared.fetchRekomendasiDetail(kode: kodeSaham)
        } catch {
            self.errorMessage = error.localizedDescription
        }
        isLoading = false
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

// Subview: Kartu Komponen Skor
struct ScoreComponentCard: View {
    let title: String
    let score: Double
    let icon: String
    let color: Color
    
    var body: some View {
        HStack(spacing: 16) {
            Image(systemName: icon)
                .font(.title2)
                .foregroundColor(color)
                .frame(width: 44, height: 44)
                .background(color.opacity(0.1))
                .cornerRadius(10)
            
            VStack(alignment: .leading, spacing: 6) {
                HStack {
                    Text(title)
                        .font(.system(size: 14, weight: .bold))
                        .foregroundColor(Color(.label))
                    Spacer()
                    Text(String(format: "%.0f/100", score))
                        .font(.system(size: 14, weight: .bold, design: .rounded))
                        .foregroundColor(color)
                }
                
                GeometryReader { geo in
                    ZStack(alignment: .leading) {
                        Capsule()
                            .fill(Color(.systemFill))
                            .frame(height: 6)
                        Capsule()
                            .fill(color)
                            .frame(width: geo.size.width * CGFloat(score / 100.0), height: 6)
                    }
                }
                .frame(height: 6)
            }
        }
        .padding()
        .background(Color(.secondarySystemGroupedBackground))
        .cornerRadius(14)
        .shadow(color: Color.black.opacity(0.02), radius: 4, x: 0, y: 2)
    }
}

// Subview: Baris Bobot
struct BobotRowView: View {
    let label: String
    let weight: Double
    
    var body: some View {
        HStack {
            Text(label)
                .font(.system(size: 13))
                .foregroundColor(.secondary)
            Spacer()
            Text(String(format: "%.0f%%", weight * 100))
                .font(.system(size: 13, weight: .bold))
                .foregroundColor(Color(.label))
        }
    }
}
