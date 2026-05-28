import SwiftUI

struct ContentView: View {
    @State private var selectedTab = 0
    @State private var chatbotViewModel = ChatbotViewModel()
    @State private var dashboardViewModel = DashboardViewModel()
    @State private var notificationBadgeCount = 0
    
    var body: some View {
        TabView(selection: $selectedTab) {
            DashboardView(
                selectedTab: $selectedTab,
                chatbotViewModel: chatbotViewModel,
                viewModel: dashboardViewModel
            )
            .tabItem {
                Label("Rekomendasi", systemImage: "chart.xyaxis.line")
            }
            .tag(0)
            
            ChatbotView(viewModel: chatbotViewModel)
                .tabItem {
                    Label("Tanya AI", systemImage: "brain.head.profile")
                }
                .tag(1)
            
            NotifikasiView(badgeCount: $notificationBadgeCount)
                .tabItem {
                    Label("Notifikasi", systemImage: "bell.badge.fill")
                }
                .badge(notificationBadgeCount > 0 ? notificationBadgeCount : 0)
                .tag(2)
        }
        .tint(.blue)
    }
}

#Preview {
    ContentView()
}
