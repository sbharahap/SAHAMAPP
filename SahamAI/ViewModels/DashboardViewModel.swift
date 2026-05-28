import Foundation
import Observation

@Observable
class DashboardViewModel {
    var rekomendasi: [Rekomendasi] = []
    var makro: Makro? = nil
    var isLoading: Bool = false
    var errorMessage: String? = nil
    
    func loadRekomendasi() async {
        isLoading = true
        errorMessage = nil
        do {
            self.rekomendasi = try await NetworkManager.shared.fetchRekomendasiMingguan()
        } catch {
            self.errorMessage = error.localizedDescription
        }
        isLoading = false
    }
    
    func loadMakro() async {
        do {
            self.makro = try await NetworkManager.shared.fetchMakroTerbaru()
        } catch {
            self.errorMessage = error.localizedDescription
        }
    }
    
    func loadDashboardData() async {
        isLoading = true
        errorMessage = nil
        
        do {
            // Parallel fetching
            async let fetchRec = NetworkManager.shared.fetchRekomendasiMingguan()
            async let fetchMkr = NetworkManager.shared.fetchMakroTerbaru()
            
            let (recList, makroRes) = try await (fetchRec, fetchMkr)
            self.rekomendasi = recList
            self.makro = makroRes
        } catch {
            self.errorMessage = error.localizedDescription
        }
        
        isLoading = false
    }
}
