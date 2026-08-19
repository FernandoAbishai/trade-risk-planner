import unittest
from trade_risk.engine import TradeInputError, build_analysis, calculate_spot_plan, reward_for_rr, risk_band

class SpotEngineTests(unittest.TestCase):
    def test_default_math(self):
        p=calculate_spot_plan(capital=100,allocation_percent=50,risk_percent=.5,entry=100);self.assertAlmostEqual(p.position_value,50);self.assertAlmostEqual(p.risk_budget,.5);self.assertAlmostEqual(p.stop_distance_percent,1);self.assertAlmostEqual(p.stop_price,99);self.assertAlmostEqual(p.quantity,.5);self.assertAlmostEqual(p.modeled_loss,.5)
    def test_allocation_changes_stop_not_risk_budget(self):
        a=calculate_spot_plan(capital=100,allocation_percent=25,risk_percent=.5,entry=100);b=calculate_spot_plan(capital=100,allocation_percent=50,risk_percent=.5,entry=100);self.assertAlmostEqual(a.risk_budget,b.risk_budget);self.assertGreater(a.stop_distance_percent,b.stop_distance_percent)
    def test_risk_changes_stop(self):
        low=calculate_spot_plan(capital=100,allocation_percent=50,risk_percent=.5,entry=100);high=calculate_spot_plan(capital=100,allocation_percent=50,risk_percent=1,entry=100);self.assertGreater(high.stop_distance_percent,low.stop_distance_percent)
    def test_universal_price_scale(self):
        penny=calculate_spot_plan(capital=100,allocation_percent=50,risk_percent=.5,entry=.25);expensive=calculate_spot_plan(capital=100,allocation_percent=50,risk_percent=.5,entry=2500);self.assertAlmostEqual(penny.stop_distance_percent,expensive.stop_distance_percent);self.assertAlmostEqual(penny.position_value,expensive.position_value)
    def test_full_allocation(self):
        p=calculate_spot_plan(capital=100,allocation_percent=100,risk_percent=1,entry=50);self.assertAlmostEqual(p.position_value,100);self.assertAlmostEqual(p.stop_distance_percent,1);self.assertAlmostEqual(p.stop_price,49.5)
    def test_costs_reduce_price_room(self):
        a=calculate_spot_plan(capital=100,allocation_percent=50,risk_percent=.5,entry=100);b=calculate_spot_plan(capital=100,allocation_percent=50,risk_percent=.5,entry=100,estimated_cost_percent=.2);self.assertLess(b.stop_distance_percent,a.stop_distance_percent);self.assertAlmostEqual(b.modeled_loss,.5)
    def test_costs_can_exhaust_risk(self):
        with self.assertRaises(TradeInputError):calculate_spot_plan(capital=100,allocation_percent=100,risk_percent=.1,entry=100,estimated_cost_percent=.2)
    def test_allocation_over_100_rejected(self):
        with self.assertRaises(TradeInputError):calculate_spot_plan(capital=100,allocation_percent=101,risk_percent=.5,entry=100)
    def test_reward_2r(self):
        p=calculate_spot_plan(capital=100,allocation_percent=50,risk_percent=.5,entry=100);r=reward_for_rr(p,2);self.assertAlmostEqual(r.modeled_profit,1);self.assertAlmostEqual(r.target_price,102);self.assertAlmostEqual(r.break_even_win_rate_percent,100/3)
    def test_risk_bands(self):
        self.assertEqual(risk_band(.5)['label'],'Low');self.assertEqual(risk_band(1)['label'],'Medium');self.assertEqual(risk_band(2)['label'],'High');self.assertEqual(risk_band(3)['label'],'Very High')
    def test_build_analysis(self):
        r=build_analysis({'trade_type':'spot','capital':100,'allocation_percent':50,'risk_percent':.5,'entry':100,'rr':2});self.assertEqual(r['trade_type'],'spot');self.assertAlmostEqual(r['plan']['stop_price'],99);self.assertEqual(len(r['reward_ladder']),5);self.assertEqual(len(r['loss_streaks']),4);self.assertFalse(r['future_modes'][0]['enabled'])
    def test_non_spot_rejected(self):
        with self.assertRaises(TradeInputError):build_analysis({'trade_type':'futures','capital':100,'allocation_percent':50,'risk_percent':.5,'entry':100})

if __name__=='__main__':unittest.main()
