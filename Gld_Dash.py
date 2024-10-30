import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import plotly.graph_objects as go
import time
import numpy as np

# Original metal price functions
def get_metal_price(symbol):
    """Get metal price from Yahoo Finance"""
    ticker = yf.Ticker(symbol)
    end = datetime.now()
    start = end - timedelta(days=1)
    df = ticker.history(start=start, end=end, interval='5m')
    return df

def create_price_chart(df, title):
    """Create a candlestick chart for metals"""
    fig = go.Figure(data=[go.Candlestick(x=df.index,
                                        open=df['Open'],
                                        high=df['High'],
                                        low=df['Low'],
                                        close=df['Close'])])
    
    fig.update_layout(title=title,
                     yaxis_title='Price (USD)',
                     xaxis_title='Time')
    
    return fig

def format_price(price):
    """Format price with appropriate decimal places"""
    return f"${price:,.2f}"

# GLD Analysis functions
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
    """Calculate buy and sell volume"""
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
    
    data['Sell_Volume'] = data['Volume'] - data['Buy_Volume']
    return data

def create_gld_chart(data, title_prefix="GLD"):
    """Create enhanced chart for GLD analysis"""
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data['VWAP'],
        name='VWAP',
        line=dict(color='purple', width=1),
        hoverinfo='y'
    ))
    
    fig.add_trace(go.Candlestick(
        x=data.index,
        open=data['Open'],
        high=data['High'],
        low=data['Low'],
        close=data['Close'],
        name='GLD'
    ))
    
    fig.add_trace(go.Bar(
        x=data.index,
        y=data['Buy_Volume'],
        name='Buy Volume',
        marker_color='rgba(0, 255, 0, 0.3)',
        yaxis='y2'
    ))
    
    fig.add_trace(go.Bar(
        x=data.index,
        y=data['Sell_Volume'],
        name='Sell Volume',
        marker_color='rgba(255, 0, 0, 0.3)',
        yaxis='y2'
    ))
    
    fig.update_layout(
        title=f'{title_prefix} Price Chart with Volume Analysis',
        yaxis_title='Price (USD)',
        xaxis_title='Time',
        height=800,
        yaxis2=dict(
            title='Volume',
            overlaying='y',
            side='right',
            showgrid=False
        )
    )
    
    return fig

def main():
    st.set_page_config(page_title='Metals Dashboard',
                      layout='wide')
    
    st.title('📈 Precious Metals Dashboard')
    st.markdown('---')
    
    # Initialize session state
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = time.time()
    
    # Add refresh button
    if st.button('🔄 Refresh Data'):
        st.session_state.last_refresh = time.time()
        st.rerun()
    
    # Create three tabs
    gold_tab, silver_tab, gld_tab = st.tabs(["Gold Spot", "Silver Spot", "GLD Analysis"])
    
    try:
        # Get metal prices data
        gold_df = get_metal_price('GC=F')
        silver_df = get_metal_price('SI=F')
        gld_df = yf.download('GLD', period='1d', interval='1m')
        
        # Process GLD data
        if not gld_df.empty:
            gld_trend, gld_reasons, gld_df = analyze_trend(gld_df)
            gld_df = calculate_buy_sell_volume(gld_df)
        
        # Gold Tab
        with gold_tab:
            if not gold_df.empty:
                gold_current_price = gold_df['Close'][-1]
                gold_open_price = gold_df['Open'][0]
                gold_change = ((gold_current_price - gold_open_price) / gold_open_price * 100)
                
                st.metric(
                    "Current Price",
                    format_price(gold_current_price),
                    delta=f"{gold_change:.2f}%"
                )
                st.plotly_chart(create_price_chart(gold_df, 'Gold Price Last 24 Hours'),
                              use_container_width=True)
                
                st.subheader("Today's Statistics")
                st.write(f"High: {format_price(gold_df['High'].max())}")
                st.write(f"Low: {format_price(gold_df['Low'].min())}")
                st.write(f"Opening: {format_price(gold_open_price)}")
            else:
                st.warning("No Gold price data available.")
        
        # Silver Tab
        with silver_tab:
            if not silver_df.empty:
                silver_current_price = silver_df['Close'][-1]
                silver_open_price = silver_df['Open'][0]
                silver_change = ((silver_current_price - silver_open_price) / silver_open_price * 100)
                
                st.metric(
                    "Current Price",
                    format_price(silver_current_price),
                    delta=f"{silver_change:.2f}%"
                )
                st.plotly_chart(create_price_chart(silver_df, 'Silver Price Last 24 Hours'),
                              use_container_width=True)
                
                st.subheader("Today's Statistics")
                st.write(f"High: {format_price(silver_df['High'].max())}")
                st.write(f"Low: {format_price(silver_df['Low'].min())}")
                st.write(f"Opening: {format_price(silver_open_price)}")
            else:
                st.warning("No Silver price data available.")
        
        # GLD Analysis Tab
        with gld_tab:
            if not gld_df.empty:
                st.subheader(f"Current Trend: {gld_trend}")
                st.write("Analysis based on:")
                for reason in gld_reasons:
                    st.write(f"• {reason}")
                
                # Display metrics
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Buy Volume", f"{int(gld_df['Buy_Volume'].sum()):,}")
                with col2:
                    st.metric("Sell Volume", f"{int(gld_df['Sell_Volume'].sum()):,}")
                
                st.plotly_chart(create_gld_chart(gld_df), use_container_width=True)
            else:
                st.warning("No GLD data available.")
        
        # Add last update time
        st.markdown("---")
        st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    except Exception as e:
        st.error("An error occurred while fetching the data.")
        st.exception(e)

if __name__ == "__main__":
    main()