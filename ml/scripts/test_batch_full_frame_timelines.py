import unittest

from batch_full_frame_timelines import fits_one_request, merge_windows, parse_absolute, plan_segments, queue_order, select_samples, window_prompt, validate_counter_objects


class SourceTimeTests(unittest.TestCase):
    def test_document_in_counter_contradiction_is_rejected(self):
        for event in ['Кассир берет карточку и помещает ее в верхний лоток счетчика.',
                      'Кассир помещает удостоверение в лоток счетчика банкнот.',
                      'Карточка остается в лотке счетчика.',
                      'Кассир извлекает удостоверение из детектора.']:
            with self.assertRaises(ValueError):
                validate_counter_objects([{'t': 1, 'event': event}])
        validate_counter_objects([{'t': 1, 'event': 'Кассир кладет купюры в лоток счетчика.'},
                                  {'t': 2, 'event': 'Документ остается на столе возле счетчика.'}])
        validate_counter_objects([
            {'t': 1, 'event': 'Кассир рассматривает удостоверение и возвращает его клиенту.'},
            {'t': 2, 'event': 'Клиент отдельно передает купюры кассиру.'},
            {'t': 3, 'event': 'Кассир загружает купюры в лоток счетчика банкнот.'},
        ])

    def test_fitting_queue_precedes_long_videos_in_numerical_order(self):
        items = [{'id': 'Х-14', 'duration_sec': 142.533},
                 {'id': 'Х-3', 'duration_sec': 20},
                 {'id': 'X-1', 'duration_sec': 25.933},
                 {'id': 'Х-4', 'duration_sec': 72.7}]
        self.assertEqual([i['id'] for i in queue_order(items)], ['X-1', 'Х-3', 'Х-4', 'Х-14'])
        self.assertTrue(fits_one_request({'duration_sec': 26}))
        self.assertFalse(fits_one_request({'duration_sec': 26.01}))

    def test_longest_video_has_four_overlapping_windows_covering_end(self):
        windows = plan_segments(142.533)
        self.assertEqual(len(windows), 4)
        self.assertEqual(windows[0][0], 0)
        self.assertAlmostEqual(windows[-1][1], 142.533)
        for a, b in zip(windows, windows[1:]):
            self.assertAlmostEqual(a[1] - b[0], 2)

    def test_short_video_remains_one_request(self):
        self.assertEqual(plan_segments(25.933), [(0, 25.933)])

    def test_thinning_keeps_native_indices_and_absolute_times(self):
        samples = [{'timestamp_sec': i / 5, 'source_index': i * 6} for i in range(715)]
        result = select_samples(samples, 70, 108)
        self.assertEqual(len(result), 130)
        self.assertEqual(result[0], {'timestamp_sec': 70, 'source_index': 2100})
        self.assertEqual(result[-1]['timestamp_sec'], 108)
        self.assertTrue(all(s['source_index'] == round(s['timestamp_sec'] * 30) for s in result))

    def test_absolute_times_are_never_divided_or_offset(self):
        raw = '[{"t":71.2,"event":"Действие"},{"t":104.0,"event":"Передача"}]'
        self.assertEqual([e['t'] for e in parse_absolute(raw, 70, 108)], [71.2, 104])

    def test_reset_to_zero_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_absolute('[{"t":0,"event":"Действие"}]', 70, 108)

    def test_decimal_string_is_only_type_normalized(self):
        result = parse_absolute('[{"t":"105.400","event":"Действие"}]', 105.3, 142.5)
        self.assertEqual(result, [{'t': 105.4, 'event': 'Действие'}])

    def test_invalid_string_and_negative_times_are_rejected(self):
        for stamp in ['"NaN"', '"неизвестно"', '-0.01']:
            with self.assertRaises(ValueError):
                parse_absolute('[{"t":' + stamp + ',"event":"x"}]', 0, 10)

    def test_fenced_json_and_fractional_seconds_are_accepted(self):
        result = parse_absolute('```json\n[{"t":70.5,"event":"Действие"}]\n```', 70, 108)
        self.assertEqual(result[0]['t'], 70.5)

    def test_bad_times_are_rejected(self):
        for raw in ['[{"t":true,"event":"x"}]', '[{"t":NaN,"event":"x"}]',
                    '[{"t":80,"event":"x"},{"t":71,"event":"y"}]']:
            with self.assertRaises(ValueError):
                parse_absolute(raw, 70, 108)

    def test_merge_does_not_double_overlap_or_rewrite_events(self):
        a = {'t': 23, 'event': 'Ранняя передача'}
        b = {'t': 24, 'event': 'Поздняя передача'}
        windows = [{'start_sec': 0, 'end_sec': 25, 'timeline': [a, {'t': 24, 'event': 'Дубль'}]},
                   {'start_sec': 23, 'end_sec': 48, 'timeline': [{'t': 23, 'event': 'Дубль'}, b]}]
        self.assertEqual(merge_windows(windows), [a, b])

    def test_late_window_prompt_has_absolute_example(self):
        samples = [{'timestamp_sec': 70 + i / 5} for i in range(130)]
        prompt = window_prompt('При t=0 пример [{"t":0.0,"event":"x"},{"t":1.2,"event":"y"}]',
                               {'id': 'test', 'duration_sec': 142}, 70, 96, samples)
        self.assertNotIn('"t":0.0', prompt)
        self.assertIn('"t":70', prompt)
        self.assertIn('70.000', prompt)


if __name__ == '__main__':
    unittest.main()
