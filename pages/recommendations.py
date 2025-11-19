"""
AI Recommendations page for trading decisions.
"""

import streamlit as st
import json
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from services import DecisionEngineService, PortfolioService
from config import settings


st.set_page_config(page_title="Recommendations", page_icon="🤖", layout="wide")


def display_decision(decision):
    """Display a single decision card."""
    # Determine color based on decision type
    if decision.decision_type == "BUY":
        color = "green"
        icon = "📈"
    elif decision.decision_type == "SELL":
        color = "red"
        icon = "📉"
    else:
        color = "gray"
        icon = "➡️"

    with st.container():
        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])

        with col1:
            st.markdown(f"### {icon} {decision.symbol}")
            st.write(f"**Type:** :{color}[{decision.decision_type}]")

        with col2:
            st.metric("Confidence", f"{decision.confidence_score:.1%}")
            if decision.recommended_price:
                st.write(f"**Price:** ${decision.recommended_price:.2f}")

        with col3:
            if decision.recommended_quantity:
                st.write(f"**Quantity:** {decision.recommended_quantity:.0f} shares")
            st.write(f"**Status:** {decision.status}")

        with col4:
            st.write(f"**Date:**")
            st.write(decision.decision_date.strftime("%Y-%m-%d"))

        # Show reasoning
        if decision.reasoning:
            with st.expander("View Analysis"):
                st.write("**AI Reasoning:**")
                st.info(decision.reasoning)

                # Technical signals
                if decision.technical_signals:
                    try:
                        tech_signals = json.loads(decision.technical_signals)
                        st.write("**Technical Signals:**")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.json({"trend": tech_signals.get("ma_trend"),
                                   "rsi": tech_signals.get("rsi_signal"),
                                   "macd": tech_signals.get("macd_signal")})
                        with col2:
                            st.json({"bb_signal": tech_signals.get("bb_signal"),
                                   "technical_score": tech_signals.get("technical_score")})
                    except:
                        pass

                # Fundamental signals
                if decision.fundamental_signals:
                    try:
                        fund_signals = json.loads(decision.fundamental_signals)
                        st.write("**Fundamental Signals:**")
                        st.json({k: v for k, v in fund_signals.items()
                               if k in ['pe_signal', 'growth_signal', 'profitability_signal', 'fundamental_score']})
                    except:
                        pass

        # Action buttons for pending decisions
        if decision.status == "PENDING":
            col1, col2, col3 = st.columns([1, 1, 4])
            with col1:
                if st.button("Accept", key=f"accept_{decision.id}", type="primary"):
                    decision.accept_decision()
                    st.session_state.db_session.commit()
                    st.success("Decision accepted")
                    st.rerun()
            with col2:
                if st.button("Reject", key=f"reject_{decision.id}"):
                    decision.reject_decision()
                    st.session_state.db_session.commit()
                    st.warning("Decision rejected")
                    st.rerun()

        st.markdown("---")


def generate_recommendation_section(decision_service, portfolio_service):
    """Section for generating new recommendations."""
    st.subheader("Generate New Recommendation")

    portfolios = portfolio_service.get_all_portfolios()
    if not portfolios:
        st.info("No portfolios available. Create a portfolio first.")
        return

    with st.form("generate_recommendation_form"):
        col1, col2 = st.columns(2)

        with col1:
            portfolio_names = [p.name for p in portfolios]
            selected_portfolio_name = st.selectbox("Select Portfolio", portfolio_names)
            selected_portfolio = next(p for p in portfolios if p.name == selected_portfolio_name)

        with col2:
            symbol = st.text_input("Stock Symbol*", placeholder="AAPL").upper()

        use_ai = st.checkbox("Use AI Reasoning", value=settings.ENABLE_AI_REASONING)

        submitted = st.form_submit_button("Generate Recommendation", type="primary")

        if submitted:
            if not symbol:
                st.error("Please provide a stock symbol")
            else:
                with st.spinner(f"Analyzing {symbol}..."):
                    try:
                        decision = decision_service.generate_decision(
                            portfolio_id=selected_portfolio.id,
                            symbol=symbol,
                            use_ai_reasoning=use_ai
                        )

                        if decision:
                            st.success(f"Recommendation generated for {symbol}")
                            st.rerun()
                        else:
                            st.error("Failed to generate recommendation. Check if symbol is valid.")

                    except Exception as e:
                        st.error(f"Error generating recommendation: {e}")


def main():
    st.title("AI Recommendations")
    st.markdown("Get AI-powered trading recommendations based on technical and fundamental analysis")
    st.markdown("---")

    decision_service = DecisionEngineService(settings=settings)
    portfolio_service = PortfolioService(settings=settings)

    # Store db_session in session_state for button callbacks
    if 'db_session' not in st.session_state:
        st.session_state.db_session = decision_service.db_session

    # Generate new recommendation section
    with st.expander("Generate New Recommendation", expanded=True):
        generate_recommendation_section(decision_service, portfolio_service)

    st.markdown("---")

    # View existing recommendations
    st.subheader("Recent Recommendations")

    portfolios = portfolio_service.get_all_portfolios()
    if portfolios:
        # Portfolio filter
        portfolio_names = ["All"] + [p.name for p in portfolios]
        selected_portfolio_filter = st.selectbox("Filter by Portfolio", portfolio_names)

        # Status filter
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "PENDING", "ACCEPTED", "REJECTED", "EXECUTED"]
        )

        # Get decisions
        all_decisions = []
        if selected_portfolio_filter == "All":
            for portfolio in portfolios:
                decisions = decision_service.get_portfolio_decisions(
                    portfolio.id,
                    status=None if status_filter == "All" else status_filter,
                    limit=50
                )
                all_decisions.extend(decisions)
        else:
            selected_portfolio = next(p for p in portfolios if p.name == selected_portfolio_filter)
            all_decisions = decision_service.get_portfolio_decisions(
                selected_portfolio.id,
                status=None if status_filter == "All" else status_filter,
                limit=50
            )

        # Sort by date
        all_decisions.sort(key=lambda d: d.decision_date, reverse=True)

        if all_decisions:
            st.write(f"**Showing {len(all_decisions)} recommendations**")
            st.markdown("---")

            for decision in all_decisions:
                display_decision(decision)
        else:
            st.info("No recommendations found. Generate a new recommendation above.")

    decision_service.close()
    portfolio_service.close()


if __name__ == "__main__":
    main()
