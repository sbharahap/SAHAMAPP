import Foundation

struct RekomendasiResponse: Codable {
    let tanggal: String?
    let rekomendasi: [Rekomendasi]
}

struct Rekomendasi: Codable, Identifiable {
    var id: String { kodeSaham }
    let rank: Int
    let kodeSaham: String
    let namaPerusahaan: String?
    let sektor: String?
    let skorTotal: Double
    let skorFundamental: Double?
    let skorSentimen: Double?
    let skorSektor: Double?
    let skorMakro: Double?
    let skorRisiko: Double?
    let rekomendasi: String // "BUY", "HOLD", "SELL"
    let confidence: Double
    let alasan: String?
    
    enum CodingKeys: String, CodingKey {
        case rank
        case kodeSaham = "kode_saham"
        case namaPerusahaan = "nama_perusahaan"
        case sektor
        case skorTotal = "skor_total"
        case skorFundamental = "skor_fundamental"
        case skorSentimen = "skor_sentimen"
        case skorSektor = "skor_sektor"
        case skorMakro = "skor_makro"
        case skorRisiko = "skor_risiko"
        case rekomendasi
        case confidence
        case alasan
    }
}

struct Bobot: Codable {
    let fundamental: Double?
    let sentimen: Double?
    let sektor: Double?
    let makro: Double?
    let risiko: Double?
}

struct RekomendasiDetail: Codable {
    let kodeSaham: String
    let namaPerusahaan: String?
    let sektor: String?
    let subSektor: String?
    let tanggalScoring: String?
    let skorTotal: Double
    let skorFundamental: Double?
    let skorSentimen: Double?
    let skorSektor: Double?
    let skorMakro: Double?
    let skorRisiko: Double?
    let bobot: Bobot?
    let rekomendasi: String
    let confidence: Double
    let alasan: String?
    
    enum CodingKeys: String, CodingKey {
        case kodeSaham = "kode_saham"
        case namaPerusahaan = "nama_perusahaan"
        case sektor
        case subSektor = "sub_sektor"
        case tanggalScoring = "tanggal_scoring"
        case skorTotal = "skor_total"
        case skorFundamental = "skor_fundamental"
        case skorSentimen = "skor_sentimen"
        case skorSektor = "skor_sektor"
        case skorMakro = "skor_makro"
        case skorRisiko = "skor_risiko"
        case bobot
        case rekomendasi
        case confidence
        case alasan
    }
}
