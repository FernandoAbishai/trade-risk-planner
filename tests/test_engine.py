import unittest
from trade_risk.engine import RISK_PROFILES, TradeInputError, build_analysis, calculate_from_stop, evaluate_target, stop_from_position_budget, stop_from_target_rr, target_for_rr

class RiskProfileTests(unittest.TestCase):
    def test_profiles(self): self.assertEqual([x['percent'] for x in RISK_PROFILES.values()],[0.25,0.50,0.75,1.00,1.50,2.00])
    def test_default_math_on_100(self):
        p=calculate_from_stop(capital=100,available_capital=100,risk_profile='low_medium',side='long',entry=100,stop=98); self.assertAlmostEqual(p.risk_budget,0.50); self.assertAlmostEqual(p.position_size,25.0); self.assertAlmostEqual(p.actual_loss_at_stop,0.50)

class ReverseStopTests(unittest.TestCase):
    def test_long_target_plus_2r_solves_stop(self):
        p,t=stop_from_target_rr(capital=100,available_capital=100,risk_profile='medium',side='long',entry=100,target=110,desired_rr=2); self.assertAlmostEqual(p.stop,95.0); self.assertAlmostEqual(p.position_size,20.0); self.assertAlmostEqual(p.actual_loss_at_stop,1.0); self.assertAlmostEqual(t.net_profit,2.0); self.assertAlmostEqual(t.rr,2.0)
    def test_short_target_plus_2r_solves_stop(self):
        p,t=stop_from_target_rr(capital=100,available_capital=100,risk_profile='medium',side='short',entry=100,target=90,desired_rr=2); self.assertAlmostEqual(p.stop,105.0); self.assertAlmostEqual(t.rr,2.0)
    def test_inverse_round_trip_without_costs(self):
        p,t=stop_from_target_rr(capital=100,available_capital=100,risk_profile='medium',side='long',entry=100,target=112,desired_rr=3); rebuilt=target_for_rr(p,3); self.assertAlmostEqual(rebuilt.target_price,112.0); self.assertAlmostEqual(rebuilt.net_profit,t.net_profit)
    def test_inverse_round_trip_with_costs(self):
        p,t=stop_from_target_rr(capital=100,available_capital=100,risk_profile='medium',side='long',entry=100,target=110,desired_rr=2,estimated_cost_percent=0.20); self.assertAlmostEqual(t.rr,2.0,places=10); self.assertAlmostEqual(target_for_rr(p,2).target_price,110.0,places=10)
    def test_impossible_target_with_costs(self):
        with self.assertRaises(TradeInputError): stop_from_target_rr(capital=100,available_capital=100,risk_profile='medium',side='long',entry=100,target=100.1,desired_rr=3,estimated_cost_percent=0.20)

class BudgetStopTests(unittest.TestCase):
    def test_position_amount_solves_stop(self):
        p=stop_from_position_budget(capital=100,risk_profile='medium',side='long',entry=100,position_size=25); self.assertAlmostEqual(p.stop,96.0); self.assertAlmostEqual(p.actual_loss_at_stop,1.0)
    def test_position_budget_short(self): self.assertAlmostEqual(stop_from_position_budget(capital=100,risk_profile='medium',side='short',entry=100,position_size=25).stop,104.0)
    def test_position_cannot_exceed_capital(self):
        with self.assertRaises(TradeInputError): stop_from_position_budget(capital=100,risk_profile='medium',side='long',entry=100,position_size=101)

class KnownStopTests(unittest.TestCase):
    def test_stop_drives_position_size(self):
        near=calculate_from_stop(capital=100,available_capital=100,risk_profile='medium',side='long',entry=100,stop=99); far=calculate_from_stop(capital=100,available_capital=100,risk_profile='medium',side='long',entry=100,stop=95); self.assertGreater(near.position_size,far.position_size); self.assertAlmostEqual(near.actual_loss_at_stop,far.actual_loss_at_stop)
    def test_capital_limited_reduces_actual_risk(self):
        p=calculate_from_stop(capital=100,available_capital=20,risk_profile='high',side='long',entry=100,stop=99); self.assertTrue(p.capital_limited); self.assertAlmostEqual(p.actual_loss_at_stop,0.20); self.assertAlmostEqual(p.actual_risk_percent,0.20)
    def test_manual_target_evaluation(self):
        p=calculate_from_stop(capital=100,available_capital=100,risk_profile='medium',side='long',entry=100,stop=98); t=evaluate_target(p,106); self.assertAlmostEqual(t['rr'],3.0); self.assertAlmostEqual(t['net_profit'],3.0)
    def test_invalid_long_stop(self):
        with self.assertRaises(TradeInputError): calculate_from_stop(capital=100,available_capital=100,risk_profile='medium',side='long',entry=100,stop=101)

class AnalysisTests(unittest.TestCase):
    def test_target_mode_payload(self):
        r=build_analysis({'mode':'target','capital':100,'available_capital':100,'risk_profile':'medium','side':'long','entry':100,'target':110,'desired_rr':2}); self.assertAlmostEqual(r['plan']['stop'],95.0); self.assertAlmostEqual(r['target']['rr'],2.0); self.assertEqual(len(r['rr_ladder']),5); self.assertEqual(len(r['risk_profiles']),6); self.assertIn('target y el R:R',r['brief']['explanation'])
    def test_stop_mode_payload(self): self.assertAlmostEqual(build_analysis({'mode':'stop','capital':100,'available_capital':100,'risk_profile':'medium','side':'long','entry':100,'stop':98,'target':106})['target']['rr'],3.0)
    def test_position_mode_payload(self):
        r=build_analysis({'mode':'position','capital':100,'available_capital':100,'risk_profile':'medium','side':'long','entry':100,'position_size':25,'target':108}); self.assertAlmostEqual(r['plan']['stop'],96.0); self.assertAlmostEqual(r['target']['rr'],2.0)

if __name__=='__main__': unittest.main()
