"""
Main Streamlit application for Money Management Service.
Entry point for the web interface.
"""

import streamlit as st
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config import settings
from models import init_db
from utils import show_navigation
from loguru import logger


# Configure logger
logger.add(
    "logs/app.log", rotation="1 day", retention="7 days", level=settings.LOG_LEVEL
)


def init_application():
    """Initialize the application."""
    try:
        # Initialize database
        init_db()
        logger.info("Application initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing application: {e}")
        st.error(f"Failed to initialize application: {e}")


def configure_page():
    """Configure Streamlit page settings."""
    st.set_page_config(
        page_title=settings.APP_NAME,
        page_icon="💰",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def main():
    """Main application entry point."""
    configure_page()
    init_application()

    # Sidebar navigation
    show_navigation()

    # Main title
    st.title(f"💰 {settings.APP_NAME}")
    st.markdown("### AI-Powered Investment Decision Support System")
    st.markdown("---")

    # Welcome message
    st.info(
        """
    👋 **Welcome to your Money Management Service!**

    This application helps you make informed investment decisions through:
    - 📈 Real-time market data and technical analysis
    - 🤖 AI-powered trading recommendations
    - ⚠️ Advanced risk management tools
    - 📊 Portfolio tracking and performance analytics
    - 🔔 Custom alerts and notifications

    👈 **Navigate using the sidebar** to access different features.
    """
    )

    # Quick stats (if portfolios exist)
    st.markdown("### 🚀 Quick Start")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.info(
            "**1. Research Investments**\n\nUse Investment Analysis to find buy opportunities"
        )

    with col2:
        st.info(
            "**2. Create Portfolio**\n\nGo to Portfolio page to create your first portfolio"
        )

    with col3:
        st.info(
            "**3. Get Recommendations**\n\nVisit Recommendations page for AI-powered insights"
        )

    with col4:
        st.info(
            "**4. Monitor Risk**\n\nCheck Risk Analysis for portfolio health metrics"
        )

    # Footer
    st.markdown("---")
    st.markdown(
        f"<div style='text-align: center; color: gray;'>"
        f"Environment: {settings.APP_ENV.upper()} | "
        f"Version: 1.0.0"
        f"</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
