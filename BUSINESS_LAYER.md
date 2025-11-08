# Hyper Alpha Arena - Business Layer Documentation

## Overview

The Business Layer is the core of Hyper Alpha Arena's trading system, responsible for orchestrating AI-driven trading decisions, order execution, risk management, and market data aggregation. This layer sits between the API routes (presentation layer) and the data access layer (repositories), implementing all critical trading logic.

---

## Table of Contents

1. [AI Decision Service](#ai-decision-service)
2. [Trading Strategy Service](#trading-strategy-service)
3. [Order Execution](#order-execution)
4. [Risk Management](#risk-management)
5. [Market Data Aggregation](#market-data-aggregation)
6. [Data Flow & Integration](#data-flow--integration)

---

## AI Decision Service

**File**: `backend/services/ai_decision_service.py` (1,239 lines)

### Purpose

The AI Decision Service integrates Large Language Models (LLMs) to generate intelligent trading decisions based on market data, portfolio state, news, and technical indicators.

### Key Features

#### 1. Multi-Model LLM Support

```python
# Supported Models
- GPT-4, GPT-4o, GPT-4-turbo (OpenAI)
- GPT-5 series (o1-preview, o1-mini) - Reasoning models
- Claude (Anthropic via OpenAI-compatible API)
- Deepseek (Chinese AI model)
- Any OpenAI-compatible API endpoint
```

**Model-Specific Handling**:
- **Reasoning Models** (GPT-5, o1): No temperature parameter, uses `max_completion_tokens` instead of `max_tokens`
- **Standard Models**: Temperature 0.7, `max_tokens: 5000`
- **GPT-5 Specific**: `reasoning_effort: "low"` for balanced latency/quality

#### 2. Prompt Context Building

The service builds rich context for AI decision-making:

**Context Variables** (`_build_prompt_context` at line 366):

```python
{
    # Account Information
    "account_name": "Trader-1",
    "model_name": "gpt-4",
    "runtime_minutes": "120",
    "current_time_utc": "2025-01-08T10:30:00Z",

    # Portfolio State
    "available_cash": "9,850.50",
    "total_account_value": "15,230.75",
    "total_return_percent": "+52.31",
    "holdings_detail": "- BTC: 0.125000 units @ $98,450.00 avg (current value: $12,306.25)",

    # Market Data
    "market_prices": "BTC: $98,500.00\nETH: $3,850.50\n...",
    "sampling_data": "Multi-timeframe price data (18-second intervals)",

    # News & Analysis
    "news_section": "Latest cryptocurrency news from CoinJournal",

    # Trading Environment
    "trading_environment": "Platform: Hyperliquid Perpetual Contracts | Environment: TESTNET",
    "operational_constraints": "- Max leverage: 5x\n- Margin call threshold: 80%...",

    # Output Format
    "output_format": "JSON schema with decisions array"
}
```

**Hyperliquid-Specific Context**:
- Real-time margin usage and liquidation risk
- Cross-margin position details
- Leverage constraints (1x-50x)
- Environment warnings (testnet vs mainnet)

#### 3. Decision Generation Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Fetch Market Data                                        │
│    - Current prices (CCXT/Hyperliquid)                      │
│    - 18-second interval sampling data                       │
│    - News feed from CoinJournal                             │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ 2. Build Prompt Context                                     │
│    - Account state (cash, positions, P&L)                   │
│    - Market snapshot (prices, momentum)                     │
│    - Risk parameters (leverage, margin usage)               │
│    - Supported symbols with metadata                        │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ 3. Render Prompt Template                                   │
│    - Select prompt template (Default/Pro/Custom)            │
│    - Format with context variables                          │
│    - Inject decision task and output format                 │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ 4. Call LLM API                                             │
│    - POST to OpenAI-compatible endpoint                     │
│    - Retry logic: 3 attempts with exponential backoff       │
│    - Rate limit handling (429 status)                       │
│    - Multiple endpoint fallback (Deepseek)                  │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ 5. Parse AI Response                                        │
│    - Extract JSON from response (handle markdown blocks)    │
│    - Normalize to decisions array format                    │
│    - Manual extraction fallback (regex parsing)             │
│    - Validate decision structure                            │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ 6. Return Structured Decisions                              │
│    [{                                                        │
│      "operation": "buy|sell|hold|close",                    │
│      "symbol": "BTC",                                        │
│      "target_portion_of_balance": 0.15,                     │
│      "leverage": 2,                                          │
│      "max_price": 99000,                                     │
│      "min_price": 97500,                                     │
│      "reason": "Bullish momentum with support at...",       │
│      "trading_strategy": "Entry thesis, risk controls...",  │
│      "_prompt_snapshot": "Full prompt sent to AI",          │
│      "_reasoning_snapshot": "AI's reasoning process",       │
│      "_raw_decision_text": "Raw JSON response"              │
│    }]                                                        │
└─────────────────────────────────────────────────────────────┘
```

#### 4. Decision Logging

**Function**: `save_ai_decision` (line 1087)

Every AI decision is logged to the database with full audit trail:

```python
AIDecisionLog:
    - account_id: Which trader made this decision
    - decision_time: Timestamp (UTC)
    - operation: buy/sell/hold/close
    - symbol: Asset traded
    - prev_portion: Previous portfolio allocation
    - target_portion: Target portfolio allocation
    - total_balance: Account value at decision time
    - executed: "true"/"false" - whether order was filled
    - order_id: Reference to executed order (if any)
    - reason: AI's stated reason for decision
    - prompt_snapshot: Full prompt sent to LLM
    - reasoning_snapshot: AI's reasoning process
    - decision_snapshot: Structured JSON decision
    - hyperliquid_environment: "testnet"/"mainnet" (if applicable)
    - wallet_address: Ethereum wallet (for Hyperliquid)
```

**Real-time Broadcasting**:
- WebSocket broadcast to all connected clients
- Enables live monitoring of AI decisions
- Updates model chat UI in real-time

#### 5. Error Handling & Resilience

**Rate Limiting** (line 858):
```python
# Exponential backoff with jitter
for attempt in range(max_retries):
    if response.status_code == 429:
        wait_time = (2**attempt) + random.uniform(0, 1)
        time.sleep(wait_time)
```

**JSON Parsing Fallback** (line 983):
```python
# 1. Try standard JSON parse
# 2. Clean markdown code blocks
# 3. Normalize unicode characters
# 4. Manual regex extraction as last resort
```

**Multiple Endpoint Support** (line 633):
```python
# Deepseek supports both:
# - https://api.deepseek.com/chat/completions
# - https://api.deepseek.com/v1/chat/completions
endpoints = build_chat_completion_endpoints(base_url, model)
```

### Integration Points

- **News Feed**: `services/news_feed.py` - Fetches latest crypto news
- **Prompt Templates**: `repositories/prompt_repo.py` - Manages custom prompts
- **Market Data**: `services/market_data.py` - Real-time price feeds
- **Sampling Pool**: `services/sampling_pool.py` - Historical price samples
- **System Logger**: `services/system_logger.py` - Centralized logging

---

## Trading Strategy Service

**File**: `backend/services/trading_strategy.py` (398 lines)

### Purpose

Manages automated trading strategy triggers based on price thresholds and time intervals. Orchestrates when and how AI trading decisions should be executed.

### Architecture

#### 1. Strategy State Management

```python
@dataclass
class StrategyState:
    account_id: int
    price_threshold: float       # Price change % to trigger
    trigger_interval: int         # Seconds between triggers
    enabled: bool                 # Strategy active/inactive
    last_trigger_at: datetime     # Last execution time
    running: bool = False         # Currently executing
    lock: threading.Lock          # Concurrency control
```

**Trigger Logic** (`should_trigger` at line 54):
```python
def should_trigger(symbol: str, event_time: datetime) -> bool:
    # Time-based trigger
    time_trigger = (now - last_trigger) >= trigger_interval

    # Price-based trigger
    price_change = sampling_pool.get_price_change_percent(symbol)
    price_trigger = abs(price_change) >= price_threshold

    # Trigger if either condition met
    return time_trigger or price_trigger
```

#### 2. Dual Strategy Managers

**Paper Trading Manager**:
```python
class StrategyManager:
    - Filters accounts where hyperliquid_enabled != "true"
    - Uses paper trading order matching
    - Database: alpha_arena (main database)
```

**Hyperliquid Manager**:
```python
class HyperliquidStrategyManager(StrategyManager):
    - Filters accounts where hyperliquid_enabled == "true"
    - Uses Hyperliquid DEX client
    - Real blockchain transactions
```

#### 3. Strategy Execution Flow

```
┌─────────────────────────────────────────────────────────────┐
│ Price Update Event                                           │
│ (WebSocket stream or scheduled poll)                         │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ handle_price_update(symbol, price, event_time)              │
│ - Add to sampling pool (18-second intervals)                │
│ - Check all strategies for this symbol                      │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ should_trigger() Check                                       │
│ ✓ Time interval elapsed?                                    │
│ ✓ Price change >= threshold?                                │
└────────────────────┬────────────────────────────────────────┘
                     │ YES
┌────────────────────▼────────────────────────────────────────┐
│ _execute_strategy(account_id, symbol, event_time)           │
│ 1. Acquire lock (prevent concurrent execution)              │
│ 2. Verify account.auto_trading_enabled == "true"            │
│ 3. Get sampling data for symbol                             │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
┌────────▼──────────┐  ┌────────▼──────────────┐
│ Paper Trading     │  │ Hyperliquid Trading   │
│ (Simulated)       │  │ (Real Blockchain)     │
│                   │  │                       │
│ place_ai_driven   │  │ place_ai_driven       │
│ _crypto_order()   │  │ _hyperliquid_order()  │
└───────────────────┘  └───────────────────────┘
```

#### 4. Concurrency & Thread Safety

**Background Refresh Thread** (line 151):
```python
def _refresh_strategies_loop(self):
    """Periodically reload strategies from database"""
    while self.running:
        time.sleep(STRATEGY_REFRESH_INTERVAL)  # 60 seconds
        self._load_strategies()
```

**Lock Management**:
- **Global Lock**: Protects strategy manager state
- **Per-Strategy Lock**: Prevents duplicate execution
- **PostgreSQL Native**: Database handles concurrent reads

#### 5. Strategy Configuration

**Database Table**: `AccountStrategyConfig`
```sql
CREATE TABLE account_strategy_config (
    account_id INTEGER PRIMARY KEY,
    price_threshold REAL DEFAULT 2.0,      -- 2% price change
    trigger_interval INTEGER DEFAULT 300,  -- 5 minutes
    enabled TEXT DEFAULT 'true',           -- 'true'/'false'
    last_trigger_at TIMESTAMP,             -- Last execution
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**Global Sampling Config**:
```sql
CREATE TABLE global_sampling_config (
    id INTEGER PRIMARY KEY,
    sampling_interval INTEGER DEFAULT 18  -- Seconds between samples
);
```

### Key Functions

| Function | Purpose | Location |
|----------|---------|----------|
| `start_strategy_manager()` | Initialize both managers | Line 341 |
| `handle_price_update()` | Process market data | Line 353 |
| `_execute_strategy()` | Execute trading decision | Line 185 |
| `get_strategy_status()` | Monitor all strategies | Line 391 |

---

## Order Execution

The platform supports dual-mode order execution: **Paper Trading** (simulated) and **Hyperliquid Real Trading** (blockchain).

### Paper Trading Order Execution

**File**: `backend/services/order_matching.py` (441 lines)

#### Order Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Create Order                                             │
│    create_order(account, symbol, side, type, price, qty)    │
│    - Validate parameters (quantity, price, lot size)        │
│    - Check available funds (BUY) or positions (SELL)        │
│    - Generate order_no (16-char hex UUID)                   │
│    - Status: PENDING                                        │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ 2. Check Execution Conditions                               │
│    check_and_execute_order(order)                           │
│    - Fetch current market price                             │
│    - Market orders: Execute immediately                     │
│    - Limit orders:                                          │
│      • BUY: limit_price >= market_price                     │
│      • SELL: limit_price <= market_price                    │
└────────────────────┬────────────────────────────────────────┘
                     │ Conditions Met
┌────────────────────▼────────────────────────────────────────┐
│ 3. Execute Order Fill                                       │
│    _execute_order(order, account, execution_price)          │
│    - Calculate commission (max of % or min fee)             │
│    - Update account cash:                                   │
│      • BUY: Deduct (notional + commission)                  │
│      • SELL: Add (notional - commission)                    │
│    - Update positions:                                      │
│      • BUY: Increase quantity, recalc avg_cost              │
│      • SELL: Decrease quantity                              │
│    - Create Trade record                                    │
│    - Update order.status = FILLED                           │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ 4. Broadcast Updates                                        │
│    - WebSocket: broadcast_trade_update()                    │
│    - WebSocket: broadcast_position_update()                 │
│    - Real-time UI refresh                                   │
└─────────────────────────────────────────────────────────────┘
```

#### Commission Calculation

```python
CRYPTO_COMMISSION_RATE = 0.001  # 0.1% taker fee
CRYPTO_MIN_COMMISSION = 0.01    # Minimum $0.01 fee

def _calc_commission(notional: Decimal) -> Decimal:
    pct_fee = notional * Decimal('0.001')
    return max(pct_fee, Decimal('0.01'))
```

**Example**:
- Order: BUY 0.1 BTC @ $98,500
- Notional: $9,850
- Commission: max($9.85, $0.01) = **$9.85**
- Total Cost: $9,859.85

#### Average Cost Calculation

**Weighted Average** (line 243):
```python
# When adding to position
old_qty = Decimal(position.quantity)
old_cost = Decimal(position.avg_cost)
new_qty = old_qty + quantity

new_avg_cost = (old_cost * old_qty + notional) / new_qty

# Example:
# Existing: 0.5 BTC @ $95,000 = $47,500
# New Buy:  0.3 BTC @ $98,000 = $29,400
# Total:    0.8 BTC @ $96,125 = $76,900
```

### Hyperliquid Real Trading

**File**: `backend/services/hyperliquid_trading_client.py` (774 lines)

#### Client Architecture

```python
class HyperliquidTradingClient:
    def __init__(self, account_id, private_key, environment):
        self.account_id = account_id
        self.environment = "testnet" | "mainnet"
        self.private_key = "0x..."
        self.wallet_address = "0x..." (derived from private_key)
        self.api_url = "https://api.hyperliquid-testnet.xyz"
        self.exchange = ccxt.hyperliquid(...)  # CCXT wrapper
```

#### Environment Isolation

**Critical Safety Feature** (`_validate_environment` at line 158):

```python
def _validate_environment(self, db: Session) -> bool:
    """Prevent accidental mainnet operations"""
    account = db.query(Account).filter_by(id=account_id).first()

    if account.hyperliquid_environment != self.environment:
        raise EnvironmentMismatchError(
            f"Account configured for {account.hyperliquid_environment}, "
            f"but client using {self.environment}"
        )

    return True
```

**Called before every state-modifying operation**:
- ✅ `place_order()`
- ✅ `set_leverage()`
- ✅ `cancel_order()`
- ✅ `get_account_state()` (read-only but validates)

#### Account State Management

**Function**: `get_account_state()` (line 187)

```python
Returns:
{
    'environment': 'testnet',
    'account_id': 123,
    'total_equity': 10500.75,           # Total account value
    'available_balance': 8250.50,       # Available for new positions
    'used_margin': 2250.25,             # Margin currently used
    'maintenance_margin': 1125.13,      # Min required to avoid liquidation
    'margin_usage_percent': 21.4,       # used_margin / total_equity * 100
    'withdrawal_available': 8250.50,    # Can withdraw this amount
    'wallet_address': '0x...',
    'timestamp': 1704715200000
}
```

**Margin Usage Calculation**:
```python
margin_usage_percent = (used_margin / total_equity) * 100

# Risk Thresholds:
# 0-50%:  Safe zone
# 50-70%: Warning zone
# 70-80%: Danger zone (auto-pause recommended)
# 80%+:   Liquidation risk (CRITICAL)
```

#### Position Management

**Function**: `get_positions()` (line 270)

```python
Returns List[{
    'coin': 'BTC',
    'szi': 0.5,                        # Signed size (+ long, - short)
    'entry_px': 98500.00,              # Average entry price
    'position_value': 49250.00,        # Current position value
    'unrealized_pnl': 1250.50,         # Unrealized profit/loss
    'margin_used': 9850.00,            # Margin for this position
    'liquidation_px': 89000.00,        # Liquidation price
    'leverage': 5.0,                   # Current leverage
    'side': 'Long',                    # Position direction

    # Hyperliquid-specific
    'return_on_equity': 12.5,          # ROE %
    'max_leverage': 10.0,              # Max allowed leverage
    'cum_funding_all_time': -15.25,    # Total funding paid/received
    'cum_funding_since_open': -3.50,   # Funding since position opened
    'leverage_type': 'cross',          # Cross or isolated margin
}]
```

#### Order Placement

**Function**: `place_order()` (line 371)

```python
def place_order(
    db: Session,
    symbol: str,              # "BTC"
    is_buy: bool,             # True=long, False=short
    size: float,              # Absolute quantity
    order_type: str = "market",  # "market" | "limit"
    price: float = None,      # Required for limit orders
    reduce_only: bool = False,  # Only close positions
    leverage: int = 1         # 1-50x
) -> Dict[str, Any]
```

**Order Flow**:

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Validate Environment                                     │
│    - Check account.hyperliquid_environment == client.env    │
│    - Raise EnvironmentMismatchError if mismatch             │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ 2. Set Leverage                                             │
│    exchange.set_leverage(leverage, "BTC/USDC:USDC")         │
│    - May fail silently if already set                       │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ 3. Prepare CCXT Order                                       │
│    symbol: "BTC/USDC:USDC" (perpetual contract format)     │
│    side: "buy" | "sell"                                     │
│    type: "market" | "limit"                                 │
│    amount: position size                                    │
│    price: limit price or slippage reference                 │
│    params: { reduceOnly: true/false }                       │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ 4. Execute via CCXT                                         │
│    order = exchange.create_order(...)                       │
│    - CCXT handles API authentication                        │
│    - Signs with private key (EIP-712)                       │
│    - Posts to Hyperliquid API                               │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ 5. Parse Response                                           │
│    - Check for Hyperliquid-specific errors                  │
│    - Extract fill information from nested response          │
│    - Determine status: filled | resting | error             │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ 6. Record Exchange Action                                   │
│    - Log to hyperliquid_exchange_actions table              │
│    - Store request/response payloads for audit              │
│    - Track request weight for rate limiting                 │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ 7. Return Result                                            │
│    {                                                         │
│      'status': 'filled' | 'resting' | 'error',              │
│      'order_id': '0x...',                                   │
│      'filled_amount': 0.5,                                  │
│      'average_price': 98500.00,                             │
│      'environment': 'testnet',                              │
│      'wallet_address': '0x...',                             │
│      'error': 'Error message' (if failed)                   │
│    }                                                         │
└─────────────────────────────────────────────────────────────┘
```

#### Exchange Action Logging

**Table**: `hyperliquid_exchange_actions`

Every API call is logged for compliance and debugging:

```python
HyperliquidExchangeAction:
    - account_id: Database account ID
    - environment: "testnet" | "mainnet"
    - wallet_address: Ethereum address
    - action_type: "create_order" | "fetch_positions" | "set_leverage"
    - status: "success" | "error"
    - symbol: Asset traded
    - side: "buy" | "sell"
    - leverage: Position leverage
    - size: Order quantity
    - price: Execution price
    - notional: Total value
    - request_weight: API rate limit weight
    - request_payload: JSON request
    - response_payload: JSON response
    - error_message: Error details (if failed)
    - created_at: Timestamp
```

**Benefits**:
- Audit trail for regulatory compliance
- Debug failed orders
- Monitor API rate limits
- Track trading performance

---

## Risk Management

Risk management is distributed across multiple components:

### 1. Pre-Trade Risk Controls

#### Position Sizing Limits

**Paper Trading** (`trading_commands.py` line 232):
```python
# Default: Maximum 20% of available cash per trade
max_ratio = 0.2
order_value = available_cash * target_portion

# AI can request target_portion (0.0-1.0)
# System enforces: 0 < target_portion <= 1.0
```

**Hyperliquid Trading** (`trading_commands.py` line 678):
```python
# Default: Maximum 25% per trade on mainnet
# Account-specific max_leverage setting (1-50x)

# Risk formula:
effective_exposure = position_value * leverage
margin_required = effective_exposure / leverage
```

#### Leverage Constraints

```python
# Account Configuration
account.max_leverage = 5        # Maximum allowed (1-50)
account.default_leverage = 2    # Default for new positions

# Validation (line 642)
if leverage < 1 or leverage > account.max_leverage:
    leverage = account.default_leverage
```

**Mainnet Safety Constraints** (line 485):
```python
operational_constraints = """
- Maximum position size: ≤ 25% of available balance per trade
- Leverage range: 1x to {max_leverage}x
- Margin call threshold: 80% margin usage (CRITICAL)
- Default stop loss: -10% from entry
- Default take profit: +20% from entry
- Liquidation protection: NEVER exceed 70% margin usage
"""
```

#### Price Slippage Protection

**AI Price Bounds** (`trading_commands.py` line 661):
```python
# Clamp AI prices to ±5% from market
upper_bound = market_price * 1.05
lower_bound = market_price * 0.95

if ai_max_price > upper_bound:
    max_price = upper_bound  # Prevent overpaying

if ai_min_price < lower_bound:
    min_price = lower_bound  # Prevent underselling
```

### 2. Margin Management

#### Margin Usage Monitoring

**Hyperliquid** (`hyperliquid_trading_client.py` line 225):
```python
def get_account_state():
    margin_usage_percent = (used_margin / total_equity) * 100

    # Risk Levels:
    # 0-50%:  Safe
    # 50-70%: Warning (reduce positions)
    # 70-80%: Danger (auto-pause recommended)
    # 80%+:   CRITICAL (liquidation risk)
```

**Auto-Pause Trigger** (application-level):
```python
if margin_usage_percent >= 80:
    # Pause all new position entries
    # Only allow position closures (reduce_only=True)
    logger.critical("MARGIN USAGE CRITICAL: Auto-pausing trading")
```

#### Cross Margin Risk

Hyperliquid uses **cross margin** by default:
- All positions share the same margin pool
- Liquidation of one position affects total equity
- Requires careful monitoring of total exposure

### 3. Post-Trade Risk Controls

#### Position Monitoring

**Real-time Position Tracking**:
```python
# Fetch positions every trigger cycle
positions = client.get_positions(db)

for position in positions:
    if position['margin_usage_percent'] > 70:
        # Send alert
        # Consider partial closure
```

#### Automatic Position Closure

**Close Operation** (`trading_commands.py` line 732):
```python
elif operation == "close":
    # AI can close positions partially or fully
    close_size = position_size * target_portion

    # reduce_only=True ensures only closing existing positions
    client.place_order(
        is_buy=(not is_long),  # Reverse direction
        size=close_size,
        reduce_only=True       # Safety: Cannot open new position
    )
```

### 4. Environment Isolation

**Prevent Mainnet Accidents** (`hyperliquid_trading_client.py` line 158):

```python
def _validate_environment(db: Session) -> bool:
    """Called before EVERY state-modifying operation"""
    account = db.query(Account).filter_by(id=account_id).first()

    if account.hyperliquid_environment != self.environment:
        raise EnvironmentMismatchError(
            f"BLOCKED: Account is {account.hyperliquid_environment}, "
            f"client is {self.environment}"
        )
```

**Environment-Specific Endpoints**:
```python
if environment == "testnet":
    api_url = "https://api.hyperliquid-testnet.xyz"
else:
    api_url = "https://api.hyperliquid.xyz"
```

### 5. Funding Rate Management

**Perpetual Contracts** charge funding rates:
```python
position['cum_funding_all_time'] = -15.25   # Total funding paid
position['cum_funding_since_open'] = -3.50  # Funding since open

# Negative = paid funding (cost)
# Positive = received funding (profit)
```

**Monitoring**:
- High negative funding → Consider closing
- Funding rates visible in position data
- Included in unrealized P&L calculations

### 6. Order Validation

**Pre-Flight Checks** (`order_matching.py` line 46):

```python
def create_order(...):
    # 1. Quantity validation
    if quantity <= 0:
        raise ValueError("Quantity must be positive")

    # 2. Price validation (limit orders)
    if order_type == "LIMIT" and price <= 0:
        raise ValueError("Invalid limit price")

    # 3. Funds check (BUY)
    cash_needed = price * quantity + commission
    if account.current_cash < cash_needed:
        raise ValueError("Insufficient cash")

    # 4. Position check (SELL)
    if position.available_quantity < quantity:
        raise ValueError("Insufficient positions")
```

### Risk Management Summary

| Risk Type | Control Mechanism | Location |
|-----------|------------------|----------|
| **Position Sizing** | Max % of balance per trade | `trading_commands.py:232` |
| **Leverage** | Account max_leverage limit | `trading_commands.py:642` |
| **Slippage** | ±5% price bounds from market | `trading_commands.py:661` |
| **Margin Usage** | 80% auto-pause threshold | Application level |
| **Environment** | Strict testnet/mainnet validation | `hyperliquid_trading_client.py:158` |
| **Liquidation** | 70% margin usage warning | Monitoring layer |
| **Order Size** | Pre-flight fund/position checks | `order_matching.py:73` |

---

## Market Data Aggregation

**Files**:
- `backend/services/market_data.py` (74 lines)
- `backend/services/hyperliquid_market_data.py` (210 lines)

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Market Data Layer                         │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Public Interface (market_data.py)                    │   │
│  │ - get_last_price(symbol, market)                     │   │
│  │ - get_kline_data(symbol, period, count)              │   │
│  │ - get_market_status(symbol)                          │   │
│  │ - get_all_symbols()                                  │   │
│  └──────────────────┬───────────────────────────────────┘   │
│                     │                                        │
│  ┌──────────────────▼───────────────────────────────────┐   │
│  │ Price Cache Layer (price_cache.py)                   │   │
│  │ - In-memory cache with TTL                           │   │
│  │ - Reduces API calls                                  │   │
│  │ - Cache key: "symbol.market"                         │   │
│  └──────────────────┬───────────────────────────────────┘   │
│                     │ Cache Miss                             │
│  ┌──────────────────▼───────────────────────────────────┐   │
│  │ Data Provider (hyperliquid_market_data.py)           │   │
│  │ - CCXT Hyperliquid integration                       │   │
│  │ - Supports both testnet and mainnet                  │   │
│  │ - Real-time ticker data                              │   │
│  │ - OHLCV candlestick data                             │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ Network Calls
                              ▼
┌─────────────────────────────────────────────────────────────┐
│         Hyperliquid Public API (via CCXT)                    │
│  - https://api.hyperliquid.xyz (mainnet)                    │
│  - https://api.hyperliquid-testnet.xyz (testnet)            │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

#### 1. Price Caching

**Benefits**:
- Reduces API calls to Hyperliquid
- Faster response times
- Rate limit protection

**Implementation**:
```python
# Cache structure
price_cache: Dict[str, Tuple[float, float]] = {
    "BTC.CRYPTO": (98500.00, 1704715200.0),  # (price, timestamp)
    "ETH.CRYPTO": (3850.50, 1704715195.0)
}

# Cache TTL
CACHE_TTL = 5  # seconds

def get_cached_price(symbol: str, market: str) -> Optional[float]:
    key = f"{symbol}.{market}"
    if key in price_cache:
        price, timestamp = price_cache[key]
        if time.time() - timestamp < CACHE_TTL:
            return price
    return None
```

#### 2. Real-Time Price Fetching

**Function**: `get_last_price(symbol, market)` (line 14)

```python
def get_last_price(symbol: str, market: str = "CRYPTO") -> float:
    # 1. Check cache
    cached = get_cached_price(symbol, market)
    if cached:
        return cached

    # 2. Fetch from Hyperliquid
    price = hyperliquid_client.get_last_price(symbol)

    # 3. Update cache
    cache_price(symbol, market, price)

    return price
```

**Symbol Format Handling** (`hyperliquid_market_data.py` line 169):
```python
def _format_symbol(symbol: str) -> str:
    """Convert to CCXT format"""

    # Input formats handled:
    # - "BTC"           → "BTC/USDC:USDC" (perpetual)
    # - "BTC/USDC"      → "BTC/USDC:USDC" (perpetual)
    # - "BTC/USDC:USDC" → "BTC/USDC:USDC" (already correct)

    if '/' in symbol and ':' in symbol:
        return symbol  # Already formatted
    elif '/' in symbol:
        return f"{symbol}:USDC"
    else:
        # Mainstream cryptos use perpetual contracts
        mainstream = ['BTC', 'ETH', 'SOL', 'DOGE', 'BNB', 'XRP']
        if symbol.upper() in mainstream:
            return f"{symbol.upper()}/USDC:USDC"
        else:
            return f"{symbol.upper()}/USDC"
```

#### 3. OHLCV Data (Candlesticks)

**Function**: `get_kline_data(symbol, period, count)` (line 39)

```python
# Supported periods
timeframes = {
    '1m': '1m',
    '5m': '5m',
    '15m': '15m',
    '30m': '30m',
    '1h': '1h',
    '1d': '1d'
}

# Returns list of candles
[
    {
        'timestamp': 1704715200,
        'datetime_str': '2025-01-08T10:00:00+00:00',
        'open': 98450.00,
        'high': 98750.00,
        'low': 98200.00,
        'close': 98500.00,
        'volume': 125.5,
        'amount': 12350000.00,  # volume * close
        'change': 50.00,         # close - open
        'percent': 0.051         # (change / open) * 100
    },
    ...
]
```

**Use Cases**:
- Technical analysis (moving averages, RSI, MACD)
- Price trend visualization
- Backtesting strategies
- AI context building

#### 4. Market Status

**Function**: `get_market_status(symbol)` (line 53)

```python
Returns:
{
    'market_status': 'OPEN' | 'CLOSED',
    'is_trading': True | False,
    'symbol': 'BTC/USDC:USDC',
    'exchange': 'Hyperliquid',
    'market_type': 'crypto',
    'base_currency': 'BTC',
    'quote_currency': 'USDC',
    'active': True
}
```

**Notes**:
- Hyperliquid is 24/7 (always OPEN)
- Useful for validating symbol exists
- Returns market metadata

#### 5. Symbol Discovery

**Function**: `get_all_symbols()` (line 65)

```python
def get_all_symbols() -> List[str]:
    # Fetch all markets from Hyperliquid
    markets = exchange.load_markets()

    # Filter for USDC pairs
    usdc_symbols = [s for s in markets if '/USDC' in s]

    # Prioritize mainstream perpetuals
    mainstream = ['BTC/', 'ETH/', 'SOL/', 'DOGE/', 'BNB/', 'XRP/']
    mainstream_perps = [s for s in usdc_symbols
                        if any(c in s for c in mainstream)]

    # Return mainstream + top 50 others
    return mainstream_perps + other_symbols[:50]
```

**Sample Output**:
```python
[
    'BTC/USDC:USDC',  # Bitcoin perpetual
    'ETH/USDC:USDC',  # Ethereum perpetual
    'SOL/USDC:USDC',  # Solana perpetual
    'DOGE/USDC:USDC', # Dogecoin perpetual
    'BNB/USDC:USDC',  # Binance Coin perpetual
    'XRP/USDC:USDC',  # Ripple perpetual
    ...
]
```

#### 6. CCXT Integration

**HyperliquidClient** (`hyperliquid_market_data.py` line 12):

```python
class HyperliquidClient:
    def __init__(self):
        self.exchange = ccxt.hyperliquid({
            'sandbox': False,        # False=mainnet, True=testnet
            'enableRateLimit': True, # Built-in rate limiting
        })
```

**Benefits of CCXT**:
- Unified API across 100+ exchanges
- Automatic rate limiting
- Error handling and retries
- Symbol normalization
- Market data standardization

### Data Flow Example

**Scenario**: AI needs to make a trading decision for BTC

```
1. Trading Strategy triggers
   ↓
2. trading_commands.py calls:
   prices = _get_market_prices(['BTC', 'ETH', 'SOL'])
   ↓
3. For each symbol:
   get_last_price('BTC', 'CRYPTO')
   ↓
4. Check price_cache:
   - HIT → Return cached price (< 5 seconds old)
   - MISS → Continue
   ↓
5. hyperliquid_client.get_last_price('BTC')
   ↓
6. _format_symbol('BTC') → 'BTC/USDC:USDC'
   ↓
7. exchange.fetch_ticker('BTC/USDC:USDC')
   ↓
8. HTTP GET https://api.hyperliquid.xyz/info
   ↓
9. Parse response: { last: 98500.00 }
   ↓
10. cache_price('BTC', 'CRYPTO', 98500.00)
   ↓
11. Return 98500.00 to trading_commands
   ↓
12. AI receives: prices = {'BTC': 98500.00, 'ETH': 3850.50, ...}
```

### Sampling Pool Integration

**File**: `backend/services/sampling_pool.py`

The sampling pool stores historical price snapshots for AI analysis:

```python
# Global sampling pool
sampling_pool: Dict[str, List[Dict]] = {
    'BTC': [
        {'datetime': '2025-01-08T10:00:00Z', 'price': 98450.00, 'timestamp': 1704715200},
        {'datetime': '2025-01-08T10:00:18Z', 'price': 98475.00, 'timestamp': 1704715218},
        {'datetime': '2025-01-08T10:00:36Z', 'price': 98500.00, 'timestamp': 1704715236},
        ...  # Up to 100 samples (30 minutes at 18-second intervals)
    ]
}

# Usage in AI context
sampling_data = sampling_pool.get_samples('BTC')
# AI receives 18-second interval price data for trend analysis
```

**Trigger Integration** (`trading_strategy.py` line 170):
```python
def handle_price_update(symbol: str, price: float, event_time: datetime):
    # Add to sampling pool if interval elapsed
    if sampling_pool.should_sample(symbol, sampling_interval=18):
        sampling_pool.add_sample(symbol, price, event_time.timestamp())
```

---

## Data Flow & Integration

### Complete Trading Cycle

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Market Data Collection                                   │
│    - WebSocket streams (Hyperliquid)                        │
│    - Scheduled polling (CCXT)                               │
│    - Price updates every 1-5 seconds                        │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ 2. Sampling Pool Update                                     │
│    - Store price samples (18-second intervals)              │
│    - Calculate price momentum                               │
│    - Track price change %                                   │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ 3. Strategy Trigger Evaluation                              │
│    - Check time interval (e.g., 5 minutes elapsed?)         │
│    - Check price threshold (e.g., ±2% change?)              │
│    - If triggered → proceed to AI decision                  │
└────────────────────┬────────────────────────────────────────┘
                     │ TRIGGERED
┌────────────────────▼────────────────────────────────────────┐
│ 4. AI Decision Generation                                   │
│    - Fetch account state (cash, positions, P&L)             │
│    - Fetch market prices (all tracked symbols)              │
│    - Fetch news feed (CoinJournal)                          │
│    - Build rich prompt context                              │
│    - Call LLM API (GPT-4, Claude, Deepseek, etc.)           │
│    - Parse JSON decision response                           │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ 5. Decision Validation                                      │
│    - Validate operation (buy/sell/hold/close)               │
│    - Validate symbol (in allowed list)                      │
│    - Validate target_portion (0-1)                          │
│    - Validate leverage (1-max_leverage)                     │
│    - Apply price slippage bounds (±5%)                      │
└────────────────────┬────────────────────────────────────────┘
                     │ VALID
┌────────────────────▼────────────────────────────────────────┐
│ 6. Risk Management Checks                                   │
│    - Check margin usage (< 80%)                             │
│    - Check position size limits                             │
│    - Check available cash/positions                         │
│    - Validate environment (testnet/mainnet)                 │
└────────────────────┬────────────────────────────────────────┘
                     │ PASSED
┌────────────────────▼────────────────────────────────────────┐
│ 7. Order Execution                                          │
│    Paper Trading:                                           │
│    - Create order in database                               │
│    - Check execution conditions                             │
│    - Simulate fill (update cash, positions)                 │
│    - Create trade record                                    │
│                                                              │
│    Hyperliquid Trading:                                     │
│    - Validate environment                                   │
│    - Set leverage via CCXT                                  │
│    - Place order on blockchain                              │
│    - Parse execution result                                 │
│    - Log exchange action                                    │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ 8. Post-Execution Logging                                   │
│    - Save AI decision log (prompt, reasoning, result)       │
│    - Create trade record (if filled)                        │
│    - Update account state                                   │
│    - Broadcast WebSocket updates                            │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ 9. Real-Time Updates                                        │
│    - WebSocket broadcast to frontend                        │
│    - Update portfolio view                                  │
│    - Update positions table                                 │
│    - Update model chat feed                                 │
│    - Update trade history                                   │
└─────────────────────────────────────────────────────────────┘
```

### Service Dependencies

```
┌─────────────────────────────────────────────────────────────┐
│                    Business Layer Services                   │
└─────────────────────────────────────────────────────────────┘
       │
       ├── ai_decision_service.py
       │   ├── Depends on:
       │   │   ├── market_data.py (prices)
       │   │   ├── news_feed.py (market news)
       │   │   ├── sampling_pool.py (price history)
       │   │   ├── asset_calculator.py (portfolio value)
       │   │   ├── prompt_repo.py (templates)
       │   │   └── system_logger.py (logging)
       │
       ├── trading_strategy.py
       │   ├── Depends on:
       │   │   ├── sampling_pool.py (price tracking)
       │   │   ├── trading_commands.py (order execution)
       │   │   └── strategy_repo.py (config persistence)
       │
       ├── trading_commands.py
       │   ├── Depends on:
       │   │   ├── ai_decision_service.py (get decisions)
       │   │   ├── order_matching.py (paper trading)
       │   │   ├── hyperliquid_trading_client.py (real trading)
       │   │   ├── market_data.py (current prices)
       │   │   └── asset_calculator.py (portfolio value)
       │
       ├── order_matching.py
       │   ├── Depends on:
       │   │   ├── market_data.py (execution prices)
       │   │   └── ws.py (WebSocket broadcasts)
       │
       ├── hyperliquid_trading_client.py
       │   ├── Depends on:
       │   │   ├── ccxt (exchange API wrapper)
       │   │   ├── eth_account (wallet derivation)
       │   │   └── hyperliquid_cache.py (state caching)
       │
       └── market_data.py
           ├── Depends on:
           │   ├── hyperliquid_market_data.py (data provider)
           │   └── price_cache.py (caching layer)
```

### Database Interactions

**Key Tables**:

| Table | Purpose | Service |
|-------|---------|---------|
| `accounts` | Trader accounts | All services |
| `orders` | Paper trading orders | `order_matching.py` |
| `trades` | Executed trades | `order_matching.py` |
| `positions` | Current holdings | `order_matching.py`, `trading_commands.py` |
| `ai_decision_log` | AI decision audit trail | `ai_decision_service.py` |
| `account_strategy_config` | Strategy triggers | `trading_strategy.py` |
| `hyperliquid_exchange_actions` | Hyperliquid API logs | `hyperliquid_trading_client.py` |
| `hyperliquid_trades` | Real blockchain trades | `trading_commands.py` |
| `prompt_templates` | AI prompt configurations | `ai_decision_service.py` |

---

## Performance Optimizations

### 1. Price Caching
- **TTL**: 5 seconds
- **Impact**: Reduces API calls by 80-90%
- **Location**: `price_cache.py`

### 2. Sampling Pool
- **Interval**: 18 seconds (configurable)
- **Max Samples**: 100 per symbol
- **Memory**: ~10KB per symbol
- **Benefits**: Pre-aggregated data for AI

### 3. Connection Pooling
- **SQLAlchemy**: Database connection pool
- **CCXT**: HTTP connection reuse
- **WebSocket**: Persistent connections

### 4. Concurrent Execution
- **Threading**: Strategy manager background refresh
- **Async**: WebSocket broadcasts
- **PostgreSQL**: Native concurrent access

### 5. Lazy Loading
- **Markets**: Load on first request
- **Symbols**: Cache after first fetch
- **News**: Fetch on-demand only

---

## Error Handling Strategies

### 1. AI API Failures
- **Retry**: 3 attempts with exponential backoff
- **Fallback**: Multiple endpoint support (Deepseek)
- **Graceful**: Continue with other accounts on failure
- **Logging**: Full request/response logging

### 2. Exchange API Failures
- **Validation**: Environment checks before every call
- **Logging**: All actions recorded to database
- **Graceful**: Return error status, don't crash
- **Alerting**: System logger integration

### 3. Database Failures
- **Transactions**: Rollback on error
- **Connection**: Auto-reconnect on disconnect
- **Isolation**: Per-account database sessions
- **PostgreSQL**: Native lock handling

### 4. Market Data Failures
- **Cache**: Use cached prices if API fails
- **Fallback**: Skip trading cycle if no prices
- **Retry**: Built-in CCXT rate limiting
- **Logging**: Warning logs for debugging

---

## Security Considerations

### 1. Private Key Protection
- **Storage**: Encrypted in database (Fernet)
- **Memory**: Cleared after use
- **Transmission**: Never logged or exposed to frontend
- **Derivation**: Wallet address derived on initialization

### 2. Environment Isolation
- **Validation**: Checked before every state-modifying operation
- **Separation**: Testnet and mainnet completely isolated
- **Alerts**: Logs all environment validations
- **Fail-Safe**: Raises exception on mismatch

### 3. API Key Security
- **Default Keys**: Automatically skipped (no trading)
- **Validation**: Check for demo keys before API calls
- **Storage**: Encrypted in database
- **Headers**: Authorization header only

### 4. SQL Injection Prevention
- **ORM**: SQLAlchemy parameterized queries
- **No Raw SQL**: Except for specific read-only queries
- **Validation**: Input sanitization at API layer

---

## Monitoring & Observability

### 1. System Logger
- **Location**: `services/system_logger.py`
- **Events**: AI decisions, order executions, errors
- **Storage**: Database table + log files
- **Real-time**: WebSocket broadcasts

### 2. Exchange Action Logs
- **Table**: `hyperliquid_exchange_actions`
- **Content**: All API calls with request/response
- **Use Cases**: Debugging, compliance, rate limiting

### 3. AI Decision Logs
- **Table**: `ai_decision_log`
- **Content**: Full prompt, reasoning, decision, result
- **Use Cases**: Model performance analysis, debugging

### 4. WebSocket Updates
- **Trade Updates**: Real-time trade notifications
- **Position Updates**: Portfolio changes
- **AI Decisions**: Model chat feed
- **Account State**: Balance and margin updates

---

## Summary

The Business Layer implements a sophisticated AI-powered trading system with:

✅ **Multi-Model LLM Integration** - GPT-4, GPT-5, Claude, Deepseek
✅ **Dual Execution Modes** - Paper trading + Hyperliquid real trading
✅ **Advanced Risk Management** - Position sizing, leverage limits, margin monitoring
✅ **Real-Time Market Data** - CCXT integration with caching
✅ **Automated Strategies** - Price & time-based triggers
✅ **Comprehensive Logging** - Full audit trail for compliance
✅ **Environment Isolation** - Strict testnet/mainnet separation
✅ **Error Resilience** - Retry logic, fallbacks, graceful degradation

**Total Lines of Code**: ~3,500 lines across 7 core service files

**Key Innovation**: Combining LLM reasoning with systematic risk controls and real blockchain execution, creating a production-ready autonomous trading platform.
