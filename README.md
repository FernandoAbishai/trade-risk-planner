# Trade Risk Planner

A local-first, dependency-free trade planning calculator focused on **risk, stop loss, position size and reward**.

## The key idea

The calculator supports three different questions because they are mathematically different:

### 1. I know my target — find my stop

Inputs:

- trading capital
- account risk level
- long / short
- entry
- target
- desired R:R

The target and desired R:R determine the stop geometry.

For a cost-free long trade:

```text
reward_distance = target - entry
risk_distance   = reward_distance / desired_R
stop            = entry - risk_distance
```

Then account capital and account risk determine the position size.

This distinction matters:

> **Target + R:R determine the stop. Capital + risk determine the size.**

### 2. I know my stop — find my position size

This is the standard risk-first workflow:

```text
risk_budget = capital × risk_percent
position_size = risk_budget / effective_stop_distance
```

### 3. I know how much I want to use — find my maximum stop

If position size is fixed:

```text
effective_stop_distance = risk_budget / position_size
```

The app can solve the corresponding stop price. This is explicitly labeled a **budget stop**, not a technical recommendation.

## Why the distinction matters

A mathematically valid stop is not automatically a good chart stop.

Support/resistance, market structure and volatility can imply a different invalidation level. If the technically valid stop is farther away, reduce the position size rather than tightening the stop only to fit the risk budget.

## Risk levels

These labels are educational conventions inside the app:

| Label | Risk |
|---|---:|
| Bajo | 0.25% |
| Bajo-Medio | 0.50% |
| Medio-Bajo | 0.75% |
| Medio | 1.00% |
| Medio-Alto | 1.50% |
| Alto | 2.00% |

The exact percentage and dollar risk are always visible.

## Run locally

No package installation is required.

```bash
python3 app.py
```

Then open:

```text
http://127.0.0.1:8501
```

## Tests

```bash
python3 -m unittest discover -s tests -v
```

## Repository structure

```text
trade-risk-planner/
├── app.py
├── trade_risk/
│   ├── __init__.py
│   └── engine.py
├── web/
│   ├── index.html
│   └── app.js
├── tests/
│   ├── test_engine.py
│   └── test_server.py
└── .github/workflows/tests.yml
```

## Research-informed design

The project deliberately follows these principles:

- risk budget and stop distance determine position size;
- capital availability caps the position in a 1x/spot model;
- execution friction can be modeled;
- stop geometry, position sizing and trade target should be shown together;
- a risk-derived stop is not the same thing as a technically justified stop;
- the app should explain the result in plain language rather than only display formulas.

## Scope

This tool does not:

- predict whether a trade will win;
- recommend a market direction;
- connect to an exchange;
- place orders;
- assume leverage.

## Disclaimer

Educational planning software only. Stop orders do not guarantee a specific exit price; gaps, spread, slippage and liquidity can make realized loss larger than modeled.
