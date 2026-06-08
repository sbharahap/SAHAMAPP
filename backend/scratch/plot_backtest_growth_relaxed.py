import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

def main():
    data_dir = "/Users/satriabaladewaharahap/Downloads/SAHAMAPP/backend/scratch"
    csv_path = os.path.join(data_dir, "backtest_growth_relaxed_results.csv")
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
    
    # Plotting
    ax.plot(df.index, df["Inv_Growth_Relaxed"], color='#06b6d4', label='Value Investing (Growth Relaxed: >25% / <-15%)', linewidth=3.2) # Bright Cyan
    ax.plot(df.index, df["Inv_Static"], color='#14b8a6', label='Value Investing (Static Optimal)', linewidth=2.0) # Teal 500
    ax.plot(df.index, df["Inv_Growth_Strict"], color='#99f6e4', label='Value Investing (Growth Strict)', linewidth=1.2, linestyle=':') # Teal 200
    ax.plot(df.index, df["IHSG"], color='#64748b', label='IHSG (Benchmark)', linewidth=1.8, linestyle='--') # Slate 500
    
    # Titles & Labels
    ax.set_title("Analisis Sensitivitas Pelonggaran Batas Tren Kuartal Laba Bersih (2022 - 2025)\nDampak Penyaringan Kebisingan Akuntansi terhadap Portofolio Value Investing", 
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
    legend = ax.legend(loc='upper left', frameon=True, facecolor='#1e293b', edgecolor='#334155', fontsize=9)
    for text in legend.get_texts():
        text.color = '#f8fafc'
        
    # Remove outer spines
    for spine in ['top', 'right', 'left', 'bottom']:
        ax.spines[spine].set_visible(False)
        
    # Annotate final values on the right
    last_date = df.index[-1]
    ax.annotate(f"Inv Growth Relaxed: Rp {df['Inv_Growth_Relaxed'].iloc[-1]:.2f} B", xy=(last_date, df['Inv_Growth_Relaxed'].iloc[-1]), xytext=(10, 8), textcoords='offset points', color='#06b6d4', fontweight='bold', fontsize=9)
    ax.annotate(f"Inv Static: Rp {df['Inv_Static'].iloc[-1]:.2f} B", xy=(last_date, df['Inv_Static'].iloc[-1]), xytext=(10, -5), textcoords='offset points', color='#14b8a6', fontweight='bold', fontsize=8)
    ax.annotate(f"Inv Growth Strict: Rp {df['Inv_Growth_Strict'].iloc[-1]:.2f} B", xy=(last_date, df['Inv_Growth_Strict'].iloc[-1]), xytext=(10, -18), textcoords='offset points', color='#99f6e4', fontsize=8)
    ax.annotate(f"IHSG: Rp {df['IHSG'].iloc[-1]:.2f} B", xy=(last_date, df['IHSG'].iloc[-1]), xytext=(10, 0), textcoords='offset points', color='#64748b', fontweight='bold', fontsize=9)
    
    plt.tight_layout()
    
    # Save targets
    out_scratch = os.path.join(data_dir, "backtest_growth_relaxed_chart.png")
    out_artifact = os.path.join(artifact_dir, "backtest_growth_relaxed_chart.png")
    
    plt.savefig(out_scratch, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.savefig(out_artifact, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.close()
    
    print(f"📊 Growth relaxed chart plotted and saved to:\n  - {out_scratch}\n  - {out_artifact}")

if __name__ == "__main__":
    main()
