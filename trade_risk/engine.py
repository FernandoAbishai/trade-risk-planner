from __future__ import annotations

from dataclasses import asdict, dataclass
from math import pow
from typing import Literal

Side = Literal["long", "short"]

RISK_PROFILES = {
    "low": {"label": "Bajo", "percent": 0.25, "summary": "Prioriza preservar capital. El impacto de un stop es pequeño."},
    "low_medium": {"label": "Bajo-Medio", "percent": 0.50, "summary": "Riesgo contenido. Permite aprender y absorber errores con menor impacto."},
    "medium_low": {"label": "Medio-Bajo", "percent": 0.75, "summary": "Participación moderada sin llegar todavía al 1% por operación."},
    "medium": {"label": "Medio", "percent": 1.00, "summary": "Cada stop ya tiene un impacto visible. La disciplina importa más."},
    "medium_high": {"label": "Medio-Alto", "percent": 1.50, "summary": "El crecimiento y el drawdown se aceleran. Las rachas negativas pesan más."},
    "high": {"label": "Alto", "percent": 2.00, "summary": "Riesgo elevado para una sola operación. Varias pérdidas seguidas reducen la cuenta con rapidez."},
}

class TradeInputError(ValueError):
    pass

@dataclass(frozen=True)
class RiskPlan:
    capital: float
    available_capital: float
    risk_profile: str
    risk_label: str
    risk_percent: float
    risk_budget: float
    side: Side
    entry: float
    stop: float
    stop_distance_percent: float
    estimated_cost_percent: float
    effective_loss_percent: float
    theoretical_position_size: float
    position_size: float
    units: float
    capital_used_percent: float
    actual_loss_at_stop: float
    actual_risk_percent: float
    capital_after_stop: float
    capital_limited: bool
    def to_dict(self) -> dict:
        return asdict(self)

@dataclass(frozen=True)
class TargetPlan:
    rr: float
    target_price: float
    gross_move_percent: float
    net_reward_percent_of_position: float
    net_profit: float
    capital_after_target: float
    break_even_win_rate_percent: float
    def to_dict(self) -> dict:
        return asdict(self)

def _positive(name: str, value: float) -> None:
    if not isinstance(value, (int, float)) or value <= 0:
        raise TradeInputError(f"{name} debe ser mayor que cero.")

def resolve_risk(profile: str) -> tuple[str, float, str]:
    data = RISK_PROFILES.get(profile)
    if not data:
        raise TradeInputError("Nivel de riesgo inválido.")
    return data["label"], float(data["percent"]), data["summary"]

def validate_side(side: Side) -> None:
    if side not in ("long", "short"):
        raise TradeInputError("La dirección debe ser LONG o SHORT.")

def validate_stop(side: Side, entry: float, stop: float) -> None:
    validate_side(side); _positive("entry", entry); _positive("stop", stop)
    if side == "long" and stop >= entry: raise TradeInputError("En LONG, el stop debe estar debajo del entry.")
    if side == "short" and stop <= entry: raise TradeInputError("En SHORT, el stop debe estar encima del entry.")

def validate_target(side: Side, entry: float, target: float) -> None:
    validate_side(side); _positive("entry", entry); _positive("target", target)
    if side == "long" and target <= entry: raise TradeInputError("En LONG, el target debe estar encima del entry.")
    if side == "short" and target >= entry: raise TradeInputError("En SHORT, el target debe estar debajo del entry.")

def _capital_inputs(capital: float, available_capital: float | None) -> float:
    _positive("capital", capital)
    available = capital if available_capital is None else float(available_capital)
    _positive("available_capital", available)
    if available > capital: raise TradeInputError("En modo 1x/spot, el capital disponible no puede superar el capital total.")
    return available

def calculate_from_stop(*, capital: float, available_capital: float | None, risk_profile: str, side: Side, entry: float, stop: float, estimated_cost_percent: float = 0.0) -> RiskPlan:
    available = _capital_inputs(capital, available_capital); validate_stop(side, entry, stop)
    if estimated_cost_percent < 0: raise TradeInputError("Los costos estimados no pueden ser negativos.")
    risk_label, risk_percent, _ = resolve_risk(risk_profile)
    stop_rate = abs(entry - stop) / entry; cost_rate = estimated_cost_percent / 100.0
    effective_loss_rate = stop_rate + cost_rate; risk_budget = capital * risk_percent / 100.0
    theoretical_position = risk_budget / effective_loss_rate; position = min(theoretical_position, available)
    actual_loss = position * effective_loss_rate
    return RiskPlan(capital, available, risk_profile, risk_label, risk_percent, risk_budget, side, entry, stop,
        stop_rate*100.0, estimated_cost_percent, effective_loss_rate*100.0, theoretical_position, position,
        position/entry, (position/capital)*100.0, actual_loss, (actual_loss/capital)*100.0,
        max(0.0, capital-actual_loss), position + 1e-12 < theoretical_position)

def target_for_rr(plan: RiskPlan, rr: float) -> TargetPlan:
    _positive("rr", rr)
    loss_rate = plan.effective_loss_percent/100.0; cost_rate = plan.estimated_cost_percent/100.0
    gross_reward_rate = rr*loss_rate + cost_rate; net_reward_rate = gross_reward_rate - cost_rate
    if plan.side == "long": target = plan.entry*(1.0+gross_reward_rate)
    else:
        target = plan.entry*(1.0-gross_reward_rate)
        if target <= 0: raise TradeInputError("El target SHORT calculado no es un precio válido.")
    profit = plan.position_size*net_reward_rate
    return TargetPlan(rr, target, gross_reward_rate*100.0, net_reward_rate*100.0, profit, plan.capital+profit, 100.0/(1.0+rr))

def stop_from_target_rr(*, capital: float, available_capital: float | None, risk_profile: str, side: Side, entry: float, target: float, desired_rr: float, estimated_cost_percent: float = 0.0) -> tuple[RiskPlan, TargetPlan]:
    _capital_inputs(capital, available_capital); validate_target(side, entry, target); _positive("desired_rr", desired_rr)
    if estimated_cost_percent < 0: raise TradeInputError("Los costos estimados no pueden ser negativos.")
    gross_reward_rate = abs(target-entry)/entry; cost_rate = estimated_cost_percent/100.0
    net_reward_rate = gross_reward_rate-cost_rate
    if net_reward_rate <= 0: raise TradeInputError("El target no cubre los costos estimados.")
    stop_rate = (net_reward_rate/desired_rr)-cost_rate
    if stop_rate <= 0: raise TradeInputError("Con ese target, R:R y costos no existe una distancia de stop positiva. Reduce el R:R deseado, aleja el target o reduce los costos estimados.")
    stop = entry*(1.0-stop_rate) if side == "long" else entry*(1.0+stop_rate)
    plan = calculate_from_stop(capital=capital, available_capital=available_capital, risk_profile=risk_profile, side=side, entry=entry, stop=stop, estimated_cost_percent=estimated_cost_percent)
    profit = plan.position_size*net_reward_rate
    target_plan = TargetPlan(profit/plan.actual_loss_at_stop if plan.actual_loss_at_stop else 0.0, target, gross_reward_rate*100.0, net_reward_rate*100.0, profit, capital+profit, 100.0/(1.0+desired_rr))
    return plan, target_plan

def stop_from_position_budget(*, capital: float, risk_profile: str, side: Side, entry: float, position_size: float, estimated_cost_percent: float = 0.0) -> RiskPlan:
    _positive("capital", capital); _positive("position_size", position_size)
    if position_size > capital: raise TradeInputError("En modo 1x/spot, el monto a usar no puede superar el capital.")
    validate_side(side); _positive("entry", entry)
    if estimated_cost_percent < 0: raise TradeInputError("Los costos estimados no pueden ser negativos.")
    _, risk_percent, _ = resolve_risk(risk_profile); risk_budget = capital*risk_percent/100.0
    effective_loss_rate = risk_budget/position_size; cost_rate = estimated_cost_percent/100.0; stop_rate = effective_loss_rate-cost_rate
    if stop_rate <= 0: raise TradeInputError("Los costos consumen todo el presupuesto de riesgo para ese monto. Reduce el monto, aumenta el riesgo permitido o reduce la estimación de costos.")
    stop = entry*(1.0-stop_rate) if side == "long" else entry*(1.0+stop_rate)
    return calculate_from_stop(capital=capital, available_capital=position_size, risk_profile=risk_profile, side=side, entry=entry, stop=stop, estimated_cost_percent=estimated_cost_percent)

def evaluate_target(plan: RiskPlan, target: float) -> dict:
    validate_target(plan.side, plan.entry, target)
    gross_rate = abs(target-plan.entry)/plan.entry; cost_rate = plan.estimated_cost_percent/100.0; net_rate = gross_rate-cost_rate
    if net_rate <= 0: raise TradeInputError("El target no cubre los costos estimados.")
    profit = plan.position_size*net_rate; rr = profit/plan.actual_loss_at_stop if plan.actual_loss_at_stop else 0.0
    return {"target_price":target,"gross_move_percent":gross_rate*100.0,"net_profit":profit,"rr":rr,"capital_after_target":plan.capital+profit,"break_even_win_rate_percent":100.0/(1.0+rr) if rr>0 else 100.0}

def capital_after_losses(capital: float, risk_percent: float, losses: int) -> float:
    _positive("capital", capital)
    if risk_percent < 0 or losses < 0: raise TradeInputError("risk_percent y losses deben ser no-negativos.")
    return capital*pow(1.0-min(risk_percent/100.0,1.0),losses)

def risk_profile_comparison(*, capital: float, available_capital: float, side: Side, entry: float, stop: float, estimated_cost_percent: float) -> list[dict]:
    rows=[]
    for key,meta in RISK_PROFILES.items():
        plan=calculate_from_stop(capital=capital,available_capital=available_capital,risk_profile=key,side=side,entry=entry,stop=stop,estimated_cost_percent=estimated_cost_percent)
        rows.append({"key":key,"label":meta["label"],"summary":meta["summary"],"risk_percent":plan.risk_percent,"risk_budget":plan.risk_budget,"position_size":plan.position_size,"actual_loss":plan.actual_loss_at_stop,"profit_2r":plan.actual_loss_at_stop*2.0,"capital_after_5_losses":capital_after_losses(capital,plan.actual_risk_percent,5),"capital_limited":plan.capital_limited})
    return rows

def build_brief(mode: str, plan: RiskPlan, target: dict | TargetPlan | None, profile_summary: str) -> dict:
    target_data=target.to_dict() if isinstance(target,TargetPlan) else target
    headline=f"Riesgas ${plan.actual_loss_at_stop:.2f} con una posición de ${plan.position_size:.2f}"; outcome=""
    if target_data:
        headline=f"Riesgas ${plan.actual_loss_at_stop:.2f} para buscar ${target_data['net_profit']:.2f}"
        outcome=f" Si alcanza {target_data['target_price']:.8g}, el beneficio neto modelado es ${target_data['net_profit']:.2f} (≈ {target_data['rr']:.2f}R)."
    if mode=="target": explanation=f"Tu target y el R:R deseado determinan un stop matemático en {plan.stop:.8g}. Tu capital y nivel de riesgo NO eligieron ese stop: determinan cuánto capital puedes poner sin superar una pérdida planeada de ${plan.risk_budget:.2f}."
    elif mode=="position": explanation=f"Usando ${plan.position_size:.2f}, el límite matemático de pérdida compatible con tu presupuesto coloca el stop en {plan.stop:.8g}. Este es un stop de presupuesto, no un nivel técnico del gráfico."
    else: explanation=f"Tu stop en {plan.stop:.8g} define una distancia de {plan.stop_distance_percent:.2f}%. Con tu riesgo de cuenta, eso produce una posición de ${plan.position_size:.2f}."
    after5=capital_after_losses(plan.capital,plan.actual_risk_percent,5)
    return {"headline":headline,"explanation":explanation+outcome,"risk_summary":profile_summary,"five_loss_capital":after5,"five_loss_drawdown_percent":(1.0-after5/plan.capital)*100.0}

def build_analysis(payload: dict) -> dict:
    mode=str(payload.get("mode","target")); capital=float(payload["capital"]); available=float(payload.get("available_capital",capital)); profile=str(payload["risk_profile"]); side=str(payload["side"]).lower(); entry=float(payload["entry"]); costs=float(payload.get("estimated_cost_percent",0.0)); _,_,profile_summary=resolve_risk(profile); target_result=None
    if mode=="target":
        target=float(payload["target"]); desired_rr=float(payload.get("desired_rr",2.0)); plan,target_result=stop_from_target_rr(capital=capital,available_capital=available,risk_profile=profile,side=side,entry=entry,target=target,desired_rr=desired_rr,estimated_cost_percent=costs)
    elif mode=="stop":
        plan=calculate_from_stop(capital=capital,available_capital=available,risk_profile=profile,side=side,entry=entry,stop=float(payload["stop"]),estimated_cost_percent=costs)
        if payload.get("target") not in (None,""): target_result=evaluate_target(plan,float(payload["target"]))
    elif mode=="position":
        plan=stop_from_position_budget(capital=capital,risk_profile=profile,side=side,entry=entry,position_size=float(payload["position_size"]),estimated_cost_percent=costs)
        if payload.get("target") not in (None,""): target_result=evaluate_target(plan,float(payload["target"]))
    else: raise TradeInputError("Modo de cálculo inválido.")
    target_dict=target_result.to_dict() if isinstance(target_result,TargetPlan) else target_result
    return {"mode":mode,"plan":plan.to_dict(),"target":target_dict,"rr_ladder":[target_for_rr(plan,rr).to_dict() for rr in (1.0,1.5,2.0,2.5,3.0)],"risk_profiles":risk_profile_comparison(capital=capital,available_capital=available,side=side,entry=entry,stop=plan.stop,estimated_cost_percent=costs),"brief":build_brief(mode,plan,target_dict,profile_summary),"risk_profile_summary":profile_summary}
