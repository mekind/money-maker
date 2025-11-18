# Money Management Service

AI-Powered Investment Decision Support System for Quantitative Trading

## Overview

A comprehensive money management and trading decision support system that combines technical analysis, fundamental data, risk management, and AI-powered reasoning to help you make informed investment decisions.

## Features

- **Portfolio Management**: Create and manage multiple investment portfolios
- **Real-Time Market Data**: Integration with Yahoo Finance for live market data
- **Technical Analysis**: 15+ technical indicators (SMA, EMA, RSI, MACD, Bollinger Bands, OBV)
- **Fundamental Analysis**: P/E ratios, growth metrics, profitability, financial health
- **AI-Powered Recommendations**: Claude AI integration for intelligent decision reasoning
- **Risk Management**: VaR, Sharpe/Sortino ratios, correlation analysis, position sizing
- **Interactive Dashboard**: Real-time portfolio visualization and performance tracking
- **Alert System**: Customizable alerts for price and indicator thresholds

## Technology Stack

- **Backend**: Python 3.10+
- **Web Framework**: Streamlit 1.51.0
- **Database**: SQLAlchemy with SQLite/PostgreSQL
- **AI Integration**: Anthropic Claude API
- **Data Sources**: yfinance, pandas-ta
- **Visualization**: Plotly

## Architecture

Built following OOP principles and design patterns:

- **Singleton Pattern**: DatabaseManager, SettingsManager, Services
- **Repository Pattern**: Clean separation of data access
- **Service Layer**: Business logic isolation
- **Dependency Injection**: Flexible component composition

### Project Structure

```
quant-trading/
├── config/                 # Configuration management
│   └── settings.py        # Settings with Pydantic validation
├── models/                # Database models
│   ├── base.py           # Base model classes
│   ├── database.py       # Database manager (Singleton)
│   ├── portfolio.py      # Portfolio & Position models
│   ├── transaction.py    # Transaction model
│   ├── decision.py       # AI decision model
│   └── alert.py          # Alert model
├── services/              # Business logic services
│   ├── base_service.py   # Base service class
│   ├── market_data_service.py
│   ├── portfolio_service.py
│   ├── risk_service.py
│   └── decision_service.py
├── ui/                    # Streamlit UI
│   └── pages/            # UI pages
│       ├── dashboard.py
│       ├── portfolio.py
│       ├── recommendations.py
│       └── risk_analysis.py
├── app.py                # Main application entry point
└── requirements.txt      # Python dependencies
```

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd quant-trading
```

### 2. Create Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```env
# Required for AI-powered recommendations
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional
OPENAI_API_KEY=your_openai_api_key_here
```

### 5. Initialize Database

The database will be automatically created on first run. By default, it uses SQLite.

## Usage

### Start the Application

```bash
streamlit run app.py
```

The application will open in your browser at `http://localhost:8501`

### Quick Start Guide

1. **Create a Portfolio**
   - Navigate to "Portfolio" page
   - Click "Create New Portfolio"
   - Enter initial capital and details

2. **Open Positions**
   - Go to "Portfolio" page
   - Use "Open Position" tab
   - Enter symbol, quantity, and price

3. **Get AI Recommendations**
   - Visit "Recommendations" page
   - Enter stock symbol
   - Click "Generate Recommendation"
   - Review AI analysis and accept/reject

4. **Monitor Risk**
   - Check "Risk Analysis" page
   - View VaR, Sharpe ratio, drawdown
   - Use position sizing calculator
   - Analyze correlation matrix

5. **Track Performance**
   - Dashboard shows real-time portfolio value
   - View P&L by position
   - Portfolio allocation charts

## Configuration

### Environment Variables

Key configuration options in `.env`:

```env
# Application
APP_ENV=development
DEBUG=True
LOG_LEVEL=INFO

# Database
DATABASE_URL=sqlite:///./money_management.db

# Risk Management
DEFAULT_POSITION_SIZE_PERCENT=0.05  # 5% per trade
MAX_POSITION_SIZE_PERCENT=0.20      # 20% max allocation
DEFAULT_STOP_LOSS_PERCENT=0.05      # 5% stop loss

# AI Decision Engine
MIN_CONFIDENCE_THRESHOLD=0.60       # 60% minimum confidence
ENABLE_AI_REASONING=True
AI_MODEL=claude-sonnet-4-5-20250929
```

## Core Services

### MarketDataService (Singleton)
- Fetches real-time and historical market data
- Calculates technical indicators
- Retrieves fundamental data
- Caches data for performance

### PortfolioService
- Portfolio CRUD operations
- Position management (open/close)
- Transaction tracking
- Cash management
- Performance analytics

### RiskManagementService
- Value at Risk (VaR) calculation
- Sharpe and Sortino ratios
- Maximum drawdown analysis
- Position sizing (Kelly Criterion)
- Correlation analysis
- Beta calculation

### DecisionEngineService
- Multi-factor analysis (technical + fundamental)
- AI-powered reasoning (Claude integration)
- Confidence scoring
- Decision tracking and outcomes

## Database Schema

### Core Tables

- **portfolios**: Portfolio information and balances
- **positions**: Open and closed positions
- **transactions**: All buy/sell operations
- **decisions**: AI-generated recommendations
- **alerts**: Price and indicator alerts

All models include:
- Automatic timestamps (created_at, updated_at)
- Built-in business logic methods
- Validation and constraints

## Development

### Running Tests

```bash
pytest tests/
```

### Code Quality

```bash
# Format code
black .

# Lint code
flake8 .

# Type checking
mypy .
```

## Design Patterns Used

1. **Singleton Pattern**: Database and service managers
2. **Repository Pattern**: Data access abstraction
3. **Factory Pattern**: Model creation
4. **Strategy Pattern**: Different analysis strategies
5. **Observer Pattern**: Alert system
6. **Dependency Injection**: Service composition

## License

GNU Affero General Public License v3.0

---

Built with Python and AI for intelligent money management.