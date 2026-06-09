//
//  DummyData.swift
//  SahamIndo
//
//  Berisi semua data dummy yang dibutuhkan UI:
//  - PortfolioItem        → HomeView (StockListView, StockRowView)
//  - StockMarketData      → fallback / preview service
//  - StockDetail          → AIInsightCard di StockDetailView
//  - StockDataPoint       → StockChartViewModel (semua TimeRange)
//  - PortfolioValuePoint  → PortfolioHistoryChart
//
//  Cara pakai preview:
//    .environmentObject(PortfolioViewModel(service: DummyStockService()))
//  atau langsung inject DummyData.portfolioItems ke View preview.
//

import SwiftUI

// ─────────────────────────────────────────────────────────────
// MARK: - DummyData  (namespace utama)
// ─────────────────────────────────────────────────────────────

enum DummyData {

    // MARK: - 1. PortfolioItem  (dipakai HomeView + StockDetailView)

    static let portfolioItems: [PortfolioItem] = [
        PortfolioItem(
            symbol:        "BBCA",
            name:          "Bank Central Asia",
            logo:          nil,
            price:         9_950,
            change:        +75,
            percentChange: +0.76,
            quantity:      1_000,
            sentiment:     Sentiment(buy: 0.65, hold: 0.25, sell: 0.10)
        ),
        PortfolioItem(
            symbol:        "BBRI",
            name:          "Bank Rakyat Indonesia",
            logo:          nil,
            price:         4_150,
            change:        -40,
            percentChange: -0.95,
            quantity:      2_000,
            sentiment:     Sentiment(buy: 0.15, hold: 0.25, sell: 0.60)
        ),
        PortfolioItem(
            symbol:        "BMRI",
            name:          "Bank Mandiri",
            logo:          nil,
            price:         5_675,
            change:        +75,
            percentChange: +1.34,
            quantity:      1_500,
            sentiment:     Sentiment(buy: 0.65, hold: 0.25, sell: 0.10)
        ),
        PortfolioItem(
            symbol:        "BREN",
            name:          "Barito Renewables Energy",
            logo:          nil,
            price:         5_025,
            change:        +50,
            percentChange: +1.01,
            quantity:      500,
            sentiment:     Sentiment(buy: 0.65, hold: 0.25, sell: 0.10)
        ),
        PortfolioItem(
            symbol:        "TPIA",
            name:          "Chandra Asri Pacific",
            logo:          nil,
            price:         8_650,
            change:        +150,
            percentChange: +1.76,
            quantity:      300,
            sentiment:     Sentiment(buy: 0.65, hold: 0.25, sell: 0.10)
        ),
        PortfolioItem(
            symbol:        "AMMN",
            name:          "Amman Mineral Internasional",
            logo:          nil,
            price:         9_200,
            change:        +100,
            percentChange: +1.10,
            quantity:      200,
            sentiment:     Sentiment(buy: 0.35, hold: 0.40, sell: 0.25)
        ),
        PortfolioItem(
            symbol:        "BYAN",
            name:          "Bayan Resources",
            logo:          nil,
            price:         18_500,
            change:        -250,
            percentChange: -1.33,
            quantity:      100,
            sentiment:     Sentiment(buy: 0.15, hold: 0.25, sell: 0.60)
        ),
        PortfolioItem(
            symbol:        "DCII",
            name:          "DCI Indonesia",
            logo:          nil,
            price:         43_000,
            change:        +500,
            percentChange: +1.18,
            quantity:      50,
            sentiment:     Sentiment(buy: 0.65, hold: 0.25, sell: 0.10)
        ),
        PortfolioItem(
            symbol:        "DSSA",
            name:          "Dian Swastatika Sentosa",
            logo:          nil,
            price:         55_750,
            change:        +750,
            percentChange: +1.36,
            quantity:      20,
            sentiment:     Sentiment(buy: 0.35, hold: 0.40, sell: 0.25)
        ),
        PortfolioItem(
            symbol:        "TLKM",
            name:          "Telkom Indonesia",
            logo:          nil,
            price:         3_020,
            change:        -30,
            percentChange: -0.98,
            quantity:      5_000,
            sentiment:     Sentiment(buy: 0.35, hold: 0.40, sell: 0.25)
        ),
    ]

    // MARK: - 2. StockMarketData  (dipakai DummyStockService / fallback)

    static let stockMarketData: [StockMarketData] = portfolioItems.map {
        StockMarketData(
            symbol:        $0.symbol,
            name:          $0.name,
            logo:          $0.logo,
            price:         $0.price,
            change:        $0.change,
            percentChange: $0.percentChange
        )
    }

    // MARK: - 3. StockDetail  (dipakai AIInsightCard di StockDetailView)
    //   → GET /stocks/{symbol}/detail

    static let stockDetails: [String: StockDetail] = [
        "BBCA": StockDetail(
            symbol:    "BBCA",
            name:      "Bank Central Asia",
            sector:    "Perbankan",
            sentiment: .recommended,
            aiSummary: "BBCA mencatat NIM stabil di 5,6% dengan NPL gross 1,9%. Pertumbuhan kredit 12% YoY terutama ditopang segmen konsumer dan KPR. Kapitalisasi modal CET1 18,2% jauh di atas batas minimum regulator. Dividen yield diproyeksikan 3,1%.",
            price:     9_950,
            change:    +75,
            pctChange: +0.76
        ),
        "BBRI": StockDetail(
            symbol:    "BBRI",
            name:      "Bank Rakyat Indonesia",
            sector:    "Perbankan",
            sentiment: .caution,
            aiSummary: "BBRI menghadapi tekanan NIM akibat kenaikan biaya dana di tengah suku bunga tinggi. NPL segmen mikro naik tipis ke 3,1%. Restrukturisasi kredit UMKM pasca-pandemi masih berjalan. Namun valuasi PBV 1,8x dinilai wajar jika target kredit 2026 tercapai.",
            price:     4_150,
            change:    -40,
            pctChange: -0.95
        ),
        "BMRI": StockDetail(
            symbol:    "BMRI",
            name:      "Bank Mandiri",
            sector:    "Perbankan",
            sentiment: .recommended,
            aiSummary: "BMRI membukukan ROE 18,9% tertinggi di antara bank BUMN. Kredit infrastruktur tumbuh 19% YoY seiring proyek PSN. Fee-based income naik 24% didorong transaksi digital Livin yang kini memiliki 28 juta pengguna aktif bulanan.",
            price:     5_675,
            change:    +75,
            pctChange: +1.34
        ),
        "BREN": StockDetail(
            symbol:    "BREN",
            name:      "Barito Renewables Energy",
            sector:    "Energi",
            sentiment: .recommended,
            aiSummary: "BREN membukukan pertumbuhan pendapatan energi terbarukan sebesar 34% YoY didorong oleh ekspansi kapasitas PLTS. Rasio utang terhadap ekuitas terjaga di 0,4x. Analis memperkirakan kenaikan laba bersih 28% untuk FY2026 seiring pipeline proyek yang kuat.",
            price:     5_025,
            change:    +50,
            pctChange: +1.01
        ),
        "TPIA": StockDetail(
            symbol:    "TPIA",
            name:      "Chandra Asri Pacific",
            sector:    "Kimia",
            sentiment: .recommended,
            aiSummary: "TPIA diuntungkan lonjakan margin petrokimia seiring penurunan harga naphtha. Proyek Chandra Asri 2 berkapasitas 4,3 juta ton/tahun dijadwalkan onstream Q3-2027. Potensi re-rating signifikan jika siklus petrokimia membaik.",
            price:     8_650,
            change:    +150,
            pctChange: +1.76
        ),
        "AMMN": StockDetail(
            symbol:    "AMMN",
            name:      "Amman Mineral Internasional",
            sector:    "Pertambangan",
            sentiment: .neutral,
            aiSummary: "AMMN membukukan produksi tembaga 120 ribu ton di semester pertama, sesuai guidance tahunan. Proyek smelter domestik berjalan on-schedule. Risiko utama adalah fluktuasi harga LME tembaga dan regulasi ekspor mineral.",
            price:     9_200,
            change:    +100,
            pctChange: +1.10
        ),
        "BYAN": StockDetail(
            symbol:    "BYAN",
            name:      "Bayan Resources",
            sector:    "Batubara",
            sentiment: .caution,
            aiSummary: "BYAN tertekan penurunan harga batubara kalori tinggi yang turun 22% dari puncak 2023. Meski demikian, strip ratio yang rendah (4,2x) menjaga EBITDA margin di atas 40%. Manajemen berencana buyback saham senilai Rp500 miliar.",
            price:     18_500,
            change:    -250,
            pctChange: -1.33
        ),
        "DCII": StockDetail(
            symbol:    "DCII",
            name:      "DCI Indonesia",
            sector:    "Teknologi",
            sentiment: .recommended,
            aiSummary: "DCII mencatat occupancy rate data center 94% dengan pipeline kontrak baru dari hyperscaler global. Ekspansi Karawang Phase-3 (32 MW) akan onstream Q4-2026. Pertumbuhan pendapatan recurring 41% YoY menjadikannya growth stock terkuat di sektor teknologi IDX.",
            price:     43_000,
            change:    +500,
            pctChange: +1.18
        ),
        "DSSA": StockDetail(
            symbol:    "DSSA",
            name:      "Dian Swastatika Sentosa",
            sector:    "Energi",
            sentiment: .neutral,
            aiSummary: "DSSA mencatatkan laba operasional yang stabil meski tekanan harga batubara global masih berlanjut. Diversifikasi bisnis ke segmen logistik dan properti mulai memberikan kontribusi 18% terhadap total pendapatan.",
            price:     55_750,
            change:    +750,
            pctChange: +1.36
        ),
        "TLKM": StockDetail(
            symbol:    "TLKM",
            name:      "Telkom Indonesia",
            sector:    "Telekomunikasi",
            sentiment: .neutral,
            aiSummary: "TLKM menghadapi tekanan ARPU IndiHome di tengah persaingan fixed broadband yang semakin ketat. Segmen Telkomsel masih solid dengan market share 53%. Transformasi digital B2B melalui Telkom Sigma berpotensi menjadi pendorong pendapatan baru.",
            price:     3_020,
            change:    -30,
            pctChange: -0.98
        ),
    ]

    // MARK: - 4. StockDataPoint  (dipakai StockChartViewModel semua TimeRange)

    /// Generate candle dummy untuk satu saham + satu TimeRange.
    /// Wrapper tipis ke IDXDummyPriceGenerator agar preview tidak perlu
    /// import / memanggil generator secara langsung.
    static func candles(symbol: String, range: TimeRange) -> [StockDataPoint] {
        IDXDummyPriceGenerator.generate(symbol: symbol, range: range)
    }

    // MARK: - 5. PortfolioValuePoint  (dipakai PortfolioHistoryChart)

    static func portfolioHistory(days: Int = 360) -> [PortfolioValuePoint] {
        PortfolioValuePoint.generate(from: portfolioItems, days: days)
    }
}

// ─────────────────────────────────────────────────────────────
// MARK: - DummyDetailService  (dipakai StockDetailView preview)
// ─────────────────────────────────────────────────────────────
//
// Mengembalikan StockDetail dari dictionary di atas, tanpa network.
// Inject ke RealStockService bisa disiasati dengan
// override / mock — atau gunakan langsung di preview:
//
//   Task { chartVM.dataPoints = DummyData.candles(symbol: "BBCA", range: .oneDay) }
//

final class DummyDetailService {

    func fetchDetail(symbol: String) async -> StockDetail {
        // Simulasi sedikit delay
        try? await Task.sleep(nanoseconds: 80_000_000)
        return DummyData.stockDetails[symbol] ?? StockDetail(
            symbol:    symbol,
            name:      symbol,
            sector:    nil,
            sentiment: .neutral,
            aiSummary: "Tidak ada ringkasan AI untuk \(symbol).",
            price:     0,
            change:    0,
            pctChange: 0
        )
    }
}

// ─────────────────────────────────────────────────────────────
// MARK: - DummyChartService  (dipakai preview StockChartViewModel)
// ─────────────────────────────────────────────────────────────

final class DummyChartService {

    func fetchCandles(symbol: String, range: TimeRange) async -> [StockDataPoint] {
        try? await Task.sleep(nanoseconds: 50_000_000)
        return IDXDummyPriceGenerator.generate(symbol: symbol, range: range)
    }
}

// ─────────────────────────────────────────────────────────────
// MARK: - Preview Helpers  (shortcut untuk #Preview blocks)
// ─────────────────────────────────────────────────────────────

extension PortfolioViewModel {

    /// PortfolioViewModel yang sudah di-prefill dengan data dummy —
    /// tidak perlu hit API. Gunakan di #Preview.
    static var preview: PortfolioViewModel {
        let vm = PortfolioViewModel(service: DummyStockService())
        // Inject items langsung lewat published var (internal setter)
        // Karena items adalah private(set), gunakan reflection-free trick:
        // buat subclass atau expose setter via extension di debug build.
        //
        // Alternatif paling sederhana: panggil fetchData() di .task { }
        // di dalam #Preview — DummyStockService sudah mengembalikan data statis.
        return vm
    }
}

// ─────────────────────────────────────────────────────────────
// MARK: - Quick Preview Data  (1 item untuk single-stock preview)
// ─────────────────────────────────────────────────────────────

extension DummyData {

    static func item(symbol: String) -> PortfolioItem {
        portfolioItems.first { $0.symbol == symbol } ?? portfolioItems[0]
    }

    /// Semua TimeRange dengan dummy candle untuk satu simbol — berguna untuk
    /// grid-preview yang menampilkan semua range sekaligus.
    static func allRangeCandles(symbol: String) -> [TimeRange: [StockDataPoint]] {
        Dictionary(uniqueKeysWithValues:
            TimeRange.allCases.map { range in
                (range, IDXDummyPriceGenerator.generate(symbol: symbol, range: range))
            }
        )
    }
}

// ─────────────────────────────────────────────────────────────
// MARK: - #Preview Contoh
// ─────────────────────────────────────────────────────────────

#if DEBUG

#Preview("HomeView — Dummy") {
    NavigationStack {
        HomeView()
            .environmentObject(PortfolioViewModel(service: DummyStockService()))
            .environmentObject(Router())
            .environmentObject(ChatbotViewModel())
    }
}

#Preview("StockDetailView — BBCA") {
    let item = DummyData.item(symbol: "BBCA")
    NavigationStack {
        StockDetailView(item: item)
            .environmentObject(PortfolioViewModel(service: DummyStockService()))
            .environmentObject(Router())
            .environmentObject(ChatbotViewModel())
    }
}

#Preview("PortfolioHistoryChart — 360 hari") {
    let history = DummyData.portfolioHistory(days: 360)
    PortfolioHistoryChart(data: history)
        .frame(height: 260)
        .padding()
        .background(Color(hex: "12112e"))
}

#endif
