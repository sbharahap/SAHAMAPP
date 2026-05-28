import SwiftUI
import Combine

struct ChatbotView: View {
    @Bindable var viewModel: ChatbotViewModel
    
    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                // Area Chat Bubbles
                ScrollViewReader { proxy in
                    ScrollView {
                        LazyVStack(spacing: 12) {
                            ForEach(viewModel.messages) { msg in
                                ChatBubbleView(message: msg)
                                    .id(msg.id)
                            }
                            
                            // Tampilkan animasi 3 titik jika sedang loading
                            if viewModel.isLoading {
                                HStack {
                                    VStack(alignment: .leading, spacing: 4) {
                                        HStack(spacing: 8) {
                                            Image(systemName: "brain.head.profile")
                                                .foregroundColor(.blue)
                                                .font(.caption)
                                            Text("SahamAI")
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
                    // Auto-scroll ke bawah saat jumlah pesan bertambah atau saat loading
                    .onChange(of: viewModel.messages) {
                        scrollToBottom(proxy: proxy)
                    }
                    .onChange(of: viewModel.isLoading) {
                        scrollToBottom(proxy: proxy)
                    }
                }
                
                Divider()
                
                // Quick Suggestion Chips (di atas input bar)
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
                    .padding(.vertical, 8)
                }
                .background(Color(.systemBackground))
                
                // Input Bar di bagian bawah
                HStack(spacing: 12) {
                    TextField("Tanyakan sesuatu (misal: Sentimen BBRI)...", text: $viewModel.inputText)
                        .padding(12)
                        .background(Color(.secondarySystemBackground))
                        .cornerRadius(12)
                        .disabled(viewModel.isLoading)
                    
                    Button(action: {
                        let query = viewModel.inputText
                        viewModel.inputText = ""
                        kirimPertanyaan(query)
                    }) {
                        Image(systemName: "paperplane.fill")
                            .foregroundColor(.white)
                            .padding(12)
                            .background(viewModel.inputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? Color.gray : Color.blue)
                            .clipShape(Circle())
                    }
                    .disabled(viewModel.inputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || viewModel.isLoading)
                }
                .padding(.horizontal)
                .padding(.bottom, 12)
                .padding(.top, 4)
                .background(Color(.systemBackground))
            }
            .navigationTitle("Tanya AI")
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
        }
    }
    
    private func kirimPertanyaan(_ teks: String) {
        Task {
            await viewModel.kirimPesan(teks)
        }
    }
    
    private func scrollToBottom(proxy: ScrollViewProxy) {
        withAnimation(.easeOut(duration: 0.25)) {
            if viewModel.isLoading {
                proxy.scrollTo("loadingIndicator", anchor: .bottom)
            } else if let lastId = viewModel.messages.last?.id {
                proxy.scrollTo(lastId, anchor: .bottom)
            }
        }
    }
}

// Subview: Suggestion Chip
struct SuggestionChip: View {
    let text: String
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            Text(text)
                .font(.system(size: 12, weight: .medium))
                .foregroundColor(.blue)
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
                .background(Color.blue.opacity(0.08))
                .cornerRadius(16)
                .overlay(
                    RoundedRectangle(cornerRadius: 16)
                        .stroke(Color.blue.opacity(0.15), lineWidth: 1)
                )
        }
    }
}

// Subview: Typing/Loading Indicator 3 titik
struct TypingIndicatorView: View {
    @State private var animStep = 0
    let timer = Timer.publish(every: 0.4, on: .main, in: .common).autoconnect()
    
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
        .background(Color(.secondarySystemBackground))
        .cornerRadius(12)
        .onReceive(timer) { _ in
            withAnimation(.easeInOut(duration: 0.25)) {
                animStep = (animStep + 1) % 3
            }
        }
    }
}

// Subview: Bubble Chat (ChatBubbleView)
struct ChatBubbleView: View {
    let message: ChatMessage
    
    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            if message.role == .assistant {
                // Avatar Ikon AI
                Image(systemName: "brain.head.profile")
                    .foregroundColor(.blue)
                    .font(.system(size: 16))
                    .frame(width: 32, height: 32)
                    .background(Color.blue.opacity(0.1))
                    .clipShape(Circle())
            } else {
                Spacer()
            }
            
            VStack(alignment: message.role == .user ? .trailing : .leading, spacing: 4) {
                if message.role == .assistant {
                    Text("SahamAI")
                        .font(.system(size: 10, weight: .bold))
                        .foregroundColor(.secondary)
                }
                
                Text(message.content)
                    .font(.system(size: 14))
                    .padding(12)
                    .background(message.role == .user ? Color.blue : Color(.secondarySystemBackground))
                    .foregroundColor(message.role == .user ? .white : Color(.label))
                    .cornerRadius(16)
                
                Text(formatTime(message.timestamp))
                    .font(.system(size: 8))
                    .foregroundColor(.secondary)
                    .padding(.horizontal, 4)
            }
            
            if message.role == .user {
                // Avatar Ikon User
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
