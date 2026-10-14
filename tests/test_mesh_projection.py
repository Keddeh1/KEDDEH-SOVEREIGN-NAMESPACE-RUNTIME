import unittest
from datetime import datetime, timezone, timedelta
from keddeh_namespace.mesh_projection import project_mesh
class ProjectionTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime.now(timezone.utc)
        self.readback={'observedAt':self.now.isoformat(),'schema':'keddeh.web4.readback.v1','nodes':[{'port':19100,'ok':True,'compute_cycles':17,'state_hash':'source-hash'}]}
        self.geometry={'origin':{'x':0,'y':0,'z':0},'substratePhase':0,'source':'test-fixture-not-production','nodes':{'19100':{'x':1,'y':0,'z':0,'loopRadius':.1,'serviceUrl':'/serverspace'}}}
    def test_identity_and_measurements_survive(self):
        node=project_mesh(self.readback,self.geometry)['nodes'][0]
        self.assertEqual(node['id'],'web4:node:19100');self.assertEqual(node['computeCycles'],17);self.assertEqual(node['loopRadius'],.1)
    def test_missing_geometry_is_not_fabricated(self):
        self.geometry['nodes']={}
        with self.assertRaises(ValueError):project_mesh(self.readback,self.geometry)
    def test_nonfinite_rejected(self):
        self.geometry['substratePhase']=float('nan')
        with self.assertRaises(ValueError):project_mesh(self.readback,self.geometry)
    def test_external_route_rejected(self):
        self.geometry['nodes']['19100']['serviceUrl']='//external.example/'
        with self.assertRaises(ValueError):project_mesh(self.readback,self.geometry)

    def test_projection_preserves_original_observation_time(self):
        self.readback['observedAt']=(self.now-timedelta(seconds=30)).isoformat()
        result=project_mesh(self.readback,self.geometry,now=self.now)
        self.assertEqual(result['observedAt'],self.readback['observedAt'])

    def test_replayed_snapshot_expires_without_refresh(self):
        project_mesh(self.readback,self.geometry,now=self.now)
        with self.assertRaises(ValueError):
            project_mesh(self.readback,self.geometry,now=self.now+timedelta(seconds=61))

    def test_missing_naive_invalid_and_future_times_rejected(self):
        for stamp in (None,'invalid','2026-10-14T00:00:00',(self.now+timedelta(seconds=1)).isoformat()):
            with self.subTest(stamp=stamp):
                self.readback['observedAt']=stamp
                with self.assertRaises(ValueError):project_mesh(self.readback,self.geometry,now=self.now)
        del self.readback['observedAt']
        with self.assertRaises(ValueError):project_mesh(self.readback,self.geometry,now=self.now)

    def test_invalid_age_policies_rejected(self):
        for age in (True,0,-1,3601,float('nan'),float('inf'),'60'):
            with self.subTest(age=age):
                with self.assertRaises(ValueError):project_mesh(self.readback,self.geometry,now=self.now,max_age_seconds=age)

    def test_missing_geometry_attribution_rejected(self):
        for source in (None,'', ' '):
            self.geometry['source']=source
            with self.assertRaises(ValueError):project_mesh(self.readback,self.geometry,now=self.now)
