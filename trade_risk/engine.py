from __future__ import annotations

from dataclasses import asdict, dataclass
from math import floor
from typing import Literal

TradeType = Literal["spot"]

class TradeInputError(ValueError):
    pass

@dataclass(frozen=True)
class SpotPlan:
    calculation_mode: str
    capital: float
    selected_risk_percent: float
    risk_budget: float
    allocation_percent: float
    position_value: float
    requested_allocation_percent: float | None
    entry: float
    stop_price: float
    stop_distance_percent: float
    quantity: float
    quantity_precision: int
    estimated_cost_percent: float
    modeled_loss: float
    actual_risk_percent: float
    capital_after_stop: float
    risk_budget_fully_used: bool
    allocation_capped: bool
    friction_share_percent: float

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass(frozen=True)
class RewardPlan:
    rr: float
    target_price: float
    target_move_percent: float
    modeled_profit: float
    capital_after_target: float
    break_even_win_rate_percent: float

    def to_dict(self) -> dict:
        return asdict(self)

def _positive(name: str, value: float) -> None:
    if not isinstance(value, (int, float)) or value <= 0:
        raise TradeInputError(f"{name} must be greater than zero.")

def _validate_common(capital: float, risk_percent: float, entry: float, estimated_cost_percent: float, quantity_precision: int) -> None:
    _positive("capital", capital)
    _positive("risk_percent", risk_percent)
    _positive("entry", entry)
    if risk_percent > 100:
        raise TradeInputError("Account risk cannot exceed 100%.")
    if estimated_cost_percent < 0:
        raise TradeInputError("Estimated costs cannot be negative.")
    if not isinstance(quantity_precision, int) or not 0 <= quantity_precision <= 12:
        raise TradeInputError("Quantity precision must be an integer from 0 to 12.")

def _round_quantity_down(quantity: float, precision: int) -> float:
    scale = 10 ** precision
    rounded = floor(quantity * scale + 1e-12) / scale
    if rounded <= 0:
        raise TradeInputError(
            "The selected quantity precision rounds the position to zero. "
            "Use more quantity decimals, a larger allocation, or a lower entry price."
        )
    return rounded

def risk_band(risk_percent: float) -> dict:
    if risk_percent <= 0.25:
        return {"key":"very_low","label":"Very Low","summary":"Small account impact per stopped trade."}
    if risk_percent <= 0.50:
        return {"key":"low","label":"Low","summary":"Conservative account risk with room for normal learning errors."}
    if risk_percent <= 0.75:
        return {"key":"low_medium","label":"Low–Medium","summary":"Moderate participation while keeping each loss relatively contained."}
    if risk_percent <= 1.00:
        return {"key":"medium","label":"Medium","summary":"Each stop has a clearly visible impact on the account."}
    if risk_percent <= 1.50:
        return {"key":"medium_high","label":"Medium–High","summary":"Loss streaks compound faster and require stronger discipline."}
    if risk_percent <= 2.00:
        return {"key":"high","label":"High","summary":"High per-trade account risk; drawdowns can accelerate quickly."}
    return {"key":"very_high","label":"Very High","summary":"Very aggressive per-trade account risk. Small losing streaks can materially damage capital."}

def _build_plan(
    *,
    calculation_mode: str,
    capital: float,
    risk_percent: float,
    requested_allocation_percent: float | None,
    entry: float,
    position_value: float,
    quantity: float,
    quantity_precision: int,
    stop_price: float,
    estimated_cost_percent: float,
    risk_budget: float,
    allocation_capped: bool,
) -> SpotPlan:
    stop_rate = max(0.0, (entry - stop_price) / entry)
    cost_rate = estimated_cost_percent / 100.0
    modeled_loss = position_value * (stop_rate + cost_rate)
    actual_risk_percent = modeled_loss / capital * 100.0
    effective_loss_rate = stop_rate + cost_rate
    friction_share = (cost_rate / effective_loss_rate * 100.0) if effective_loss_rate > 0 else 0.0
    fully_used = abs(modeled_loss - risk_budget) <= max(1e-9, risk_budget * 1e-8)

    return SpotPlan(
        calculation_mode=calculation_mode,
        capital=capital,
        selected_risk_percent=risk_percent,
        risk_budget=risk_budget,
        allocation_percent=position_value / capital * 100.0,
        position_value=position_value,
        requested_allocation_percent=requested_allocation_percent,
        entry=entry,
        stop_price=stop_price,
        stop_distance_percent=stop_rate * 100.0,
        quantity=quantity,
        quantity_precision=quantity_precision,
        estimated_cost_percent=estimated_cost_percent,
        modeled_loss=modeled_loss,
        actual_risk_percent=actual_risk_percent,
        capital_after_stop=max(0.0, capital - modeled_loss),
        risk_budget_fully_used=fully_used,
        allocation_capped=allocation_capped,
        friction_share_percent=friction_share,
    )

def calculate_budget_stop(
    *,
    capital: float,
    allocation_percent: float,
    risk_percent: float,
    entry: float,
    estimated_cost_percent: float = 0.0,
    quantity_precision: int = 8,
) -> SpotPlan:
    """Spot/1x: allocation fixes quantity; account risk solves the maximum budget stop."""
    _validate_common(capital, risk_percent, entry, estimated_cost_percent, quantity_precision)
    _positive("allocation_percent", allocation_percent)
    if allocation_percent > 100:
        raise TradeInputError("Allocation cannot exceed 100% in Spot Simple.")

    requested_position = capital * allocation_percent / 100.0
    raw_quantity = requested_position / entry
    quantity = _round_quantity_down(raw_quantity, quantity_precision)
    position_value = quantity * entry
    risk_budget = capital * risk_percent / 100.0
    cost_rate = estimated_cost_percent / 100.0

    effective_loss_rate = risk_budget / position_value
    price_stop_rate = effective_loss_rate - cost_rate
    if price_stop_rate <= 0:
        raise TradeInputError(
            "Estimated execution costs consume the full risk budget at this allocation. "
            "Lower allocation, raise the risk budget, or lower the cost estimate."
        )

    allocation_capped = False
    if price_stop_rate >= 1.0:
        stop_price = 0.0
        allocation_capped = True
    else:
        stop_price = entry * (1.0 - price_stop_rate)

    return _build_plan(
        calculation_mode="budget_stop",
        capital=capital,
        risk_percent=risk_percent,
        requested_allocation_percent=allocation_percent,
        entry=entry,
        position_value=position_value,
        quantity=quantity,
        quantity_precision=quantity_precision,
        stop_price=stop_price,
        estimated_cost_percent=estimated_cost_percent,
        risk_budget=risk_budget,
        allocation_capped=allocation_capped,
    )

def calculate_from_chart_stop(
    *,
    capital: float,
    risk_percent: float,
    entry: float,
    stop_price: float,
    estimated_cost_percent: float = 0.0,
    quantity_precision: int = 8,
) -> SpotPlan:
    """Spot/1x: chart stop fixes loss per unit; account risk solves max allocation."""
    _validate_common(capital, risk_percent, entry, estimated_cost_percent, quantity_precision)
    _positive("stop_price", stop_price)
    if stop_price >= entry:
        raise TradeInputError("For a spot long plan, the chart stop must be below the entry price.")

    stop_rate = (entry - stop_price) / entry
    cost_rate = estimated_cost_percent / 100.0
    effective_loss_rate = stop_rate + cost_rate
    risk_budget = capital * risk_percent / 100.0
    required_position = risk_budget / effective_loss_rate
    allocation_capped = required_position > capital
    requested_position = min(required_position, capital)

    raw_quantity = requested_position / entry
    quantity = _round_quantity_down(raw_quantity, quantity_precision)
    position_value = quantity * entry

    return _build_plan(
        calculation_mode="chart_stop",
        capital=capital,
        risk_percent=risk_percent,
        requested_allocation_percent=None,
        entry=entry,
        position_value=position_value,
        quantity=quantity,
        quantity_precision=quantity_precision,
        stop_price=stop_price,
        estimated_cost_percent=estimated_cost_percent,
        risk_budget=risk_budget,
        allocation_capped=allocation_capped,
    )

def reward_for_rr(plan: SpotPlan, rr: float) -> RewardPlan:
    _positive("rr", rr)
    if plan.position_value <= 0:
        raise TradeInputError("Position value must be positive.")

    cost_rate = plan.estimated_cost_percent / 100.0
    required_net_profit_rate = (plan.modeled_loss * rr) / plan.position_value
    gross_target_rate = required_net_profit_rate + cost_rate
    target_price = plan.entry * (1.0 + gross_target_rate)
    modeled_profit = plan.position_value * (gross_target_rate - cost_rate)

    return RewardPlan(
        rr=rr,
        target_price=target_price,
        target_move_percent=gross_target_rate * 100.0,
        modeled_profit=modeled_profit,
        capital_after_target=plan.capital + modeled_profit,
        break_even_win_rate_percent=100.0 / (1.0 + rr),
    )

def loss_streak(capital: float, actual_risk_percent: float, losses: int) -> dict:
    _positive("capital", capital)
    if actual_risk_percent < 0 or losses < 0:
        raise TradeInputError("risk_percent and losses must be non-negative.")
    remaining = capital * ((1.0 - min(actual_risk_percent / 100.0, 1.0)) ** losses)
    return {
        "losses": losses,
        "capital_remaining": remaining,
        "drawdown_percent": (1.0 - remaining / capital) * 100.0,
    }

def _warnings(plan: SpotPlan) -> list[dict]:
    warnings: list[dict] = []
    if plan.allocation_capped:
        if plan.calculation_mode == "budget_stop":
            warnings.append({
                "level":"info",
                "title":"Your allocation is smaller than your risk budget",
                "message":(
                    "Even a 100% price loss would not use the full selected account-risk budget. "
                    "The stop is therefore capped at zero; your actual modeled account risk is lower."
                ),
            })
        else:
            warnings.append({
                "level":"info",
                "title":"Full capital still stays below your selected risk",
                "message":(
                    "The chart stop is close enough that using 100% of the account still risks less "
                    "than your selected account-risk percentage. Spot Simple does not add leverage."
                ),
            })
    if plan.friction_share_percent >= 50:
        warnings.append({
            "level":"warning",
            "title":"Execution friction dominates this risk budget",
            "message":(
                f"Estimated costs consume about {plan.friction_share_percent:.0f}% of the modeled loss budget. "
                "The remaining price room to the stop is very small."
            ),
        })
    if not plan.risk_budget_fully_used and not plan.allocation_capped:
        warnings.append({
            "level":"info",
            "title":"Rounding reduced the actual risk",
            "message":"Quantity precision rounded the position down, so modeled loss is slightly below the selected risk budget.",
        })
    return warnings

def build_analysis(payload: dict) -> dict:
    trade_type = str(payload.get("trade_type", "spot")).lower()
    if trade_type != "spot":
        raise TradeInputError("Only Spot Simple is enabled in this version.")

    capital = float(payload["capital"])
    risk = float(payload["risk_percent"])
    entry = float(payload["entry"])
    costs = float(payload.get("estimated_cost_percent", 0.0))
    rr = float(payload.get("rr", 2.0))
    precision = int(payload.get("quantity_precision", 8))
    mode = str(payload.get("calculation_mode", "budget_stop"))

    if mode == "budget_stop":
        plan = calculate_budget_stop(
            capital=capital,
            allocation_percent=float(payload["allocation_percent"]),
            risk_percent=risk,
            entry=entry,
            estimated_cost_percent=costs,
            quantity_precision=precision,
        )
    elif mode == "chart_stop":
        plan = calculate_from_chart_stop(
            capital=capital,
            risk_percent=risk,
            entry=entry,
            stop_price=float(payload["chart_stop"]),
            estimated_cost_percent=costs,
            quantity_precision=precision,
        )
    else:
        raise TradeInputError("Unknown calculation mode.")

    selected = reward_for_rr(plan, rr)
    ladder = [reward_for_rr(plan, x).to_dict() for x in (1.0, 1.5, 2.0, 2.5, 3.0, 4.0)]
    band = risk_band(risk)
    streaks = [loss_streak(capital, plan.actual_risk_percent, n) for n in (1, 3, 5, 10)]

    if mode == "budget_stop":
        why = (
            f"You chose to deploy {plan.allocation_percent:.2f}% of the account and cap modeled account loss "
            f"near {plan.selected_risk_percent:.2f}%. Those two choices imply a maximum budget stop "
            f"{plan.stop_distance_percent:.2f}% below entry."
        )
    else:
        why = (
            f"You supplied a chart stop {plan.stop_distance_percent:.2f}% below entry. "
            f"To keep modeled account loss near {plan.selected_risk_percent:.2f}%, the planner limits "
            f"the spot allocation to about {plan.allocation_percent:.2f}%."
        )

    return {
        "trade_type":"spot",
        "calculation_mode":mode,
        "plan":plan.to_dict(),
        "risk_band":band,
        "selected_reward":selected.to_dict(),
        "reward_ladder":ladder,
        "loss_streaks":streaks,
        "warnings":_warnings(plan),
        "brief":{
            "headline":f"Deploy ${plan.position_value:.2f} · modeled loss ${plan.modeled_loss:.2f} · {selected.rr:g}R target +${selected.modeled_profit:.2f}",
            "summary":why,
        },
        "future_modes":[
            {"key":"margin","label":"Margin","enabled":False},
            {"key":"futures","label":"Futures / Perps","enabled":False},
            {"key":"options","label":"Options","enabled":False},
        ],
    }
