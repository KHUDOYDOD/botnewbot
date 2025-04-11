import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import os

def create_analysis_image(analysis_result, market_data, lang_code='tg'):
    try:
        # Create figure with subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), height_ratios=[3, 1])
        fig.patch.set_facecolor('#1a1b26')
        
        # Plot price data
        ax1.plot(market_data.index, market_data['Close'], label='Price', color='white', linewidth=2)
        
        # Calculate and plot moving averages
        ema_7 = market_data['Close'].ewm(span=7, adjust=False).mean()
        ema_21 = market_data['Close'].ewm(span=21, adjust=False).mean()
        ax1.plot(market_data.index, ema_7, label='EMA 7', color='#00ff00', alpha=0.7)
        ax1.plot(market_data.index, ema_21, label='EMA 21', color='#ff6b6b', alpha=0.7)
        
        # Plot volume
        ax2.bar(market_data.index, market_data['Volume'], color='#4a9eff', alpha=0.3)
        
        # Style the price plot
        ax1.set_facecolor('#24283b')
        ax1.grid(True, color='#414868', linestyle='--', alpha=0.3)
        ax1.set_title('Price Analysis', color='white', pad=20)
        ax1.legend(facecolor='#24283b', edgecolor='#414868', labelcolor='white')
        ax1.tick_params(colors='white')
        
        # Style the volume plot
        ax2.set_facecolor('#24283b')
        ax2.grid(True, color='#414868', linestyle='--', alpha=0.3)
        ax2.set_title('Volume', color='white', pad=10)
        ax2.tick_params(colors='white')
        
        # Format x-axis
        for ax in [ax1, ax2]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['bottom'].set_color('#414868')
            ax.spines['left'].set_color('#414868')
        
        # Adjust layout and save
        plt.tight_layout()
        plt.savefig('analysis_sample.png', dpi=100, bbox_inches='tight', facecolor='#1a1b26')
        plt.close()
        
        return True
    except Exception as e:
        print(f"Error generating chart: {str(e)}")
        return False
