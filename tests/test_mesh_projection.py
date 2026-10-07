import unittest
from keddeh_namespace.mesh_projection import project_mesh
class ProjectionTests(unittest.TestCase):
    def setUp(self):
        self.readback={'schema':'keddeh.web4.readback.v1','nodes':[{'port':19100,'ok':True,'compute_cycles':17,'state_hash':'source-hash'}]}
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
