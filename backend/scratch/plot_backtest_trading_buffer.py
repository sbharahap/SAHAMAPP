import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

def main():
    data_dir = "/Users/satriabaladewaharahap/Downloads/SAHAMAPP/backend/scratch"
    csv_path = os.path.join(data_dir, "backtest_trading_buffer_results.csv")
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
    
    # Plotting
    ax.plot(df.index, df["Trade_Buffer_10"], color='#ea580c', label='Swing Trading (Buffer Rank 10)', linewidth=3.2) # Orange 600
    ax.plot(df.index, df["Trade_Buffer_8"], color='#f97316', label='Swing Trading (Buffer Rank 8)', linewidth=2.2) # Orange 500
    ax.plot(df.index, df["Trade_Buffer_12"], color='#eab308', label='Swing Trading (Buffer Rank 12)', linewidth=2.2) # Yellow 500
    ax.plot(df.index, df["Trade_No_Buffer"], color='#ffedd5', label='Swing Trading (No Buffer)', linewidth=1.2, linestyle=':') # Dotted Orange 100
    ax.plot(df.index, df["IHSG"], color='#64748b', label='IHSG (Benchmark)', linewidth=1.8, linestyle='--') # Dashed Slate 500
    
    # Titles & Labels
    ax.set_title("Analisis Portofolio Swing Trading Mingguan dengan Holding Buffer (2022 - 2025)\nDampak Minimalisasi Churn & Biaya Transaksi", 
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
    ax.annotate(f"Trade Buf 10: Rp {df['Trade_Buffer_10'].iloc[-1]:.2f} B", xy=(last_date, df['Trade_Buffer_10'].iloc[-1]), xytext=(10, 5), textcoords='offset points', color='#ea580c', fontweight='bold', fontsize=9)
    ax.annotate(f"Trade Buf 8: Rp {df['Trade_Buffer_8'].iloc[-1]:.2f} B", xy=(last_date, df['Trade_Buffer_8'].iloc[-1]), xytext=(10, -5), textcoords='offset points', color='#f97316', fontweight='bold', fontsize=8)
    ax.annotate(f"Trade Buf 12: Rp {df['Trade_Buffer_12'].iloc[-1]:.2f} B", xy=(last_date, df['Trade_Buffer_12'].iloc[-1]), xytext=(10, -15), textcoords='offset points', color='#eab308', fontweight='bold', fontsize=8)
    ax.annotate(f"Trade No Buf: Rp {df['Trade_No_Buffer'].iloc[-1]:.2f} B", xy=(last_date, df['Trade_No_Buffer'].iloc[-1]), xytext=(10, -25), textcoords='offset points', color='#ffedd5', fontsize=8)
    ax.annotate(f"IHSG: Rp {df['IHSG'].iloc[-1]:.2f} B", xy=(last_date, df['IHSG'].iloc[-1]), xytext=(10, 0), textcoords='offset points', color='#64748b', fontweight='bold', fontsize=9)
    
    plt.tight_layout()
    
    # Save targets
    out_scratch = os.path.join(data_dir, "backtest_trading_buffer_chart.png")
    out_artifact = os.path.join(artifact_dir, "backtest_trading_buffer_chart.png")
    
    plt.savefig(out_scratch, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.savefig(out_artifact, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.close()
    
    print(f"📊 Trading buffer chart plotted and saved to:\n  - {out_scratch}\n  - {out_artifact}")

if __name__ == "__main__":
    main()
