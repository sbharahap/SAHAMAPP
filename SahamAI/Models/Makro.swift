import Foundation

struct Makro: Codable, Hashable {
    let biRate: Double
    let usdIdr: Double
    let inflasi: Double
    let ihsg: Double
    
    enum CodingKeys: String, CodingKey {
        case biRate = "bi_rate"
        case usdIdr = "usd_idr"
        case inflasi = "inflasi"
        case ihsg = "ihsg"
    }
}

struct IndikatorDetail: Codable, Hashable {
    let nilai: Double
    let satuan: String?
    let tanggal: String?
    let sumber: String?
}

struct MakroResponse: Codable, Hashable {
    let tanggalFetch: String?
    let indikator: [String: IndikatorDetail?]
    
    enum CodingKeys: String, CodingKey {
        case tanggalFetch = "tanggal_fetch"
        case indikator
    }
    
    var biRate: IndikatorDetail? {
        indikator["bi_rate"] ?? nil
    }
    
    var usdIdr: IndikatorDetail? {
        indikator["kurs_usd_idr"] ?? nil
    }
    
    var inflasi: IndikatorDetail? {
        indikator["inflasi_yoy"] ?? nil
    }
    
    var ihsg: IndikatorDetail? {
        indikator["ihsg"] ?? nil
    }
}
