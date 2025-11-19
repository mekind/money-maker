"""
Investment Analysis page for tracking buy opportunities and sector attractiveness.
This is a research tool - no real transactions are made.
"""

import streamlit as st
import plotly.graph_objects as go
from pathlib import Path
import sys
import pandas as pd

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from services import MarketDataService
from config import settings
from utils import show_navigation

st.set_page_config(page_title="Investment Analysis", page_icon="🔍", layout="wide")


# Sector mapping with representative ETFs and major stocks
SECTORS = {
    "Technology": {
        "etf": "XLK",
        "stocks": ["AAPL", "MSFT", "NVDA", "GOOGL", "META"],
        "description": "Software, hardware, semiconductors, and IT services"
    },
    "Healthcare": {
        "etf": "XLV",
        "stocks": ["JNJ", "UNH", "PFE", "ABBV", "MRK"],
        "description": "Pharmaceuticals, biotechnology, and healthcare services"
    },
    "Financial": {
        "etf": "XLF",
        "stocks": ["JPM", "BAC", "WFC", "GS", "MS"],
        "description": "Banks, insurance, and financial services"
    },
    "Consumer Discretionary": {
        "etf": "XLY",
        "stocks": ["AMZN", "TSLA", "HD", "NKE", "MCD"],
        "description": "Retail, automotive, and consumer products"
    },
    "Consumer Staples": {
        "etf": "XLP",
        "stocks": ["PG", "KO", "PEP", "WMT", "COST"],
        "description": "Food, beverages, and household products"
    },
    "Energy": {
        "etf": "XLE",
        "stocks": ["XOM", "CVX", "COP", "SLB", "EOG"],
        "description": "Oil, gas, and energy services"
    },
    "Industrials": {
        "etf": "XLI",
        "stocks": ["BA", "CAT", "UPS", "HON", "GE"],
        "description": "Manufacturing, aerospace, and transportation"
    },
    "Materials": {
        "etf": "XLB",
        "stocks": ["LIN", "APD", "ECL", "DD", "NEM"],
        "description": "Chemicals, metals, and mining"
    },
    "Real Estate": {
        "etf": "XLRE",
        "stocks": ["PLD", "AMT", "CCI", "EQIX", "PSA"],
        "description": "REITs and real estate services"
    },
    "Utilities": {
        "etf": "XLU",
        "stocks": ["NEE", "DUK", "SO", "D", "AEP"],
        "description": "Electric, gas, and water utilities"
    },
    "Communication": {
        "etf": "XLC",
        "stocks": ["GOOGL", "META", "DIS", "NFLX", "T"],
        "description": "Telecom and media services"
    }
}


def calculate_buy_signal_score(technical_indicators):
    """
    Calculate a buy signal score (0-100) based on technical indicators.
    Higher score = more attractive for buying.
    """
    if not technical_indicators:
        return None, "No data available"

    score = 50  # Start neutral
    signals = []

    # RSI Analysis (30 points)
    rsi = technical_indicators.get('RSI_14')
    if rsi:
        if rsi < 30:
            score += 15
            signals.append("🟢 Oversold (RSI < 30)")
        elif rsi < 40:
            score += 10
            signals.append("🟡 Approaching oversold (RSI < 40)")
        elif rsi > 70:
            score -= 15
            signals.append("🔴 Overbought (RSI > 70)")
        elif rsi > 60:
            score -= 10
            signals.append("🟡 Approaching overbought (RSI > 60)")
        else:
            signals.append("⚪ Neutral RSI")

    # MACD Analysis (25 points)
    macd = technical_indicators.get('MACD')
    macd_signal = technical_indicators.get('MACD_signal')
    if macd is not None and macd_signal is not None:
        if macd > macd_signal:
            score += 12
            signals.append("🟢 Bullish MACD crossover")
        else:
            score -= 12
            signals.append("🔴 Bearish MACD crossover")

    # Moving Average Trend (25 points)
    sma_20 = technical_indicators.get('SMA_20')
    sma_50 = technical_indicators.get('SMA_50')
    current_price = technical_indicators.get('current_price')

    if current_price and sma_20 and sma_50:
        if current_price > sma_20 > sma_50:
            score += 15
            signals.append("🟢 Strong uptrend (price > SMA20 > SMA50)")
        elif current_price < sma_20 < sma_50:
            score -= 15
            signals.append("🔴 Strong downtrend (price < SMA20 < SMA50)")
        elif current_price > sma_20:
            score += 8
            signals.append("🟡 Price above short-term average")
        else:
            score -= 8
            signals.append("🟡 Price below short-term average")

    # Bollinger Bands (20 points)
    bb_lower = technical_indicators.get('BB_lower')
    bb_upper = technical_indicators.get('BB_upper')
    if current_price and bb_lower and bb_upper:
        bb_position = (current_price - bb_lower) / (bb_upper - bb_lower)
        if bb_position < 0.2:
            score += 10
            signals.append("🟢 Near lower Bollinger Band")
        elif bb_position > 0.8:
            score -= 10
            signals.append("🔴 Near upper Bollinger Band")

    # Ensure score is within 0-100
    score = max(0, min(100, score))

    # Determine overall signal
    if score >= 70:
        overall = "🟢 STRONG BUY"
    elif score >= 55:
        overall = "🟡 BUY"
    elif score >= 45:
        overall = "⚪ NEUTRAL"
    elif score >= 30:
        overall = "🟠 SELL"
    else:
        overall = "🔴 STRONG SELL"

    return score, overall, signals


def get_sector_performance():
    """Get performance data for all sectors."""
    market_data = MarketDataService(settings=settings)
    sector_data = []

    for sector_name, sector_info in SECTORS.items():
        etf_symbol = sector_info["etf"]

        # Get historical data for the sector ETF
        historical_data = market_data.get_historical_data(
            etf_symbol, period="1mo", interval="1d"
        )

        if historical_data is not None and not historical_data.empty:
            # Calculate performance
            start_price = historical_data['Close'].iloc[0]
            end_price = historical_data['Close'].iloc[-1]
            performance = ((end_price - start_price) / start_price) * 100

            # Get technical indicators
            technical = market_data.calculate_technical_indicators(etf_symbol, period="3mo")

            sector_data.append({
                'Sector': sector_name,
                'ETF': etf_symbol,
                'Performance (1M)': performance,
                'Current Price': end_price,
                'Technical': technical,
                'Description': sector_info['description']
            })

    market_data.close()
    return pd.DataFrame(sector_data)


def analyze_stock_timing(symbol):
    """Analyze if it's a good time to buy a specific stock."""
    market_data = MarketDataService(settings=settings)

    try:
        # Get technical indicators
        technical = market_data.calculate_technical_indicators(symbol, period="6mo")

        if not technical:
            return None

        # Get current price
        current_price = market_data.get_current_price(symbol)
        if current_price:
            technical['current_price'] = current_price

        # Get historical data for chart
        historical = market_data.get_historical_data(symbol, period="6mo", interval="1d")

        # Calculate buy signal
        score, overall, signals = calculate_buy_signal_score(technical)

        return {
            'symbol': symbol,
            'current_price': current_price,
            'technical': technical,
            'historical': historical,
            'buy_score': score,
            'buy_signal': overall,
            'signals': signals
        }

    finally:
        market_data.close()


def plot_sector_performance(sector_df):
    """Create bar chart for sector performance."""
    if sector_df.empty:
        return None

    # Sort by performance
    df_sorted = sector_df.sort_values('Performance (1M)', ascending=True)

    # Color code based on performance
    colors = ['red' if x < 0 else 'green' for x in df_sorted['Performance (1M)']]

    fig = go.Figure(data=[
        go.Bar(
            y=df_sorted['Sector'],
            x=df_sorted['Performance (1M)'],
            orientation='h',
            marker_color=colors,
            text=[f"{x:.2f}%" for x in df_sorted['Performance (1M)']],
            textposition='outside'
        )
    ])

    fig.update_layout(
        title="Sector Performance (Last 30 Days)",
        xaxis_title="Performance (%)",
        yaxis_title="Sector",
        height=500,
        showlegend=False
    )

    return fig


def plot_stock_chart(historical_data, symbol):
    """Create candlestick chart with moving averages."""
    if historical_data is None or historical_data.empty:
        return None

    fig = go.Figure()

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=historical_data.index,
        open=historical_data['Open'],
        high=historical_data['High'],
        low=historical_data['Low'],
        close=historical_data['Close'],
        name=symbol
    ))

    # Add moving averages if available
    if 'SMA_20' in historical_data.columns:
        fig.add_trace(go.Scatter(
            x=historical_data.index,
            y=historical_data['SMA_20'],
            name='SMA 20',
            line=dict(color='orange', width=1)
        ))

    if 'SMA_50' in historical_data.columns:
        fig.add_trace(go.Scatter(
            x=historical_data.index,
            y=historical_data['SMA_50'],
            name='SMA 50',
            line=dict(color='blue', width=1)
        ))

    fig.update_layout(
        title=f"{symbol} - 6 Month Price Chart",
        xaxis_title="Date",
        yaxis_title="Price ($)",
        height=500,
        xaxis_rangeslider_visible=False
    )

    return fig


def main():
    """Main function for investment analysis page."""
    # Sidebar navigation
    show_navigation()

    st.title("🔍 Investment Analysis")
    st.markdown("### Research buy opportunities and sector attractiveness")
    st.info("📌 This is a research tool - no real transactions are made here.")
    st.markdown("---")

    # Create tabs
    tab1, tab2, tab3 = st.tabs([
        "📊 Sector Overview",
        "🎯 Stock Buy Timing",
        "🔥 Sector Deep Dive"
    ])

    # Tab 1: Sector Overview
    with tab1:
        st.subheader("Market Sector Performance")
        st.markdown("Compare sector performance and identify attractive sectors")

        if st.button("🔄 Refresh Sector Data", key="refresh_sectors"):
            with st.spinner("Analyzing all sectors..."):
                sector_df = get_sector_performance()
                st.session_state['sector_data'] = sector_df

        # Load or display cached data
        if 'sector_data' not in st.session_state:
            with st.spinner("Loading sector data..."):
                sector_df = get_sector_performance()
                st.session_state['sector_data'] = sector_df
        else:
            sector_df = st.session_state['sector_data']

        if not sector_df.empty:
            # Display chart
            fig = plot_sector_performance(sector_df)
            if fig:
                st.plotly_chart(fig, use_container_width=True)

            # Display table
            st.markdown("#### Detailed Sector Data")
            display_df = sector_df[['Sector', 'ETF', 'Performance (1M)', 'Current Price', 'Description']].copy()
            display_df['Performance (1M)'] = display_df['Performance (1M)'].apply(lambda x: f"{x:.2f}%")
            display_df['Current Price'] = display_df['Current Price'].apply(lambda x: f"${x:.2f}")

            st.dataframe(display_df, use_container_width=True, hide_index=True)

            # Highlight best and worst
            col1, col2 = st.columns(2)
            with col1:
                best_sector = sector_df.loc[sector_df['Performance (1M)'].idxmax()]
                st.success(f"🏆 **Best Performing**: {best_sector['Sector']} ({best_sector['Performance (1M)']:.2f}%)")

            with col2:
                worst_sector = sector_df.loc[sector_df['Performance (1M)'].idxmin()]
                st.error(f"📉 **Worst Performing**: {worst_sector['Sector']} ({worst_sector['Performance (1M)']:.2f}%)")
        else:
            st.warning("No sector data available")

    # Tab 2: Stock Buy Timing
    with tab2:
        st.subheader("Analyze When to Buy a Stock")
        st.markdown("Get technical analysis and buy signals for specific stocks")

        col1, col2 = st.columns([3, 1])
        with col1:
            stock_symbol = st.text_input(
                "Enter Stock Symbol",
                placeholder="e.g., AAPL, TSLA, MSFT",
                key="stock_symbol"
            ).upper()

        with col2:
            analyze_button = st.button("🔍 Analyze", key="analyze_stock", type="primary")

        if analyze_button and stock_symbol:
            with st.spinner(f"Analyzing {stock_symbol}..."):
                analysis = analyze_stock_timing(stock_symbol)

            if analysis:
                # Display buy score prominently
                col1, col2, col3 = st.columns([1, 2, 1])

                with col2:
                    st.markdown("### Buy Signal Score")
                    score = analysis['buy_score']
                    signal = analysis['buy_signal']

                    # Create gauge chart for score
                    fig_gauge = go.Figure(go.Indicator(
                        mode="gauge+number",
                        value=score,
                        domain={'x': [0, 1], 'y': [0, 1]},
                        title={'text': signal, 'font': {'size': 24}},
                        gauge={
                            'axis': {'range': [None, 100]},
                            'bar': {'color': "darkblue"},
                            'steps': [
                                {'range': [0, 30], 'color': "red"},
                                {'range': [30, 45], 'color': "orange"},
                                {'range': [45, 55], 'color': "yellow"},
                                {'range': [55, 70], 'color': "lightgreen"},
                                {'range': [70, 100], 'color': "green"}
                            ],
                            'threshold': {
                                'line': {'color': "black", 'width': 4},
                                'thickness': 0.75,
                                'value': score
                            }
                        }
                    ))

                    fig_gauge.update_layout(height=300)
                    st.plotly_chart(fig_gauge, use_container_width=True)

                # Display signals
                st.markdown("#### 📈 Technical Signals")
                for signal_text in analysis['signals']:
                    st.markdown(f"- {signal_text}")

                # Display price and technical data
                col1, col2, col3, col4 = st.columns(4)
                technical = analysis['technical']

                with col1:
                    st.metric("Current Price", f"${analysis['current_price']:.2f}")

                with col2:
                    rsi = technical.get('RSI_14')
                    st.metric("RSI (14)", f"{rsi:.2f}" if rsi else "N/A")

                with col3:
                    sma_20 = technical.get('SMA_20')
                    st.metric("SMA (20)", f"${sma_20:.2f}" if sma_20 else "N/A")

                with col4:
                    sma_50 = technical.get('SMA_50')
                    st.metric("SMA (50)", f"${sma_50:.2f}" if sma_50 else "N/A")

                # Display chart
                st.markdown("#### 📊 Price Chart")
                fig_chart = plot_stock_chart(analysis['historical'], stock_symbol)
                if fig_chart:
                    st.plotly_chart(fig_chart, use_container_width=True)

                # Add interpretation
                st.markdown("#### 💡 Interpretation Guide")
                st.markdown("""
                - **Score 70-100**: Strong technical indicators suggest good buying opportunity
                - **Score 55-69**: Moderate buy signals, favorable conditions
                - **Score 45-54**: Neutral, no clear buy or sell signal
                - **Score 30-44**: Weak signals, may want to wait
                - **Score 0-29**: Overbought or negative indicators, avoid buying

                ⚠️ **Remember**: Technical analysis is just one tool. Consider fundamentals, news, and your investment goals.
                """)
            else:
                st.error(f"Could not analyze {stock_symbol}. Please check the symbol and try again.")

        elif analyze_button:
            st.warning("Please enter a stock symbol")

    # Tab 3: Sector Deep Dive
    with tab3:
        st.subheader("Explore Stocks by Sector")
        st.markdown("Analyze top stocks within each sector")

        selected_sector = st.selectbox(
            "Select a Sector",
            options=list(SECTORS.keys()),
            key="selected_sector"
        )

        if selected_sector:
            sector_info = SECTORS[selected_sector]

            st.markdown(f"#### {selected_sector}")
            st.markdown(f"*{sector_info['description']}*")
            st.markdown(f"**Sector ETF**: {sector_info['etf']}")

            st.markdown("#### Top Stocks in this Sector")

            # Analyze each stock in the sector
            if st.button(f"🔍 Analyze {selected_sector} Stocks", key="analyze_sector_stocks"):
                stock_results = []

                progress_bar = st.progress(0)
                status_text = st.empty()

                for idx, stock in enumerate(sector_info['stocks']):
                    status_text.text(f"Analyzing {stock}...")

                    analysis = analyze_stock_timing(stock)
                    if analysis:
                        stock_results.append({
                            'Symbol': stock,
                            'Price': f"${analysis['current_price']:.2f}",
                            'Buy Score': analysis['buy_score'],
                            'Signal': analysis['buy_signal'],
                            'RSI': f"{analysis['technical'].get('RSI_14', 0):.2f}"
                        })

                    progress_bar.progress((idx + 1) / len(sector_info['stocks']))

                status_text.empty()
                progress_bar.empty()

                # Display results
                if stock_results:
                    df_results = pd.DataFrame(stock_results)
                    df_results = df_results.sort_values('Buy Score', ascending=False)

                    st.dataframe(df_results, use_container_width=True, hide_index=True)

                    # Highlight best opportunity
                    best_stock = df_results.iloc[0]
                    st.success(f"🎯 **Top Opportunity**: {best_stock['Symbol']} with buy score of {best_stock['Buy Score']:.0f}")
                else:
                    st.warning("Could not analyze stocks in this sector")

    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray;'>"
        "💡 This tool provides research and analysis only. Always do your own due diligence before investing."
        "</div>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
