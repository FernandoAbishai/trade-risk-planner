from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Literal

Side = Literal["long"]

class TradeInputError(ValueError):
    pass

@dataclass(frozen=True)
class SpotPlan:
    capital: float
    allocation_percent: float
    position_value: float
    risk_percent: float
    risk_budget: float
    entry: float
    stop_price: float
    stop_distance_percent: float
    quantity: float
    estimated_cost_percent: float
    modeled_loss: float
    capital_after_stop: float

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

def calculate_spot_plan(*, capital: float, allocation_percent: float, risk_percent: float, entry: float, estimated_cost_percent: float = 0.0) -> SpotPlan:
    _positive("capital", capital); _positive("allocation_percent", allocation_percent); _positive("risk_percent", risk_percent); _positive("entry", entry)
    if allocation_percent > 100: raise TradeInputError("Allocation cannot exceed 100% in Spot Simple.")
    if estimated_cost_percent < 0: raise TradeInputError("Estimated costs cannot be negative.")
    position_value = capital * allocation_percent / 100.0
    risk_budget = capital * risk_percent / 100.0
    effective_loss_rate = risk_budget / position_value
    cost_rate = estimated_cost_percent / 100.0
    price_stop_rate = effective_loss_rate - cost_rate
    if price_stop_rate <= 0: raise TradeInputError("Estimated costs consume the entire risk budget at this allocation. Use a smaller allocation, a larger risk budget, or a lower cost estimate.")
    if price_stop_rate >= 1: raise TradeInputError("This combination implies a stop at or below zero. Increase allocation or reduce account risk.")
    stop_price = entry * (1.0 - price_stop_rate)
    quantity = position_value / entry
    modeled_loss = position_value * (price_stop_rate + cost_rate)
    return SpotPlan(capital, allocation_percent, position_value, risk_percent, risk_budget, entry, stop_price, price_stop_rate*100.0, quantity, estimated_cost_percent, modeled_loss, max(0.0, capital-modeled_loss))

def reward_for_rr(plan: SpotPlan, rr: float) -> RewardPlan:
    _positive("rr", rr)
    cost_rate = plan.estimated_cost_percent / 100.0
    stop_rate = plan.stop_distance_percent / 100.0
    gross_target_rate = rr * (stop_rate + cost_rate) + cost_rate
    target_price = plan.entry * (1.0 + gross_target_rate)
    modeled_profit = plan.modeled_loss * rr
    return RewardPlan(rr, target_price, gross_target_rate*100.0, modeled_profit, plan.capital+modeled_profit, 100.0/(1.0+rr))

def loss_streak(capital: float, risk_percent: float, losses: int) -> dict:
    _positive("capital", capital)
    if risk_percent < 0 or losses < 0: raise TradeInputError("risk_percent and losses must be non-negative.")
    remaining = capital * ((1.0 - min(risk_percent/100.0,1.0)) ** losses)
    return {"losses":losses,"capital_remaining":remaining,"drawdown_percent":(1.0-remaining/capital)*100.0}

def build_analysis(payload: dict) -> dict:
    mode = str(payload.get("trade_type","spot")).lower()
    if mode != "spot": raise TradeInputError("Only Spot Simple is enabled in this version.")
    capital=float(payload["capital"]); allocation=float(payload["allocation_percent"]); risk=float(payload["risk_percent"]); entry=float(payload["entry"]); costs=float(payload.get("estimated_cost_percent",0.0)); rr=float(payload.get("rr",2.0))
    plan=calculate_spot_plan(capital=capital,allocation_percent=allocation,risk_percent=risk,entry=entry,estimated_cost_percent=costs)
    selected=reward_for_rr(plan,rr); ladder=[reward_for_rr(plan,x).to_dict() for x in (1.0,1.5,2.0,2.5,3.0)]; band=risk_band(risk); streaks=[loss_streak(capital,risk,n) for n in (1,3,5,10)]
    return {"trade_type":"spot","plan":plan.to_dict(),"risk_band":band,"selected_reward":selected.to_dict(),"reward_ladder":ladder,"loss_streaks":streaks,"brief":{"headline":f"Deploy ${plan.position_value:.2f} and cap modeled loss near ${plan.modeled_loss:.2f}","summary":f"You are deploying {plan.allocation_percent:.1f}% of a ${plan.capital:.2f} trading pool (${plan.position_value:.2f}). With account risk set to {plan.risk_percent:.2f}% (${plan.risk_budget:.2f}), the modeled stop is {plan.stop_distance_percent:.2f}% below entry, at {plan.stop_price:.8g}. At {selected.rr:g}R, the modeled target is {selected.target_price:.8g} for about +${selected.modeled_profit:.2f}."},"future_modes":[{"key":"margin","label":"Margin","enabled":False},{"key":"futures","label":"Futures / Perps","enabled":False},{"key":"options","label":"Options","enabled":False}]}
