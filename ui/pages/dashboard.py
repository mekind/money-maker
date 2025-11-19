"""
Dashboard page showing portfolio overview and key metrics.
"""

import streamlit as st
import plotly.graph_objects as go
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from services import PortfolioService, MarketDataService
from config import settings


st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")


def plot_portfolio_allocation(positions):
    """Create pie chart for portfolio allocation."""
    if not positions:
        return None

    symbols = [pos.symbol for pos in positions]
    values = [pos.calculate_current_value() for pos in positions]

    fig = go.Figure(data=[go.Pie(
        labels=symbols,
        values=values,
        hole=0.3,
        textinfo='label+percent'
    )])

    fig.update_layout(
        title="Portfolio Allocation",
        height=400
    )

    return fig


def plot_position_pnl(positions):
    """Create bar chart for position P&L."""
    if not positions:
        return None

    symbols = [pos.symbol for pos in positions]
    pnls = [pos.calculate_pnl() for pos in positions]
    colors = ['green' if pnl >= 0 else 'red' for pnl in pnls]

    fig = go.Figure(data=[go.Bar(
        x=symbols,
        y=pnls,
        marker_color=colors,
        text=[f'${pnl:,.2f}' for pnl in pnls],
        textposition='auto'
    )])

    fig.update_layout(
        title="Position P&L",
        xaxis_title="Symbol",
        yaxis_title="P&L ($)",
        height=400
    )

    return fig


def main():
    st.title("Dashboard")
    st.markdown("---")

    # Initialize services
    portfolio_service = PortfolioService(settings=settings)
    market_service = MarketDataService(settings=settings)

    # Get all portfolios
    portfolios = portfolio_service.get_all_portfolios()

    if not portfolios:
        st.warning("No portfolios found. Please create a portfolio first.")
        st.info("Go to the Portfolio page to create your first portfolio.")
        return

    # Portfolio selector
    portfolio_names = [p.name for p in portfolios]
    selected_portfolio_name = st.selectbox("Select Portfolio", portfolio_names)

    selected_portfolio = next(p for p in portfolios if p.name == selected_portfolio_name)

    if selected_portfolio:
        # Get portfolio summary
        summary = portfolio_service.get_portfolio_summary(selected_portfolio.id)

        if summary:
            # Key metrics row
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    "Total Value",
                    f"${summary['total_value']:,.2f}",
                    f"{summary['return_percentage']:.2f}%"
                )

            with col2:
                st.metric(
                    "Cash Balance",
                    f"${summary['cash_balance']:,.2f}"
                )

            with col3:
                pnl_delta = summary['total_pnl']
                st.metric(
                    "Total P&L",
                    f"${abs(pnl_delta):,.2f}",
                    f"{summary['return_percentage']:.2f}%",
                    delta_color="normal" if pnl_delta >= 0 else "inverse"
                )

            with col4:
                st.metric(
                    "Open Positions",
                    summary['num_positions']
                )

            st.markdown("---")

            # Get positions
            positions = portfolio_service.get_portfolio_positions(selected_portfolio.id)

            if positions:
                # Charts row
                col1, col2 = st.columns(2)

                with col1:
                    allocation_chart = plot_portfolio_allocation(positions)
                    if allocation_chart:
                        st.plotly_chart(allocation_chart, use_container_width=True)

                with col2:
                    pnl_chart = plot_position_pnl(positions)
                    if pnl_chart:
                        st.plotly_chart(pnl_chart, use_container_width=True)

                st.markdown("---")

                # Positions table
                st.subheader("Current Positions")

                positions_data = []
                for pos in positions:
                    pnl = pos.calculate_pnl()
                    pnl_pct = pos.calculate_pnl_percentage()

                    positions_data.append({
                        'Symbol': pos.symbol,
                        'Quantity': f"{pos.quantity:,.0f}",
                        'Entry Price': f"${pos.average_entry_price:,.2f}",
                        'Current Price': f"${pos.current_price:,.2f}",
                        'Value': f"${pos.calculate_current_value():,.2f}",
                        'P&L': f"${pnl:,.2f}",
                        'P&L %': f"{pnl_pct:.2f}%",
                        'Type': pos.position_type
                    })

                st.dataframe(positions_data, use_container_width=True)

                # Update prices button
                if st.button("Update Prices", type="primary"):
                    with st.spinner("Updating prices..."):
                        updated = portfolio_service.update_position_prices(selected_portfolio.id)
                        st.success(f"Updated {updated} positions")
                        st.rerun()

            else:
                st.info("No open positions in this portfolio.")

    portfolio_service.close()
    market_service.close()


if __name__ == "__main__":
    main()
