import copy
import unittest

from guardrails.core import check, InvalidManifest


def deployment():
    return {'apiVersion': 'apps/v1', 'kind': 'Deployment', 'metadata': {'name': 'demo'},
            'spec': {'template': {'spec': {'automountServiceAccountToken': False,
                'securityContext': {'runAsNonRoot': True, 'seccompProfile': {'type': 'RuntimeDefault'}},
                'containers': [{'name': 'web', 'image': 'example.com/demo@sha256:' + 'a' * 64,
                    'resources': {'requests': {'cpu': '100m', 'memory': '64Mi'}, 'limits': {'cpu': '200m', 'memory': '128Mi'}},
                    'securityContext': {'allowPrivilegeEscalation': False, 'readOnlyRootFilesystem': True,
                                        'capabilities': {'drop': ['ALL']}}}]}}}}


class GuardrailTests(unittest.TestCase):
    def test_safe_workload(self): self.assertEqual(check(deployment())['findings'], [])

    def test_mutable_image(self):
        d=deployment();d['spec']['template']['spec']['containers'][0]['image']='example.com/demo:latest'
        self.assertIn('IMAGE_DIGEST', {f['rule'] for f in check(d)['findings']})

    def test_privileged_init_container(self):
        d=deployment();pod=d['spec']['template']['spec'];c=copy.deepcopy(pod['containers'][0]);c['securityContext']['privileged']=True;pod['initContainers']=[c]
        self.assertIn('PRIVILEGED', {f['rule'] for f in check(d)['findings']})

    def test_host_access(self):
        d=deployment();d['spec']['template']['spec']['hostNetwork']=True
        self.assertIn('HOST_ACCESS',{f['rule'] for f in check(d)['findings']})

    def test_secret_values_never_in_report(self):
        text='SYNTHETIC_DO_NOT_ECHO'
        r=check({'apiVersion':'v1','kind':'Secret','metadata':{'name':'demo'},'stringData':{'password':text}})
        self.assertIn('SECRET_PAYLOAD',{f['rule'] for f in r['findings']});self.assertNotIn(text,str(r))

    def test_env_literal(self):
        d=deployment();d['spec']['template']['spec']['containers'][0]['env']=[{'name':'API_TOKEN','value':'synthetic-value'}]
        self.assertIn('LITERAL_CREDENTIAL',{f['rule'] for f in check(d)['findings']})

    def test_secret_reference_allowed(self):
        d=deployment();d['spec']['template']['spec']['containers'][0]['env']=[{'name':'API_TOKEN','valueFrom':{'secretKeyRef':{'name':'runtime','key':'token'}}}]
        self.assertEqual(check(d)['findings'],[])

    def test_wildcard_role(self):
        d={'apiVersion':'rbac.authorization.k8s.io/v1','kind':'ClusterRole','metadata':{'name':'demo'},'rules':[{'verbs':['*'],'resources':['pods']}]}
        self.assertIn('RBAC_WILDCARD',{f['rule'] for f in check(d)['findings']})

    def test_missing_resources(self):
        d=deployment();del d['spec']['template']['spec']['containers'][0]['resources']
        self.assertIn('RESOURCE_BUDGET',{f['rule'] for f in check(d)['findings']})

    def test_nested_cronjob(self):
        d=deployment();d['kind']='CronJob';d['spec']={'jobTemplate':{'spec':d['spec']}}
        self.assertEqual(check(d)['findings'],[])

    def test_list_wrapper(self):
        self.assertEqual(check({'apiVersion':'v1','kind':'List','items':[deployment()]})['inspected'],1)

    def test_unknown_kind_visible(self):
        r=check({'apiVersion':'example.com/v1','kind':'Widget','metadata':{'name':'demo'}})
        self.assertEqual(r['uninspected'],['Widget'])

    def test_malformed_input(self):
        for d in (None,{},[],{'kind':'Deployment','spec':{'template':{'spec':{'containers':'invalid'}}}}):
            with self.subTest(d=d),self.assertRaises(InvalidManifest):check(d)

    def test_root_user(self):
        d=deployment();d['spec']['template']['spec']['containers'][0]['securityContext']['runAsUser']=0
        self.assertIn('ROOT_USER',{f['rule'] for f in check(d)['findings']})


if __name__=='__main__':unittest.main()
