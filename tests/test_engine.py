import unittest

from trade_risk.engine import (
    TradeInputError,
    build_analysis,
    calculate_budget_stop,
    calculate_from_chart_stop,
    reward_for_rr,
    risk_band,
)

class BudgetStopTests(unittest.TestCase):
    def test_default_math(self):
        p = calculate_budget_stop(capital=100, allocation_percent=50, risk_percent=.5, entry=100)
        self.assertAlmostEqual(p.position_value, 50)
        self.assertAlmostEqual(p.risk_budget, .5)
        self.assertAlmostEqual(p.stop_distance_percent, 1)
        self.assertAlmostEqual(p.stop_price, 99)
        self.assertAlmostEqual(p.quantity, .5)
        self.assertAlmostEqual(p.modeled_loss, .5)

    def test_allocation_changes_stop(self):
        a = calculate_budget_stop(capital=100, allocation_percent=25, risk_percent=.5, entry=100)
        b = calculate_budget_stop(capital=100, allocation_percent=50, risk_percent=.5, entry=100)
        self.assertAlmostEqual(a.risk_budget, b.risk_budget)
        self.assertAlmostEqual(a.stop_distance_percent, 2)
        self.assertAlmostEqual(b.stop_distance_percent, 1)

    def test_risk_changes_stop(self):
        low = calculate_budget_stop(capital=100, allocation_percent=50, risk_percent=.5, entry=100)
        high = calculate_budget_stop(capital=100, allocation_percent=50, risk_percent=1, entry=100)
        self.assertAlmostEqual(low.stop_distance_percent, 1)
        self.assertAlmostEqual(high.stop_distance_percent, 2)

    def test_universal_price_scale(self):
        a = calculate_budget_stop(capital=100, allocation_percent=50, risk_percent=.5, entry=.25)
        b = calculate_budget_stop(capital=100, allocation_percent=50, risk_percent=.5, entry=2500)
        self.assertAlmostEqual(a.stop_distance_percent, b.stop_distance_percent)
        self.assertAlmostEqual(a.position_value, b.position_value)

    def test_costs_reduce_stop_room(self):
        p = calculate_budget_stop(capital=100, allocation_percent=50, risk_percent=.5, entry=100, estimated_cost_percent=.2)
        self.assertAlmostEqual(p.stop_distance_percent, .8)
        self.assertAlmostEqual(p.stop_price, 99.2)
        self.assertAlmostEqual(p.modeled_loss, .5)

    def test_allocation_too_small_caps_stop_at_zero(self):
        p = calculate_budget_stop(capital=100, allocation_percent=1, risk_percent=5, entry=100)
        self.assertTrue(p.allocation_capped)
        self.assertEqual(p.stop_price, 0)
        self.assertAlmostEqual(p.modeled_loss, 1)
        self.assertAlmostEqual(p.actual_risk_percent, 1)
        self.assertFalse(p.risk_budget_fully_used)

    def test_quantity_precision_rounds_down_and_recalculates_stop(self):
        p = calculate_budget_stop(capital=100, allocation_percent=50, risk_percent=.5, entry=33, quantity_precision=2)
        self.assertEqual(p.quantity, 1.51)
        self.assertAlmostEqual(p.position_value, 49.83)
        self.assertAlmostEqual(p.modeled_loss, .5, places=10)

    def test_quantity_precision_can_make_trade_impossible(self):
        with self.assertRaises(TradeInputError):
            calculate_budget_stop(capital=10, allocation_percent=10, risk_percent=.5, entry=1000, quantity_precision=0)

    def test_costs_can_exhaust_budget(self):
        with self.assertRaises(TradeInputError):
            calculate_budget_stop(capital=100, allocation_percent=100, risk_percent=.1, entry=100, estimated_cost_percent=.2)

class ChartStopTests(unittest.TestCase):
    def test_chart_stop_solves_allocation(self):
        p = calculate_from_chart_stop(capital=100, risk_percent=1, entry=100, stop_price=95)
        self.assertAlmostEqual(p.position_value, 20)
        self.assertAlmostEqual(p.allocation_percent, 20)
        self.assertAlmostEqual(p.modeled_loss, 1)

    def test_chart_stop_can_be_capital_limited(self):
        p = calculate_from_chart_stop(capital=100, risk_percent=1, entry=100, stop_price=99.5)
        self.assertTrue(p.allocation_capped)
        self.assertAlmostEqual(p.position_value, 100)
        self.assertAlmostEqual(p.modeled_loss, .5)
        self.assertAlmostEqual(p.actual_risk_percent, .5)

    def test_chart_stop_with_costs(self):
        p = calculate_from_chart_stop(capital=100, risk_percent=1, entry=100, stop_price=98, estimated_cost_percent=.5)
        self.assertAlmostEqual(p.position_value, 40)
        self.assertAlmostEqual(p.modeled_loss, 1)

    def test_chart_stop_must_be_below_entry(self):
        with self.assertRaises(TradeInputError):
            calculate_from_chart_stop(capital=100, risk_percent=1, entry=100, stop_price=101)

class RewardTests(unittest.TestCase):
    def test_two_r_without_costs(self):
        p = calculate_budget_stop(capital=100, allocation_percent=50, risk_percent=.5, entry=100)
        r = reward_for_rr(p, 2)
        self.assertAlmostEqual(r.modeled_profit, 1)
        self.assertAlmostEqual(r.target_price, 102)
        self.assertAlmostEqual(r.break_even_win_rate_percent, 100/3)

    def test_two_r_with_costs(self):
        p = calculate_budget_stop(capital=100, allocation_percent=50, risk_percent=.5, entry=100, estimated_cost_percent=.2)
        r = reward_for_rr(p, 2)
        self.assertAlmostEqual(r.modeled_profit, 1)
        self.assertAlmostEqual(r.target_price, 102.2)

class AnalysisTests(unittest.TestCase):
    def test_risk_bands(self):
        self.assertEqual(risk_band(.5)["label"], "Low")
        self.assertEqual(risk_band(1)["label"], "Medium")
        self.assertEqual(risk_band(2)["label"], "High")
        self.assertEqual(risk_band(3)["label"], "Very High")

    def test_budget_mode_analysis(self):
        r = build_analysis({"trade_type":"spot", "calculation_mode":"budget_stop", "capital":100, "allocation_percent":50, "risk_percent":.5, "entry":100, "rr":2})
        self.assertEqual(r["calculation_mode"], "budget_stop")
        self.assertAlmostEqual(r["plan"]["stop_price"], 99)
        self.assertEqual(len(r["reward_ladder"]), 6)
        self.assertEqual(len(r["loss_streaks"]), 4)

    def test_chart_mode_analysis(self):
        r = build_analysis({"trade_type":"spot", "calculation_mode":"chart_stop", "capital":100, "risk_percent":1, "entry":100, "chart_stop":95, "rr":2})
        self.assertAlmostEqual(r["plan"]["allocation_percent"], 20)
        self.assertIn("supplied a chart stop", r["brief"]["summary"])

    def test_high_friction_warning(self):
        r = build_analysis({"trade_type":"spot", "calculation_mode":"budget_stop", "capital":100, "allocation_percent":50, "risk_percent":.5, "entry":100, "estimated_cost_percent":.6, "rr":2})
        self.assertTrue(any(w["level"]=="warning" for w in r["warnings"]))

    def test_non_spot_rejected(self):
        with self.assertRaises(TradeInputError):
            build_analysis({"trade_type":"futures", "capital":100, "allocation_percent":50, "risk_percent":.5, "entry":100})

if __name__ == "__main__":
    unittest.main()
