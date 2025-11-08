# Hyper Alpha Arena - Project Structure Documentation

## Project Overview

**Hyper Alpha Arena** is an open-source AI-powered cryptocurrency trading platform that enables autonomous trading with Large Language Models (LLMs). The platform supports both paper trading (risk-free simulation) and real trading on Hyperliquid DEX (testnet & mainnet).

**Current Version**: v0.5.0

**Key Features**:
- Paper Trading: Risk-free simulation with real market data
- Real Trading: Live perpetual contract trading on Hyperliquid DEX
- Multi-Model LLM Support: GPT-5, Claude, Deepseek integration
- 1-50x Leverage: Perpetual contracts on decentralized exchanges
- Real-time Updates: WebSocket-based live data streaming

---

## Directory Structure

### Root Level

```
/Hyper-Alpha-Arena/
├── backend/              # Python FastAPI backend (15,734 lines of code)
├── frontend/             # React + TypeScript frontend (48 component files)
├── docker-compose.yml    # Multi-service orchestration
├── Dockerfile            # Multi-stage build (frontend + backend)
├── package.json          # Workspace root (pnpm monorepo)
├── init-db.sh            # PostgreSQL initialization script
└── README.md             # Comprehensive documentation
```

---

## Backend Architecture (`/backend/`)

### Overview
Python FastAPI backend with 15,734 lines of code organized in a layered architecture pattern.

### Directory Structure

```
backend/
├── api/                  # FastAPI route handlers (15 route files)
│   ├── account_routes.py         # AI trader account management
│   ├── hyperliquid_routes.py     # Hyperliquid DEX integration
│   ├── order_routes.py           # Order execution & management
│   ├── market_data_routes.py     # Real-time market data
│   ├── prompt_routes.py          # AI prompt template management
│   └── ws.py                     # WebSocket real-time communication
│
├── database/             # Data layer & models
│   ├── models.py                 # SQLAlchemy ORM models
│   ├── connection.py             # PostgreSQL connection pool
│   ├── snapshot_models.py        # Historical snapshot tables
│   └── migrations/               # Database schema migrations
│
├── services/             # Business logic layer (27 service files)
│   ├── ai_decision_service.py    # LLM API integration & decision engine
│   ├── trading_strategy.py       # Trading strategy execution
│   ├── hyperliquid_trading_client.py  # Hyperliquid DEX client
│   ├── order_matching.py         # Paper trading order simulation
│   ├── scheduler.py              # APScheduler task management
│   ├── market_data.py            # CCXT market data fetching
│   └── system_logger.py          # Centralized logging system
│
├── repositories/         # Data access layer (6 repository files)
│   ├── account_repo.py           # Account CRUD operations
│   ├── prompt_repo.py            # Prompt template management
│   └── strategy_repo.py          # Strategy configuration
│
├── schemas/              # Pydantic data validation
│   ├── account.py                # Account request/response schemas
│   ├── order.py                  # Order schemas
│   └── prompt.py                 # Prompt schemas
│
├── config/               # Configuration files
│   ├── settings.py               # Market configs (commission, rates)
│   └── prompt_templates.py       # Default AI prompt templates
│
├── factors/              # Technical analysis indicators
│   ├── momentum.py               # Momentum indicators
│   └── support.py                # Support/resistance levels
│
├── utils/                # Utility functions
│   └── encryption.py             # Fernet encryption for private keys
│
└── main.py               # FastAPI application entry point
```

### Backend Technologies

- **Framework**: FastAPI (Python 3.11) - Modern async web framework
- **Database**: PostgreSQL 14 with SQLAlchemy 2.0 ORM
- **Real-time**: WebSockets for live data streaming
- **Task Scheduling**: APScheduler for automated trading triggers
- **Market Data**: CCXT library for multi-exchange integration
- **Blockchain**: eth-account for Ethereum wallet management
- **Security**: Cryptography (Fernet) for private key encryption
- **Package Manager**: uv (ultra-fast Python package installer)

---

## Frontend Architecture (`/frontend/`)

### Overview
React 18 + TypeScript SPA with 48 component files, built with Vite and styled with Tailwind CSS.

### Directory Structure

```
frontend/
├── app/
│   ├── components/       # React components
│   │   ├── hyperliquid/          # Hyperliquid DEX UI
│   │   │   ├── HyperliquidPage.tsx
│   │   │   ├── BalanceCard.tsx
│   │   │   ├── OrderForm.tsx
│   │   │   ├── PositionsTable.tsx
│   │   │   └── ConfigPanel.tsx
│   │   ├── trader/               # AI Trader management
│   │   │   └── TraderManagement.tsx
│   │   ├── portfolio/            # Portfolio views
│   │   ├── prompt/               # Prompt template editor
│   │   ├── layout/               # Layout components
│   │   ├── trading/              # Trading interface
│   │   └── ui/                   # shadcn/ui components
│   │
│   ├── contexts/         # React Context providers
│   │   ├── ArenaDataContext.tsx  # Global state management
│   │   └── TradingModeContext.tsx # Paper/Real mode switching
│   │
│   ├── lib/              # Utility libraries
│   │   └── api.ts                # API client functions
│   │
│   ├── main.tsx          # React application entry point
│   └── index.css         # Tailwind CSS styles
│
├── package.json          # Frontend dependencies
├── vite.config.ts        # Vite build configuration
└── tailwind.config.js    # Tailwind CSS configuration
```

### Frontend Technologies

- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite 4 (fast HMR and bundling)
- **Styling**: Tailwind CSS + shadcn/ui components
- **Charts**:
  - recharts (asset curves)
  - chart.js + react-chartjs-2
  - lightweight-charts (trading view)
- **UI Components**: Radix UI primitives
- **State Management**: React Context API
- **Notifications**: react-hot-toast

---

## System Architecture

### Layered Architecture Pattern

```
┌─────────────────────────────────────────────────────────┐
│                  Presentation Layer                      │
│  React SPA (WebSocket + REST) | shadcn/ui Components    │
└─────────────────────────────────────────────────────────┘
                      ↕
┌─────────────────────────────────────────────────────────┐
│                  Application Layer                       │
│  FastAPI Routes | WebSocket Handlers | Middleware       │
└─────────────────────────────────────────────────────────┘
                      ↕
┌─────────────────────────────────────────────────────────┐
│                   Business Layer                         │
│  Trading Strategy | AI Decision | Order Execution       │
│  Risk Management | Market Data Aggregation              │
└─────────────────────────────────────────────────────────┘
                      ↕
┌─────────────────────────────────────────────────────────┐
│                   Data Access Layer                      │
│  Repositories | SQLAlchemy ORM | Query Builders         │
└─────────────────────────────────────────────────────────┘
                      ↕
┌─────────────────────────────────────────────────────────┐
│                   Persistence Layer                      │
│  PostgreSQL (Main DB + Snapshots DB)                    │
└─────────────────────────────────────────────────────────┘

        ┌───────────────────────────────┐
        │    External Integrations      │
        ├───────────────────────────────┤
        │  • LLM APIs (OpenAI, Claude)  │
        │  • Hyperliquid DEX Blockchain │
        │  • CCXT (Multi-exchange data) │
        │  • Ethereum Wallet            │
        └───────────────────────────────┘
```

### Component Relationships

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (React + TS)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Hyperliquid  │  │   Trader     │  │  Portfolio   │      │
│  │     Page     │  │  Management  │  │    View      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         │                  │                  │              │
│         └──────────────────┼──────────────────┘              │
│                            │                                 │
│                    WebSocket + REST API                      │
└────────────────────────────┼─────────────────────────────────┘
                             │
┌────────────────────────────┼─────────────────────────────────┐
│                  Backend (FastAPI)                           │
│                            │                                 │
│  ┌─────────────────────────┴──────────────────────────┐     │
│  │              API Routes Layer                      │     │
│  │  account_routes | hyperliquid_routes | ws.py       │     │
│  └─────────────────────────┬──────────────────────────┘     │
│                            │                                 │
│  ┌─────────────────────────┴──────────────────────────┐     │
│  │           Services Layer (Business Logic)          │     │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐│     │
│  │  │AI Decision  │  │  Trading    │  │ Hyperliquid ││     │
│  │  │   Service   │  │  Strategy   │  │   Client    ││     │
│  │  └─────────────┘  └─────────────┘  └─────────────┘│     │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐│     │
│  │  │   Market    │  │   Order     │  │  Scheduler  ││     │
│  │  │    Data     │  │  Matching   │  │             ││     │
│  │  └─────────────┘  └─────────────┘  └─────────────┘│     │
│  └─────────────────────────┬──────────────────────────┘     │
│                            │                                 │
│  ┌─────────────────────────┴──────────────────────────┐     │
│  │         Repositories Layer (Data Access)           │     │
│  │  account_repo | prompt_repo | strategy_repo        │     │
│  └─────────────────────────┬──────────────────────────┘     │
│                            │                                 │
│  ┌─────────────────────────┴──────────────────────────┐     │
│  │              Database Models (ORM)                 │     │
│  │  Account | Position | Order | Trade | AIDecision   │     │
│  └─────────────────────────┬──────────────────────────┘     │
└────────────────────────────┼─────────────────────────────────┘
                             │
                    ┌────────┴────────┐
                    │   PostgreSQL    │
                    │   (2 databases) │
                    │ alpha_arena +   │
                    │ alpha_snapshots │
                    └─────────────────┘
```

---

## Trading Decision Flow

```
1. Trigger Event
   ├─ Scheduled (cron: every 5/15/30/60 min)
   └─ Real-time (WebSocket market data)
          ↓
2. AI Decision Service
   ├─ Fetch market data (CCXT/Hyperliquid)
   ├─ Build prompt context (positions, balance, news)
   ├─ Call LLM API (OpenAI/Anthropic/Deepseek)
   └─ Parse AI response (structured JSON)
          ↓
3. Trading Strategy Service
   ├─ Validate AI decision
   ├─ Apply risk management rules
   └─ Generate trade commands
          ↓
4. Order Execution (dual path)
   ├─ Paper Trading → Order Matching Service (simulated)
   └─ Real Trading → Hyperliquid Trading Client (blockchain)
          ↓
5. Position Management
   ├─ Update account balances
   ├─ Record trades & P&L
   └─ Snapshot to database
          ↓
6. Real-time Updates
   └─ Broadcast via WebSocket → Frontend UI
```

---

## Key Architectural Patterns

1. **Monorepo Structure**: pnpm workspace with backend + frontend
2. **Repository Pattern**: Data access abstraction (`repositories/`)
3. **Service Layer Pattern**: Business logic separation (`services/`)
4. **DTO/Schema Pattern**: Pydantic validation (`schemas/`)
5. **Dependency Injection**: FastAPI's `Depends()` for DB sessions
6. **Real-time Communication**: WebSocket for live updates
7. **Task Scheduling**: APScheduler for cron-like automation
8. **Database Per Context**: Separate DBs for operational data vs snapshots
9. **Encryption at Rest**: Fernet symmetric encryption for private keys
10. **Multi-stage Docker Build**: Optimized container images

---

## Trading Modes

The system operates in **dual mode**:

### 1. Paper Trading Mode
- Simulated order matching engine
- Risk-free strategy testing
- Full feature parity with real trading
- Historical backtesting capabilities

### 2. Hyperliquid Real Trading Mode
- Live blockchain transactions
- 1-50x leverage perpetual contracts
- Testnet and mainnet environments
- Auto-pause on 80% margin usage
- Real-time position monitoring

---

## Data Flow

### Key Data Relationships

1. **AI Decision Service** ↔ **LLM APIs**: Sends prompts, receives trading decisions
2. **Scheduler** → **Trading Strategy**: Triggers automated trading cycles
3. **Market Data** → **AI Context**: Feeds real-time prices to decision engine
4. **Hyperliquid Client** ↔ **Blockchain**: Executes real perpetual contracts
5. **WebSocket** ↔ **Frontend**: Bi-directional real-time communication
6. **Snapshot Service** → **Database**: Historical performance tracking

### Database Schema

**Main Database (`alpha_arena`)**:
- `accounts` - AI trader accounts
- `positions` - Current open positions
- `orders` - Order history
- `trades` - Executed trades
- `ai_decisions` - LLM decision logs
- `prompt_templates` - AI prompt configurations

**Snapshots Database (`alpha_snapshots`)**:
- Historical snapshots for performance analysis
- Time-series data for portfolio tracking
- Audit trail for regulatory compliance

---

## Security Features

- **Private Key Encryption**: Fernet symmetric encryption with key rotation
- **Environment Isolation**: Strict testnet/mainnet separation
- **API Key Storage**: Encrypted in PostgreSQL
- **CORS Configuration**: Controlled API access
- **No Password Storage**: Single-user mode (default user only)

---

## DevOps & Deployment

### Infrastructure

- **Containerization**: Docker multi-stage builds
- **Orchestration**: Docker Compose (2 services: app + postgres)
- **Proxy**: FastAPI serves static frontend (SPA routing)
- **Hot Reload**: Custom file watcher for frontend auto-rebuild
- **Workspace**: pnpm monorepo with workspace support

### Performance Optimizations

- **Price Caching**: Redis-like in-memory cache for market data
- **Asset Curve Caching**: Computed performance metrics cached
- **WebSocket Broadcasting**: Efficient real-time updates
- **Database Connection Pooling**: SQLAlchemy engine optimization
- **Frontend Hot Reload**: Custom file watcher for development

---

## Project Statistics

- **Backend Code**: 15,734 lines of Python
- **Frontend Components**: 48 TypeScript component files
- **Architecture**: Full-stack integration with React + FastAPI + PostgreSQL
- **Trading Modes**: Dual mode (paper + real blockchain trading)
- **LLM Support**: Multi-model via OpenAI-compatible APIs
- **Real-time**: WebSocket-based live data streaming

---

## Getting Started

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Node.js 18+ (for local development)
- PostgreSQL 14+ (or use Docker)

### Quick Start

```bash
# Clone the repository
git clone <repository-url>
cd Hyper-Alpha-Arena

# Start with Docker Compose
docker-compose up --build

# Access the application
# Frontend: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

For detailed setup instructions, refer to the main [README.md](./README.md).

---

## Contributing

This is an open-source project. Contributions are welcome! Please refer to the contribution guidelines in the README.

## License

Refer to the LICENSE file in the repository root.
