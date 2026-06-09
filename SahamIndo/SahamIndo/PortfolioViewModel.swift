//
//  PortfolioViewModel.swift
//  SahamIndo
//
//  Perubahan: ganti DummyStockService → RealStockService
//

import SwiftUI
import Combine

@MainActor
final class PortfolioViewModel: ObservableObject {

    // MARK: - Published
    @Published private(set) var items:    [PortfolioItem] = []
    @Published private(set) var holdings: [Holding]      = []
    @Published private(set) var isLoading: Bool           = false
    @Published var errorMessage: String?                  = nil
    @Published var cacheState: CacheState = .live
    
    @Published var cashBalance: Double = 50_000_000.0
    @Published var totalDepositedCash: Double = 50_000_000.0

    // MARK: - Private
    private let service:    StockServiceProtocol
    private let realService = RealStockService()
    private let storageKey  = "portfolio_holdings_idn_v4"
    private let cashKey     = "portfolio_cash_balance_v4"
    private let depositedKey = "portfolio_deposited_cash_v4"

    // MARK: - Computed
    var totalValue: Double { items.reduce(0) { $0 + $1.value } }
    var totalCost: Double  { holdings.reduce(0) { $0 + $1.totalCostBasis } }
    var totalProfitIDR: Double { totalValue - totalCost }
    
    var totalAssetValue: Double { totalValue + cashBalance }
    var portfolioGrowthPercent: Double {
        let diff = totalAssetValue - totalDepositedCash
        return (diff / max(totalDepositedCash, 1.0)) * 100.0
    }

    // MARK: - Init
    init() {
        self.service = DummyStockService()
        loadHoldings()
        loadCash()
    }

    init(service: StockServiceProtocol) {
        self.service = service
        loadHoldings()
        loadCash()
    }

    // MARK: - Fetch (sekarang pakai RealStockService)
    func fetchData() async {
        await fetchDataWithCache()
    }

    // Fallback ke DummyStockService kalau server mati
    private func fetchDataFallback() async {
        do {
            var temp: [PortfolioItem] = []
            for holding in holdings {
                let data = try await service.fetchStock(symbol: holding.symbol)
                temp.append(PortfolioItem(
                    symbol:        data.symbol,
                    name:          data.name,
                    logo:          data.logo,
                    price:         data.price,
                    change:        data.change,
                    percentChange: data.percentChange,
                    quantity:      holding.quantity,
                    sentiment:     makeSentiment(for: data.percentChange)
                ))
            }
            items = temp
        } catch {
            print("[PortfolioViewModel] fallback error:", error)
        }
    }

    // MARK: - Deposit

    func deposit(amount: Double) {
        guard amount > 0 else { return }
        cashBalance += amount
        totalDepositedCash += amount
        saveCash()
    }

    // MARK: - Auto Trade (AI Auto-Pilot)

    func autoTrade() {
        // 1. Get Top 5 recommended symbols by Sentiment Score
        let top5Symbols = items.sorted { $0.sentiment.score > $1.sentiment.score }
                               .prefix(5)
                               .map { $0.symbol }
        
        guard top5Symbols.count == 5 else { return }
        
        let fee_buy = 0.0020
        let fee_sell = 0.0030
        
        // 2. Sell holdings not in Top 5
        for idx in 0..<holdings.count {
            let symbol = holdings[idx].symbol
            let qty = holdings[idx].quantity
            if !top5Symbols.contains(symbol) && qty > 0 {
                let currentPrice = items.first(where: { $0.symbol == symbol })?.price ?? (holdings[idx].totalCostBasis / qty)
                let revenue = qty * currentPrice
                let netRevenue = revenue * (1.0 - fee_sell)
                cashBalance += netRevenue
                holdings[idx].quantity = 0
                holdings[idx].totalCostBasis = 0
            }
        }
        
        // 3. Calculate total portfolio value (cash + remaining stock value)
        var totalStockValue = 0.0
        for holding in holdings {
            if top5Symbols.contains(holding.symbol) && holding.quantity > 0 {
                let price = items.first(where: { $0.symbol == holding.symbol })?.price ?? 0
                totalStockValue += holding.quantity * price
            }
        }
        let totalAsset = cashBalance + totalStockValue
        let targetPerStock = totalAsset / 5.0
        
        // 4. Adjust each of the Top 5 stocks to match target allocation (20%)
        for symbol in top5Symbols {
            guard let price = items.first(where: { $0.symbol == symbol })?.price, price > 0 else { continue }
            
            let idx: Int
            if let existingIdx = holdings.firstIndex(where: { $0.symbol == symbol }) {
                idx = existingIdx
            } else {
                holdings.append(Holding(symbol: symbol, quantity: 0, totalCostBasis: 0))
                idx = holdings.count - 1
            }
            
            let currentQty = holdings[idx].quantity
            let currentVal = currentQty * price
            let diff = targetPerStock - currentVal
            
            if diff > 0 {
                // Buy more to reach 20% weight
                let cost = diff / (1.0 + fee_buy)
                let actualCost = min(cost, cashBalance / (1.0 + fee_buy))
                let lots = floor(actualCost / (price * 100.0))
                let qtyToBuy = lots * 100.0
                if qtyToBuy > 0 {
                    let costPaid = qtyToBuy * price
                    cashBalance -= costPaid * (1.0 + fee_buy)
                    holdings[idx].quantity += qtyToBuy
                    holdings[idx].totalCostBasis += costPaid
                }
            } else if diff < 0 && currentQty > 0 {
                // Sell excess to reach 20% weight
                let valToSell = abs(diff)
                let sharesToSell = min(floor(valToSell / price), currentQty)
                let lots = floor(sharesToSell / 100.0)
                let qtyToSell = lots * 100.0
                if qtyToSell > 0 {
                    let revenue = qtyToSell * price
                    cashBalance += revenue * (1.0 - fee_sell)
                    let avgCost = holdings[idx].totalCostBasis / currentQty
                    holdings[idx].quantity -= qtyToSell
                    holdings[idx].totalCostBasis -= qtyToSell * avgCost
                }
            }
        }
        
        // Clean up empty holdings
        for i in 0..<holdings.count {
            if holdings[i].quantity < 1e-5 {
                holdings[i].quantity = 0
                holdings[i].totalCostBasis = 0
            }
        }
        
        saveHoldings()
        saveCash()
        Task { await fetchData() }
    }

    // MARK: - Buy / Sell / Reset

    func buy(symbol: String, amountIDR: Double, price: Double) {
        guard price > 0, amountIDR > 0 else { return }
        let lots = floor(amountIDR / (price * 100))
        let qty  = lots * 100
        guard qty > 0 else { return }
        let cost = qty * price
        
        let fee_buy = 0.0020
        let totalCost = cost * (1.0 + fee_buy)
        
        // Ensure user has enough cash balance
        guard totalCost <= cashBalance else {
            errorMessage = "Saldo tidak mencukupi untuk melakukan pembelian."
            return
        }
        
        cashBalance -= totalCost
        
        if let idx = holdings.firstIndex(where: { $0.symbol == symbol }) {
            holdings[idx].quantity       += qty
            holdings[idx].totalCostBasis += cost
        } else {
            holdings.append(Holding(symbol: symbol, quantity: qty, totalCostBasis: cost))
        }
        
        saveHoldings()
        saveCash()
        Task { await fetchData() }
    }

    func sell(symbol: String, quantity: Double) {
        guard quantity > 0 else { return }
        guard let idx = holdings.firstIndex(where: { $0.symbol == symbol }) else { return }
        let owned    = holdings[idx].quantity
        let sellQty  = min(quantity, owned)
        guard sellQty > 0 else { return }
        
        let avgPrice = owned > 0 ? holdings[idx].totalCostBasis / owned : 0
        let currentPrice = items.first(where: { $0.symbol == symbol })?.price ?? avgPrice
        
        let revenue = sellQty * currentPrice
        let fee_sell = 0.0030
        let netRevenue = revenue * (1.0 - fee_sell)
        
        holdings[idx].quantity       -= sellQty
        holdings[idx].totalCostBasis -= sellQty * avgPrice
        
        if holdings[idx].quantity < 1e-5 {
            holdings[idx].quantity = 0
            holdings[idx].totalCostBasis = 0
        }
        
        cashBalance += netRevenue
        
        saveHoldings()
        saveCash()
        Task { await fetchData() }
    }

    func resetPortfolio() {
        UserDefaults.standard.removeObject(forKey: storageKey)
        UserDefaults.standard.removeObject(forKey: cashKey)
        UserDefaults.standard.removeObject(forKey: depositedKey)
        holdings = defaultHoldings()
        cashBalance = 50_000_000.0
        totalDepositedCash = 50_000_000.0
        Task { await fetchData() }
    }

    // MARK: - Persistence

    private func saveHoldings() {
        guard let encoded = try? JSONEncoder().encode(holdings) else { return }
        UserDefaults.standard.set(encoded, forKey: storageKey)
    }

    private func loadHoldings() {
        if let data    = UserDefaults.standard.data(forKey: storageKey),
           var decoded = try? JSONDecoder().decode([Holding].self, from: data) {
            
            var migrated = false
            // Terapkan migrasi GOTO ke GGRM agar portofolio user tidak perlu di-reset
            for i in 0..<decoded.count {
                if decoded[i].symbol == "GOTO" {
                    decoded[i] = Holding(symbol: "GGRM", quantity: decoded[i].quantity, totalCostBasis: decoded[i].totalCostBasis)
                    migrated = true
                }
            }
            
            // Pastikan GGRM ada dalam list
            let hasGGRM = decoded.contains(where: { $0.symbol == "GGRM" })
            if !hasGGRM {
                decoded.append(Holding(symbol: "GGRM", quantity: 0, totalCostBasis: 0))
                migrated = true
            }
            
            // Bersihkan sisa GOTO jika ada
            if decoded.contains(where: { $0.symbol == "GOTO" }) {
                decoded.removeAll(where: { $0.symbol == "GOTO" })
                migrated = true
            }
            
            holdings = decoded
            if migrated {
                saveHoldings()
            }
        } else {
            holdings = defaultHoldings()
        }
    }
    
    private func saveCash() {
        UserDefaults.standard.set(cashBalance, forKey: cashKey)
        UserDefaults.standard.set(totalDepositedCash, forKey: depositedKey)
    }

    private func loadCash() {
        if UserDefaults.standard.object(forKey: cashKey) != nil {
            cashBalance = UserDefaults.standard.double(forKey: cashKey)
        } else {
            cashBalance = 50_000_000.0
        }
        
        if UserDefaults.standard.object(forKey: depositedKey) != nil {
            totalDepositedCash = UserDefaults.standard.double(forKey: depositedKey)
        } else {
            totalDepositedCash = 50_000_000.0
        }
    }

    private func defaultHoldings() -> [Holding] {
        ["BBCA", "BBRI", "BMRI", "BBNI", "TLKM", "ASII", "UNVR", "ADRO", "GGRM", "KLBF", "ANTM", "PGAS", "ICBP", "INDF", "UNTR", "PTBA", "MEDC", "BRIS", "AMRT", "MDKA"].map {
            Holding(symbol: $0, quantity: 0, totalCostBasis: 0)
        }
    }

    // MARK: - Helpers

    private func makeSentiment(for pct: Double) -> Sentiment {
        if pct > 1 {
            return Sentiment(buy:  .random(in: 0.55...0.75),
                             hold: .random(in: 0.15...0.25),
                             sell: .random(in: 0.05...0.15),
                             score: .random(in: 75.0...95.0))
        } else if pct < -1 {
            return Sentiment(buy:  .random(in: 0.10...0.25),
                             hold: .random(in: 0.20...0.30),
                             sell: .random(in: 0.45...0.65),
                             score: .random(in: 15.0...40.0))
        } else {
            return Sentiment(buy:  .random(in: 0.30...0.50),
                             hold: .random(in: 0.30...0.40),
                             sell: .random(in: 0.15...0.30),
                             score: .random(in: 45.0...70.0))
        }
    }
}

extension PortfolioViewModel {

    /// Versi baru fetchData() — pakai cache otomatis saat offline.
    /// Salin isi function ini ke fetchData() di PortfolioViewModel.swift.
    func fetchDataWithCache() async {
        isLoading    = true
        errorMessage = nil

        let (allData, state) = await realService.fetchAllStocksCached()
        cacheState = state
        
        print("[Portfolio] allData count:", allData.count)       // ← berapa yang di-fetch/cache?
        print("[Portfolio] holdings count:", holdings.count)     // ← holdings terisi?
        print("[Portfolio] cacheState:", state)                  // ← live/cached/noData?

        if allData.isEmpty {
            // Tidak ada data sama sekali (API mati + cache kosong) → fallback dummy
            print("[Portfolio] allData kosong → fallback dummy")
            await fetchDataFallback()
            isLoading = false
            return
        }

        let dataMap = Dictionary(uniqueKeysWithValues: allData.map { ($0.symbol, $0) })
        print("[Portfolio] dataMap keys:", dataMap.keys.sorted())

        // Fetch detail (sentiment) semua saham secara paralel
        let symbols = holdings.map { $0.symbol }
        let details: [String: StockDetail] = await withTaskGroup(of: (String, StockDetail?).self) { group in
            for symbol in symbols {
                group.addTask {
                    let detail = try? await self.realService.fetchDetail(symbol: symbol)
                    return (symbol, detail)
                }
            }
            var result: [String: StockDetail] = [:]
            for await (symbol, detail) in group {
                if let d = detail { result[symbol] = d }
            }
            return result
        }

        var temp: [PortfolioItem] = []
        for holding in holdings {
            guard let data = dataMap[holding.symbol] else {
                print("[Portfolio] SKIP:", holding.symbol, "tidak ada di dataMap")
                continue
            }
            let sentiment = details[holding.symbol].map {
                Sentiment.from(dbValue: $0.sentiment.rawValue, score: $0.score)
            } ?? makeSentiment(for: data.percentChange)
            temp.append(PortfolioItem(
                symbol:        data.symbol,
                name:          data.name,
                logo:          data.logo,
                price:         data.price,
                change:        data.change,
                percentChange: data.percentChange,
                quantity:      holding.quantity,
                sentiment:     sentiment
            ))
        }
        print("[Portfolio] items terbentuk:", temp.count)

        items     = temp
        isLoading = false
    }
}
