import unittest
from ramsc.joint_policy import JointInputs, simulate_policy


class JointPolicyTests(unittest.TestCase):
    def test_no_stock_deterministic_cycle(self):
        p=JointInputs(assets=1,lead_days=3,corrective_days=2,warmup_days=0,measurement_days=30)
        r=simulate_policy(p,float('inf'),0,lifetime_draw=lambda _:10)
        # Demands at days 10 and 25; waits+interventions cover 10--15,25--30.
        self.assertEqual(r['failures'],2)
        self.assertAlmostEqual(r['availability'],2/3)
        self.assertAlmostEqual(r['annual_down_asset_days'],10*365/30)

    def test_zero_lead_and_service_have_no_downtime(self):
        p=JointInputs(assets=3,lead_days=0,corrective_days=0,preventive_days=0,
                      warmup_days=0,measurement_days=31)
        r=simulate_policy(p,5,0,lifetime_draw=lambda _:10)
        self.assertEqual(r['availability'],1)
        self.assertEqual(r['failures'],0)
        self.assertEqual(r['preventive'],18)

    def test_stock_removes_wait_not_intervention(self):
        p=JointInputs(assets=1,lead_days=3,corrective_days=2,warmup_days=0,measurement_days=24)
        r=simulate_policy(p,float('inf'),1,lifetime_draw=lambda _:10)
        self.assertAlmostEqual(r['availability'],20/24)
        self.assertEqual(r['immediate_fraction'],1)
        self.assertAlmostEqual(r['annual_cost'],sum(r[k] for k in
            ['annual_procurement','annual_work_cost','annual_down_cost','annual_capital_charge']))

    def test_warmup_intersection_and_no_failures(self):
        p=JointInputs(assets=1,lead_days=3,corrective_days=2,warmup_days=12,measurement_days=8)
        r=simulate_policy(p,float('inf'),0,lifetime_draw=lambda _:10)
        # The downtime interval 10--15 overlaps measurement 12--20 by three days.
        self.assertAlmostEqual(r['availability'],5/8)
        self.assertEqual(r['demands'],0)
        empty=simulate_policy(p,float('inf'),2,lifetime_draw=lambda _:100000)
        self.assertEqual(empty['availability'],1.)
        self.assertEqual(empty['annual_cost'],2*p.part_price*p.capital_rate)


if __name__ == '__main__':
    unittest.main()
