//
//  Router.swift
//  SahamIndo
//

import SwiftUI
import Combine
// MARK: - Route

enum Route: Hashable {
    case stockDetail(PortfolioItem)
    case portfolioDetail(PortfolioItem)
}

// MARK: - Router

@MainActor
final class Router: ObservableObject {
    @Published var path = NavigationPath()
    @Published var selectedTab: String = "home"

    func push(_ route: Route) {
        path.append(route)
    }

    func pop() {
        guard !path.isEmpty else { return }
        path.removeLast()
    }

    func popToRoot() {
        path.removeLast(path.count)
    }
}
