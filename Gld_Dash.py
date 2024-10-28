import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import pandas as pd
import os
import numpy as np

def analyze_trend(data):
    """Analyze the trend using multiple indicators"""
    data['SMA20'] = data['Close'].rolling(window=20).mean()
    data['SMA50'] = data['Close'].rolling(window=50).mean()
    
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    data['RSI'] = 100 - (100 / (1 + rs))
    
    current_price = data['Close'].iloc[-1]
    sma20 = data['SMA20'].iloc[-1]
    sma50 = data['SMA50'].iloc[-1]
    rsi = data['RSI'].iloc[-1]
    
    reasons = []
    
    if current_price > sma20:
        reasons.append("Price above 20-period MA")
    else:
        reasons.append("Price below 20-period MA")
        
    if sma20 > sma50:
        reasons.append("20MA above 50MA (Golden Cross)")
    else:
        reasons.append("50MA above 20MA (Death Cross)")
        
    if rsi > 70:
        reasons.append("RSI showing overbought conditions")
    elif rsi < 30:
        reasons.append("RSI showing oversold conditions")
    
    bullish_signals = sum([
        current_price > sma20,
        current_price > sma50,
        sma20 > sma50,
        30 < rsi < 70
    ])
    
    if bullish_signals >= 3:
        trend = "🟢 Bullish"
    elif bullish_signals <= 1:
        trend = "🔴 Bearish"
    else:
        trend = "⚪ Neutral"
        
    return trend, reasons, data

def calculate_buy_sell_volume(data):
    data['Typical_Price'] = (data['High'] + data['Low'] + data['Close']) / 3
    data['VP'] = data['Typical_Price'] * data['Volume']
    data['Cumulative_VP'] = data['VP'].cumsum()
    data['Cumulative_Volume'] = data['Volume'].cumsum()
    data['VWAP'] = data['Cumulative_VP'] / data['Cumulative_Volume']
    
    data['Price_Change'] = data['Close'] - data['Open']
    data['Price_Momentum'] = data['Close'] - data['VWAP']
    
    data['Volume_MA'] = data['Volume'].rolling(window=20).mean()
    data['Relative_Volume'] = data['Volume'] / data['Volume_MA']
    
    data['Buy_Volume'] = np.where(
        (data['Close'] > data['VWAP']) & 
        (data['Price_Change'] > 0) & 
        (data['Close'] > data['Open']),
        data['Volume'] * data['Relative_Volume'],
        np.where(
            (data['Close'] > data['VWAP']),
            data['Volume'] * 0.7,
            data['Volume'] * 0.3
        )
    )
    
    data['Sell_Volume'] = np.where(
        (data['Close'] < data['VWAP']) & 
        (data['Price_Change'] < 0) & 
        (data['Close'] < data['Open']),
        data['Volume'] * data['Relative_Volume'],
        np.where(
            (data['Close'] < data['VWAP']),
            data['Volume'] * 0.7,
            data['Volume'] * 0.3
        )
    )
    
    total_volume = data['Volume'].sum()
    calculated_volume = data['Buy_Volume'].sum() + data['Sell_Volume'].sum()
    
    data['Buy_Volume'] = (data['Buy_Volume'] / calculated_volume) * total_volume
    data['Sell_Volume'] = (data['Sell_Volume'] / calculated_volume) * total_volume
    
    return data

def get_gld_data():
    gld = yf.Ticker("GLD")
    data = gld.history(period='1d', interval='1m')
    return data

def save_daily_summary(current_price, day_high, day_low, buy_volume, sell_volume, trend):
    try:
        # Skip if any value is NaN or None
        if pd.isna([current_price, day_high, day_low, buy_volume, sell_volume]).any():
            return

        # Skip if we don't have valid trend data
        if not isinstance(trend, str) or not any(symbol in trend for symbol in ['🟢', '🔴', '⚪']):
            return
            
        # Create a single row of data
        data = pd.DataFrame([{
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'current_price': f"{float(current_price):.2f}",
            'day_high': f"{float(day_high):.2f}",
            'day_low': f"{float(day_low):.2f}",
            'buy_volume': f"{int(buy_volume)}",
            'sell_volume': f"{int(sell_volume)}",
            'trend': trend
        }])

        file_path = 'gld_daily_data.csv'
        
        # Write to CSV
        data.to_csv(file_path, 
                   mode='a',
                   header=not os.path.exists(file_path),
                   index=False)
                     
    except Exception as e:
        st.error(f"Error saving to CSV: {e}")

def create_price_chart(data):
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data['VWAP'],
        name='VWAP',
        line=dict(color='purple', width=1),
        hoverinfo='y',
        hoverlabel=dict(
            bgcolor='rgba(50, 50, 50, 0.9)',
            font=dict(color='white', size=14)
        )
    ))
    
    fig.add_trace(go.Candlestick(
        x=data.index,
        open=data['Open'],
        high=data['High'],
        low=data['Low'],
        close=data['Close'],
        name='GLD',
        hoverinfo='all',
        hoverlabel=dict(
            bgcolor='rgba(50, 50, 50, 0.9)',
            font=dict(color='white', size=14)
        ),
        text=[f"Time: {idx}<br>" +
              f"Open: ${o:.2f}<br>" +
              f"High: ${h:.2f}<br>" +
              f"Low: ${l:.2f}<br>" +
              f"Close: ${c:.2f}<br>" +
              f"VWAP: ${v:.2f}"
              for idx, o, h, l, c, v in zip(data.index, 
                                       data['Open'], 
                                       data['High'], 
                                       data['Low'], 
                                       data['Close'],
                                       data['VWAP'])]
    ))
    
    fig.add_trace(go.Bar(
        x=data.index,
        y=data['Buy_Volume'],
        name='Buy Volume',
        marker_color='rgba(0, 255, 0, 0.3)',
        yaxis='y2',
        hoverinfo='y',
        hoverlabel=dict(
            bgcolor='rgba(50, 50, 50, 0.9)',
            font=dict(color='white', size=14)
        )
    ))
    
    fig.add_trace(go.Bar(
        x=data.index,
        y=data['Sell_Volume'],
        name='Sell Volume',
        marker_color='rgba(255, 0, 0, 0.3)',
        yaxis='y2',
        hoverinfo='y',
        hoverlabel=dict(
            bgcolor='rgba(50, 50, 50, 0.9)',
            font=dict(color='white', size=14)
        )
    ))
    
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data['SMA20'],
        name='20 MA',
        line=dict(color='yellow', width=1),
        hoverinfo='y',
        hoverlabel=dict(
            bgcolor='rgba(50, 50, 50, 0.9)',
            font=dict(color='white', size=14)
        )
    ))
    
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data['SMA50'],
        name='50 MA',
        line=dict(color='orange', width=1),
        hoverinfo='y',
        hoverlabel=dict(
            bgcolor='rgba(50, 50, 50, 0.9)',
            font=dict(color='white', size=14)
        )
    ))
    
    fig.update_layout(
        title='GLD Price Chart with Volume Analysis',
        yaxis_title='Price (USD)',
        xaxis_title='Time',
        template='plotly_dark',
        height=800,
        xaxis_rangeslider=dict(
            visible=True,
            thickness=0.1,
            bgcolor='rgba(100, 100, 255, 0.1)',
            bordercolor='rgba(100, 100, 255, 0.4)',
        ),
        yaxis2=dict(
            title='Volume',
            overlaying='y',
            side='right',
            showgrid=False,
            tickformat=',.0f'
        ),
        margin=dict(l=50, r=50, t=50, b=50),
        font=dict(size=14),
    )
    
    return fig

def main():
    st.set_page_config(
        page_title="GLD Price Dashboard",
        page_icon="📈",
        layout="wide"
    )
    
    st.title("📈 Real-time GLD Price Dashboard")
    
    csv_status = st.empty()
    trend_placeholder = st.empty()
    price_placeholder = st.empty()
    chart_placeholder = st.empty()
    
    refresh_rate = st.sidebar.slider(
        "Refresh Rate (seconds)",
        min_value=5,
        max_value=60,
        value=30
    )
    
    if 'chart_key' not in st.session_state:
        st.session_state.chart_key = 0
    
    while True:
        try:
            data = get_gld_data()
            if data.empty:
                continue
            
            trend, reasons, data = analyze_trend(data)
            data = calculate_buy_sell_volume(data)
            
            try:
                current_price = float(data['Close'].iloc[-1])
                day_high = float(data['High'].max())
                day_low = float(data['Low'].min())
                buy_volume = int(data['Buy_Volume'].sum())
                sell_volume = int(data['Sell_Volume'].sum())
                price_change = float(data['Close'].iloc[-1] - data['Close'].iloc[0])
                price_change_pct = (price_change / float(data['Close'].iloc[0])) * 100
                
                if all([current_price, day_high, day_low, buy_volume, sell_volume, trend]):
                    save_daily_summary(current_price, day_high, day_low, 
                                    buy_volume, sell_volume, trend)
                    
                    last_update = datetime.now().strftime('%H:%M:%S')
                    csv_status.success(f"Data saved to gld_daily.csv (Last update: {last_update})")
                    
                    with trend_placeholder.container():
                        st.subheader(f"Current Trend: {trend}")
                        st.write("Analysis based on:")
                        for reason in reasons:
                            st.write(f"• {reason}")
                        
                        col1, col2 = st.columns(2)
                        col1.metric("Buy Volume", f"{buy_volume:,.0f}")
                        col2.metric("Sell Volume", f"{sell_volume:,.0f}")
                    
                    with price_placeholder.container():
                        col1, col2, col3 = st.columns(3)
                        
                        col1.metric(
                            "Current Price",
                            f"${current_price:.2f}",
                            f"{price_change:.2f} ({price_change_pct:.2f}%)"
                        )
                        
                        col2.metric(
                            "Day High",
                            f"${day_high:.2f}"
                        )
                        
                        col3.metric(
                            "Day Low",
                            f"${day_low:.2f}"
                        )
                    
                    with chart_placeholder:
                        st.plotly_chart(
                            create_price_chart(data),
                            use_container_width=True,
                            key=f"chart_{st.session_state.chart_key}"
                        )
                        st.session_state.chart_key += 1
            
            except (ValueError, IndexError, TypeError) as e:
                print(f"Error processing data: {e}")
                continue
            
            time.sleep(refresh_rate)
            
        except Exception as e:
            st.error(f"Error fetching data: {e}")
            time.sleep(refresh_rate)

if __name__ == "__main__":
    main()