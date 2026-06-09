//
//  ChatbotViewModel.swift
//  SahamIndo
//

import SwiftUI
import Combine

@MainActor
final class ChatbotViewModel: ObservableObject {
    @Published var messages: [ChatMessage] = []
    @Published var inputText: String = ""
    @Published var isLoading: Bool = false
    @Published var errorMessage: String? = nil

    init() {
        // Welcome message
        messages.append(ChatMessage(
            role: .assistant,
            content: "Halo! Saya adalah SahamIndo AI Assistant. Tanyakan apa saja mengenai rekomendasi emiten saham IDX atau analisis makroekonomi."
        ))
    }

    func kirimPesan(_ teks: String) async {
        let trimmed = teks.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }

        let userMessage = ChatMessage(role: .user, content: trimmed)
        messages.append(userMessage)

        isLoading = true
        errorMessage = nil

        let historyLimit = 10
        let recentMessages = messages.suffix(historyLimit)
        let riwayat = recentMessages.compactMap { msg -> ChatHistoryItem? in
            if msg.id == userMessage.id { return nil }
            return ChatHistoryItem(role: msg.role.rawValue, content: msg.content)
        }

        let emptyAssistantMessage = ChatMessage(role: .assistant, content: "")
        messages.append(emptyAssistantMessage)

        guard let index = messages.firstIndex(where: { $0.id == emptyAssistantMessage.id }) else {
            isLoading = false
            return
        }

        do {
            let stream = try await APIClient.sendChatMessageStream(
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
                content: "Halo! Saya adalah SahamIndo AI Assistant. Tanyakan apa saja mengenai rekomendasi emiten saham IDX atau analisis makroekonomi."
            )
        ]
        inputText = ""
    }
}
