# Trade Risk Planner

A universal, local-first trade planning tool.

## Current product: Spot Simple

The first version focuses on the cleanest possible spot-trading workflow:

1. Enter the capital you have set aside for trading.
2. Drag **Capital Allocation %** to choose how much of that capital goes into this position.
3. Drag **Account Risk %** to choose the maximum modeled account loss for the trade.
4. Enter the asset's planned entry price.
5. The app calculates:
   - position value;
   - quantity / units;
   - stop-loss price;
   - stop distance;
   - modeled loss;
   - 1R–3R+ targets;
   - modeled profit;
   - account balance after stop/target;
   - losing-streak drawdown examples.

There is no BTC-specific, stock-specific, or token-specific math in Spot Simple. Any positive unit price works.

## Why there are two sliders

**Capital Allocation %** and **Account Risk %** are not the same thing.

Example:

```text
Trading capital: $100
Capital allocation: 50%
Position value: $50

Account risk: 0.50%
Maximum modeled loss: $0.50
```

Therefore the position can move approximately:

```text
$0.50 / $50 = 1%
```

against the entry before reaching the modeled loss budget.

At a $100 entry:

```text
Stop loss ≈ $99
```

This is the mathematical relationship the Spot Simple UI is built around.

## Important: budget stop vs technical stop

The calculated stop is a **budget stop**: the maximum price distance compatible with your chosen allocation and account-risk budget.

It does not know support/resistance, ATR, volatility, liquidity, market structure, or your trade thesis.

If a technically valid stop needs to be wider, reduce allocation instead of forcing the stop tighter.

## Universal asset model

Spot Simple uses only:

```text
capital
allocation %
risk %
entry price
estimated transaction friction
reward/risk multiple
```

Quantity is:

```text
position value / entry price
```

This makes the model usable for any divisible spot asset quoted in the account currency.

## Future trade modes

The architecture intentionally reserves separate modes for:

- Margin
- Futures / Perpetuals
- Options

Those should not reuse the spot formulas blindly.

Future leverage-aware modes will need, depending on instrument:

- leverage;
- margin used;
- notional exposure;
- maintenance margin;
- liquidation approximation;
- contract / point / tick value;
- lot or quantity precision;
- funding / borrow costs;
- isolated vs cross margin;
- exchange/broker constraints.

## Run locally

No external dependencies:

```bash
python3 app.py
```

Open:

```text
http://127.0.0.1:8501
```

## Test

```bash
python3 -m unittest discover -s tests -v
```

## Design principle

The tool should answer:

> “Given how much capital I have, how much I want to deploy, how much I can afford to lose, and my entry price — where is my maximum risk stop and what is the upside/downside?”

It does not predict whether the trade is good.

## Disclaimer

Educational planning software only. Actual fills can differ because of spread, fees, slippage, gaps and liquidity. A stop order does not guarantee the modeled exit price.
