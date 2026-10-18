"""Contract tests for combined scenarios and real JPEG evidence."""
import base64
import io
import json
from pathlib import Path
import tempfile
import unittest

from final_text_audit import ROOT, attach_evidence, combined_prompt, validate, description_without_timestamps, output_schema
from finding_catalog import allowed_types, catalog


class FinalAuditTests(unittest.TestCase):
    def test_description_has_no_extra_timestamps(self):
        self.assertEqual(description_without_timestamps(
            'На t=20.0 кассир возвращает купюры (t=22.0) после пересчета (t=14-19).'),
            'Кассир возвращает купюры после пересчета.')
        self.assertEqual(description_without_timestamps('Согласно правилу (шаг 8), это отклонение.'),
                         'Согласно правилу (шаг 8), это отклонение.')
        self.assertEqual(description_without_timestamps(
            'Виден вход (55.0с), затем прием денег (60.8с).'),
            'Виден вход, затем прием денег.')

    def setUp(self):
        self.record = {'duration_sec': 10, 'timeline': [{'t': 1.0, 'event': 'Действие'},
                                                       {'t': 3.0, 'event': 'Переход'}]}
        source = (ROOT / 'scenario (2).md').read_text()
        self.prompt, self.rules = combined_prompt(source, ['3', '2'], self.record)

    def test_combined_categories_include_both_scopes_and_no_old_statuses(self):
        self.assertIn('НАЙДЕННЫЕ КАТЕГОРИИ: 3, 2', self.prompt)
        self.assertEqual({r['section'] for r in self.rules.values()}, {2, 6})
        self.assertIn('Вариант А.', self.prompt)
        self.assertIn('Вариант Б.', self.prompt)
        self.assertIn('МОЖЕТ БЫТЬ ТОЛЬКО ОТРЕЗКОМ', self.prompt)
        self.assertIn('интерпретируй этот предмет как ДЕНЬГИ/КУПЮРЫ', self.prompt)

    def finding(self, violation=True):
        rule_id = next(k for k, r in self.rules.items()
                       if r['quote'].startswith('Нарушение:') == violation)
        return {'rule_id': rule_id,
                'type': allowed_types(rule_id, self.rules[rule_id])[0],
                'timecode_sec': 1.0, 'description': 'Наблюдение и обоснование'}

    def test_binary_verdict_and_warning(self):
        for events in ([], [self.finding()], [self.finding(False)]):
            value = {'verdict': 'violation' if events else 'no_violation',
                     'violations': events, 'limitations': ['Показан только фрагмент']}
            self.assertEqual(validate(json.dumps(value), self.rules, self.record), value)
        with self.assertRaises(ValueError):
            validate(json.dumps({'verdict': 'no_violation', 'violations': [self.finding()],
                                 'limitations': []}), self.rules, self.record)

    def test_reject_hallucinated_times_and_wrong_rule_scope(self):
        ideal_id = next(k for k, r in self.rules.items() if not r['quote'].startswith('Нарушение:'))
        for changes in ({'timecode_sec': 2}, {'timecode_sec': 11},
                        {'evidence_timestamps_sec': []}, {'rule_id': 'unknown'},
                        {'rule_id': ideal_id}):
            event = dict(self.finding(), **changes)
            with self.assertRaises(ValueError):
                validate(json.dumps({'verdict': 'violation', 'violations': [event],
                                     'limitations': []}), self.rules, self.record)

    def test_description_length_is_guidance_and_evidence_check_is_bounded(self):
        event = self.finding()
        value = {'evidence_check': ['Наблюдаемое действие сверено с правилом.'],
                 'verdict': 'violation', 'violations': [event], 'limitations': []}
        self.assertEqual(validate(json.dumps(value), self.rules, self.record), value)
        long_value = dict(value, violations=[dict(event, description='Наблюдение и связь с правилом. ' * 40)])
        self.assertEqual(validate(json.dumps(long_value), self.rules, self.record), long_value)
        for check, description in ((['x' * 221], 'Наблюдение'),
                                   (['Факт'] * 3, 'Наблюдение')):
            bad = dict(value, evidence_check=check,
                       violations=[dict(event, description=description)])
            with self.assertRaises(ValueError):
                validate(json.dumps(bad), self.rules, self.record)

    def test_warning_can_reference_unconfirmed_typical_violation(self):
        event = self.finding()
        event['type'] = allowed_types(event['rule_id'], self.rules[event['rule_id']])[1]
        value = {'verdict': 'violation', 'violations': [event], 'limitations': []}
        self.assertEqual(validate(json.dumps(value), self.rules, self.record), value)

    def test_real_jpeg_base64_and_actual_frame_timestamp(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            Image.new('RGB', (20, 30), 'red').save(root / 'frame.png')
            record = dict(self.record, windows=[{'samples': [
                {'timestamp_sec': 1.1, 'path': 'frame.png'},
                {'timestamp_sec': 3.1, 'path': 'frame.png'}]}])
            value = {'verdict': 'violation', 'violations': [self.finding()]}
            result = attach_evidence(value, record, 'test', root)
            self.assertEqual(set(result), {'job_id', 'status', 'verdict', 'violations'})
            finding = result['violations'][0]
            self.assertEqual(set(finding), {'type', 'timecode_sec', 'description', 'evidence_frames'})
            self.assertEqual([f['timestamp_sec'] for f in finding['evidence_frames']], [1.1])
            self.assertEqual(finding['timecode_sec'], 1.1)
            for frame in finding['evidence_frames']:
                image = Image.open(io.BytesIO(base64.b64decode(frame['image_base64'], validate=True)))
                self.assertEqual(image.format, 'JPEG')
                self.assertEqual(image.size, (20, 30))

    def test_fixed_enum_rejects_random_or_other_rule_type(self):
        from jsonschema import validate as schema_validate
        from jsonschema.exceptions import ValidationError
        event=self.finding()
        value={'evidence_check':['Наблюдаемый факт.'], 'limitations':[],
               'violations':[event], 'verdict':'violation'}
        schema_validate(value,output_schema(self.rules,self.record))
        wrong=dict(value,violations=[dict(event,type=event['type']+' RANDOM')])
        with self.assertRaises(ValidationError):schema_validate(wrong,output_schema(self.rules,self.record))
        with self.assertRaises(ValueError):validate(json.dumps(wrong),self.rules,self.record)
        other=next(rid for rid in self.rules if rid!=event['rule_id'])
        wrong=dict(value,violations=[dict(event,type=allowed_types(other,self.rules[other])[0])])
        with self.assertRaises(ValueError):validate(json.dumps(wrong),self.rules,self.record)

    def test_catalogue_has_exactly_the_actual_rules(self):
        from scenario_audit import rule_catalog
        source=(ROOT/'scenario (2).md').read_text()
        rules=rule_catalog(source,list(range(1,8)))
        self.assertEqual(set(rules),set(catalog()))
        for rid,rule in rules.items():
            self.assertEqual(catalog()[rid]['quote'],rule['quote'])
            for kind in allowed_types(rid,rule):self.assertTrue(kind)


if __name__ == '__main__':
    unittest.main()
