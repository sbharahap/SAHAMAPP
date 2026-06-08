import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

def main():
    data_dir = "/Users/satriabaladewaharahap/Downloads/SAHAMAPP/backend/scratch"
    csv_path = os.path.join(data_dir, "backtest_results.csv")
    artifact_dir = "/Users/satriabaladewaharahap/.gemini/antigravity-ide/brain/85414e74-7f32-4a34-98f1-6bf79908bc9d"
    
    if not os.path.exists(csv_path):
        print("❌ CSV results not found!")
        return
        
    df = pd.read_csv(csv_path)
    df["tanggal"] = pd.to_datetime(df["tanggal"])
    df.set_index("tanggal", inplace=True)
    
    # Normalize values or keep absolute (convert to Billion IDR for readability)
    df = df / 1e9
    
    # Style configuration for a premium dark mode look
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(12, 7), dpi=150)
    fig.patch.set_facecolor('#0f172a')  # Slate 900
    ax.set_facecolor('#0f172a')
    
    # Plot lines with modern premium colors
    ax.plot(df.index, df["Investing_Port"], color='#2dd4bf', label='Value Investing (Monthly, no Sentiment)', linewidth=2.5) # Teal 400
    ax.plot(df.index, df["Hybrid_Port"], color='#a78bfa', label='Hybrid Strategy (Monthly + Sentiment)', linewidth=2.2) # Violet 400
    ax.plot(df.index, df["IHSG"], color='#94a3b8', label='IHSG (Benchmark)', linewidth=1.8, linestyle='--') # Slate 400
    ax.plot(df.index, df["Trading_Port"], color='#fb923c', label='Swing Trading (Weekly + Sentiment)', linewidth=2.0) # Orange 400
    
    # Add titles & descriptions
    ax.set_title("Perbandingan Portofolio Saham AI (2022 - 2025)\nModal Awal: Rp 1.0 Miliar", 
                 fontsize=16, fontweight='bold', color='#f8fafc', pad=20, family='sans-serif')
    
    ax.set_xlabel("Tanggal", fontsize=11, color='#cbd5e1', labelpad=10)
    ax.set_ylabel("Nilai Portofolio (Miliar Rupiah)", fontsize=11, color='#cbd5e1', labelpad=10)
    
    # Grid styling
    ax.grid(True, which='both', color='#1e293b', linestyle=':', linewidth=0.8) # Slate 800
    
    # Format axes
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    plt.xticks(rotation=30, color='#cbd5e1')
    plt.yticks(color='#cbd5e1')
    
    # Legend styling
    legend = ax.legend(loc='upper left', frameon=True, facecolor='#1e293b', edgecolor='#334155', fontsize=10)
    for text in legend.get_texts():
        text.color = '#f8fafc'
        
    # Remove outer spines for cleaner look
    for spine in ['top', 'right', 'left', 'bottom']:
        ax.spines[spine].set_visible(False)
        
    # Annotate final values on the right
    last_date = df.index[-1]
    ax.annotate(f"Rp {df['Investing_Port'].iloc[-1]:.2f} B", 
                xy=(last_date, df['Investing_Port'].iloc[-1]), 
                xytext=(10, 0), textcoords='offset points', 
                color='#2dd4bf', fontweight='bold', fontsize=10)
                
    ax.annotate(f"Rp {df['IHSG'].iloc[-1]:.2f} B", 
                xy=(last_date, df['IHSG'].iloc[-1]), 
                xytext=(10, -5), textcoords='offset points', 
                color='#94a3b8', fontweight='bold', fontsize=10)
                
    ax.annotate(f"Rp {df['Hybrid_Port'].iloc[-1]:.2f} B", 
                xy=(last_date, df['Hybrid_Port'].iloc[-1]), 
                xytext=(10, 5), textcoords='offset points', 
                color='#a78bfa', fontweight='bold', fontsize=10)
                
    ax.annotate(f"Rp {df['Trading_Port'].iloc[-1]:.2f} B", 
                xy=(last_date, df['Trading_Port'].iloc[-1]), 
                xytext=(10, 0), textcoords='offset points', 
                color='#fb923c', fontweight='bold', fontsize=10)
                
    plt.tight_layout()
    
    # Save targets
    out_scratch = os.path.join(data_dir, "backtest_chart.png")
    out_artifact = os.path.join(artifact_dir, "backtest_chart.png")
    
    plt.savefig(out_scratch, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.savefig(out_artifact, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.close()
    
    print(f"📊 Chart successfully plotted and saved to:\n  - {out_scratch}\n  - {out_artifact}")

if __name__ == "__main__":
    main()
