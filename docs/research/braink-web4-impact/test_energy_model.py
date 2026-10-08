import unittest
from energy_model import evaluate
class EnergyModelChecks(unittest.TestCase):
 def base(self):return dict(days=30,servers_off=6,server_watts=300,pue=1.4,endpoints=1000,endpoint_extra_watts=2,endpoint_hours_per_day=8,extra_kwh=218.8,server_kg_per_kwh=.4,endpoint_kg_per_kwh=.65,extra_kg_per_kwh=.4,tariff_per_kwh=.25,monthly_added_operations=250,migration_cost=5000)
 def test_no_shutdown_cannot_create_avoided_server_energy(self):
  v=self.base();v['servers_off']=0;r=evaluate(v);self.assertEqual(r['avoidedServerFacilityKWh'],0);self.assertLess(r['netEnergySavedKWh'],0)
 def test_extra_endpoint_power_can_reverse_saving(self):
  v=self.base();v['endpoint_extra_watts']=8;r=evaluate(v);self.assertAlmostEqual(r['netEnergySavedKWh'],-324.4);self.assertIsNone(r['simplePaybackMonths'])
 def test_monthly_units_and_break_even(self):
  r=evaluate(self.base());self.assertAlmostEqual(r['avoidedServerFacilityKWh'],1814.4);self.assertAlmostEqual(r['netEnergySavedKWh'],1115.6);self.assertAlmostEqual(r['endpointEnergyBreakEvenExtraWatts'],6.6483,places=4)
 def test_nonfinite_and_impossible_activity_rejected(self):
  for k,value in [('server_watts',float('nan')),('pue',.9),('endpoint_hours_per_day',25)]:
   v=self.base();v[k]=value
   with self.assertRaises(ValueError):evaluate(v)
if __name__=='__main__':unittest.main()
