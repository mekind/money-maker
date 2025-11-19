"""
Portfolio Management page for creating and managing portfolios and positions.
"""

import streamlit as st
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from services import PortfolioService, MarketDataService
from config import settings


st.set_page_config(page_title="Portfolio", page_icon="💼", layout="wide")


def create_portfolio_section(portfolio_service):
    """Section for creating new portfolios."""
    st.subheader("Create New Portfolio")

    with st.form("create_portfolio_form"):
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("Portfolio Name*", placeholder="My Investment Portfolio")
            initial_capital = st.number_input(
                "Initial Capital*",
                min_value=1000.0,
                value=100000.0,
                step=1000.0,
                format="%.2f"
            )

        with col2:
            description = st.text_area("Description", placeholder="Optional description")
            currency = st.selectbox("Currency", ["USD", "EUR", "GBP", "JPY", "CNY"])

        submitted = st.form_submit_button("Create Portfolio", type="primary")

        if submitted:
            if not name:
                st.error("Please provide a portfolio name")
            else:
                try:
                    portfolio = portfolio_service.create_portfolio(
                        name=name,
                        initial_capital=initial_capital,
                        description=description,
                        currency=currency
                    )
                    st.success(f"Portfolio '{name}' created successfully")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error creating portfolio: {e}")


def manage_positions_section(portfolio_service, market_service):
    """Section for managing positions."""
    st.subheader("Manage Positions")

    portfolios = portfolio_service.get_all_portfolios()
    if not portfolios:
        st.info("No portfolios available. Create a portfolio first.")
        return

    portfolio_names = [p.name for p in portfolios]
    selected_portfolio_name = st.selectbox("Select Portfolio", portfolio_names, key="position_portfolio")

    selected_portfolio = next(p for p in portfolios if p.name == selected_portfolio_name)

    tab1, tab2, tab3 = st.tabs(["Open Position", "Close Position", "Cash Management"])

    # Tab 1: Open Position
    with tab1:
        with st.form("open_position_form"):
            col1, col2 = st.columns(2)

            with col1:
                symbol = st.text_input("Stock Symbol*", placeholder="AAPL", help="Enter ticker symbol").upper()
                quantity = st.number_input("Quantity*", min_value=1, value=100, step=1)
                entry_price = st.number_input("Entry Price*", min_value=0.01, value=100.0, step=0.01)

            with col2:
                position_type = st.selectbox("Position Type", ["LONG", "SHORT"])
                stop_loss = st.number_input("Stop Loss (Optional)", min_value=0.0, value=0.0, step=0.01)
                take_profit = st.number_input("Take Profit (Optional)", min_value=0.0, value=0.0, step=0.01)

            notes = st.text_area("Notes (Optional)")

            submitted = st.form_submit_button("Open Position", type="primary")

            if submitted:
                if not symbol:
                    st.error("Please provide a stock symbol")
                else:
                    try:
                        # Fetch current price to verify symbol
                        current_price = market_service.get_current_price(symbol)
                        if current_price:
                            st.info(f"Current market price for {symbol}: ${current_price:.2f}")

                        position = portfolio_service.open_position(
                            portfolio_id=selected_portfolio.id,
                            symbol=symbol,
                            quantity=quantity,
                            entry_price=entry_price,
                            position_type=position_type,
                            stop_loss=stop_loss if stop_loss > 0 else None,
                            take_profit=take_profit if take_profit > 0 else None,
                            notes=notes
                        )

                        if position:
                            st.success(f"Opened {position_type} position: {symbol} x {quantity} @ ${entry_price:.2f}")
                            st.rerun()
                        else:
                            st.error("Failed to open position. Check cash balance.")

                    except Exception as e:
                        st.error(f"Error opening position: {e}")

    # Tab 2: Close Position
    with tab2:
        positions = portfolio_service.get_portfolio_positions(selected_portfolio.id, open_only=True)

        if not positions:
            st.info("No open positions to close")
        else:
            position_options = [f"{p.symbol} (x{p.quantity:.0f})" for p in positions]
            selected_position_str = st.selectbox("Select Position to Close", position_options)

            # Find selected position
            selected_idx = position_options.index(selected_position_str)
            selected_position = positions[selected_idx]

            # Show position details
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Current Price", f"${selected_position.current_price:.2f}")
            with col2:
                pnl = selected_position.calculate_pnl()
                st.metric("Current P&L", f"${pnl:.2f}", f"{selected_position.calculate_pnl_percentage():.2f}%")
            with col3:
                st.metric("Entry Price", f"${selected_position.average_entry_price:.2f}")

            with st.form("close_position_form"):
                closing_price = st.number_input(
                    "Closing Price",
                    value=selected_position.current_price,
                    min_value=0.01,
                    step=0.01
                )
                close_notes = st.text_area("Notes (Optional)")

                submitted = st.form_submit_button("Close Position", type="secondary")

                if submitted:
                    try:
                        success = portfolio_service.close_position(
                            selected_position.id,
                            closing_price=closing_price,
                            notes=close_notes
                        )

                        if success:
                            st.success(f"Position closed: {selected_position.symbol}")
                            st.rerun()
                        else:
                            st.error("Failed to close position")

                    except Exception as e:
                        st.error(f"Error closing position: {e}")

    # Tab 3: Cash Management
    with tab3:
        col1, col2 = st.columns(2)

        with col1:
            st.write("**Add Cash**")
            with st.form("add_cash_form"):
                add_amount = st.number_input("Amount to Add", min_value=0.01, value=1000.0, step=100.0)
                add_notes = st.text_input("Notes")
                if st.form_submit_button("Add Cash"):
                    if portfolio_service.add_cash(selected_portfolio.id, add_amount, add_notes):
                        st.success(f"Added ${add_amount:,.2f}")
                        st.rerun()

        with col2:
            st.write("**Withdraw Cash**")
            with st.form("withdraw_cash_form"):
                withdraw_amount = st.number_input("Amount to Withdraw", min_value=0.01, value=1000.0, step=100.0)
                withdraw_notes = st.text_input("Notes ", key="withdraw_notes")
                if st.form_submit_button("Withdraw Cash"):
                    if portfolio_service.withdraw_cash(selected_portfolio.id, withdraw_amount, withdraw_notes):
                        st.success(f"Withdrew ${withdraw_amount:,.2f}")
                        st.rerun()
                    else:
                        st.error("Insufficient cash balance")


def main():
    st.title("Portfolio Management")
    st.markdown("---")

    portfolio_service = PortfolioService(settings=settings)
    market_service = MarketDataService(settings=settings)

    # Create portfolio section
    with st.expander("Create New Portfolio", expanded=False):
        create_portfolio_section(portfolio_service)

    st.markdown("---")

    # Manage positions section
    manage_positions_section(portfolio_service, market_service)

    # Show existing portfolios
    st.markdown("---")
    st.subheader("Existing Portfolios")

    portfolios = portfolio_service.get_all_portfolios(active_only=False)

    if portfolios:
        for portfolio in portfolios:
            status_icon = "Active" if portfolio.is_active else "Inactive"
            with st.expander(f"{portfolio.name} ({status_icon})"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**Initial Capital:** ${portfolio.initial_capital:,.2f}")
                    st.write(f"**Cash Balance:** ${portfolio.cash_balance:,.2f}")
                with col2:
                    st.write(f"**Currency:** {portfolio.currency}")
                    st.write(f"**Status:** {status_icon}")
                with col3:
                    total_value = portfolio.calculate_total_value()
                    pnl = portfolio.calculate_total_pnl()
                    st.write(f"**Total Value:** ${total_value:,.2f}")
                    st.write(f"**Total P&L:** ${pnl:,.2f}")

                if portfolio.description:
                    st.write(f"**Description:** {portfolio.description}")

    portfolio_service.close()
    market_service.close()


if __name__ == "__main__":
    main()
