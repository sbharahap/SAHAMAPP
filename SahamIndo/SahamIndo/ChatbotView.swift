//
//  ChatbotView.swift
//  SahamIndo
//

import SwiftUI
import Combine

// MARK: - Markdown Parsing Helpers

private enum ContentSegment {
    case text(String)
    case table(headers: [String], rows: [[String]])
}

private func parseMarkdownSegments(_ content: String) -> [ContentSegment] {
    let lines = content.components(separatedBy: "\n")
    var segments: [ContentSegment] = []
    var textLines: [String] = []
    var i = 0

    while i < lines.count {
        let trimmedLine = lines[i].trimmingCharacters(in: .whitespaces)
        let pipeCount = trimmedLine.filter { $0 == "|" }.count

        if trimmedLine.hasPrefix("|") && pipeCount >= 2 {
            if !textLines.isEmpty {
                segments.append(.text(textLines.joined(separator: "\n")))
                textLines = []
            }
            var tableLines: [String] = []
            while i < lines.count && lines[i].trimmingCharacters(in: .whitespaces).hasPrefix("|") {
                tableLines.append(lines[i])
                i += 1
            }
            if let parsed = parseMarkdownTable(tableLines) {
                segments.append(.table(headers: parsed.headers, rows: parsed.rows))
            } else {
                segments.append(.text(tableLines.joined(separator: "\n")))
            }
        } else {
            textLines.append(lines[i])
            i += 1
        }
    }

    if !textLines.isEmpty {
        segments.append(.text(textLines.joined(separator: "\n")))
    }
    return segments
}

private func parseMarkdownTable(_ lines: [String]) -> (headers: [String], rows: [[String]])? {
    guard lines.count >= 2 else { return nil }

    // Second line must be a separator row (only |, -, :, space)
    let separatorAllowed = CharacterSet(charactersIn: "|-: ")
    let isSeparator = lines[1].trimmingCharacters(in: .whitespaces).unicodeScalars
        .allSatisfy { separatorAllowed.contains($0) } && lines[1].contains("-")
    guard isSeparator else { return nil }

    func parseCells(from line: String) -> [String] {
        var s = line.trimmingCharacters(in: .whitespaces)
        if s.hasPrefix("|") { s = String(s.dropFirst()) }
        if s.hasSuffix("|") { s = String(s.dropLast()) }
        return s.components(separatedBy: "|").map { $0.trimmingCharacters(in: .whitespaces) }
    }

    let headers = parseCells(from: lines[0])
    guard !headers.isEmpty else { return nil }
    let rows = lines.dropFirst(2).map { parseCells(from: $0) }
    return (headers: headers, rows: rows)
}

// MARK: - ChatbotView

struct ChatbotView: View {
    @EnvironmentObject var viewModel: ChatbotViewModel
    @State private var hasScrolledToCurrentResponse = false

    private let accentColor = Color(hex: "FFA500")
    private let bgColor = Color.appBackground
    private let cardColor = Color.appCardBackground

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                ScrollViewReader { proxy in
                    ScrollView {
                        LazyVStack(spacing: 16) {
                            ForEach(viewModel.messages) { msg in
                                if msg.role != .assistant || !msg.content.isEmpty {
                                    ChatBubbleView(message: msg)
                                        .id(msg.id)
                                }
                            }

                            if viewModel.isLoading {
                                HStack {
                                    VStack(alignment: .leading, spacing: 4) {
                                        HStack(spacing: 8) {
                                            Image(systemName: "sparkles")
                                                .foregroundColor(accentColor)
                                                .font(.caption)
                                            Text("Saham.AI Agent")
                                                .font(.system(size: 10, weight: .bold))
                                                .foregroundColor(.secondary)
                                        }
                                        TypingIndicatorView()
                                    }
                                    Spacer()
                                }
                                .id("loadingIndicator")
                                .padding(.horizontal, 4)
                            }
                        }
                        .padding()
                    }
                    .background(bgColor)
                    .onChange(of: viewModel.isLoading) { _, isLoading in
                        if isLoading {
                            hasScrolledToCurrentResponse = false
                            withAnimation(.easeOut(duration: 0.25)) {
                                proxy.scrollTo("loadingIndicator", anchor: .bottom)
                            }
                        }
                    }
                    .onChange(of: viewModel.messages) { oldMessages, newMessages in
                        // Scroll to user message when a new one is added
                        if newMessages.count > oldMessages.count,
                           let lastMsg = newMessages.last,
                           lastMsg.role == .user {
                            withAnimation(.easeOut(duration: 0.25)) {
                                proxy.scrollTo(lastMsg.id, anchor: .top)
                            }
                            return
                        }
                        // Scroll to the TOP of the AI bubble only once (on first content chunk)
                        if !hasScrolledToCurrentResponse,
                           viewModel.isLoading,
                           let lastAssistant = newMessages.last(where: { $0.role == .assistant }),
                           !lastAssistant.content.isEmpty {
                            hasScrolledToCurrentResponse = true
                            withAnimation(.easeOut(duration: 0.25)) {
                                proxy.scrollTo(lastAssistant.id, anchor: .top)
                            }
                        }
                    }
                }

                Divider()
                    .background(Color.primary.opacity(0.1))

                // Quick Suggestion Chips
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 10) {
                        SuggestionChip(text: "Kenapa BBCA direkomendasikan?") {
                            kirimPertanyaan("Kenapa BBCA direkomendasikan?")
                        }
                        SuggestionChip(text: "Bandingkan BBCA vs BMRI") {
                            kirimPertanyaan("Bandingkan BBCA vs BMRI")
                        }
                        SuggestionChip(text: "Sektor bank masih menarik?") {
                            kirimPertanyaan("Apakah sektor perbankan (Banks) masih menarik minggu ini?")
                        }
                        SuggestionChip(text: "Saham apa yang harus dihindari?") {
                            kirimPertanyaan("Saham apa saja yang berisiko tinggi atau sebaiknya dihindari saat ini?")
                        }
                    }
                    .padding(.horizontal)
                    .padding(.vertical, 10)
                }
                .background(bgColor)

                // Input Bar
                HStack(spacing: 12) {
                    TextField("Tanyakan sesuatu (misal: Sentimen BBRI)...", text: $viewModel.inputText)
                        .padding(14)
                        .background(cardColor)
                        .foregroundColor(.primary)
                        .cornerRadius(12)
                        .overlay(
                            RoundedRectangle(cornerRadius: 12)
                                .strokeBorder(accentColor.opacity(0.25), lineWidth: 0.5)
                        )
                        .disabled(viewModel.isLoading)

                    Button(action: {
                        let query = viewModel.inputText
                        viewModel.inputText = ""
                        kirimPertanyaan(query)
                    }) {
                        Image(systemName: "paperplane.fill")
                            .foregroundColor(.white)
                            .padding(12)
                            .background(viewModel.inputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? Color.gray : accentColor)
                            .clipShape(Circle())
                    }
                    .disabled(viewModel.inputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || viewModel.isLoading)
                }
                .padding(.horizontal)
                .padding(.bottom, 12)
                .padding(.top, 6)
                .background(bgColor)
            }
            .navigationTitle("Chat Agent")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button(action: {
                        viewModel.clearChat()
                    }) {
                        Image(systemName: "trash")
                            .foregroundColor(.red)
                    }
                    .disabled(viewModel.isLoading)
                }
            }
            .background(bgColor)
        }
    }

    private func kirimPertanyaan(_ teks: String) {
        Task {
            await viewModel.kirimPesan(teks)
        }
    }
}

// MARK: - MarkdownContentView

struct MarkdownContentView: View {
    let content: String

    private var segments: [ContentSegment] {
        parseMarkdownSegments(content)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            ForEach(segments.indices, id: \.self) { i in
                segmentView(segments[i])
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    @ViewBuilder
    private func segmentView(_ segment: ContentSegment) -> some View {
        switch segment {
        case .text(let text):
            textSegmentView(text)
        case .table(let headers, let rows):
            MarkdownTableView(headers: headers, rows: rows)
        }
    }

    @ViewBuilder
    private func textSegmentView(_ text: String) -> some View {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        if !trimmed.isEmpty {
            Text(LocalizedStringKey(trimmed))
                .font(.system(size: 14))
                .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}

// MARK: - MarkdownTableView

struct MarkdownTableView: View {
    let headers: [String]
    let rows: [[String]]

    var body: some View {
        VStack(spacing: 0) {
            // Header row
            HStack(spacing: 0) {
                ForEach(headers.indices, id: \.self) { i in
                    Text(headers[i])
                        .font(.system(size: 11, weight: .semibold))
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 6)
                    if i < headers.count - 1 {
                        Rectangle()
                            .fill(Color.primary.opacity(0.15))
                            .frame(width: 0.5)
                    }
                }
            }
            .background(Color.primary.opacity(0.1))

            Rectangle()
                .fill(Color.primary.opacity(0.2))
                .frame(height: 0.5)

            // Data rows
            ForEach(rows.indices, id: \.self) { rowIdx in
                HStack(spacing: 0) {
                    ForEach(headers.indices, id: \.self) { colIdx in
                        Text(colIdx < rows[rowIdx].count ? rows[rowIdx][colIdx] : "")
                            .font(.system(size: 11))
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding(.horizontal, 8)
                            .padding(.vertical, 5)
                        if colIdx < headers.count - 1 {
                            Rectangle()
                                .fill(Color.primary.opacity(0.12))
                                .frame(width: 0.5)
                        }
                    }
                }
                .background(rowIdx % 2 == 1 ? Color.primary.opacity(0.04) : Color.clear)

                if rowIdx < rows.count - 1 {
                    Rectangle()
                        .fill(Color.primary.opacity(0.1))
                        .frame(height: 0.5)
                }
            }
        }
        .overlay(
            RoundedRectangle(cornerRadius: 6)
                .strokeBorder(Color.primary.opacity(0.15), lineWidth: 0.5)
        )
        .clipShape(RoundedRectangle(cornerRadius: 6))
    }
}

// MARK: - SuggestionChip

struct SuggestionChip: View {
    let text: String
    let action: () -> Void

    private let accentColor = Color(hex: "FFA500")
    private let cardColor = Color.appCardBackground

    var body: some View {
        Button(action: action) {
            Text(text)
                .font(.system(size: 12, weight: .medium))
                .foregroundColor(accentColor)
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
                .background(cardColor)
                .cornerRadius(16)
                .overlay(
                    RoundedRectangle(cornerRadius: 16)
                        .stroke(accentColor.opacity(0.35), lineWidth: 0.5)
                )
        }
    }
}

// MARK: - TypingIndicatorView

struct TypingIndicatorView: View {
    @State private var animStep = 0
    let timer = Timer.publish(every: 0.4, on: .main, in: .common).autoconnect()

    private let cardColor = Color.appCardBackground

    var body: some View {
        HStack(spacing: 5) {
            Circle()
                .frame(width: 6, height: 6)
                .foregroundColor(.secondary)
                .opacity(animStep == 0 ? 1.0 : 0.4)
            Circle()
                .frame(width: 6, height: 6)
                .foregroundColor(.secondary)
                .opacity(animStep == 1 ? 1.0 : 0.4)
            Circle()
                .frame(width: 6, height: 6)
                .foregroundColor(.secondary)
                .opacity(animStep == 2 ? 1.0 : 0.4)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background(cardColor)
        .cornerRadius(12)
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .strokeBorder(Color.primary.opacity(0.08), lineWidth: 0.5)
        )
        .onReceive(timer) { _ in
            withAnimation(.easeInOut(duration: 0.25)) {
                animStep = (animStep + 1) % 3
            }
        }
    }
}

// MARK: - ChatBubbleView

struct ChatBubbleView: View {
    let message: ChatMessage

    private let accentColor = Color(hex: "FFA500")
    private let cardColor = Color.appCardBackground

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            if message.role == .assistant {
                Image(systemName: "sparkles")
                    .foregroundColor(accentColor)
                    .font(.system(size: 14))
                    .frame(width: 32, height: 32)
                    .background(accentColor.opacity(0.12))
                    .clipShape(Circle())
                    .overlay(Circle().strokeBorder(accentColor.opacity(0.35), lineWidth: 0.5))
            } else {
                Spacer()
            }

            VStack(alignment: message.role == .user ? .trailing : .leading, spacing: 4) {
                if message.role == .assistant {
                    Text("Saham.AI Agent")
                        .font(.system(size: 10, weight: .bold))
                        .foregroundColor(.secondary)
                }

                // Message bubble content
                Group {
                    if message.role == .assistant {
                        MarkdownContentView(content: message.content)
                    } else {
                        Text(LocalizedStringKey(message.content))
                            .font(.system(size: 14))
                    }
                }
                .padding(12)
                .background(
                    Group {
                        if message.role == .user {
                            LinearGradient(
                                colors: [Color(hex: "FFA500"), Color(hex: "FF7F00")],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            )
                        } else {
                            cardColor
                        }
                    }
                )
                .foregroundColor(message.role == .user ? .white : .primary)
                .cornerRadius(16)
                .overlay(
                    Group {
                        if message.role == .assistant {
                            RoundedRectangle(cornerRadius: 16)
                                .strokeBorder(Color(hex: "818CF8").opacity(0.18), lineWidth: 0.5)
                        }
                    }
                )

                // Disclaimer always shown for every AI response
                if message.role == .assistant {
                    HStack(spacing: 4) {
                        Image(systemName: "exclamationmark.triangle.fill")
                            .font(.system(size: 9))
                            .foregroundColor(.orange.opacity(0.7))
                        Text("Bukan saran investasi. Lakukan riset mandiri sebelum mengambil keputusan.")
                            .font(.system(size: 9))
                            .foregroundColor(.secondary)
                            .multilineTextAlignment(.leading)
                    }
                    .padding(.horizontal, 4)
                    .padding(.top, 1)
                }

                Text(formatTime(message.timestamp))
                    .font(.system(size: 8))
                    .foregroundColor(.secondary)
                    .padding(.horizontal, 4)
            }

            if message.role == .user {
                Image(systemName: "person.crop.circle.fill")
                    .foregroundColor(.gray)
                    .font(.system(size: 24))
                    .frame(width: 32, height: 32)
            } else {
                Spacer()
            }
        }
    }

    private func formatTime(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "HH:mm"
        return formatter.string(from: date)
    }
}
