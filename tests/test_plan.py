import copy
import unittest
from guardrails.plan import plan
from guardrails.core import InvalidManifest
from test_core import deployment


class PlanTests(unittest.TestCase):
    def test_unchanged(self):
        r=plan(deployment(),deployment());self.assertFalse(r['blocked']);self.assertEqual(r['actions'][0]['action'],'unchanged')
    def test_changed_image(self):
        newer=deployment();newer['spec']['template']['spec']['containers'][0]['image']='example.com/demo@sha256:'+'b'*64
        self.assertEqual(plan(deployment(),newer)['actions'][0]['action'],'update')
    def test_delete_requires_ack(self):
        newer=deployment();newer['metadata']['name']='replacement'
        self.assertTrue(plan(deployment(),newer)['blocked']);self.assertFalse(plan(deployment(),newer,True)['blocked'])
    def test_unsafe_after_blocked(self):
        newer=deployment();newer['spec']['template']['spec']['hostNetwork']=True
        self.assertTrue(plan(deployment(),newer)['blocked'])
    def test_duplicate_identity(self):
        with self.assertRaises(InvalidManifest):plan([deployment(),deployment()],deployment())
    def test_values_not_emitted(self):
        newer=deployment();newer['spec']['template']['spec']['containers'][0]['env']=[{'name':'API_TOKEN','value':'SYNTHETIC_NEVER_ECHO'}]
        self.assertNotIn('SYNTHETIC_NEVER_ECHO',str(plan(deployment(),newer)))
    def test_server_metadata_ignored(self):
        old=deployment();old['metadata']['resourceVersion']='123';old['status']={'readyReplicas':1}
        self.assertEqual(plan(old,deployment())['actions'][0]['action'],'unchanged')
