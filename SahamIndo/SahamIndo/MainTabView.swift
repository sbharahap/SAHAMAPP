//
//  MainTabView.swift
//  SahamIndo
//

import SwiftUI

struct MainTabView: View {

    @EnvironmentObject private var router: Router

    var body: some View {
        TabView(selection: $router.selectedTab) {

            Tab("Home",
                systemImage: router.selectedTab == "home" ? "chart.bar.fill" : "chart.bar",
                value: "home") {
                HomeNavigationView()
            }

            Tab("Portfolio",
                systemImage: "briefcase.fill",
                value: "portfolio") {
                PortfolioNavigationView()
            }

            Tab("Chat Agent",
                systemImage: "sparkles.square.filled.on.square",
                value: "assets") {
                ChatbotView()
            }
        }
        .tint(Color(hex: "FFA500"))
    }
}

// MARK: - Navigation Wrappers

struct HomeNavigationView: View {

    @EnvironmentObject private var router: Router

    var body: some View {
        NavigationStack(path: $router.path) {
            HomeView()
                .navigationDestination(for: Route.self) { route in
                    switch route {
                    case .stockDetail(let item):
                        StockDetailView(item: item)
                            .toolbar(.hidden, for: .tabBar)
                    case .notification:
                        NotificationView()
                            .toolbar(.hidden, for: .tabBar)
                    }
                }
        }
    }
}

struct PortfolioNavigationView: View {

    @EnvironmentObject private var router: Router

    var body: some View {
        NavigationStack(path: $router.path) {
            PortfolioView()
                .navigationDestination(for: Route.self) { route in
                    switch route {
                    case .stockDetail(let item):
                        StockDetailView(item: item)
                            .toolbar(.hidden, for: .tabBar)
                    case .notification:
                        NotificationView()
                            .toolbar(.hidden, for: .tabBar)
                    }
                }
        }
    }
}

// MARK: - Placeholder Views

struct AssetsView: View {
    var body: some View {
        Text("Assets View")
            .navigationTitle("Assets")
    }
}

struct NewsView: View {
    var body: some View {
        Text("News View")
            .navigationTitle("Berita")
    }
}

struct ProfileView: View {
    var body: some View {
        Text("Profile View")
            .navigationTitle("Profil")
    }
}

struct SearchView: View {

    @State private var searchText = ""

    private let symbols = [
        "BREN","BBCA","DSSA","BBRI","TPIA",
        "AMMN","BYAN","DCII","BMRI","TLKM"
    ]

    var body: some View {
        List(
            symbols.filter { searchText.isEmpty || $0.contains(searchText.uppercased()) },
            id: \.self
        ) { symbol in
            Text(symbol)
        }
        .navigationTitle("Cari Saham")
        .searchable(text: $searchText)
    }
}
