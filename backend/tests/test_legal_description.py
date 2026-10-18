import json
from pathlib import Path
import unittest
from app.legal import load_legal, citation
from app.worker import _description, _type_name
from app.analyzers.local import result_to_analysis
from app.finding_catalog import catalog, require_type

ROOT=Path(__file__).resolve().parents[2]

class LegalDescriptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.legal=load_legal(ROOT/'backend/fortebank_violation_legal_mapping_updated.yaml',ROOT/'backend/specialist_crosswalk.yaml')

    def finding(self,rid='s2:L58'):
        entry=catalog()[rid]
        return {'rule_id':rid,'type':'НАРУШЕНИЕ: '+entry['name_ru'], 'quote':entry['quote'],
                'evidence':'Наблюдаемое действие.', 'limitations':['Содержание документа неразборчиво.']}

    def test_every_actual_rule_has_an_explicit_mapping(self):
        self.assertEqual(set(self.legal.crosswalk),set(catalog()))
        for rid,rule in self.legal.crosswalk.items():
            self.assertEqual(rule['name_ru'],catalog()[rid]['name_ru'])
            for key in rule.get('rule_ids',[]):
                self.assertIn(key,self.legal.rules)
                self.assertIn(self.legal.rules[key]['source_id'],self.legal.sources)

    def test_limits_before_official_source_with_blank_lines(self):
        r=self.finding();basis=self.legal.resolve(r['rule_id'])
        text=_description(r,basis)
        self.assertIn('\n\nОграничения: ',text)
        self.assertIn('\n\nИсточник: ',text)
        self.assertLess(text.index('Ограничения:'),text.index('Источник:'))
        self.assertIn('https://adilet.zan.kz/rus/docs/V1900019680',text)
        self.assertIn('п. 19, подп. 1',text)
        self.assertIn('Содержание документа неразборчиво.',text)
        self.assertNotIn('Основание:',text)

    def test_no_source_for_unmapped_or_nonbinding_types(self):
        for rid in ['s1:L15','s2:L57','s2:L61','s3:L85','s4:L110','s4:L111','s7:L182','s7:L186']:
            r=self.finding(rid);basis=self.legal.resolve(rid)
            self.assertIsNotNone(basis)
            self.assertEqual(basis['rules'],[])
            text=_description(r,basis)
            self.assertNotIn('Источник',text)
            self.assertNotIn('http',text)
            self.assertNotIn('норма не',text.lower())
            self.assertIn('Ограничения:',text)

    def test_bag_document_check_not_replaced_by_seal_check(self):
        basis=self.legal.resolve('s5:L136')
        ids={c['rule_id'] for c in basis['rules']}
        self.assertEqual(ids,{'R14','R15'})
        self.assertNotIn('п. 107',citation(basis))

    def test_type_is_exact_and_wrong_rule_or_suffix_is_rejected(self):
        r=self.finding();self.assertEqual(_type_name(self.legal.resolve(r['rule_id']),r),r['type'])
        for kind in [r['type']+' xyz','НАРУШЕНИЕ: Проход клиента в служебную зону']:
            with self.assertRaises(ValueError):require_type(r['rule_id'],kind)

    def test_model_limits_and_ids_survive_local_adapter(self):
        r=self.finding()
        data={'violations':[{'type':r['type'],'timecode_sec':1.2,'description':r['evidence']}],
              '_findings':[{'rule_id':r['rule_id'],'type':r['type']}], '_limitations':r['limitations']}
        result=result_to_analysis(data).specialist_results[0]
        self.assertEqual(result.rule_id,r['rule_id'])
        self.assertEqual(result.quote,r['quote'])
        self.assertEqual(result.limitations,r['limitations'])
        data['_findings']=[]
        with self.assertRaisesRegex(ValueError,'metadata'):result_to_analysis(data)

if __name__=='__main__':unittest.main()
