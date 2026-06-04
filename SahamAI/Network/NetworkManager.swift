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
    
    // URL yang sudah terverifikasi sukses terhubung
    private var verifiedBaseURL: String? = nil
    
    private init() {}
    
    /// Mendapatkan Base URL secara dinamis dengan mencoba kandidat secara paralel.
    /// Urutan prioritas:
    ///   1. mDNS/Bonjour hostname → bekerja di jaringan apapun tanpa perlu tahu IP
    ///   2. IP jaringan rumah (192.168.100.21)
    ///   3. IP jaringan kantor (10.67.49.69) — static, tidak berubah (lihat pengaturan di bawah)
    ///   4. localhost → untuk iOS Simulator
    private func getBaseURL() async -> String {
        if let verified = verifiedBaseURL {
            return verified
        }
        
        let candidates = [
            "http://MacBook-Pro-Satria.local:8080", // mDNS Bonjour — otomatis di jaringan apapun ✅
            "http://192.168.100.21:8080",            // Static IP rumah
            "http://10.67.49.69:8080",               // Static IP kantor (di-set manual di System Settings)
            "http://localhost:8080"                  // iOS Simulator
        ]
        
        let workingURL = await withTaskGroup(of: String?.self) { group -> String in
            for candidate in candidates {
                group.addTask {
                    // Menggunakan endpoint /api/status untuk verifikasi koneksi backend
                    guard let url = URL(string: "\(candidate)/api/status") else { return nil }
                    var request = URLRequest(url: url)
                    request.timeoutInterval = 2.0 // Sedikit lebih lama untuk mDNS resolve
                    request.httpMethod = "GET"
                    
                    do {
                        let (_, response) = try await URLSession.shared.data(for: request)
                        if let httpResponse = response as? HTTPURLResponse, (200...299).contains(httpResponse.statusCode) {
                            return candidate
                        }
                    } catch {
                        // Gagal terhubung ke kandidat ini
                    }
                    return nil
                }
            }
            
            // Ambil kandidat pertama yang merespons sukses
            for await result in group {
                if let url = result {
                    group.cancelAll() // Batalkan pengecekan kandidat lain
                    return url
                }
            }
            
            // Fallback default jika semuanya tidak merespons
            return candidates[0]
        }
        
        self.verifiedBaseURL = workingURL
        print("🔌 NetworkManager: Menggunakan backend \(workingURL)")
        return workingURL
    }
    
    /// Reset URL yang tersimpan — dipanggil saat deteksi pergantian jaringan
    func resetVerifiedURL() {
        verifiedBaseURL = nil
        print("🔄 NetworkManager: URL di-reset, akan re-detect koneksi.")
    }

    
    /// Mengambil daftar semua kode emiten saham
    func fetchSahamList() async throws -> [Saham] {
        let base = await getBaseURL()
        guard let url = URL(string: "\(base)/saham/list") else {
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
        let base = await getBaseURL()
        guard let url = URL(string: "\(base)/rekomendasi/mingguan") else {
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
        let base = await getBaseURL()
        guard let url = URL(string: "\(base)/rekomendasi/saham/\(kode)") else {
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
        let base = await getBaseURL()
        guard let url = URL(string: "\(base)/makro/terbaru") else {
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
        let base = await getBaseURL()
        guard let url = URL(string: "\(base)/alerts") else {
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
        let base = await getBaseURL()
        guard let url = URL(string: "\(base)/chat") else {
            throw NetworkError.invalidURL
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.timeoutInterval = 240.0 // Meningkatkan timeout ke 4 menit untuk LLM lokal
        
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
