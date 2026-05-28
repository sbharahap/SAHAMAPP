import Foundation

enum NetworkError: Error, LocalizedError {
    case invalidURL
    case noData
    case decodingError
    case serverError(String)
    case custom(Error)
    
    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "URL tidak valid. Silakan hubungi pengembang."
        case .noData:
            return "Tidak ada data yang diterima dari server."
        case .decodingError:
            return "Gagal memproses data dari server."
        case .serverError(let message):
            return "Server Error: \(message)"
        case .custom(let error):
            return error.localizedDescription
        }
    }
}

class NetworkManager {
    static let shared = NetworkManager()
    
    // Ganti IP di bawah ini dengan IP aktual Mac Anda
    private let baseURL = "http://10.67.49.69:8080"
    
    private init() {}
    
    /// Mengambil daftar semua kode emiten saham
    func fetchSahamList() async throws -> [Saham] {
        guard let url = URL(string: "\(baseURL)/saham/list") else {
            throw NetworkError.invalidURL
        }
        
        let (data, response) = try await URLSession.shared.data(from: url)
        
        guard let httpResponse = response as? HTTPURLResponse, (200...299).contains(httpResponse.statusCode) else {
            throw NetworkError.serverError("Gagal mengambil daftar saham")
        }
        
        do {
            return try JSONDecoder().decode([Saham].self, from: data)
        } catch {
            throw NetworkError.decodingError
        }
    }
    
    /// Mengambil top 10 rekomendasi saham mingguan
    func fetchRekomendasiMingguan() async throws -> [Rekomendasi] {
        guard let url = URL(string: "\(baseURL)/rekomendasi/mingguan") else {
            throw NetworkError.invalidURL
        }
        
        let (data, response) = try await URLSession.shared.data(from: url)
        
        guard let httpResponse = response as? HTTPURLResponse, (200...299).contains(httpResponse.statusCode) else {
            throw NetworkError.serverError("Gagal mengambil data rekomendasi mingguan")
        }
        
        do {
            let res = try JSONDecoder().decode(RekomendasiResponse.self, from: data)
            return res.rekomendasi
        } catch {
            throw NetworkError.decodingError
        }
    }
    
    /// Mengambil detail rekomendasi untuk satu saham
    func fetchRekomendasiDetail(kode: String) async throws -> RekomendasiDetail {
        guard let url = URL(string: "\(baseURL)/rekomendasi/saham/\(kode)") else {
            throw NetworkError.invalidURL
        }
        
        let (data, response) = try await URLSession.shared.data(from: url)
        
        guard let httpResponse = response as? HTTPURLResponse, (200...299).contains(httpResponse.statusCode) else {
            throw NetworkError.serverError("Gagal mengambil detail rekomendasi saham \(kode)")
        }
        
        do {
            return try JSONDecoder().decode(RekomendasiDetail.self, from: data)
        } catch {
            throw NetworkError.decodingError
        }
    }
    
    /// Mengambil snapshot indikator makroekonomi terkini
    func fetchMakroTerbaru() async throws -> Makro {
        guard let url = URL(string: "\(baseURL)/makro/terbaru") else {
            throw NetworkError.invalidURL
        }
        
        let (data, response) = try await URLSession.shared.data(from: url)
        
        guard let httpResponse = response as? HTTPURLResponse, (200...299).contains(httpResponse.statusCode) else {
            throw NetworkError.serverError("Gagal mengambil data makroekonomi")
        }
        
        // Coba decode format flat: {"bi_rate": 6.25, "usd_idr": 15820, ...}
        if let flatMakro = try? JSONDecoder().decode(Makro.self, from: data) {
            return flatMakro
        }
        
        // Coba decode format nested: {"tanggal_fetch": "...", "indikator": {"bi_rate": {"nilai": 6.25, ...}, ...}}
        do {
            let nestedResponse = try JSONDecoder().decode(MakroResponse.self, from: data)
            let bi = nestedResponse.biRate?.nilai ?? 0.0
            let usd = nestedResponse.usdIdr?.nilai ?? 0.0
            let inf = nestedResponse.inflasi?.nilai ?? 0.0
            let ihsgVal = nestedResponse.ihsg?.nilai ?? 0.0
            
            return Makro(biRate: bi, usdIdr: usd, inflasi: inf, ihsg: ihsgVal)
        } catch {
            throw NetworkError.decodingError
        }
    }
    
    /// Mengambil riwayat alert terbaru untuk notifikasi
    func fetchAlerts() async throws -> [AlertModel] {
        guard let url = URL(string: "\(baseURL)/alerts") else {
            throw NetworkError.invalidURL
        }
        
        let (data, response) = try await URLSession.shared.data(from: url)
        
        guard let httpResponse = response as? HTTPURLResponse, (200...299).contains(httpResponse.statusCode) else {
            throw NetworkError.serverError("Gagal mengambil riwayat alert")
        }
        
        do {
            return try JSONDecoder().decode([AlertModel].self, from: data)
        } catch {
            throw NetworkError.decodingError
        }
    }
    
    /// Mengirim pertanyaan ke RAG Chatbot dan menerima streaming jawaban
    func sendChatMessageStream(pertanyaan: String, riwayat: [ChatHistoryItem]) async throws -> AsyncThrowingStream<String, Error> {
        guard let url = URL(string: "\(baseURL)/chat") else {
            throw NetworkError.invalidURL
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let payload = ChatPayload(pertanyaan: pertanyaan, riwayat: riwayat)
        request.httpBody = try JSONEncoder().encode(payload)
        
        let (bytes, response) = try await URLSession.shared.bytes(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse, (200...299).contains(httpResponse.statusCode) else {
            throw NetworkError.serverError("Koneksi chatbot ke server gagal")
        }
        
        return AsyncThrowingStream { continuation in
            Task {
                do {
                    var buffer = Data()
                    var iterator = bytes.makeAsyncIterator()
                    
                    while let byte = try await iterator.next() {
                        buffer.append(byte)
                        // Coba decode sebagai string UTF-8. 
                        // Jika gagal, mungkin byte-nya merupakan bagian dari karakter multibyte
                        // yang belum lengkap (seperti emoji). Teruskan append.
                        if let decodedString = String(data: buffer, encoding: .utf8) {
                            continuation.yield(decodedString)
                            buffer.removeAll()
                        }
                    }
                    continuation.finish()
                } catch {
                    continuation.finish(throwing: error)
                }
            }
        }
    }
}
