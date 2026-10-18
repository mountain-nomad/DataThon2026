"""Video-grounded timelines: contextual object naming in the prompt, no code relabeling."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import sys
import time

from batch_full_frame_timelines import prepare_frames, select_samples, parse_absolute, save_json
from timeline_json_schema import prefix_constraint, validate as validate_schema

ROOT = Path(__file__).resolve().parents[1]
PROMPT = '''Составь подробную хронологию видимых действий в кассовом кабинете.
Это наблюдение по видео, а не проверка нарушений и не пересказ идеального сценария.
Видео может быть только отрезком операции. Не достраивай пропущенные действия.

ОТСЛЕЖИВАНИЕ ПЕРЕДАВАЕМЫХ ПРЕДМЕТОВ
Сначала просмотри весь доступный эпизод и проследи непрерывную историю каждого
предмета: откуда взят, кто кому передал, кто рассматривал, куда вернул или положил,
какое оборудование затем использовали с ЭТИМ ЖЕ предметом. Определяй название по
контексту использования и последовательности передач, а не по сходству маленьких
светлых прямоугольников. Удостоверение и купюры визуально трудно различимы.

Используй следующую общую рабочую договорённость для каждого клиента отдельно:
если видны две отдельные передачи разных предметов клиентом кассиру, сначала
передано удостоверение, затем деньги. Первый предмет обычно рассматривают и
возвращают; второй используют как наличные. Если в наблюдаемом взаимодействии
видна только одна такая передача, называй переданное деньгами. Это договорённость
для наименования наблюдаемых предметов, а не доказательство полноты процедуры.
Не придумывай первый обмен только потому, что он ожидается по сценарию.
Предмет, действительно загруженный в приёмный лоток счётчика банкнот, — деньги.
Согласуй его название с предыдущими и последующими действиями того же предмета.
Просто нахождение рядом со счётчиком ещё не означает загрузку.

Различай отдельные передачи и продолжение одного движения: протягивание и приём
того же предмета — одна передача. Возврат кассиром клиенту не является новой
передачей клиентом кассиру. Повторное перекладывание, несколько кадров одного
движения, части одной пачки — не дополнительные предметы. Не назначай типы
механически по числу строк таймлайна. При смене клиента начни отслеживание его
предметов заново, не переноси предыдущие обмены на следующего человека.
Когда связь теряется из-за перекрытия/качества, прямо опиши видимое действие и
ограничение: «перемещает предмет, дальнейшее положение закрыто рукой».
Можно оставить «предмет», если контекст действительно не позволяет связать его.
Не добавляй предполагаемую передачу и не меняй направление ради договорённости.
В итоговом тексте используй естественные названия с правильными падежами, без p1/p2.

МЕСТОПОЛОЖЕНИЕ ПРЕДМЕТОВ И СЕЙФ
Описывай помещение в сейф, когда виден открытый сейф и по движению предмета
понятно, что его кладут внутрь. Аналогично отмечай извлечение, открытие и закрытие,
когда эти действия различимы. Отдельно различай движение к сейфу и помещение внутрь:
нахождение денег рядом с корпусом само по себе ещё не показывает, что они в сейфе.
Если рука или предмет перекрыты и конечное место не видно, опиши видимую часть
движения и укажи, что дальнейшее положение скрыто. Не дополняй её ожидаемым
следующим шагом процедуры. Это же правило наблюдения применяй к столу, сумкам,
карманам и оборудованию. Сохраняй реально видимые действия с сейфом в хронологии.

ПОЛНОТА И СТИЛЬ
Кассир — сотрудник, работающий с оборудованием, клиент — посетитель. Роли сохраняй
по всему взаимодействию, не определяй их только по одежде, полу или стороне кадра.
Обычно пиши просто «клиент». Только когда в одном ролике действительно несколько
разных клиентов и нужно их различить, используй «первый клиент», «второй клиент».
Не нумеруй единственного клиента и не называй отражение отдельным участником.

Первое событие конкретно описывает видимую исходную сцену: участники, оборудование,
стол и предметы, дверь кабинета, дверца сейфа, крышка ноутбука, если это видно.
Не перечисляй невидимое и не ограничивайся словом «обстановка».
Далее сохраняй все значимые изменения, а не только обмен предметами: вход и дверь,
подход/посадка/вставание, передачи/проверки/возвраты, положение предметов на столе,
загрузка, запуск и извлечение из счётчика, детектор, работа с ноутбуком, записи,
печати, сумки, сейф и ключ, личные вещи, выход. Не повторяй неизменные паузы.
В активном эпизоде фиксируй значимые переходы примерно через 1–2 секунды, если они
видны. Не придумывай события ради частоты. Различай загрузку и запуск счётчика.
Следи за обеими руками и остатком денег: передача части не означает передачу всего.
Суммы, количество купюр, намерения, содержание экранов не угадывай.
В конце укажи последнее видимое положение предметов, если оно прослеживается.
Особенно сохрани наблюдение о деньгах, оставшихся на столе: это важный факт для
последующей проверки правил. Не заменяй его ожидаемым помещением в сейф и не
называй нарушением на этапе хронологии. Если окончание операции не видно, отметь
именно последнее наблюдаемое положение, не утверждая её завершение.
Не считай исчезновение предмета помещением в сейф, а закрытие ноутбука выключением.
Не делай вывод о завершении операции только по окончанию файла.

Верни только JSON-массив событий по времени. Каждая запись:
Поля записи: t — число секунд, action — строка типа действия, event — описание по-русски.
Ответ начинается с [ и заканчивается ], без внешних фигурных скобок.
action: setup, client_enter, client_leave, receive, return, inspect,
counter_load, counter_unload, safe_put, safe_open, safe_close, other.
Типы действий служебные, а event должен быть полноценным конкретным предложением.
Используй только времена из списка кадров, не выдумывай секунды между ними.
Для нескольких клиентов у client_enter добавь поле client — порядковый номер
клиента, нужный только для поиска подробного фрагмента; в тексте номера не нужны.
Никаких вердиктов, нарушений, идеальных процедур или пояснений вне массива.
'''


TEXT_PROMPT = """Согласуй названия передаваемых предметов в наблюдениях за кассовой операцией.
Это текстовый этап после просмотра видео. Не добавляй визуальные факты и действия.
Сохрани ровно те же события, порядок, время t и action. Уточни только названия
предметов и согласование слов, сохраняя участника, движение и место каждого действия.
Проследи историю каждого предмета от получения до проверки, возврата, стола,
счётчика; один предмет называй последовательно во всех связанных событиях.
Общая договорённость для каждого клиента отдельно: две отдельные передачи разных
предметов от клиента кассиру — сначала удостоверение, потом деньги; одна передача —
деньги. Возврат клиенту, повторное перекладывание и части одной пачки не считай
новой передачей. Не придумывай отсутствующие обмены. Предмет в лотке счётчика — деньги,
применяй это название ко всей его прослеживаемой цепочке. Не меняй деньги на
удостоверение лишь по внешнему сходству. Если связь действительно потеряна,
сохрани неопределённость; это не повод выдумать действие или новый предмет.
Предмет в составном событии может упоминаться вместе с другим предметом:
обрабатывай каждое упоминание по его собственной истории, не дели события на
взаимоисключающие группы. Правила здесь служат наименованию, не оценке нарушений.
Обычно пиши «клиент», а при необходимости различать нескольких — «первый клиент»,
«второй клиент». Сохрани наблюдаемое положение и ограничения видимости.
Сохрани последнее наблюдаемое положение денег, особенно оставшиеся на столе:
это значимый факт для будущей проверки правил, а не лишнее описание паузы.
Не добавляй помещение в сейф по ожидаемому сценарию, не удаляй реально описанное
наблюдателем действие. Не меняй направление передач. Не добавляй события.
Верни только корректный JSON-массив тех же событий с полями t, action, event и
остальными исходными служебными полями. Поле client сохраняй отдельным полем,
не переноси его в event и не добавляй приписки «Клиент: 1». Единственного клиента
называй просто «клиент». Начни с [ и закончи ], без внешних {}.
"""


def read_observations(raw, start, end):
    # Repair only a redundant outer wrapper; do not change any event content.
    text = raw.strip()
    if text.startswith('```'):
        text = text.split('\n', 1)[1].rsplit('```', 1)[0].strip()
    if re.fullmatch(r'\{\s*\[.*\]\s*\}', text, re.S):
        text = text[1:-1].strip()
    events = parse_absolute(text, start, end)
    validate_schema(events)
    return events


def export(base, records, total, finished=False):
    lines = ['# Таймстепы: контекст предметов', '',
             'Названия и действия выданы видеомоделью по общему промпту. '
             'Код не назначает типы предметов; названия согласует txt2txt по общему промпту. '
             'Финальный анализ нарушений не запускался.', '']
    for r in records:
        body = [f'## {r["id"]}', '', f'Статус: {r["status"]}.', '']
        if r['status'] == 'done':
            body += ['```json', json.dumps(r['timeline'], ensure_ascii=False, indent=2), '```', '']
        else:
            body += [r.get('error', ''), '']
        (base / 'outputs' / (r['id'] + '.md')).write_text('\n'.join(body))
        lines += [f'[Отдельный файл {r["id"]}](outputs/{r["id"]}.md)', ''] + body
    (base / 'current_outputs.md').write_text('\n'.join(lines))
    save_json(base / 'progress.json', {
        'status': ('done' if all(r['status'] == 'done' for r in records) else 'failed') if finished else 'running',
        'done': sum(r['status'] == 'done' for r in records), 'total': total})


def run(args, folder, config, infer, passed, root):
    import numpy as np
    import torch
    from PIL import Image
    from transformers.video_utils import VideoMetadata
    base = OPTIONS.output_dir
    objects = [cell.cell_contents for cell in infer.__closure__]
    model = next(o for o in objects if hasattr(o, 'generate') and hasattr(o, 'named_modules'))
    processor = next(o for o in objects if hasattr(o, 'apply_chat_template') and hasattr(o, 'tokenizer'))
    original_generate = model.generate

    def structured_generate(*positional, **kwargs):
        kwargs['prefix_allowed_tokens_fn'] = prefix_constraint(processor.tokenizer)
        return original_generate(*positional, **kwargs)

    # Synthetic control has already run; all subsequent calls produce timelines.
    model.generate = structured_generate
    inventory = {r['id']: r for r in json.loads((ROOT / 'artifacts/all_videos_full_frame_usage_rule/manifest.json').read_text())}
    records = []
    for video_id in OPTIONS.ids:
        item = inventory[video_id]
        started = time.monotonic()
        r = {'id': video_id, 'sha256': item['sha256'], 'duration_sec': item['duration_sec'],
             'status': 'running', 'synthetic_control_passed': passed,
             'prompt_sha256': hashlib.sha256(PROMPT.encode()).hexdigest()}
        try:
            all_samples = prepare_frames(item)

            def observe(start, end, suffix, context=''):
                samples = select_samples(all_samples, start, end, cap=130)
                frames = np.stack([np.asarray(Image.open(ROOT / s['path']).convert('RGB')) for s in samples])
                metadata = VideoMetadata(total_num_frames=item['total_num_frames'], fps=item['source_fps'],
                    frames_indices=[s['source_index'] for s in samples], duration=item['duration_sec'])
                prompt = PROMPT + f'\nПередан интервал {start:.3f}–{end:.3f} секунд исходного видео. '
                prompt += 'Время абсолютное, не начинай его заново. ' + context
                prompt += '\nСекунды кадров: ' + ', '.join(str(s['timestamp_sec']) for s in samples)
                (base / 'prompts' / f'{video_id}_{suffix}.txt').write_text(prompt)
                cached = OPTIONS.reuse_visual / 'raw' / f'{video_id}_{suffix}.txt' if OPTIONS.reuse_visual else None
                if cached and cached.exists() and not (OPTIONS.reuse_full_only and suffix != 'full'):
                    raw, stats = cached.read_text(), {'reused_raw': str(cached)}
                else:
                    raw, stats = infer(frames, metadata, prompt, max_new_tokens=4096)
                (base / 'raw' / f'{video_id}_{suffix}.txt').write_text(raw)
                original = read_observations(raw, start, end)
                text_prompt = TEXT_PROMPT + '\nНАБЛЮДЕНИЯ\n' + json.dumps(original, ensure_ascii=False)
                (base / 'prompts' / f'{video_id}_{suffix}_text.txt').write_text(text_prompt)
                chat = processor.apply_chat_template([{'role':'user', 'content':[{'type':'text','text':text_prompt}]}],
                    tokenize=False, add_generation_prompt=True, enable_thinking=False)
                inputs = processor.tokenizer([chat], return_tensors='pt').to('cuda')
                with torch.inference_mode():
                    output = model.generate(**inputs, do_sample=False, max_new_tokens=4096, use_cache=True)
                text_raw = processor.tokenizer.batch_decode(output[:, inputs['input_ids'].shape[1]:], skip_special_tokens=True)[0]
                (base / 'raw' / f'{video_id}_{suffix}_text.txt').write_text(text_raw)
                events = read_observations(text_raw, start, end)
                if [(e['t'], e.get('action')) for e in events] != [(e['t'], e.get('action')) for e in original]:
                    raise ValueError('Text refinement changed event count, timestamps or action types')
                return {'start': start, 'end': end, 'events': events, 'original_events': original,
                        'samples': samples, 'stats': stats, 'text_input_keys': list(inputs)}

            full = observe(0, item['duration_sec'], 'full')
            r['full'] = full
            events = full['events']
            focus = []
            if item['duration_sec'] > 30:
                entries = [e for e in events if e.get('action') == 'client_enter']
                for n, entry in enumerate(entries):
                    start = max(0, entry['t'] - 1.5)
                    end = min(item['duration_sec'], entry['t'] + 24,
                              entries[n+1]['t'] - 1.5 if n+1 < len(entries) else item['duration_sec'])
                    if end <= start:
                        continue
                    context = ('В полном ролике видны несколько клиентов. Это взаимодействие '
                               f'клиента по порядку {n+1}; сохраняй роли. ') if len(entries) > 1 else ''
                    # Whole-video observations are fallible context, not an answer key.
                    context += ('\nКонтекст предварительного просмотра всего ролика (может содержать ошибки):\n'
                                + json.dumps(full['original_events'], ensure_ascii=False)
                                + '\nПерепроверь по переданным кадрам. Проследи, у кого предмет до передачи '
                                'и у кого после: не путай приём с возвратом. Если направление скрыто, '
                                'опиши обмен без догадки о направлении. Не копируй события вне текущего интервала.\n')
                    focus.append(observe(start, end, f'focus_{n}', context))
                events = [e for e in events if e.get('action') == 'setup' or not any(w['start'] <= e['t'] <= w['end'] for w in focus)]
                events += [e for w in focus for e in w['events'] if e.get('action') != 'setup']
                events.sort(key=lambda e: e['t'])
            r.update(status='done', focus_windows=focus, observations=events,
                     timeline=[{'t': e['t'], 'event': e['event']} for e in events])
        except Exception as exc:
            r.update(status='failed', error=f'{type(exc).__name__}: {exc}')
        r['elapsed_sec'] = time.monotonic() - started
        save_json(base / 'records' / f'{video_id}.json', r)
        records.append(r)
        export(base, records, len(OPTIONS.ids))
        print(video_id, r['status'], r.get('error', ''), round(r['elapsed_sec'], 2), flush=True)
    export(base, records, len(OPTIONS.ids), finished=True)
    if any(r['status'] != 'done' for r in records):
        raise RuntimeError('Some video timelines failed; inspect records')


def main():
    global OPTIONS
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ids', nargs='+', default=['X-1', 'X-2', 'Х-3', 'Х-4'])
    parser.add_argument('--output-dir', type=Path, default=Path('artifacts/context_object_timelines_first4'))
    parser.add_argument('--reuse-full-only', action='store_true')
    parser.add_argument('--reuse-visual', type=Path, help='Reuse raw observations from an earlier run')
    OPTIONS = parser.parse_args()
    OPTIONS.output_dir = ROOT / OPTIONS.output_dir
    for name in ('outputs', 'records', 'raw', 'prompts'):
        (OPTIONS.output_dir / name).mkdir(parents=True, exist_ok=True)
    (OPTIONS.output_dir / 'prompt.txt').write_text(PROMPT)
    (OPTIONS.output_dir / 'text_prompt.txt').write_text(TEXT_PROMPT)
    save_json(OPTIONS.output_dir / 'policy.json', {'model': 'qwen38_27b', 'object_typing': 'video_and_text_model_prompts',
        'code_relabeling': False, 'structured_output': 'lm-format-enforcer==0.11.3', 'final_audit_run': False, 'ids': OPTIONS.ids})
    import timeline_inference
    import benchmark_vlm_v2
    timeline_inference.run = run
    sys.argv = [sys.argv[0], '--model', 'qwen38_27b', '--task', 'timeline-only', '--full-video',
                '--sampling-fps', '5', '--frame-edge', '848', '--video-max-pixels', '56000000',
                '--prompt-file', str((OPTIONS.output_dir / 'prompt.txt').relative_to(ROOT)),
                '--output-dir', str((OPTIONS.output_dir / 'run').relative_to(ROOT))]
    benchmark_vlm_v2.main()


if __name__ == '__main__':
    import fcntl
    with (ROOT / 'artifacts/benchmark_v2_gpu.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        main()
