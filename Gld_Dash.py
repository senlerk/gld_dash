import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import plotly.subplots as make_subplots
from datetime import datetime, timedelta
import time
import pandas as pd
import numpy as np
import ta

# Optional imports with fallbacks
try:
    from scipy.signal import argrelextrema
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    st.warning("scipy not installed. Some features will be disabled. Install scipy for full functionality.")

class TechnicalAnalysis:
    @staticmethod
    def calculate_all_indicators(data):
        """Calculate all technical indicators"""
        # Basic indicators from previous version
        data['SMA20'] = ta.trend.sma_indicator(data['Close'], window=20)
        data['SMA50'] = ta.trend.sma_indicator(data['Close'], window=50)
        
        # RSI
        data['RSI'] = ta.momentum.rsi(data['Close'], window=14)
        
        # Bollinger Bands
        data['BB_middle'] = ta.volatility.bollinger_mavg(data['Close'], window=20)
        data['BB_upper'] = ta.volatility.bollinger_hband(data['Close'], window=20)
        data['BB_lower'] = ta.volatility.bollinger_lband(data['Close'], window=20)
        
        # MACD
        data['MACD'] = ta.trend.macd_diff(data['Close'])
        data['MACD_signal'] = ta.trend.macd_signal(data['Close'])
        
        # ATR
        data['ATR'] = ta.volatility.average_true_range(data['High'], data['Low'], data['Close'])
        
        return data

    @staticmethod
    def find_support_resistance(data, window=20):
        """Find support and resistance levels"""
        if not SCIPY_AVAILABLE:
            # Simplified S/R calculation without scipy
            resistance_levels = data['High'].rolling(window=window).max()
            support_levels = data['Low'].rolling(window=window).min()
            return support_levels, resistance_levels

        local_max = argrelextrema(data['High'].values, np.greater_equal, order=window)[0]
        local_min = argrelextrema(data['Low'].values, np.less_equal, order=window)[0]
        
        resistance_levels = data['High'].iloc[local_max]
        support_levels = data['Low'].iloc[local_min]
        
        return support_levels, resistance_levels

    @staticmethod
    def calculate_volume_profile(data, price_bins=50):
        """Calculate volume profile"""
        price_range = np.linspace(data['Low'].min(), data['High'].max(), price_bins)
        volume_profile = np.zeros(price_bins)
        
        for i in range(len(data)):
            price_idx = np.digitize(data['Close'].iloc[i], price_range)
            volume_profile[price_idx-1] += data['Volume'].iloc[i]
            
        return price_range, volume_profile

class DataManager:
    @staticmethod
    def get_gld_data(timeframe='1d', interval='1m'):
        """Fetch GLD data from Yahoo Finance"""
        periods = {
            '1d': '1d',
            '1w': '5d',
            '1m': '1mo',
            '3m': '3mo',
            '6m': '6mo',
            '1y': '1y'
        }
        
        intervals = {
            '1d': '1m',
            '1w': '5m',
            '1m': '1h',
            '3m': '1h',
            '6m': '1d',
            '1y': '1d'
        }
        
        try:
            gld = yf.Ticker("GLD")
            data = gld.history(
                period=periods.get(timeframe, '1d'),
                interval=intervals.get(timeframe, '1m')
            )
            return data
        except Exception as e:
            st.error(f"Error fetching data: {str(e)}")
            return pd.DataFrame()  # Return empty DataFrame on error

    @staticmethod
    def calculate_buy_sell_volume(data):
        """Enhanced volume analysis"""
        if data.empty:
            return data
            
        data['Typical_Price'] = (data['High'] + data['Low'] + data['Close']) / 3
        data['VP'] = data['Typical_Price'] * data['Volume']
        data['VWAP'] = data['VP'].cumsum() / data['Volume'].cumsum()
        
        data['Price_Change'] = data['Close'] - data['Open']
        data['Volume_MA'] = data['Volume'].rolling(window=20).mean()
        data['Relative_Volume'] = data['Volume'] / data['Volume_MA']
        
        # Enhanced buy/sell volume calculation
        data['Buy_Volume'] = np.where(
            (data['Close'] > data['VWAP']) & 
            (data['Price_Change'] > 0),
            data['Volume'] * data['Relative_Volume'],
            data['Volume'] * 0.5
        )
        
        data['Sell_Volume'] = np.where(
            (data['Close'] < data['VWAP']) & 
            (data['Price_Change'] < 0),
            data['Volume'] * data['Relative_Volume'],
            data['Volume'] * 0.5
        )
        
        # Normalize volumes
        total_volume = data['Volume'].sum()
        total_calculated = data['Buy_Volume'].sum() + data['Sell_Volume'].sum()
        
        if total_calculated > 0:  # Prevent division by zero
            data['Buy_Volume'] = (data['Buy_Volume'] / total_calculated) * total_volume
            data['Sell_Volume'] = (data['Sell_Volume'] / total_calculated) * total_volume
        
        return data

class ChartManager:
    @staticmethod
    def create_advanced_chart(data, selected_indicators, chart_type="Candlestick"):
        """Create advanced chart with multiple panels"""
        if data.empty:
            return None
            
        fig = make_subplots(
            rows=3, 
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            row_heights=[0.6, 0.2, 0.2]
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
        elif chart_type == "Line":
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data['Close'],
                    name="GLD",
                    line=dict(color='blue')
                ),
                row=1, col=1
            )

        # Add selected indicators
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

        if "Bollinger Bands" in selected_indicators:
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data['BB_upper'],
                    name="BB Upper",
                    line=dict(color='gray', width=1)
                ),
                row=1, col=1
            )
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data['BB_lower'],
                    name="BB Lower",
                    line=dict(color='gray', width=1),
                    fill='tonexty'
                ),
                row=1, col=1
            )

        # Volume panel
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

        # Indicators panel
        if "RSI" in selected_indicators:
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data['RSI'],
                    name="RSI",
                    line=dict(color='purple')
                ),
                row=3, col=1
            )
            # Add RSI levels
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)

        # Update layout
        fig.update_layout(
            title='GLD Advanced Analysis',
            template='plotly_dark',
            height=900,
            xaxis_rangeslider_visible=False,
            showlegend=True
        )

        return fig

class Dashboard:
    def __init__(self):
        self.setup_page()
        self.setup_sidebar()
        self.create_tabs()
        
    def setup_page(self):
        """Setup the main page configuration"""
        st.set_page_config(
            page_title="GLD Advanced Dashboard",
            page_icon="📈",
            layout="wide"
        )
        st.title("📈 Advanced GLD Price Dashboard")

    def setup_sidebar(self):
        """Setup the sidebar controls"""
        st.sidebar.title("Dashboard Controls")
        
        # Time period selector
        self.timeframe = st.sidebar.selectbox(
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
        
        # Technical indicators selector
        self.selected_indicators = st.sidebar.multiselect(
            "Select Technical Indicators",
            ["Moving Averages", "Bollinger Bands", "RSI", "MACD"],
            default=["Moving Averages", "RSI"]
        )
        
        # Chart type selector
        self.chart_type = st.sidebar.selectbox(
            "Select Chart Type",
            ["Candlestick", "Line"]
        )
        
        # Refresh rate in minutes
        self.refresh_rate = st.sidebar.slider(
            "Refresh Rate (minutes)",
            min_value=1,
            max_value=30,
            value=5
        )

    def create_tabs(self):
        """Create the main dashboard tabs"""
        self.price_tab, self.analysis_tab = st.tabs(["Price Analysis", "Technical Analysis"])

    def display_metrics(self, data):
        """Display key metrics"""
        if data.empty:
            return
            
        current_price = float(data['Close'].iloc[-1])
        period_high = float(data['High'].max())
        period_low = float(data['Low'].min())
        price_change = float(data['Close'].iloc[-1] - data['Close'].iloc[0])
        price_change_pct = (price_change / float(data['Close'].iloc[0])) * 100

        col1, col2, col3, col4 = st.columns(4)
        
        col1.metric(
            "Current Price",
            f"${current_price:.2f}",
            f"{price_change:.2f} ({price_change_pct:.2f}%)"
        )
        
        col2.metric("Period High", f"${period_high:.2f}")
        col3.metric("Period Low", f"${period_low:.2f}")
        
        # Add ATR if available
        if 'ATR' in data.columns:
            col4.metric("ATR", f"${data['ATR'].iloc[-1]:.3f}")

    def run(self):
        """Main dashboard loop"""
        while True:
            try:
                # Fetch and process data
                data = DataManager.get_gld_data(self.timeframe)
                if not data.empty:
                    # Calculate indicators
                    data = TechnicalAnalysis.calculate_all_indicators(data)
                    data = DataManager.calculate_buy_sell_volume(data)
                    
                    # Price Analysis Tab
                    with self.price_tab:
                        self.display_metrics(data)
                        
                        # Main chart
                        chart = ChartManager.create_advanced_chart(
                            data,
                            self.selected_indicators,
                            self.chart_type
                        )
                        if chart:
                            st.plotly_chart(chart, use_container_width=True)
                    
                    # Technical Analysis Tab
                    with self.analysis_tab:
                        # Support/Resistance
                        support, resistance = TechnicalAnalysis.find_support_resistance(data)
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.subheader("Support Levels")
                            for level in support.tail().sort_values(ascending=True):
                                st.write(f"${level:.2f}")
                        
                        with col2:
                            st.subheader("Resistance Levels")
                            for level in resistance.tail().sort_values(ascending=True):
                                st.write(f"${level:.2f}")
                        
                        # Technical Indicators
                        st.subheader("Technical Indicators Analysis")
                        
                        # RSI Analysis
                        rsi_value = data['RSI'].iloc[-1]
                        rsi_color = (
                            "🔴" if rsi_value > 70 else 
                            "🟢" if rsi_value < 30 else 
                            "⚪"
                        )