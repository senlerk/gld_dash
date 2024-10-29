import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import pandas as pd
import numpy as np
import ta

def create_chart(data, selected_indicators, chart_type="Candlestick"):
    """Create the main chart"""
    if data.empty:
        return None
        
    # Create figure with secondary y-axis
    fig = go.Figure()

    # Add price data
    if chart_type == "Candlestick":
        fig.add_trace(
            go.Candlestick(
                x=data.index,
                open=data['Open'],
                high=data['High'],
                low=data['Low'],
                close=data['Close'],
                name="GLD"
            )
        )
    else:
        fig.add_trace(
            go.Scatter(
                x=data.index,
                y=data['Close'],
                name="GLD",
                line=dict(color='blue')
            )
        )

    # Add indicators
    if "Moving Averages" in selected_indicators:
        fig.add_trace(
            go.Scatter(
                x=data.index,
                y=data['SMA20'],
                name="SMA20",
                line=dict(color='yellow', width=1)
            )
        )
        fig.add_trace(
            go.Scatter(
                x=data.index,
                y=data['SMA50'],
                name="SMA50",
                line=dict(color='orange', width=1)
            )
        )

    # Add volume as bar chart
    fig.add_trace(
        go.Bar(
            x=data.index,
            y=data['Volume'],
            name="Volume",
            marker_color='rgba(0, 255, 0, 0.3)',
            yaxis="y2"
        )
    )

    # Update layout
    fig.update_layout(
        title='GLD Price Analysis',
        template='plotly_dark',
        height=800,
        showlegend=True,
        # Add a secondary y-axis for volume
        yaxis2=dict(
            title="Volume",
            overlaying="y",
            side="right",
            showgrid=False
        ),
        # Update y-axes labels
        yaxis_title="Price (USD)",
        xaxis_title="Date"
    )

    return fig

def get_data(timeframe='1d'):
    """Fetch GLD data"""
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

def calculate_indicators(data):
    """Calculate technical indicators"""
    if data.empty:
        return data
        
    # Calculate SMAs
    data['SMA20'] = data['Close'].rolling(window=20).mean()
    data['SMA50'] = data['Close'].rolling(window=50).mean()
    
    return data

def main():
    # Page config
    st.set_page_config(page_title="GLD Dashboard", page_icon="📈", layout="wide")
    st.title("📈 GLD Price Dashboard")

    # Sidebar
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

    # Get and process data
    data = get_data(timeframe)
    
    if not data.empty:
        data = calculate_indicators(data)
        
        # Display metrics
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
        
        # Create and display chart
        fig = create_chart(data, selected_indicators, chart_type)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
            
        # Display last update time
        st.sidebar.write(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")
    else:
        st.error("No data available")

if __name__ == "__main__":
    main()