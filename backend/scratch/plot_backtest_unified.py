import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

def main():
    data_dir = "/Users/satriabaladewaharahap/Downloads/SAHAMAPP/backend/scratch"
    csv_path = os.path.join(data_dir, "backtest_unified_results.csv")
    artifact_dir = "/Users/satriabaladewaharahap/.gemini/antigravity-ide/brain/85414e74-7f32-4a34-98f1-6bf79908bc9d"
    
    if not os.path.exists(csv_path):
        print("❌ CSV results not found!")
        return
        
    df = pd.read_csv(csv_path)
    df["tanggal"] = pd.to_datetime(df["tanggal"])
    df.set_index("tanggal", inplace=True)
    
    # Normalize to Billion IDR
    df = df / 1e9
    
    # Style configuration for a premium dark mode look
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(15, 9), dpi=150)
    fig.patch.set_facecolor('#0f172a')  # Slate 900
    ax.set_facecolor('#0f172a')
    
    # Plotting: Solid lines for Optimal/Buffered, Dotted/Dashed for Original/Benchmark
    # 1. Value Investing (Teal)
    ax.plot(df.index, df["Investing_Optimal"], color='#14b8a6', label='Value Investing (Optimal: Buffer 8)', linewidth=3.2) # Teal 500
    ax.plot(df.index, df["Investing_Old"], color='#99f6e4', label='Value Investing (Original)', linewidth=1.5, linestyle=':') # Teal 200
    
    # 2. Swing Trading (Orange)
    ax.plot(df.index, df["Trading_Optimal"], color='#f97316', label='Swing Trading (Optimal: Buffer 10)', linewidth=2.8) # Orange 500
    ax.plot(df.index, df["Trading_Old"], color='#ffedd5', label='Swing Trading (Original)', linewidth=1.2, linestyle=':') # Orange 100
    
    # 3. Hybrid (Purple)
    ax.plot(df.index, df["Hybrid_Optimal"], color='#8b5cf6', label='Hybrid (Optimal: Buffer 8)', linewidth=2.5) # Purple 500
    ax.plot(df.index, df["Hybrid_Old"], color='#ddd6fe', label='Hybrid (Original)', linewidth=1.2, linestyle=':') # Purple 200
    
    # 4. IHSG Benchmark (Slate)
    ax.plot(df.index, df["IHSG"], color='#64748b', label='IHSG (Benchmark)', linewidth=1.8, linestyle='--') # Slate 500
    
    # Titles & Labels
    ax.set_title("Analisis Konsolidasi Performa Portofolio Saham AI (2022 - 2025)\nPerbandingan Strategi Original vs Optimal/Buffered", 
                 fontsize=17, fontweight='bold', color='#f8fafc', pad=20)
    
    ax.set_xlabel("Tanggal", fontsize=11, color='#cbd5e1', labelpad=10)
    ax.set_ylabel("Nilai Portofolio (Miliar Rupiah)", fontsize=11, color='#cbd5e1', labelpad=10)
    
    # Grid styling
    ax.grid(True, which='both', color='#1e293b', linestyle=':', linewidth=0.8)
    
    # Format axes
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    plt.xticks(rotation=30, color='#cbd5e1')
    plt.yticks(color='#cbd5e1')
    
    # Legend
    legend = ax.legend(loc='upper left', frameon=True, facecolor='#1e293b', edgecolor='#334155', fontsize=9, ncol=2)
    for text in legend.get_texts():
        text.color = '#f8fafc'
        
    # Remove outer spines
    for spine in ['top', 'right', 'left', 'bottom']:
        ax.spines[spine].set_visible(False)
        
    # Annotate final values on the right
    last_date = df.index[-1]
    ax.annotate(f"Inv Opt: Rp {df['Investing_Optimal'].iloc[-1]:.2f} B", xy=(last_date, df['Investing_Optimal'].iloc[-1]), xytext=(10, 8), textcoords='offset points', color='#14b8a6', fontweight='bold', fontsize=9)
    ax.annotate(f"Inv Old: Rp {df['Investing_Old'].iloc[-1]:.2f} B", xy=(last_date, df['Investing_Old'].iloc[-1]), xytext=(10, -5), textcoords='offset points', color='#99f6e4', fontsize=8)
    
    ax.annotate(f"Trad Opt: Rp {df['Trading_Optimal'].iloc[-1]:.2f} B", xy=(last_date, df['Trading_Optimal'].iloc[-1]), xytext=(10, 5), textcoords='offset points', color='#f97316', fontweight='bold', fontsize=9)
    ax.annotate(f"Trad Old: Rp {df['Trading_Old'].iloc[-1]:.2f} B", xy=(last_date, df['Trading_Old'].iloc[-1]), xytext=(10, 0), textcoords='offset points', color='#ffedd5', fontsize=8)
    
    ax.annotate(f"Hyb Opt: Rp {df['Hybrid_Optimal'].iloc[-1]:.2f} B", xy=(last_date, df['Hybrid_Optimal'].iloc[-1]), xytext=(10, 5), textcoords='offset points', color='#8b5cf6', fontweight='bold', fontsize=8)
    ax.annotate(f"Hyb Old: Rp {df['Hybrid_Old'].iloc[-1]:.2f} B", xy=(last_date, df['Hybrid_Old'].iloc[-1]), xytext=(10, -5), textcoords='offset points', color='#ddd6fe', fontsize=8)
    
    ax.annotate(f"IHSG: Rp {df['IHSG'].iloc[-1]:.2f} B", xy=(last_date, df['IHSG'].iloc[-1]), xytext=(10, 0), textcoords='offset points', color='#64748b', fontweight='bold', fontsize=9)
    
    plt.tight_layout()
    
    # Save targets
    out_scratch = os.path.join(data_dir, "backtest_unified_chart.png")
    out_artifact = os.path.join(artifact_dir, "backtest_unified_chart.png")
    
    plt.savefig(out_scratch, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.savefig(out_artifact, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.close()
    
    print(f"📊 Unified chart plotted and saved to:\n  - {out_scratch}\n  - {out_artifact}")

if __name__ == "__main__":
    main()
