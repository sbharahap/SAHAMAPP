import Foundation

struct Saham: Codable, Identifiable, Hashable {
    var id: String { kode }
    let kode: String
    let namaPerusahaan: String
    let sektor: String
    let subSektor: String?
    
    enum CodingKeys: String, CodingKey {
        case kode
        case namaPerusahaan = "nama_perusahaan"
        case sektor
        case subSektor = "sub_sektor"
    }
}
