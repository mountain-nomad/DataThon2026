import unittest
from jsonschema import ValidationError
from timeline_json_schema import validate
from context_object_timelines import read_observations


class TimelineSchemaTests(unittest.TestCase):
    def test_valid_scene_and_transfer(self):
        validate([{'t': 0, 'action': 'setup', 'event': 'Кассир сидит за столом.'},
                  {'t': 4.2, 'action': 'receive', 'event': 'Клиент передаёт деньги.'}])

    def test_rejects_wrong_envelope_and_missing_fields(self):
        for value in ({'events': []}, [], [{'t': 0, 'event': 'Кассир у стола.'}],
                      [{'t': '4.2', 'action': 'receive', 'event': 'Клиент передаёт деньги.'}]):
            with self.assertRaises(ValidationError):
                validate(value)

    def test_rejects_unknown_action_and_extra_fields(self):
        for value in ([{'t': 0, 'action': 'invented', 'event': 'Текст'}],
                      [{'t': 0, 'action': 'other', 'event': 'Текст', 'verdict': 'violation'}]):
            with self.assertRaises(ValidationError):
                validate(value)

    def test_cached_wrapper_repair_preserves_content(self):
        value = read_observations('{[{"t":25,"action":"other","event":"Конечное место скрыто."}]}',0,26)
        self.assertEqual(value, [{'t':25, 'action':'other', 'event':'Конечное место скрыто.'}])


if __name__ == '__main__':
    unittest.main()
