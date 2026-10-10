"""Auditable scenario model; inputs are assumptions unless accompanied by meters."""
import json,math,sys

def evaluate(v):
 required=['days','servers_off','server_watts','pue','endpoints','endpoint_extra_watts','endpoint_hours_per_day','extra_kwh','server_kg_per_kwh','endpoint_kg_per_kwh','extra_kg_per_kwh','tariff_per_kwh','monthly_added_operations','migration_cost']
 for k in required:
  n=v[k]
  if not isinstance(n,(int,float)) or isinstance(n,bool) or not math.isfinite(n) or n<0:raise ValueError('Invalid nonnegative finite input: '+k)
 if v['days']==0 or v['pue']<1 or v['endpoint_hours_per_day']>24:raise ValueError('Days/PUE/activity range invalid')
 server=v['servers_off']*v['server_watts']/1000*24*v['days']*v['pue']
 edge=v['endpoints']*v['endpoint_extra_watts']/1000*v['endpoint_hours_per_day']*v['days']
 net=server-edge-v['extra_kwh'];carbon=server*v['server_kg_per_kwh']-edge*v['endpoint_kg_per_kwh']-v['extra_kwh']*v['extra_kg_per_kwh'];cash=net*v['tariff_per_kwh']-v['monthly_added_operations']
 denominator=v['endpoints']*v['endpoint_hours_per_day']*v['days'];threshold=1000*(server-v['extra_kwh'])/denominator if denominator else None
 return {'scenarioOnly':True,'input':v,'avoidedServerFacilityKWh':round(server,4),'addedEndpointKWh':round(edge,4),'addedOtherKWh':v['extra_kwh'],'netEnergySavedKWh':round(net,4),'netOperationalCarbonAvoidedKg':round(carbon,4),'electricitySavingCurrency':round(net*v['tariff_per_kwh'],4),'netOperatingSavingCurrency':round(cash,4),'simplePaybackMonths':round(v['migration_cost']/cash,2) if cash>0 else None,'endpointEnergyBreakEvenExtraWatts':round(threshold,4) if threshold is not None else None,'boundary':'Assumed physical shutdown and measured-equivalent workload. No embodied-carbon credit, rack-wide saving, observed Keddeh result, verified tariff or guaranteed payback.'}
if __name__=='__main__':
 try:print(json.dumps(evaluate(json.load(open(sys.argv[1]))),indent=2))
 except Exception as e:print(json.dumps({'state':'failed','error':str(e)}),file=sys.stderr);sys.exit(1)
