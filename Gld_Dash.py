import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import plotly.subplots as make_subplots
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import ta

class TechnicalAnalysis:
    @staticmethod
    def calculate_all_indicators(data):
        """Calculate all technical indicators"""
        # Basic indicators
        data['SMA20'] = ta.trend.sma_indicator(data['Close'], window=20)
        data['SMA50'] = ta.trend.sma_indicator(data['Close'], window=50)
        data['RSI'] = ta.momentum.rsi(data['Close'], window=14)
        return data

class DataManager:
    @staticmethod
    def get_gld_data(timeframe='1d'):
        """Fetch GLD data from Yahoo Finance"""
        periods = {
            '1d': '1d',
            '1w': '5d',
            '1m': '1mo',
            '3m': '3mo',
            '6m': '6mo',
            '1y': '1y'
        }
        
        try:
            gld = yf.Ticker("GLD")
            data = gld.history(period=periods.get(timeframe, '1d'))
            return data
        except Exception as e:
            st.error(f"Error fetching data: {str(e)}")
            return pd.DataFrame()

    @staticmethod
    def calculate_buy_sell_volume(data):
        if data.empty:
            return data
            
        data['Typical_Price'] = (data['High'] + data['Low'] + data['Close']) / 3
        data['Volume_MA'] = data['Volume'].rolling(window=20).mean()
        
        # Simple buy/sell volume split
        data['Buy_Volume'] = np.where(
            data['Close'] > data['Open'],
            data['Volume'],
            data['Volume'] * 0.5
        )
        
        data['Sell_Volume'] = np.where(
            data['Close'] < data['Open'],
            data['Volume'],
            data['Volume'] * 0.5
        )
        
        return data

class ChartManager:
    @staticmethod
    def create_chart(data, selected_indicators, chart_type="Candlestick"):
        if data.empty:
            return None
            
        fig = make_subplots(
            rows=2, 
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            row_heights=[0.7, 0.3]
        )

        # Main price chart
        if chart_type == "Candlestick":
            fig.add_trace(
                go.Candlestick(
                    x=data.index,
                    open=data['Open'],
                    high=data['High'],
                    low=data['Low'],
                    close=data['Close'],
                    name="GLD"
                ),
                row=1, col=1
            )
        else:
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data['Close'],
                    name="GLD",
                    line=dict(color='blue')
                ),
                row=1, col=1
            )

        # Add indicators
        if "Moving Averages" in selected_indicators:
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data['SMA20'],
                    name="SMA20",
                    line=dict(color='yellow', width=1)
                ),
                row=1, col=1
            )
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data['SMA50'],
                    name="SMA50",
                    line=dict(color='orange', width=1)
                ),
                row=1, col=1
            )

        # Volume
        fig.add_trace(
            go.Bar(
                x=data.index,
                y=data['Buy_Volume'],
                name="Buy Volume",
                marker_color='rgba(0, 255, 0, 0.3)'
            ),
            row=2, col=1
        )
        fig.add_trace(
            go.Bar(
                x=data.index,
                y=data['Sell_Volume'],
                name="Sell Volume",
                marker_color='rgba(255, 0, 0, 0.3)'
            ),
            row=2, col=1
        )

        # Update layout
        fig.update_layout(
            title='GLD Price Analysis',
            template='plotly_dark',
            height=800,
            showlegend=True
        )

        return fig

def setup_sidebar():
    """Setup sidebar controls"""
    st.sidebar.title("Dashboard Controls")
    
    timeframe = st.sidebar.selectbox(
        "Select Time Period",
        ['1d', '1w', '1m', '3m', '6m', '1y'],
        format_func=lambda x: {
            '1d': '1 Day',
            '1w': '1 Week',
            '1m': '1 Month',
            '3m': '3 Months',
            '6m': '6 Months',
            '1y': '1 Year'
        }[x]
    )
    
    selected_indicators = st.sidebar.multiselect(
        "Select Technical Indicators",
        ["Moving Averages"],
        default=["Moving Averages"]
    )
    
    chart_type = st.sidebar.selectbox(
        "Select Chart Type",
        ["Candlestick", "Line"]
    )
    
    return timeframe, selected_indicators, chart_type

def display_metrics(data):
    """Display key metrics"""
    if data.empty:
        return
        
    current_price = float(data['Close'].iloc[-1])
    period_high = float(data['High'].max())
    period_low = float(data['Low'].min())
    price_change = float(data['Close'].iloc[-1] - data['Close'].iloc[0])
    price_change_pct = (price_change / float(data['Close'].iloc[0])) * 100
    
    col1, col2, col3 = st.columns(3)
    col1.metric(
        "Current Price", 
        f"${current_price:.2f}", 
        f"{price_change_pct:.2f}%"
    )
    col2.metric("Period High", f"${period_high:.2f}")
    col3.metric("Period Low", f"${period_low:.2f}")

def main():
    st.set_page_config(page_title="GLD Dashboard", page_icon="📈", layout="wide")
    st.title("📈 GLD Price Dashboard")

    # Setup sidebar
    timeframe, selected_indicators, chart_type = setup_sidebar()

    # Get data
    data = DataManager.get_gld_data(timeframe)
    
    if not data.empty:
        # Calculate indicators
        data = TechnicalAnalysis.calculate_all_indicators(data)
        data = DataManager.calculate_buy_sell_volume(data)
        
        # Display metrics
        display_metrics(data)
        
        # Display chart
        chart = ChartManager.create_chart(
            data,
            selected_indicators,
            chart_type
        )
        if chart:
            st.plotly_chart(chart, use_container_width=True)

        # Display last update time
        st.sidebar.write(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

if __name__ == "__main__":
    main()