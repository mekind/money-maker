"""
Navigation utility for consistent sidebar navigation across all pages.
"""

import streamlit as st


def show_navigation():
    """
    Display navigation hint in sidebar.

    Note: Streamlit automatically adds pages from the 'pages/' directory to the sidebar.
    This function just adds additional information or styling.
    """
    st.sidebar.markdown("---")
    st.sidebar.info("👈 Use the navigation above to switch between pages")
    st.sidebar.markdown("---")
