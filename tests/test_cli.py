import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class CLITests(unittest.TestCase):
    def run_manifest(self,text):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'manifest.json';p.write_text(text)
            return subprocess.run([sys.executable,'-m','guardrails','check',str(p)],capture_output=True,text=True)

    def test_duplicate_key_exit_2(self):
        p=self.run_manifest('{"kind":"Secret","kind":"Pod"}')
        self.assertEqual(p.returncode,2)

    def test_unsupported_kind_exit_1(self):
        p=self.run_manifest(json.dumps({'apiVersion':'example.com/v1','kind':'Widget','metadata':{'name':'demo'}}))
        self.assertEqual(p.returncode,1)
        self.assertEqual(json.loads(p.stdout)['uninspected'],['Widget'])

    def test_secret_payload_redacted(self):
        p=self.run_manifest(json.dumps({'apiVersion':'v1','kind':'Secret','metadata':{'name':'demo'},'data':{'password':'SYNTHETIC_VALUE'}}))
        self.assertEqual(p.returncode,1)
        self.assertNotIn('SYNTHETIC_VALUE',p.stdout+p.stderr)

    def test_nonfinite_json_exit_2(self):
        self.assertEqual(self.run_manifest('{"value":NaN}').returncode,2)


if __name__=='__main__':unittest.main()
