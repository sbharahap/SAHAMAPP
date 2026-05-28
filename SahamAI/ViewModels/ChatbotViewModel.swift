import Foundation
import Observation

@Observable
class ChatbotViewModel {
    var messages: [ChatMessage] = []
    var inputText: String = ""
    var isLoading: Bool = false
    var errorMessage: String? = nil
    
    init() {
        // Pesan sambutan default dari asisten
        messages.append(ChatMessage(
            role: .assistant,
            content: "Halo! Saya adalah SahamAI Assistant. Tanyakan apa saja mengenai rekomendasi emiten saham IDX atau analisis makroekonomi."
        ))
    }
    
    func kirimPesan(_ teks: String) async {
        let trimmed = teks.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        
        // Tampilkan pesan user ke layar
        let userMessage = ChatMessage(role: .user, content: trimmed)
        messages.append(userMessage)
        
        isLoading = true
        errorMessage = nil
        
        // Siapkan riwayat chat untuk dikirim (batasi 10 pesan terakhir)
        let historyLimit = 10
        let recentMessages = messages.suffix(historyLimit)
        let riwayat = recentMessages.compactMap { msg -> ChatHistoryItem? in
            // Skip pesan user yang baru saja dikirim agar tidak duplikat di riwayat
            if msg.id == userMessage.id { return nil }
            return ChatHistoryItem(role: msg.role.rawValue, content: msg.content)
        }
        
        // Tambahkan bubble kosong asisten untuk menerima streaming jawaban
        let emptyAssistantMessage = ChatMessage(role: .assistant, content: "")
        messages.append(emptyAssistantMessage)
        
        guard let index = messages.firstIndex(where: { $0.id == emptyAssistantMessage.id }) else {
            isLoading = false
            return
        }
        
        do {
            let stream = try await NetworkManager.shared.sendChatMessageStream(
                pertanyaan: trimmed,
                riwayat: riwayat
            )
            
            for try await chunk in stream {
                messages[index].content += chunk
            }
        } catch {
            self.errorMessage = error.localizedDescription
            
            if messages[index].content.isEmpty {
                messages.remove(at: index)
            }
            
            messages.append(ChatMessage(
                role: .assistant,
                content: "⚠️ Gagal terhubung ke AI server lokal. Pastikan backend Anda aktif.\nError: \(error.localizedDescription)"
            ))
        }
        
        isLoading = false
    }
    
    func clearChat() {
        messages = [
            ChatMessage(
                role: .assistant,
                content: "Halo! Saya adalah SahamAI Assistant. Tanyakan apa saja mengenai rekomendasi emiten saham IDX atau analisis makroekonomi."
            )
        ]
        inputText = ""
    }
}
