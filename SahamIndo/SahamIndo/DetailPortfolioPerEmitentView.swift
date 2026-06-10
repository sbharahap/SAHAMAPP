//
//  DetailPortfolioPerEmitentView.swift
//  SahamIndo
//

import SwiftUI

struct DetailPortfolioPerEmitentView: View {

    let item: PortfolioItem

    @EnvironmentObject private var vm: PortfolioViewModel
    @EnvironmentObject private var router: Router

    @State private var showTradeSheet = false

    private let accent  = Color(hex: "FFA500")
    private let green   = Color(hex: "22C55E")
    private let red     = Color(hex: "EF4444")
    private let cardBg  = Color.appCardBackground
    private let bgColor = Color.appBackground

    // MARK: - Derived holding data

    private var holding: Holding? {
        vm.holdings.first(where: { $0.symbol == item.symbol })
    }

    private var hasPurchaseDate: Bool { holding?.purchaseDate != nil }

    private var purchaseDate: Date {
        holding?.purchaseDate
            ?? Calendar.current.date(byAdding: .day, value: -30, to: Date())!
    }

    private var costBasis: Double { holding?.totalCostBasis ?? 0 }

    private var avgBuyPrice: Double {
        guard item.quantity > 0 else { return 0 }
        return costBasis / item.quantity
    }

    private var profitIDR: Double { item.value - costBasis }

    private var profitPct: Double {
        guard costBasis > 0 else { return 0 }
        return (profitIDR / costBasis) * 100
    }

    private var chartData: [PortfolioValuePoint] {
        guard item.quantity > 0 else { return [] }
        return PortfolioValuePoint.generateForHolding(
            item: item,
            purchaseDate: purchaseDate,
            costBasis: max(costBasis, 1)
        )
    }

    // MARK: - Body

    private var tradeRecords: [TradeRecord] {
        vm.tradeHistory.filter { $0.symbol == item.symbol }
    }

    var body: some View {
        ScrollView {
            VStack(spacing: 16) {
                stockHeaderCard
                chartSection
                holdingDetailsCard
                if !tradeRecords.isEmpty {
                    tradeHistorySection
                }
                actionButtons
            }
            .padding(16)
            .padding(.bottom, 24)
        }
        .background(bgColor.ignoresSafeArea())
        .navigationTitle(item.symbol)
        .navigationBarTitleDisplayMode(.inline)
        .sheet(isPresented: $showTradeSheet) {
            TradeSheetView(stock: item)
                .presentationDetents([.large])
                .environmentObject(vm)
        }
    }

    // MARK: - Stock Header Card

    private var stockHeaderCard: some View {
        VStack(spacing: 12) {
            HStack(spacing: 12) {
                StockAvatarView(symbol: item.symbol)

                VStack(alignment: .leading, spacing: 3) {
                    Text(item.symbol)
                        .font(.system(size: 18, weight: .bold))
                        .foregroundColor(.primary)
                    Text(item.name ?? "-")
                        .font(.system(size: 11))
                        .foregroundColor(.secondary)
                        .lineLimit(1)
                }

                Spacer()

                VStack(alignment: .trailing, spacing: 3) {
                    Text(formatIDR(item.price))
                        .font(.system(size: 16, weight: .bold, design: .rounded))
                        .foregroundColor(.primary)
                    HStack(spacing: 3) {
                        Image(systemName: item.percentChange >= 0 ? "arrow.up.right" : "arrow.down.right")
                            .font(.system(size: 8, weight: .bold))
                        Text(String(format: "%+.2f%%", item.percentChange))
                            .font(.system(size: 11, weight: .bold))
                    }
                    .foregroundColor(item.percentChange >= 0 ? green : red)
                    .padding(.horizontal, 7).padding(.vertical, 3)
                    .background((item.percentChange >= 0 ? green : red).opacity(0.12))
                    .clipShape(Capsule())
                }
            }

            Rectangle().fill(Color.primary.opacity(0.08)).frame(height: 1)

            HStack(alignment: .bottom) {
                VStack(alignment: .leading, spacing: 2) {
                    Text("Nilai Kepemilikan")
                        .font(.system(size: 10))
                        .foregroundColor(.secondary)
                    Text(formatIDR(item.value))
                        .font(.system(size: 24, weight: .bold, design: .rounded))
                        .foregroundColor(.primary)
                }
                Spacer()
                VStack(alignment: .trailing, spacing: 2) {
                    Text("Profit / Loss")
                        .font(.system(size: 10))
                        .foregroundColor(.secondary)
                    Text(profitIDR >= 0 ? "+\(formatIDR(profitIDR))" : formatIDR(profitIDR))
                        .font(.system(size: 15, weight: .bold, design: .rounded))
                        .foregroundColor(profitIDR >= 0 ? green : red)
                    Text(String(format: "%+.2f%%", profitPct))
                        .font(.system(size: 10, weight: .semibold))
                        .foregroundColor(profitIDR >= 0 ? green : red)
                }
            }
        }
        .padding(16)
        .background(cardBg)
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .overlay(RoundedRectangle(cornerRadius: 16).stroke(Color.primary.opacity(0.08), lineWidth: 1))
    }

    // MARK: - Chart Section

    @ViewBuilder
    private var chartSection: some View {
        if !chartData.isEmpty {
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Text("Grafik Nilai Kepemilikan")
                        .font(.system(size: 13, weight: .bold))
                        .foregroundColor(.primary)
                    Spacer()
                    if !hasPurchaseDate {
                        HStack(spacing: 3) {
                            Image(systemName: "info.circle")
                                .font(.system(size: 9))
                            Text("Estimasi 30 hari")
                                .font(.system(size: 9, weight: .medium))
                        }
                        .foregroundColor(.secondary)
                    }
                }

                PortfolioHistoryChart(data: chartData)
                    .background(cardBg)
                    .clipShape(RoundedRectangle(cornerRadius: 16))
                    .overlay(
                        RoundedRectangle(cornerRadius: 16)
                            .stroke(Color.primary.opacity(0.08), lineWidth: 1)
                    )
            }
        }
    }

    // MARK: - Holding Details Card

    private var holdingDetailsCard: some View {
        VStack(spacing: 12) {
            HStack {
                Text("Detail Kepemilikan")
                    .font(.system(size: 14, weight: .bold))
                    .foregroundColor(.primary)
                Spacer()
            }

            Rectangle().fill(Color.primary.opacity(0.08)).frame(height: 1)

            VStack(spacing: 10) {
                infoRow(label: "Jumlah Saham",
                        value: "\(Int(item.quantity)) lembar (\(Int(item.quantity / 100)) Lot)")
                infoRow(label: "Harga Rata-Rata Beli", value: formatIDR(avgBuyPrice))
                infoRow(label: "Total Modal",          value: formatIDR(costBasis))
                infoRow(label: "Nilai Pasar Saat Ini", value: formatIDR(item.value))

                Rectangle().fill(Color.primary.opacity(0.08)).frame(height: 1)

                HStack {
                    Text("Profit / Loss")
                        .font(.system(size: 12))
                        .foregroundColor(.secondary)
                    Spacer()
                    VStack(alignment: .trailing, spacing: 1) {
                        Text(profitIDR >= 0 ? "+\(formatIDR(profitIDR))" : formatIDR(profitIDR))
                            .font(.system(size: 13, weight: .bold, design: .rounded))
                            .foregroundColor(profitIDR >= 0 ? green : red)
                        Text(String(format: "%+.2f%%", profitPct))
                            .font(.system(size: 10, weight: .semibold))
                            .foregroundColor(profitIDR >= 0 ? green : red)
                    }
                }

                if let pd = holding?.purchaseDate {
                    infoRow(label: "Tanggal Pertama Beli", value: formatDate(pd))

                    let daysSince = Calendar.current.dateComponents([.day], from: pd, to: Date()).day ?? 0
                    infoRow(label: "Lama Kepemilikan", value: "\(daysSince) hari")
                }
            }
        }
        .padding(16)
        .background(cardBg)
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .overlay(RoundedRectangle(cornerRadius: 16).stroke(Color.primary.opacity(0.08), lineWidth: 1))
    }

    // MARK: - Action Buttons

    private var actionButtons: some View {
        HStack(spacing: 12) {
            
            Button(action: { router.push(.stockDetail(item)) }) {
                HStack(spacing: 6) {
                    Image(systemName: "chart.line.uptrend.xyaxis")
                    Text("See Details")
                }
                .font(.system(size: 14, weight: .bold))
                .foregroundColor(accent)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 14)
                .background(cardBg)
                .cornerRadius(12)
                .overlay(
                    RoundedRectangle(cornerRadius: 12)
                        .stroke(accent.opacity(0.35), lineWidth: 1)
                )
            }
            Button(action: { showTradeSheet = true }) {
                HStack(spacing: 6) {
                    Image(systemName: "arrow.left.arrow.right")
                    Text("Transaksi")
                }
                .font(.system(size: 14, weight: .bold))
                .foregroundColor(.black)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 14)
                .background(accent)
                .cornerRadius(12)
            }
        }
    }

    // MARK: - Trade History Section

    private var tradeHistorySection: some View {
        VStack(spacing: 12) {
            HStack {
                Text("Riwayat Transaksi")
                    .font(.system(size: 14, weight: .bold))
                    .foregroundColor(.primary)
                Spacer()
                Text("\(tradeRecords.count) transaksi")
                    .font(.system(size: 11))
                    .foregroundColor(.secondary)
            }

            Rectangle().fill(Color.primary.opacity(0.08)).frame(height: 1)

            VStack(spacing: 0) {
                ForEach(tradeRecords) { record in
                    VStack(spacing: 0) {
                        HStack(spacing: 12) {
                            // Type badge
                            Text(record.type == .buy ? "BELI" : "JUAL")
                                .font(.system(size: 10, weight: .bold))
                                .foregroundColor(record.type == .buy ? .black : .white)
                                .padding(.horizontal, 8).padding(.vertical, 4)
                                .background(record.type == .buy ? accent : red)
                                .clipShape(Capsule())

                            VStack(alignment: .leading, spacing: 2) {
                                Text("\(Int(record.quantity)) lembar @ \(formatIDR(record.price))")
                                    .font(.system(size: 12, weight: .semibold))
                                    .foregroundColor(.primary)
                                Text(formatDateTime(record.date))
                                    .font(.system(size: 10))
                                    .foregroundColor(.secondary)
                            }

                            Spacer()

                            VStack(alignment: .trailing, spacing: 2) {
                                Text(record.type == .buy ? "-\(formatIDR(record.totalAmount))" : "+\(formatIDR(record.totalAmount))")
                                    .font(.system(size: 12, weight: .bold, design: .rounded))
                                    .foregroundColor(record.type == .buy ? red : green)
                                Text("fee \(formatIDR(record.fee))")
                                    .font(.system(size: 9))
                                    .foregroundColor(.secondary)
                            }
                        }
                        .padding(.vertical, 10)

                        if record.id != tradeRecords.last?.id {
                            Rectangle().fill(Color.primary.opacity(0.06)).frame(height: 1)
                        }
                    }
                }
            }
        }
        .padding(16)
        .background(cardBg)
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .overlay(RoundedRectangle(cornerRadius: 16).stroke(Color.primary.opacity(0.08), lineWidth: 1))
    }

    // MARK: - Helpers

    private func infoRow(label: String, value: String) -> some View {
        HStack {
            Text(label)
                .font(.system(size: 12))
                .foregroundColor(.secondary)
            Spacer()
            Text(value)
                .font(.system(size: 12, weight: .semibold))
                .foregroundColor(.primary)
        }
    }

    private func formatDate(_ date: Date) -> String {
        let f = DateFormatter()
        f.dateFormat = "d MMMM yyyy"
        f.locale = Locale(identifier: "id_ID")
        return f.string(from: date)
    }

    private func formatDateTime(_ date: Date) -> String {
        let f = DateFormatter()
        f.dateFormat = "d MMM yyyy, HH:mm"
        f.locale = Locale(identifier: "id_ID")
        return f.string(from: date)
    }
}
