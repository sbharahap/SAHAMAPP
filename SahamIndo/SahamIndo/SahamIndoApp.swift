//
//  SahamIndoApp.swift
//  SahamIndo
//

import SwiftUI

@main
struct SahamIndoApp: App {

    @StateObject private var portfolioVM = PortfolioViewModel()
    @StateObject private var router      = Router()
    @StateObject private var chatbotVM   = ChatbotViewModel()
    @StateObject private var notifVM     = NotificationViewModel()

    var body: some Scene {
        WindowGroup {
            MainTabView()
                .environmentObject(portfolioVM)
                .environmentObject(router)
                .environmentObject(chatbotVM)
                .environmentObject(notifVM)
        }
    }
}
