"""
Risk Analysis page for portfolio risk metrics and assessment.
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from services import RiskManagementService, PortfolioService
from config import settings


st.set_page_config(page_title="Risk Analysis", page_icon="⚠️", layout="wide")


def plot_correlation_heatmap(correlation_matrix):
    """Create correlation heatmap."""
    if correlation_matrix is None:
        return None

    fig = go.Figure(data=go.Heatmap(
        z=correlation_matrix.values,
        x=correlation_matrix.columns,
        y=correlation_matrix.index,
        colorscale='RdYlGn',
        zmid=0,
        text=correlation_matrix.values,
        texttemplate='%{text:.2f}',
        textfont={"size": 10}
    ))

    fig.update_layout(
        title="Position Correlation Matrix",
        height=500
    )

    return fig


def display_risk_metrics(risk_summary):
    """Display risk metrics in organized layout."""
    if not risk_summary:
        st.warning("Unable to calculate risk metrics")
        return

    # Value at Risk
    if risk_summary.get('value_at_risk'):
        var_data = risk_summary['value_at_risk']
        st.subheader("Value at Risk (VaR)")
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                f"VaR ({var_data.get('confidence_level', 0.95):.0%} Confidence)",
                f"${var_data.get('var_amount', 0):,.2f}"
            )
        with col2:
            st.metric(
                "VaR Percentage",
                f"{var_data.get('var_percent', 0):.2f}%"
            )
        with col3:
            st.metric(
                "Time Horizon",
                f"{var_data.get('time_horizon_days', 1)} day(s)"
            )

        st.markdown("---")

    # Risk-Adjusted Returns
    st.subheader("Risk-Adjusted Returns")
    col1, col2 = st.columns(2)

    with col1:
        sharpe = risk_summary.get('sharpe_ratio')
        if sharpe is not None:
            st.metric("Sharpe Ratio", f"{sharpe:.3f}")
            if sharpe > 1:
                st.success("Excellent risk-adjusted returns")
            elif sharpe > 0.5:
                st.info("Good risk-adjusted returns")
            else:
                st.warning("Poor risk-adjusted returns")

    with col2:
        sortino = risk_summary.get('sortino_ratio')
        if sortino is not None:
            st.metric("Sortino Ratio", f"{sortino:.3f}")
            if sortino > 1:
                st.success("Excellent downside risk management")
            elif sortino > 0.5:
                st.info("Good downside risk management")
            else:
                st.warning("Poor downside risk management")

    st.markdown("---")

    # Maximum Drawdown
    if risk_summary.get('max_drawdown'):
        dd_data = risk_summary['max_drawdown']
        st.subheader("Drawdown Analysis")
        col1, col2 = st.columns(2)

        with col1:
            max_dd = dd_data.get('max_drawdown_percent', 0)
            st.metric("Maximum Drawdown", f"{max_dd:.2f}%")
            if max_dd < 10:
                st.success("Low drawdown risk")
            elif max_dd < 20:
                st.info("Moderate drawdown risk")
            else:
                st.warning("High drawdown risk")

        with col2:
            current_dd = dd_data.get('current_drawdown_percent', 0)
            st.metric("Current Drawdown", f"{current_dd:.2f}%")


def position_sizing_calculator(risk_service, portfolio_service):
    """Position sizing calculator section."""
    st.subheader("Position Sizing Calculator")

    portfolios = portfolio_service.get_all_portfolios()
    if not portfolios:
        st.info("No portfolios available")
        return

    with st.form("position_sizing_form"):
        col1, col2 = st.columns(2)

        with col1:
            portfolio_names = [p.name for p in portfolios]
            selected_portfolio_name = st.selectbox("Select Portfolio", portfolio_names)
            selected_portfolio = next(p for p in portfolios if p.name == selected_portfolio_name)

            symbol = st.text_input("Stock Symbol*", placeholder="AAPL").upper()

        with col2:
            risk_per_trade = st.number_input(
                "Risk Per Trade (%)",
                min_value=0.1,
                max_value=10.0,
                value=settings.DEFAULT_POSITION_SIZE_PERCENT * 100,
                step=0.1,
                format="%.1f"
            ) / 100

            stop_loss_pct = st.number_input(
                "Stop Loss (%)",
                min_value=0.1,
                max_value=20.0,
                value=settings.DEFAULT_STOP_LOSS_PERCENT * 100,
                step=0.1,
                format="%.1f"
            ) / 100

        submitted = st.form_submit_button("Calculate Position Size", type="primary")

        if submitted:
            if not symbol:
                st.error("Please provide a stock symbol")
            else:
                try:
                    sizing = risk_service.calculate_position_size(
                        portfolio_id=selected_portfolio.id,
                        symbol=symbol,
                        risk_per_trade=risk_per_trade,
                        stop_loss_percent=stop_loss_pct
                    )

                    st.success("Position sizing calculated")

                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.metric("Recommended Shares", f"{sizing['recommended_shares']:,.0f}")
                        st.metric("Current Price", f"${sizing['current_price']:.2f}")

                    with col2:
                        st.metric("Position Value", f"${sizing['position_value']:,.2f}")
                        st.metric("Stop Loss Price", f"${sizing['stop_loss_price']:.2f}")

                    with col3:
                        st.metric("Risk Amount", f"${sizing['risk_amount']:,.2f}")
                        st.metric("Max Loss", f"${sizing['max_loss']:,.2f}")

                except Exception as e:
                    st.error(f"Error calculating position size: {e}")


def main():
    st.title("Risk Analysis")
    st.markdown("Advanced risk management and portfolio analysis tools")
    st.markdown("---")

    risk_service = RiskManagementService(settings=settings)
    portfolio_service = PortfolioService(settings=settings)

    # Position sizing calculator
    with st.expander("Position Sizing Calculator", expanded=False):
        position_sizing_calculator(risk_service, portfolio_service)

    st.markdown("---")

    # Portfolio risk analysis
    st.subheader("Portfolio Risk Metrics")

    portfolios = portfolio_service.get_all_portfolios()
    if not portfolios:
        st.info("No portfolios available. Create a portfolio first.")
        return

    portfolio_names = [p.name for p in portfolios]
    selected_portfolio_name = st.selectbox("Select Portfolio for Analysis", portfolio_names)

    selected_portfolio = next(p for p in portfolios if p.name == selected_portfolio_name)

    if st.button("Calculate Risk Metrics", type="primary"):
        with st.spinner("Calculating risk metrics..."):
            try:
                risk_summary = risk_service.get_portfolio_risk_summary(selected_portfolio.id)

                if risk_summary:
                    display_risk_metrics(risk_summary)
                else:
                    st.warning("Unable to calculate risk metrics. Ensure portfolio has positions with sufficient historical data.")

            except Exception as e:
                st.error(f"Error calculating risk metrics: {e}")

    st.markdown("---")

    # Correlation analysis
    st.subheader("Correlation Analysis")

    positions = portfolio_service.get_portfolio_positions(selected_portfolio.id)

    if len(positions) >= 2:
        if st.button("Generate Correlation Matrix"):
            with st.spinner("Calculating correlations..."):
                try:
                    correlation_matrix = risk_service.calculate_correlation_matrix(
                        selected_portfolio.id,
                        period='6mo'
                    )

                    if correlation_matrix is not None:
                        heatmap = plot_correlation_heatmap(correlation_matrix)
                        if heatmap:
                            st.plotly_chart(heatmap, use_container_width=True)

                        st.write("**Correlation Matrix:**")
                        st.dataframe(correlation_matrix.style.background_gradient(cmap='RdYlGn', vmin=-1, vmax=1))

                        st.info("""
                        **Interpretation:**
                        - Values close to +1 indicate strong positive correlation
                        - Values close to -1 indicate strong negative correlation
                        - Values close to 0 indicate no correlation
                        - Diversification is better when correlations are low or negative
                        """)
                    else:
                        st.warning("Unable to calculate correlation matrix")

                except Exception as e:
                    st.error(f"Error calculating correlations: {e}")
    else:
        st.info("Need at least 2 positions to calculate correlation matrix")

    st.markdown("---")

    # Individual position risk
    st.subheader("Position Risk Assessment")

    if positions:
        position_options = [f"{p.symbol} (x{p.quantity:.0f})" for p in positions]
        selected_position_str = st.selectbox("Select Position", position_options)

        selected_idx = position_options.index(selected_position_str)
        selected_position = positions[selected_idx]

        if st.button("Assess Position Risk"):
            with st.spinner("Assessing position risk..."):
                try:
                    risk_assessment = risk_service.assess_position_risk(selected_position.id)

                    if risk_assessment:
                        col1, col2, col3, col4 = st.columns(4)

                        with col1:
                            st.metric("Current P&L", f"${risk_assessment['current_pnl']:,.2f}")

                        with col2:
                            st.metric("P&L %", f"{risk_assessment['pnl_percent']:.2f}%")

                        with col3:
                            volatility = risk_assessment.get('volatility')
                            if volatility:
                                st.metric("Volatility", f"{volatility:.2%}")

                        with col4:
                            beta = risk_assessment.get('beta')
                            if beta:
                                st.metric("Beta", f"{beta:.2f}")

                        # Risk level indicator
                        risk_level = risk_assessment.get('risk_level', 'UNKNOWN')
                        if risk_level == 'HIGH':
                            st.error(f"Risk Level: {risk_level}")
                        elif risk_level == 'MEDIUM':
                            st.warning(f"Risk Level: {risk_level}")
                        else:
                            st.success(f"Risk Level: {risk_level}")

                        # Stop loss status
                        if risk_assessment.get('has_stop_loss'):
                            st.info(f"Stop Loss: ${risk_assessment['stop_loss_price']:.2f}")
                        else:
                            st.warning("No stop loss set")

                except Exception as e:
                    st.error(f"Error assessing position risk: {e}")
    else:
        st.info("No open positions to analyze")

    risk_service.close()
    portfolio_service.close()


if __name__ == "__main__":
    main()
