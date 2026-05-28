import Foundation

struct AlertModel: Codable, Identifiable, Hashable {
    let id: Int
    let kodeSaham: String
    let tanggal: String
    let pesan: String
    let delta: Double
    let dikirim: Bool
    
    enum CodingKeys: String, CodingKey {
        case id
        case kodeSaham = "kode_saham"
        case tanggal
        case pesan
        case delta
        case dikirim
    }
}
