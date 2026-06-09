//
//  ChatModels.swift
//  SahamIndo
//

import Foundation

enum MessageRole: String, Codable {
    case user
    case assistant
}

struct ChatMessage: Identifiable, Equatable {
    let id = UUID()
    let role: MessageRole
    var content: String
    let timestamp: Date = Date()
}

struct ChatPayload: Codable {
    let pertanyaan: String
    let riwayat: [ChatHistoryItem]
}

struct ChatHistoryItem: Codable {
    let role: String // "user" or "assistant"
    let content: String
}
