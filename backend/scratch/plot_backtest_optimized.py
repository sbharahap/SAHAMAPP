import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

def main():
    data_dir = "/Users/satriabaladewaharahap/Downloads/SAHAMAPP/backend/scratch"
    csv_path = os.path.join(data_dir, "backtest_opt_results.csv")
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
    fig, ax = plt.subplots(figsize=(14, 8), dpi=150)
    fig.patch.set_facecolor('#0f172a')  # Slate 900
    ax.set_facecolor('#0f172a')
    
    # Plotting: Solid lines for Optimized, Dashed/Dotted lines for Old versions
    # 1. Value Investing (Teal)
    ax.plot(df.index, df["Investing_Opt"], color='#0d9488', label='Value Investing (Optimized)', linewidth=3.0) # Solid Teal 600
    ax.plot(df.index, df["Investing_Old"], color='#5eead4', label='Value Investing (Old)', linewidth=1.5, linestyle=':') # Dotted Teal 300
    
    # 2. Hybrid (Purple)
    ax.plot(df.index, df["Hybrid_Opt"], color='#7c3aed', label='Hybrid Strategy (Optimized)', linewidth=2.5) # Solid Purple 600
    ax.plot(df.index, df["Hybrid_Old"], color='#c084fc', label='Hybrid Strategy (Old)', linewidth=1.2, linestyle=':') # Dotted Purple 400
    
    # 3. Trading (Orange)
    ax.plot(df.index, df["Trading_Opt"], color='#ea580c', label='Swing Trading (Optimized)', linewidth=2.5) # Solid Orange 600
    ax.plot(df.index, df["Trading_Old"], color='#ffedd5', label='Swing Trading (Old)', linewidth=1.2, linestyle=':') # Dotted Orange 100
    
    # 4. IHSG (Slate)
    ax.plot(df.index, df["IHSG"], color='#64748b', label='IHSG (Benchmark)', linewidth=1.8, linestyle='--') # Dashed Slate 500
    
    # Titles & Labels
    ax.set_title("Analisis Sensitivitas Portofolio Saham AI (2022 - 2025)\nPerbandingan Fitur Sebelum vs Sesudah Optimasi", 
                 fontsize=16, fontweight='bold', color='#f8fafc', pad=20)
    
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
    ax.annotate(f"Inv Opt: Rp {df['Investing_Opt'].iloc[-1]:.2f} B", xy=(last_date, df['Investing_Opt'].iloc[-1]), xytext=(10, 5), textcoords='offset points', color='#0d9488', fontweight='bold', fontsize=9)
    ax.annotate(f"Inv Old: Rp {df['Investing_Old'].iloc[-1]:.2f} B", xy=(last_date, df['Investing_Old'].iloc[-1]), xytext=(10, -5), textcoords='offset points', color='#5eead4', fontsize=8)
    ax.annotate(f"Trad Opt: Rp {df['Trading_Opt'].iloc[-1]:.2f} B", xy=(last_date, df['Trading_Opt'].iloc[-1]), xytext=(10, 0), textcoords='offset points', color='#ea580c', fontweight='bold', fontsize=9)
    ax.annotate(f"IHSG: Rp {df['IHSG'].iloc[-1]:.2f} B", xy=(last_date, df['IHSG'].iloc[-1]), xytext=(10, 0), textcoords='offset points', color='#64748b', fontweight='bold', fontsize=9)
    ax.annotate(f"Hyb Opt: Rp {df['Hybrid_Opt'].iloc[-1]:.2f} B", xy=(last_date, df['Hybrid_Opt'].iloc[-1]), xytext=(10, 5), textcoords='offset points', color='#7c3aed', fontweight='bold', fontsize=9)
    ax.annotate(f"Hyb Old: Rp {df['Hybrid_Old'].iloc[-1]:.2f} B", xy=(last_date, df['Hybrid_Old'].iloc[-1]), xytext=(10, -5), textcoords='offset points', color='#c084fc', fontsize=8)
    ax.annotate(f"Trad Old: Rp {df['Trading_Old'].iloc[-1]:.2f} B", xy=(last_date, df['Trading_Old'].iloc[-1]), xytext=(10, 0), textcoords='offset points', color='#ffedd5', fontsize=8)
    
    plt.tight_layout()
    
    # Save targets
    out_scratch = os.path.join(data_dir, "backtest_opt_chart.png")
    out_artifact = os.path.join(artifact_dir, "backtest_opt_chart.png")
    
    plt.savefig(out_scratch, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.savefig(out_artifact, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.close()
    
    print(f"📊 Chart successfully plotted and saved to:\n  - {out_scratch}\n  - {out_artifact}")

if __name__ == "__main__":
    main()
