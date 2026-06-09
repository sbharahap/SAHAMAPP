//
//  ViewModel+Cache.swift
//  SahamIndo
//
//  Patch tipis — GANTI dua method di PortfolioViewModel & StockChartViewModel
//  supaya memakai fetchAllStocksCached() & fetchCandlesCached().
//
//  CARA PAKAI:
//  1. Tambahkan file StockCache.swift ke project.
//  2. Di PortfolioViewModel.swift — ganti method fetchData() dengan versi di bawah.
//  3. Di StockChartViewModel.swift — ganti method fetchData() dengan versi di bawah.
//  4. Tambahkan @Published var cacheState ke masing-masing ViewModel.
//  5. (Opsional) Tampilkan CacheStatusBanner di HomeView & StockDetailView.
//

import SwiftUI
import Combine

// ─────────────────────────────────────────────────────────────
// MARK: - PortfolioViewModel (patch)
// ─────────────────────────────────────────────────────────────
//
// Tambahkan property ini ke deklarasi class PortfolioViewModel:
//
//   @Published var cacheState: CacheState = .live
//
// Lalu GANTI fetchData() dengan:


// ─────────────────────────────────────────────────────────────
// MARK: - StockChartViewModel (patch)
// ─────────────────────────────────────────────────────────────
//
// Tambahkan property ini ke deklarasi class StockChartViewModel:
//
//   @Published var cacheState: CacheState = .live
//
// Lalu GANTI fetchData() dengan:



// ─────────────────────────────────────────────────────────────
// MARK: - CacheStatusBanner  (View helper — taruh di HomeView & StockDetailView)
// ─────────────────────────────────────────────────────────────
//
// Contoh pemakaian di HomeView:
//
//   CacheStatusBanner(state: vm.cacheState)
//       .padding(.horizontal, 16)
//
// Contoh pemakaian di StockDetailView:
//
//   CacheStatusBanner(state: chartVM.cacheState)
//

struct CacheStatusBanner: View {

    let state: CacheState

    var body: some View {
        switch state {
        case .live:
            // Tidak tampilkan apa-apa saat data live
            EmptyView()

        case .cached(let age):
            HStack(spacing: 6) {
                Image(systemName: "wifi.slash")
                    .font(.system(size: 11, weight: .semibold))
                Text("Offline · data \(age)")
                    .font(.system(size: 11, weight: .medium))
            }
            .foregroundColor(Color(hex: "EAB308"))
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(Color(hex: "EAB308").opacity(0.12))
            .clipShape(Capsule())
            .overlay(Capsule().strokeBorder(Color(hex: "EAB308").opacity(0.3), lineWidth: 0.5))
            .transition(.opacity.combined(with: .scale(scale: 0.95)))

        case .noData:
            HStack(spacing: 6) {
                Image(systemName: "exclamationmark.triangle.fill")
                    .font(.system(size: 11, weight: .semibold))
                Text("Offline · tidak ada data tersimpan")
                    .font(.system(size: 11, weight: .medium))
            }
            .foregroundColor(Color(hex: "EF4444"))
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(Color(hex: "EF4444").opacity(0.12))
            .clipShape(Capsule())
            .overlay(Capsule().strokeBorder(Color(hex: "EF4444").opacity(0.3), lineWidth: 0.5))
            .transition(.opacity.combined(with: .scale(scale: 0.95)))
        }
    }
}
