import json
import subprocess
import time
import unittest
from unittest.mock import patch, Mock
from app.analyzers import AnalysisContext
from app.analyzers.local import LocalAnalyzer, read_completed_scenario
from pathlib import Path
import tempfile

class LocalAnalyzerTests(unittest.TestCase):
    def analyze(self, payload, code=0):
        reply = Mock(returncode=code)
        reply.communicate.return_value = (json.dumps(payload), 'pipeline failed' if code else '')
        with patch('app.analyzers.local.subprocess.Popen', return_value=reply):
            return LocalAnalyzer().analyze('/tmp/example.mov', AnalysisContext(time.time()+60, lambda _:None))

    def test_finding_preserves_timestamp_and_description(self):
        result=self.analyze({'status':'done','_categories':['3','2'],'violations':[
            {'type':'ПРЕДУПРЕЖДЕНИЕ: Частичный возврат денег без предусмотренного процедурой основания','timecode_sec':1.2,'description':'Observed event'}], '_findings':[{'rule_id':'s2:L57','type':'ПРЕДУПРЕЖДЕНИЕ: Частичный возврат денег без предусмотренного процедурой основания'}]})
        self.assertEqual(result.scenario.primary,'CLIENT_CASH_DEPOSIT')
        self.assertEqual(result.scenario.secondary,'COUNTING_DEPOSIT_WITHOUT_CLIENT')
        finding=result.specialist_results[0]
        self.assertEqual((finding.start_sec,finding.evidence_timestamps),(1.2,[1.2]))
        self.assertEqual(finding.evidence,'Observed event')

    def test_empty_findings_produce_explicit_no_violation(self):
        result=self.analyze({'status':'done','violations':[]})
        self.assertEqual(result.specialist_results[0].status,'no_violation')

    def test_pipeline_failure_is_not_reported_as_no_violation(self):
        with self.assertRaisesRegex(RuntimeError,'bad video'):
            self.analyze({'status':'failed','error':'bad video'})

    def test_process_failure_is_reported(self):
        with self.assertRaisesRegex(RuntimeError,'pipeline failed'):
            self.analyze({},code=1)

class ProgressTests(unittest.TestCase):
    def test_incomplete_router_file_is_not_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory); route=folder/'artifacts/run/router'
            route.mkdir(parents=True); (route/'clip.json').write_text('{"status":')
            self.assertIsNone(read_completed_scenario(folder))
            (route/'clip.json').write_text(json.dumps({'status':'failed','predicted_labels':['3']}))
            self.assertIsNone(read_completed_scenario(folder))

    def test_router_completion_is_reported_before_final_result(self):
        partials=[]
        reply=Mock(returncode=0)
        reply.communicate.side_effect=[subprocess.TimeoutExpired('pipeline',0.5),
            (json.dumps({'status':'done','violations':[], '_categories':['3']}),'')]
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); route=root/'local/jobs/example/artifacts/run/router'
            route.mkdir(parents=True)
            (route/'clip.json').write_text(json.dumps({'status':'done','predicted_labels':['3']}))
            with patch('app.analyzers.local.ROOT',root), patch('app.analyzers.local.subprocess.Popen',return_value=reply):
                LocalAnalyzer().analyze('/tmp/example.mov',AnalysisContext(time.time()+60,partials.append))
        self.assertEqual(len(partials),1)
        self.assertEqual(partials[0]['scenario']['primary'],'CLIENT_CASH_DEPOSIT')
        self.assertEqual(partials[0]['specialist_results'],[])

if __name__=='__main__':unittest.main()
