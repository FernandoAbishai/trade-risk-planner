# Trade Risk Planner

A universal, local-first **spot risk planner** that explains the relationship between trading capital, capital allocation, account risk, entry price, stop-loss distance, quantity, reward/risk, and modeled P/L.

The project intentionally starts with **Spot Simple** before adding leverage-aware trade types.

## Core workflow

The default experience asks for four decisions:

1. **Trading capital** — the money set aside for trading.
2. **Capital Allocation %** — how much of that capital will be deployed in this position.
3. **Account Risk %** — the maximum modeled loss allowed for the trade.
4. **Entry price** — any positive unit price.

Because allocation fixes the spot position value, the risk budget can solve the maximum budget stop.

```text
position_value = capital × allocation_percent
risk_budget = capital × risk_percent

effective_loss_rate = risk_budget / position_value
price_stop_rate = effective_loss_rate - estimated_cost_rate

stop_price = entry × (1 - price_stop_rate)
```

If the allocation is so small that even a total price loss would stay below the risk budget, the planner caps the stop at zero and explains that the selected risk budget is not fully used.

## Chart-stop mode

A secondary workflow supports the more traditional risk-management sequence:

> **I already know my chart stop.**

In this mode, the user enters capital, account risk, entry, and technical/invalidation stop. The planner solves the maximum 1x spot position that fits the risk budget:

```text
effective_stop_rate =
    abs(entry - stop) / entry
    + estimated_cost_rate

position_value =
    risk_budget / effective_stop_rate
```

The position is capped at 100% of the account because Spot Simple never assumes leverage.

This keeps two concepts separate:

- **Budget stop**: derived from allocation + account risk.
- **Chart stop**: supplied from technical invalidation; allocation is solved from it.

## Universal asset model

There is no BTC-specific or stock-specific formula. Spot Simple needs only a unit price, a cash position value, and quantity precision. The optional asset symbol is display text only.

This makes the same model usable for divisible spot assets such as shares, ETFs, coins, tokens, or similar instruments, subject to actual broker/exchange rules.

## Quantity precision

The planner supports configurable quantity precision from whole units through 12 decimals. Quantity is rounded **down** so rounding does not make the position larger than planned. After rounding, the risk math is recalculated from the actual position value.

## Reward / risk

The selected `R` multiple produces target price, target move %, modeled net profit, mathematical break-even win rate, and account balance after target.

A reward ladder shows 1R, 1.5R, 2R, 2.5R, 3R, and 4R.

## Visual explanations

The UI includes:

- capital-deployed bar;
- account-risk bar;
- Stop → Entry → Target price rail;
- modeled loss vs modeled reward cards;
- reward ladder;
- risk-level explanation;
- loss-streak perspective;
- warnings when transaction friction consumes a large part of the risk budget.

## Execution-cost model

An optional advanced input estimates total round-trip friction:

```text
fees + spread + slippage
```

The value is modeled as a percentage of position notional. It is intentionally an estimate; actual fees and fills depend on venue, order type, liquidity, and market conditions.

## Why these inputs

The design is influenced by established position-sizing interfaces:

- TradingView separates quantity as units, cash, or % of balance from risk as cash or % of balance.
- TradingView allows risk to solve either quantity or stop-loss, but not both simultaneously.
- TradingView's position tools expose account size, risk, entry, stop, target, quantity precision, leverage, P/L and R:R.
- EarnForex PositionSizer centers sizing around account size, stop distance and account risk.

References:

- https://www.tradingview.com/support/solutions/43000784804-what-is-an-order-ticket/
- https://www.tradingview.com/support/solutions/43000480940-i-d-like-to-set-my-take-profit-and-stop-loss-in-dollar-terms-and-as-a-percentage-of-my-account-balance/
- https://www.tradingview.com/support/solutions/43000475660-how-to-use-long-and-short-position-drawing-tools/
- https://github.com/EarnForex/PositionSizer

## Future trade types

The UI reserves separate modes for Margin, Futures / Perpetuals, and Options. They are intentionally disabled.

Leverage-aware modes should not reuse spot formulas blindly. Future work can add leverage, margin used, notional exposure, liquidation estimate, isolated vs cross, maintenance margin, contract/point/tick value, funding or borrow costs, and venue-specific quantity/tick rules.

## Run locally

No external dependencies are required.

```bash
python3 app.py
```

Open:

```text
http://127.0.0.1:8501
```

## Tests

```bash
python3 -m unittest discover -s tests -v
```

## Disclaimer

Educational planning software only. A calculated budget stop is not a technical trading signal. Stop orders can fill worse than the modeled level because of gaps, spread, slippage, liquidity, or venue behavior. The tool does not predict direction or probability of success.
