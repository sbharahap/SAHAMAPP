//
//  PortfolioView.swift
//  SahamIndo
//
//  Dibuat untuk memenuhi kebutuhan Tab Portfolio.
//  Menyediakan:
//  - Total Asset & Growth %
//  - Cash Balance & Deposit (Modal)
//  - Portfolio Value Chart
//  - Active Positions (Top 5)
//  - AI Auto-Pilot (Auto Trade)
//  - Top 5 AI Trade Recommendations
//  - Trading Sheet Simulator (Buy/Sell)
//

import SwiftUI

struct PortfolioView: View {
    @EnvironmentObject private var vm: PortfolioViewModel
    @EnvironmentObject private var router: Router
    
    @State private var showDepositSheet = false
    @State private var showTradeSheet = false
    @State private var selectedStockForTrade: PortfolioItem? = nil
    
    // Auto Trade State
    @State private var showAutoTradeConfirmation = false
    @State private var isAutoTrading = false
    @State private var autoTradeSuccessMessage: String? = nil
    
    private let darkBg = Color(hex: "12112e")
    private let cardBg = Color(hex: "1C1B35")
    private let accent = Color(hex: "EAB308")
    private let green = Color(hex: "22C55E")
    private let red = Color(hex: "EF4444")
    
    // Filter owned stocks
    private var activePositions: [PortfolioItem] {
        vm.items.filter { $0.quantity > 0 }
            .sorted { $0.value > $1.value }
    }
    
    // Top 5 AI Recommended stocks based on score
    private var aiRecommendations: [PortfolioItem] {
        vm.items.sorted { $0.sentiment.score > $1.sentiment.score }
            .prefix(5)
            .map { $0 }
    }
    
    var body: some View {
        ScrollView {
            VStack(spacing: 20) {
                // 1. Header Card (Portfolio Summary)
                summaryHeaderCard
                
                // 2. Portfolio Chart
                chartSection
                
                // 3. Active Positions
                positionsSection
                
                // 4. AI Auto-Pilot (Auto Trade)
                autoTradeSection
                
                // 5. AI Recommendations
                recommendationsSection
            }
            .padding(.bottom, 24)
        }
        .background(darkBg.ignoresSafeArea())
        .navigationTitle("")
        .navigationBarTitleDisplayMode(.inline)
        .safeAreaInset(edge: .top) {
            HStack {
                HStack(spacing: 0) {
                    Text("MY")
                        .font(.title)
                        .fontWeight(.bold)
                        .foregroundColor(.white)
                    Text(" PORTFOLIO")
                        .font(.title)
                        .fontWeight(.bold)
                        .foregroundColor(accent)
                }
                Spacer()
                
                Button(action: { vm.resetPortfolio() }) {
                    Image(systemName: "arrow.counterclockwise")
                        .foregroundColor(.red)
                        .padding(8)
                        .background(Color.white.opacity(0.05))
                        .clipShape(Circle())
                }
            }
            .padding(.horizontal)
            .padding(.vertical, 8)
            .background(darkBg)
        }
        .toolbar(.hidden, for: .navigationBar)
        .sheet(isPresented: $showDepositSheet) {
            DepositSheetView()
                .presentationDetents([.medium])
                .environmentObject(vm)
        }
        .sheet(item: $selectedStockForTrade) { stock in
            TradeSheetView(stock: stock)
                .presentationDetents([.large])
                .environmentObject(vm)
        }
        .task {
            await vm.fetchData()
        }
    }
    
    // MARK: - Summary Card
    private var summaryHeaderCard: some View {
        VStack(spacing: 16) {
            VStack(spacing: 4) {
                Text("Total Nilai Aset")
                    .font(.caption)
                    .foregroundColor(.secondary)
                
                Text(formatIDR(vm.totalAssetValue))
                    .font(.system(size: 30, weight: .bold, design: .rounded))
                    .foregroundColor(.white)
                
                let isGrowthPos = vm.portfolioGrowthPercent >= 0
                HStack(spacing: 4) {
                    Image(systemName: isGrowthPos ? "arrow.up.right" : "arrow.down.right")
                        .font(.system(size: 10, weight: .bold))
                    Text(String(format: "%+.2f%% Growth", vm.portfolioGrowthPercent))
                        .font(.system(size: 12, weight: .bold))
                }
                .foregroundColor(isGrowthPos ? green : red)
                .padding(.horizontal, 10)
                .padding(.vertical, 4)
                .background((isGrowthPos ? green : red).opacity(0.12))
                .clipShape(Capsule())
            }
            
            Divider()
                .background(Color.white.opacity(0.1))
            
            // Sub-details
            Grid(alignment: .leading, horizontalSpacing: 16, verticalSpacing: 10) {
                GridRow {
                    detailRow(label: "Saldo Kas (Cash)", value: vm.cashBalance, color: accent)
                    detailRow(label: "Nilai Saham", value: vm.totalValue, color: .white)
                }
                GridRow {
                    detailRow(label: "Total Deposit", value: vm.totalDepositedCash, color: .secondary)
                    detailRow(label: "Profit / Loss", value: vm.totalProfitIDR, color: vm.totalProfitIDR >= 0 ? green : red)
                }
            }
            
            // Deposit Button
            Button(action: { showDepositSheet = true }) {
                HStack {
                    Image(systemName: "plus.circle.fill")
                        .font(.system(size: 16, weight: .bold))
                    Text("Tambah Deposit")
                        .font(.system(size: 14, weight: .bold))
                }
                .foregroundColor(.black)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 12)
                .background(accent)
                .cornerRadius(10)
                .shadow(color: accent.opacity(0.3), radius: 5, x: 0, y: 3)
            }
        }
        .padding(16)
        .background(cardBg)
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .overlay(
            RoundedRectangle(cornerRadius: 16)
                .stroke(Color.white.opacity(0.08), lineWidth: 1)
        )
        .padding(.horizontal, 16)
    }
    
    private func detailRow(label: String, value: Double, color: Color) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(label)
                .font(.system(size: 10))
                .foregroundColor(.secondary)
            Text(formatIDR(value))
                .font(.system(size: 14, weight: .bold, design: .rounded))
                .foregroundColor(color)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
    
    // MARK: - Chart Section
    private var chartSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Grafik Pertumbuhan Aset")
                .font(.system(size: 15, weight: .bold))
                .foregroundColor(.white)
                .padding(.horizontal, 16)
            
            let historyPoints = PortfolioValuePoint.generate(from: vm.items)
            if historyPoints.isEmpty {
                VStack {
                    ProgressView()
                        .tint(accent)
                }
                .frame(height: 160)
                .frame(maxWidth: .infinity)
            } else {
                PortfolioHistoryChart(data: historyPoints)
                    .background(cardBg)
                    .clipShape(RoundedRectangle(cornerRadius: 16))
                    .overlay(
                        RoundedRectangle(cornerRadius: 16)
                            .stroke(Color.white.opacity(0.08), lineWidth: 1)
                    )
                    .padding(.horizontal, 16)
            }
        }
    }
    
    // MARK: - Positions Section
    private var positionsSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Portofolio Aktif Saya (Top 5)")
                .font(.system(size: 15, weight: .bold))
                .foregroundColor(.white)
                .padding(.horizontal, 16)
            
            if activePositions.isEmpty {
                VStack(spacing: 8) {
                    Image(systemName: "briefcase")
                        .font(.system(size: 32))
                        .foregroundColor(.secondary)
                        .padding(.bottom, 4)
                    Text("Belum Ada Kepemilikan Saham")
                        .font(.system(size: 13, weight: .bold))
                        .foregroundColor(.white)
                    Text("Gunakan saldo kas Anda dan rekomendasi AI di bawah untuk mulai membeli saham.")
                        .font(.system(size: 11))
                        .foregroundColor(.secondary)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, 24)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 24)
                .background(cardBg)
                .clipShape(RoundedRectangle(cornerRadius: 16))
                .overlay(
                    RoundedRectangle(cornerRadius: 16)
                        .stroke(Color.white.opacity(0.08), lineWidth: 1)
                )
                .padding(.horizontal, 16)
            } else {
                VStack(spacing: 0) {
                    ForEach(activePositions.prefix(5)) { item in
                        VStack(spacing: 0) {
                            HStack {
                                StockAvatarView(symbol: item.symbol)
                                
                                VStack(alignment: .leading, spacing: 2) {
                                    Text(item.symbol)
                                        .font(.system(size: 14, weight: .bold))
                                        .foregroundColor(.white)
                                    Text("\(Int(item.quantity)) lembar")
                                        .font(.caption2)
                                        .foregroundColor(.secondary)
                                }
                                
                                Spacer()
                                
                                VStack(alignment: .trailing, spacing: 2) {
                                    Text(formatIDR(item.value))
                                        .font(.system(size: 14, weight: .bold, design: .rounded))
                                        .foregroundColor(.white)
                                    
                                    let profit = item.value - (item.quantity * (vm.holdings.first(where: { $0.symbol == item.symbol })?.totalCostBasis ?? item.value) / max(item.quantity, 1))
                                    Text(profit >= 0 ? "+\(formatIDR(profit))" : formatIDR(profit))
                                        .font(.system(size: 10, weight: .medium))
                                        .foregroundColor(profit >= 0 ? green : red)
                                }
                                .padding(.trailing, 8)
                                
                                Button(action: { selectedStockForTrade = item }) {
                                    Text("Trade")
                                        .font(.system(size: 11, weight: .bold))
                                        .foregroundColor(.black)
                                        .padding(.horizontal, 12)
                                        .padding(.vertical, 6)
                                        .background(accent)
                                        .cornerRadius(6)
                                        .fixedSize(horizontal: true, vertical: false)
                                }
                            }
                            .padding(.vertical, 10)
                            
                            if item.symbol != activePositions.prefix(5).last?.symbol {
                                Divider().background(Color.white.opacity(0.08))
                            }
                        }
                    }
                }
                .padding(.horizontal, 12)
                .background(cardBg)
                .clipShape(RoundedRectangle(cornerRadius: 16))
                .overlay(
                    RoundedRectangle(cornerRadius: 16)
                        .stroke(Color.white.opacity(0.08), lineWidth: 1)
                )
                .padding(.horizontal, 16)
            }
        }
    }
    
    // MARK: - Auto Trade Section
    private var autoTradeSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("AI Auto-Pilot (Auto Trade)")
                .font(.system(size: 15, weight: .bold))
                .foregroundColor(.white)
                .padding(.horizontal, 16)
            
            VStack(alignment: .leading, spacing: 12) {
                HStack(alignment: .top, spacing: 12) {
                    Image(systemName: "sparkles")
                        .font(.system(size: 20, weight: .semibold))
                        .foregroundColor(accent)
                        .padding(10)
                        .background(accent.opacity(0.12))
                        .clipShape(RoundedRectangle(cornerRadius: 10))
                    
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Aktifkan Sistem Auto Trade")
                            .font(.system(size: 13, weight: .bold))
                            .foregroundColor(.white)
                        Text("Menyelaraskan aset kas & saham Anda secara seimbang (20% per emiten) langsung ke Top 5 rekomendasi AI terbaik sistem saat ini.")
                            .font(.system(size: 10.5))
                            .foregroundColor(.secondary)
                            .lineSpacing(2)
                    }
                }
                
                if let msg = autoTradeSuccessMessage {
                    Text(msg)
                        .font(.system(size: 12, weight: .semibold))
                        .foregroundColor(green)
                        .padding(.vertical, 2)
                }
                
                Button(action: { showAutoTradeConfirmation = true }) {
                    HStack {
                        if isAutoTrading {
                            ProgressView()
                                .tint(.black)
                                .padding(.trailing, 4)
                        } else {
                            Image(systemName: "bolt.fill")
                        }
                        Text(isAutoTrading ? "Menyelaraskan Portofolio..." : "Aktifkan AI Auto-Pilot")
                            .font(.system(size: 13, weight: .bold))
                    }
                    .foregroundColor(.black)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 11)
                    .background(isAutoTrading ? Color.gray : accent)
                    .cornerRadius(8)
                }
                .disabled(isAutoTrading)
            }
            .padding(14)
            .background(cardBg)
            .clipShape(RoundedRectangle(cornerRadius: 16))
            .overlay(
                RoundedRectangle(cornerRadius: 16)
                    .stroke(Color.white.opacity(0.08), lineWidth: 1)
            )
            .padding(.horizontal, 16)
            .alert("Aktifkan AI Auto-Pilot?", isPresented: $showAutoTradeConfirmation) {
                Button("Ya, Eksekusi", role: .none) {
                    executeAutoTrade()
                }
                Button("Batal", role: .cancel) {}
            } message: {
                Text("Saldo kas dan aset saham Anda akan disesuaikan otomatis mengikuti formula pembobotan seimbang (20% per saham) untuk Top 5 emiten rekomendasi AI saat ini.")
            }
        }
    }
    
    private func executeAutoTrade() {
        isAutoTrading = true
        autoTradeSuccessMessage = nil
        UIImpactFeedbackGenerator(style: .medium).impactOccurred()
        
        // Simulasikan delay restrukturisasi 1.2 detik agar terlihat premium
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.2) {
            vm.autoTrade()
            isAutoTrading = false
            autoTradeSuccessMessage = "✓ Portofolio berhasil diselaraskan ke Top 5 rekomendasi AI!"
            UINotificationFeedbackGenerator().notificationOccurred(.success)
            
            // Hilangkan success message setelah 3 detik
            DispatchQueue.main.asyncAfter(deadline: .now() + 3.0) {
                autoTradeSuccessMessage = nil
            }
        }
    }
    
    // MARK: - AI Recommendations Section
    private var recommendationsSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            VStack(alignment: .leading, spacing: 2) {
                Text("Rekomendasi Trading AI (Top 5)")
                    .font(.system(size: 15, weight: .bold))
                    .foregroundColor(.white)
                Text("Saham terbaik minggu ini disaring oleh model multi-timeframe trend & fundamental.")
                    .font(.system(size: 10))
                    .foregroundColor(.secondary)
            }
            .padding(.horizontal, 16)
            
            VStack(spacing: 0) {
                ForEach(aiRecommendations) { item in
                    VStack(spacing: 0) {
                        HStack {
                            StockAvatarView(symbol: item.symbol)
                            
                            VStack(alignment: .leading, spacing: 2) {
                                HStack(spacing: 6) {
                                    Text(item.symbol)
                                        .font(.system(size: 14, weight: .bold))
                                        .foregroundColor(.white)
                                        .fixedSize(horizontal: true, vertical: false)
                                    
                                    // FIXED: Tambahkan fixedSize agar tulisan tidak kepotong
                                    SentimentPill(sentiment: item.sentiment, size: .small)
                                        .fixedSize(horizontal: true, vertical: false)
                                }
                                Text(item.name ?? "-")
                                    .font(.caption2)
                                    .foregroundColor(.secondary)
                                    .lineLimit(1)
                                    .truncationMode(.tail)
                                
                                SentimentBarMiniView(sentiment: item.sentiment)
                            }
                            .layoutPriority(1)
                            
                            Spacer()
                            
                            VStack(alignment: .trailing, spacing: 2) {
                                Text(formatIDR(item.price))
                                    .font(.system(size: 14, weight: .semibold))
                                    .foregroundColor(.white)
                                
                                Text(String(format: "%+.2f%%", item.percentChange))
                                    .font(.system(size: 10, weight: .bold))
                                    .foregroundColor(item.percentChange >= 0 ? green : red)
                            }
                            .padding(.trailing, 8)
                            
                            Button(action: { selectedStockForTrade = item }) {
                                Text("Trade")
                                    .font(.system(size: 11, weight: .bold))
                                    .foregroundColor(.black)
                                    .padding(.horizontal, 12)
                                    .padding(.vertical, 6)
                                    .background(accent)
                                    .cornerRadius(6)
                                    .fixedSize(horizontal: true, vertical: false)
                            }
                        }
                        .padding(.vertical, 10)
                        
                        if item.symbol != aiRecommendations.last?.symbol {
                            Divider().background(Color.white.opacity(0.08))
                        }
                    }
                }
            }
            .padding(.horizontal, 12)
            .background(cardBg)
            .clipShape(RoundedRectangle(cornerRadius: 16))
            .overlay(
                RoundedRectangle(cornerRadius: 16)
                    .stroke(Color.white.opacity(0.08), lineWidth: 1)
            )
            .padding(.horizontal, 16)
        }
    }
}

// MARK: - Deposit Sheet View
struct DepositSheetView: View {
    @Environment(\.dismiss) private var dismiss
    @EnvironmentObject private var vm: PortfolioViewModel
    
    @State private var depositAmountStr = ""
    @State private var successMessage: String? = nil
    
    // Keyboard Focus State
    @FocusState private var isInputFocused: Bool
    
    private let darkBg = Color(hex: "12112e")
    private let cardBg = Color(hex: "1C1B35")
    private let accent = Color(hex: "EAB308")
    
    private let quickOptions: [Double] = [5_000_000, 10_000_000, 50_000_000, 100_000_000]
    
    var body: some View {
        NavigationStack {
            VStack(spacing: 20) {
                Text("Tambah saldo kas untuk mulai bertransaksi simulasi trading saham.")
                    .font(.system(size: 13))
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
                    .padding(.top, 12)
                
                // Input
                VStack(alignment: .leading, spacing: 8) {
                    Text("Nominal Deposit (IDR)")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    
                    TextField("Masukkan jumlah deposit", text: $depositAmountStr)
                        .keyboardType(.numberPad)
                        .focused($isInputFocused) // FIXED: Bind focus state
                        .padding()
                        .background(Color.white.opacity(0.05))
                        .cornerRadius(10)
                        .foregroundColor(.white)
                        .font(.system(size: 18, weight: .bold, design: .rounded))
                        .overlay(
                            RoundedRectangle(cornerRadius: 10)
                                .stroke(accent.opacity(0.3), lineWidth: 1)
                        )
                }
                
                // Quick options
                HStack(spacing: 8) {
                    ForEach(quickOptions, id: \.self) { amount in
                        Button(action: {
                            depositAmountStr = String(format: "%.0f", amount)
                        }) {
                            Text(formatIDRShort(amount))
                                .font(.system(size: 12, weight: .bold))
                                .foregroundColor(.white)
                                .padding(.vertical, 8)
                                .frame(maxWidth: .infinity)
                                .background(Color.white.opacity(0.08))
                                .cornerRadius(8)
                        }
                    }
                }
                
                if let msg = successMessage {
                    Text(msg)
                        .font(.system(size: 13, weight: .medium))
                        .foregroundColor(Color(hex: "22C55E"))
                        .padding(.vertical, 4)
                }
                
                Spacer()
                
                Button(action: executeDeposit) {
                    Text("Konfirmasi Deposit")
                        .font(.system(size: 15, weight: .bold))
                        .foregroundColor(.black)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 14)
                        .background(accent)
                        .cornerRadius(12)
                }
                .disabled(Double(depositAmountStr) ?? 0 <= 0)
                .opacity(Double(depositAmountStr) ?? 0 <= 0 ? 0.5 : 1)
            }
            .padding(16)
            .background(darkBg.ignoresSafeArea())
            .navigationTitle("Deposit Portfolio")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Tutup") { dismiss() }
                        .foregroundColor(.secondary)
                }
                
                // FIXED: Tambahkan keyboard toolbar Done untuk menutup keyboard
                ToolbarItemGroup(placement: .keyboard) {
                    Spacer()
                    Button("Selesai") {
                        isInputFocused = false
                    }
                    .foregroundColor(accent)
                    .fontWeight(.bold)
                }
            }
            .preferredColorScheme(.dark)
        }
    }
    
    private func executeDeposit() {
        guard let amount = Double(depositAmountStr), amount > 0 else { return }
        
        vm.deposit(amount: amount)
        successMessage = "Berhasil deposit \(formatIDR(amount)) ke kas portofolio!"
        UIImpactFeedbackGenerator(style: .medium).impactOccurred()
        
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
            dismiss()
        }
    }
}

// MARK: - Trade Sheet View
struct TradeSheetView: View {
    @Environment(\.dismiss) private var dismiss
    @EnvironmentObject private var vm: PortfolioViewModel
    
    let stock: PortfolioItem
    
    @State private var tradeType = 0 // 0: BELI, 1: JUAL
    @State private var useNominal = true // true: IDR, false: LOT
    @State private var tradeAmountStr = ""
    @State private var message: String? = nil
    @State private var isError = false
    
    // Keyboard Focus State
    @FocusState private var isInputFocused: Bool
    
    private let darkBg = Color(hex: "12112e")
    private let cardBg = Color(hex: "1C1B35")
    private let accent = Color(hex: "EAB308")
    private let green = Color(hex: "22C55E")
    private let red = Color(hex: "EF4444")
    
    private var price: Double { stock.price }
    
    // Quick Amount Buttons
    private let quickIDROptions: [Double] = [1_000_000, 5_000_000, 10_000_000, 50_000_000]
    private let quickLotOptions: [Double] = [1, 5, 10, 50]
    
    // Sanitation helper
    private var inputAmount: Double {
        let sanitized = tradeAmountStr.filter { "0123456789".contains($0) }
        return Double(sanitized) ?? 0
    }
    
    // Calculations
    private var calculatedLots: Double {
        if useNominal {
            let idr = inputAmount
            guard idr > 0 else { return 0 }
            return floor(idr / (price * 100.0))
        } else {
            return inputAmount
        }
    }
    
    private var calculatedShares: Double {
        calculatedLots * 100.0
    }
    
    private var subtotal: Double {
        calculatedShares * price
    }
    
    private var transactionFee: Double {
        let rate = (tradeType == 0) ? 0.0020 : 0.0030 // Buy: 0.20%, Sell: 0.30%
        return subtotal * rate
    }
    
    private var estTotal: Double {
        if tradeType == 0 {
            return subtotal + transactionFee
        } else {
            return subtotal - transactionFee
        }
    }
    
    private var ownedQuantity: Double {
        vm.holdings.first(where: { $0.symbol == stock.symbol })?.quantity ?? 0
    }
    
    private var canExecute: Bool {
        guard calculatedShares > 0 else { return false }
        if tradeType == 0 {
            return estTotal <= vm.cashBalance
        } else {
            return calculatedShares <= ownedQuantity
        }
    }
    
    var body: some View {
        NavigationStack {
            VStack(spacing: 20) {
                // Segmented control
                Picker("Tipe Transaksi", selection: $tradeType) {
                    Text("BELI").tag(0)
                    Text("JUAL").tag(1)
                }
                .pickerStyle(.segmented)
                .padding(.top, 12)
                
                // Info Section
                HStack(spacing: 12) {
                    StockAvatarView(symbol: stock.symbol)
                    VStack(alignment: .leading, spacing: 2) {
                        Text(stock.symbol)
                            .font(.system(size: 16, weight: .bold))
                            .foregroundColor(.white)
                        Text(stock.name ?? "-")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                    Spacer()
                    VStack(alignment: .trailing, spacing: 2) {
                        Text(formatIDR(price))
                            .font(.system(size: 16, weight: .bold, design: .rounded))
                            .foregroundColor(.white)
                        Text("Harga saat ini")
                            .font(.caption2)
                            .foregroundColor(.secondary)
                    }
                }
                .padding()
                .background(cardBg)
                .cornerRadius(12)
                
                // Cash & holdings info
                HStack {
                    VStack(alignment: .leading) {
                        Text("Saldo Kas Tersedia")
                            .font(.caption2)
                            .foregroundColor(.secondary)
                        Text(formatIDR(vm.cashBalance))
                            .font(.system(size: 14, weight: .bold))
                            .foregroundColor(accent)
                    }
                    Spacer()
                    VStack(alignment: .trailing) {
                        Text("Saham Dimiliki")
                            .font(.caption2)
                            .foregroundColor(.secondary)
                        Text("\(Int(ownedQuantity)) lembar (\(Int(ownedQuantity/100)) Lot)")
                            .font(.system(size: 14, weight: .bold))
                            .foregroundColor(.white)
                    }
                }
                .padding(.horizontal, 4)
                
                // Input type picker
                Picker("Input Tipe", selection: $useNominal) {
                    Text("Nominal (Rupiah)").tag(true)
                    Text("Jumlah Lot").tag(false)
                }
                .pickerStyle(.segmented)
                
                // Input field
                VStack(alignment: .leading, spacing: 8) {
                    Text(useNominal ? "Nominal Transaksi (IDR)" : "Jumlah Pembelian (Lot)")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    
                    TextField(useNominal ? "Masukkan nominal Rupiah" : "Masukkan jumlah Lot", text: $tradeAmountStr)
                        .keyboardType(.numberPad)
                        .focused($isInputFocused) // FIXED: Bind focus state
                        .padding()
                        .background(Color.white.opacity(0.05))
                        .cornerRadius(10)
                        .foregroundColor(.white)
                        .font(.system(size: 16, weight: .bold))
                        .overlay(
                            RoundedRectangle(cornerRadius: 10)
                                .stroke(accent.opacity(0.3), lineWidth: 1)
                        )
                }
                
                // Quick options
                HStack(spacing: 8) {
                    if useNominal {
                        ForEach(quickIDROptions, id: \.self) { amount in
                            Button(action: { tradeAmountStr = String(format: "%.0f", amount) }) {
                                Text(formatIDRShort(amount))
                                    .font(.system(size: 12, weight: .bold))
                                    .foregroundColor(.white)
                                    .padding(.vertical, 8)
                                    .frame(maxWidth: .infinity)
                                    .background(Color.white.opacity(0.08))
                                    .cornerRadius(8)
                            }
                        }
                    } else {
                        ForEach(quickLotOptions, id: \.self) { lot in
                            Button(action: { tradeAmountStr = String(format: "%.0f", lot) }) {
                                Text("\(Int(lot)) Lot")
                                    .font(.system(size: 12, weight: .bold))
                                    .foregroundColor(.white)
                                    .padding(.vertical, 8)
                                    .frame(maxWidth: .infinity)
                                    .background(Color.white.opacity(0.08))
                                    .cornerRadius(8)
                            }
                        }
                    }
                }
                
                // Live Calculation Invoice
                VStack(spacing: 8) {
                    invoiceRow(label: "Jumlah Transaksi", value: "\(Int(calculatedLots)) Lot (\(Int(calculatedShares)) lembar)")
                    invoiceRow(label: "Subtotal", value: formatIDR(subtotal))
                    invoiceRow(label: "Broker Fee (Pajak + Levy)", value: formatIDR(transactionFee))
                    Divider().background(Color.white.opacity(0.1))
                    invoiceRow(
                        label: (tradeType == 0) ? "Total Estimasi Bayar" : "Total Estimasi Terima",
                        value: formatIDR(estTotal),
                        isBold: true,
                        color: (tradeType == 0) ? accent : green
                    )
                }
                .padding()
                .background(cardBg)
                .cornerRadius(12)
                
                let minLotPrice = price * 100.0
                if useNominal, inputAmount > 0, inputAmount < minLotPrice {
                    Text("Nominal di bawah batas minimum 1 Lot (Rp \(formatIDR(minLotPrice)))")
                        .font(.system(size: 11, weight: .semibold))
                        .foregroundColor(red)
                        .padding(.vertical, 2)
                }
                
                if let msg = message {
                    Text(msg)
                        .font(.system(size: 12, weight: .semibold))
                        .foregroundColor(isError ? red : green)
                        .multilineTextAlignment(.center)
                        .padding(.vertical, 2)
                }
                
                Spacer()
                
                // Action Button
                Button(action: executeTrade) {
                    Text((tradeType == 0) ? "Eksekusi Beli Saham" : "Eksekusi Jual Saham")
                        .font(.system(size: 15, weight: .bold))
                        .foregroundColor(.black)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 14)
                        .background((tradeType == 0) ? accent : green)
                        .cornerRadius(12)
                }
                .disabled(!canExecute)
                .opacity(canExecute ? 1.0 : 0.4)
            }
            .padding(16)
            .background(darkBg.ignoresSafeArea())
            .navigationTitle("Transaksi Simulator")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Batal") { dismiss() }
                        .foregroundColor(.secondary)
                }
                
                // FIXED: Tambahkan keyboard toolbar Done untuk menutup keyboard
                ToolbarItemGroup(placement: .keyboard) {
                    Spacer()
                    Button("Selesai") {
                        isInputFocused = false
                    }
                    .foregroundColor(accent)
                    .fontWeight(.bold)
                }
            }
            .preferredColorScheme(.dark)
        }
    }
    
    private func invoiceRow(label: String, value: String, isBold: Bool = false, color: Color = .white) -> some View {
        HStack {
            Text(label)
                .font(.system(size: 11))
                .foregroundColor(.secondary)
            Spacer()
            Text(value)
                .font(.system(size: 12, weight: isBold ? .bold : .regular))
                .foregroundColor(color)
        }
    }
    
    private func executeTrade() {
        guard canExecute else { return }
        
        let qtyVal = calculatedShares
        
        if tradeType == 0 {
            vm.buy(symbol: stock.symbol, amountIDR: subtotal, price: price)
            isError = false
            message = "Berhasil membeli \(Int(calculatedLots)) Lot (\(Int(qtyVal)) lembar) \(stock.symbol)!"
        } else {
            vm.sell(symbol: stock.symbol, quantity: qtyVal)
            isError = false
            message = "Berhasil menjual \(Int(calculatedLots)) Lot (\(Int(qtyVal)) lembar) \(stock.symbol)!"
        }
        
        UIImpactFeedbackGenerator(style: .medium).impactOccurred()
        
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.2) {
            dismiss()
        }
    }
}

// MARK: - Sentiment Bar Mini
struct SentimentBarMiniView: View {
    let sentiment: Sentiment

    var body: some View {
        HStack(spacing: 4) {
            ZStack(alignment: .leading) {
                RoundedRectangle(cornerRadius: 2)
                    .fill(Color.white.opacity(0.12))
                    .frame(width: 80, height: 4)
                
                RoundedRectangle(cornerRadius: 2)
                    .fill(sentiment.color)
                    .frame(width: 80 * CGFloat(sentiment.score / 100.0), height: 4)
            }
            
            Text(String(format: "%.1f%%", sentiment.score))
                .font(.system(size: 9, weight: .bold, design: .rounded))
                .foregroundColor(sentiment.color)
                .fixedSize(horizontal: true, vertical: false)
        }
    }
}
