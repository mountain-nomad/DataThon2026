"""Resumable full-frame timelines with absolute source timestamps and bounded windows."""
import argparse
import gc
import hashlib
import json
import math
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'artifacts/all_videos_full_frame_usage_rule'
VIDEO_BUDGET_SEC = 210
MAX_NEW_TOKENS = 1536
TARGET_IDS = None
FORCE_REGENERATE = False


def fits_one_request(item):
    return math.ceil(item['duration_sec'] * 5 - 1e-6) <= 130


def queue_order(items):
    return sorted(items, key=lambda item: (not fits_one_request(item), int(re.search(r'\d+', item['id']).group())))


def save_json(path, value):
    path = Path(path)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2))
    temp.replace(path)


def plan_segments(duration):
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError('Invalid video duration')
    if duration <= 30:
        return [(0.0, duration)]
    count = min(4, math.ceil((duration - 2) / 23))
    length = (duration + 2 * (count - 1)) / count
    return [(i * (length - 2), min(duration, i * (length - 2) + length)) for i in range(count)]


def select_samples(samples, start, end, cap=130):
    selected = [s for s in samples if start - 1e-6 <= s['timestamp_sec'] <= end + 1e-6]
    if not selected:
        raise ValueError('Empty video window')
    if len(selected) > cap:
        indices = [round(i * (len(selected) - 1) / (cap - 1)) for i in range(cap)]
        selected = [selected[i] for i in indices]
    if len(selected) % 2:
        selected.append(selected[-1])
    return selected


def parse_absolute(raw, start, end):
    text = raw.strip()
    if text.startswith('```'):
        text = text.split('\n', 1)[1].rsplit('```', 1)[0].strip()
    values = json.loads(text)
    if not isinstance(values, list) or not values:
        raise ValueError('Expected a nonempty event array')
    previous = start - 0.051
    for event in values:
        if not isinstance(event, dict):
            raise ValueError('Invalid event object')
        stamp = event.get('t')
        # Normalize a decimal JSON string without changing its value or origin.
        if isinstance(stamp, str) and re.fullmatch(r'\d+(?:\.\d+)?', stamp):
            stamp = float(stamp)
            event['t'] = stamp
        if type(stamp) not in (int, float) or not math.isfinite(stamp):
            raise ValueError('Timestamp must be finite source seconds')
        if stamp < 0:
            raise ValueError('Negative source timestamp')
        if not start - 0.051 <= stamp <= end + 0.051:
            raise ValueError(f'Absolute timestamp {stamp} outside source window [{start}, {end}]')
        if stamp < previous:
            raise ValueError('Unordered timestamps')
        if not isinstance(event.get('event'), str) or not event['event'].strip():
            raise ValueError('Missing event description')
        previous = stamp
    return values


def merge_windows(windows):
    result = []
    for i, window in enumerate(windows):
        # A seam belongs to the following window. No semantic edits to events.
        lower = (windows[i - 1]['end_sec'] + window['start_sec']) / 2 if i else -math.inf
        upper = (window['end_sec'] + windows[i + 1]['start_sec']) / 2 if i + 1 < len(windows) else math.inf
        result.extend(e for e in window.get('timeline', []) if lower <= e['t'] < upper)
    if any(a['t'] > b['t'] for a, b in zip(result, result[1:])):
        raise ValueError('Merged timeline is not ordered')
    return result


def validate_counter_objects(timeline):
    """Reject the observed card-in-counter failure rather than edit model events."""
    for event in timeline:
        text = event['event']
        if (re.search(r'удостоверен|карточк|документ', text, re.I)
                and not re.search(r'купюр|деньг', text, re.I)
                and re.search(r'\b(?:в|из)\s+(?:\w+\s+){0,3}(?:лот\w*|сч[её]тчик\w*|детектор\w*)', text, re.I)):
            raise ValueError('Object consistency: a card/document in the counter tray must be identified as cash throughout its tracked chain')


def prepare_inventory():
    import av
    BASE.mkdir(exist_ok=True)
    source = ROOT / 'artifacts/scenario_qwen38_first2_2fps/full_frame_usage_rule/prompt.txt'
    prompt = source.read_text()
    target = BASE / 'prompt.txt'
    if target.exists() and target.read_text() != prompt:
        raise RuntimeError('Batch prompt differs; use a new run directory')
    target.write_text(prompt)
    files = sorted((ROOT / 'open/videos').glob('*.mov'), key=lambda p: int(re.search(r'\d+', p.stem).group()))
    items = []
    for path in files:
        with av.open(str(path)) as container:
            stream = container.streams.video[0]
            duration = float(stream.duration * stream.time_base)
            items.append({'id': path.stem, 'path': str(path.relative_to(ROOT)),
                          'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                          'duration_sec': duration, 'source_fps': float(stream.base_rate),
                          'total_num_frames': stream.frames, 'width': stream.width, 'height': stream.height})
    items = queue_order(items)
    save_json(BASE / 'manifest.json', items)
    save_json(BASE / 'policy.json', {'full_frame': True, 'crop': None, 'reasoning': False,
                                   'preferred_fps': 5, 'max_frames_per_request': 130,
                                   'preferred_window_sec': 25, 'overlap_sec': 2,
                                   'max_windows': 4, 'target_video_budget_sec': 210,
                                   'long_video_policy': 'Balanced overlapping windows; uniformly thin frames when a window exceeds 130; preserve spatial detail',
                                   'timestamps': 'Absolute native source timestamps; never add an offset to model output',
                                   'merge': 'Disjoint midpoint ownership of overlap; all raw windows retained',
                                   'prompt_source': str(source.relative_to(ROOT)),
                                   'order': 'All videos fitting 130 frames at 5 FPS first, then long videos; numerical order within each phase',
                                   'count': len(items)})
    print(f'Prepared {len(items)} videos; fitting first: {sum(map(fits_one_request, items))}; first: {items[0]["id"]}', flush=True)
    return items


def prepare_frames(item):
    import av
    folder = BASE / 'frames' / item['sha256']
    manifest = folder / 'samples.json'
    if manifest.exists():
        return json.loads(manifest.read_text())
    folder.mkdir(parents=True, exist_ok=True)
    samples = []
    next_stamp = 0.0
    origin = None
    with av.open(str(ROOT / item['path'])) as container:
        for index, frame in enumerate(container.decode(video=0)):
            stamp = float(frame.pts * frame.time_base)
            if origin is None:
                origin = stamp
            stamp -= origin
            if stamp + 1e-5 < next_stamp:
                continue
            path = folder / f'{len(samples):05d}.png'
            frame.to_image().convert('RGB').save(path)
            samples.append({'path': str(path.relative_to(ROOT)), 'source_index': index,
                            'timestamp_sec': round(stamp, 3)})
            next_stamp += 0.2
    save_json(manifest, samples)
    return samples


def window_prompt(base, item, start, end, samples, retry=False):
    first = samples[0]['timestamp_sec']
    prompt = base.replace('При t=0', f'При t={first:g}').replace('"t":0.0', f'"t":{first:g}')
    if first > 1.2:
        prompt = prompt.replace('"t":1.2', f'"t":{samples[min(6, len(samples) - 1)]["timestamp_sec"]:g}')
    scope = (f'Сейчас передан только отрезок исходного видео {item["id"]}: '
             f'от {start:.3f} до {end:.3f} с. Полная длительность: {item["duration_sec"]:.3f} с. '
             f'Опиши только видимые события этого отрезка. t — АБСОЛЮТНЫЕ секунды исходного видео. '
             f'Не начинай время заново с нуля и не дели его на FPS. Первый доступный кадр: t={first:.3f}. '
             'Метки самого видео также относятся к исходному ролику. Не выдумывай события вне переданного отрезка.\n')
    if retry:
        scope = ('ПОВТОРНАЯ ПРОВЕРКА: предыдущий ответ не прошел проверку JSON, времени '
                 'или согласованности предметов. Если ты назвал предмет в лотке карточкой '
                 'или документом, пересмотри ВСЮ его цепочку: это КУПЮРЫ. '
                 'С самого первого появления этой цепочки называй предмет деньгами.\n') + scope
    formatting = ('\nФормат: компактный JSON-массив одной строкой, без отступов и Markdown. '
                  't — число, не строка. Сохрани важные действия, кратко формулируй события и обязательно закрой весь массив.\n')
    return scope + prompt + '\nДопустимые исходные секунды кадров: ' + ', '.join(f'{s["timestamp_sec"]:.3f}' for s in samples) + '\n' + scope + formatting


def write_reports(items, records, active=None, overall='running'):
    by_id = {r['id']: r for r in records}
    ordered = sorted(items, key=lambda x: int(re.search(r'\d+', x['id']).group()))
    index = ['# Таймлайны всех роликов — полный кадр, Qwen3.8', '',
             'Полный промпт со всеми категориями; без reasoning. Длинные видео обработаны перекрывающимися отрезками. '
             'Время абсолютное, от начала исходного ролика. События модели не исправлялись. '
             'Статус done означает валидный ответ, не подтвержденную точность распознавания.', '',
             '| Ролик | Длительность | Статус | Время обработки | Описание |',
             '|---|---:|---|---:|---|']
    combined = ['# Исходные описания всех роликов', '']
    for item in ordered:
        r = by_id.get(item['id'])
        if not r:
            index.append(f'| {item["id"]} | {item["duration_sec"]:.1f} с | ожидает | — | — |')
            continue
        elapsed = r.get('elapsed_sec', 0)
        output = f'outputs/{item["id"]}.md'
        body = f'## {item["id"]}\n\nСтатус: {r["status"]}. Обработка: {elapsed:.2f} с. '
        body += f'Отрезков: {len(r.get("windows", []))}. Полный кадр, без reasoning.\n\n'
        body += '```json\n' + json.dumps(r.get('timeline', []), ensure_ascii=False, indent=2) + '\n```\n'
        combined.append(body + f'\n[Исходные ответы отрезков]({output})\n')
        body += '\n### Исходные ответы отрезков\n'
        for w in r.get('windows', []):
            body += f'\nОтрезок {w["start_sec"]:.3f}–{w["end_sec"]:.3f} с; статус {w["status"]}; '
            body += f'выбрано кадров: {w.get("selected_frames", 0)}, FPS: {w.get("effective_fps", 0):.2f}.\n'
            if w.get('error'):
                body += '\nОшибка: ' + w['error'] + '\n'
            body += '\n```text\n' + w.get('raw_output', 'Ответа нет.') + '\n```\n'
        (BASE / output).write_text(body)
        index.append(f'| {item["id"]} | {item["duration_sec"]:.1f} с | {r["status"]} | {elapsed:.1f} с | [открыть]({output}) |')
    (BASE / 'index.md').write_text('\n'.join(index) + '\n')
    (BASE / 'current_outputs.md').write_text('\n'.join(combined))
    save_json(BASE / 'progress.json', {'status': overall, 'active': active, 'total': len(items),
                                      'done': sum(r['status'] == 'done' for r in records),
                                      'partial': sum(r['status'] != 'done' for r in records),
                                      'processed': len(records), 'records': [
                                          {k: r.get(k) for k in ('id', 'status', 'elapsed_sec')} for r in records]})


def run_batch(args, folder, config, infer, passed, root):
    import numpy as np
    import torch
    from PIL import Image
    from transformers.video_utils import VideoMetadata
    items = json.loads((BASE / 'manifest.json').read_text())
    (BASE / 'outputs').mkdir(exist_ok=True)
    (BASE / 'records').mkdir(exist_ok=True)
    records = []
    for item in items:
        path = BASE / 'records' / (item['id'] + '.json')
        if path.exists():
            records.append(json.loads(path.read_text()))
    write_reports(items, records)
    model = next(c.cell_contents for c in infer.__closure__ if hasattr(c.cell_contents, 'generate') and hasattr(c.cell_contents, 'named_modules'))
    original_generate = model.generate
    deadline = [math.inf]
    def timed_generate(*a, **kw):
        kw['max_time'] = max(1, deadline[0] - time.monotonic())
        return original_generate(*a, **kw)
    model.generate = timed_generate
    try:
        for item in items:
            if TARGET_IDS is not None and item['id'] not in TARGET_IDS:
                continue
            path = BASE / 'records' / (item['id'] + '.json')
            if path.exists():
                previous = json.loads(path.read_text())
                if previous['status'] == 'done' and not FORCE_REGENERATE:
                    continue
            started = time.monotonic()
            write_reports(items, records, item['id'])
            print('VIDEO_START', item['id'], flush=True)
            windows = []
            try:
                samples = prepare_frames(item)
                plans = plan_segments(item['duration_sec'])
                for i, (start, end) in enumerate(plans):
                    selected = select_samples(samples, start, end)
                    w = {'start_sec': start, 'end_sec': end, 'selected_frames': len(selected),
                         'effective_fps': (len(selected) - 1) / max(0.001, selected[-1]['timestamp_sec'] - selected[0]['timestamp_sec']),
                         'samples': selected, 'status': 'pending', 'timeline': []}
                    remaining = VIDEO_BUDGET_SEC - (time.monotonic() - started)
                    if remaining < 5:
                        w.update(status='failed', error='Video time budget exhausted')
                        windows.append(w)
                        continue
                    gc.collect()
                    torch.cuda.empty_cache()
                    frames = np.stack([np.asarray(Image.open(root / s['path']).convert('RGB')) for s in selected])
                    metadata = VideoMetadata(total_num_frames=item['total_num_frames'], fps=item['source_fps'],
                                             frames_indices=[s['source_index'] for s in selected], duration=item['duration_sec'])
                    for attempt in range(2):
                        attempt_started = time.monotonic()
                        remaining = VIDEO_BUDGET_SEC - (attempt_started - started)
                        deadline[0] = min(started + VIDEO_BUDGET_SEC - 2, attempt_started + remaining / max(1, len(plans) - i) + 8)
                        prompt = window_prompt(config['prompt'], item, start, end, selected, retry=bool(attempt))
                        w['prompt'] = prompt
                        try:
                            raw, stats = infer(frames, metadata, prompt, max_new_tokens=MAX_NEW_TOKENS)
                            w.update(raw_output=raw, stats=stats, inference_sec=time.monotonic() - attempt_started)
                            w['timeline'] = parse_absolute(raw, start, end)
                            validate_counter_objects(w['timeline'])
                            w.update(status='done', attempts=attempt + 1)
                            w.pop('error', None)
                            break
                        except Exception as exc:
                            w.update(status='failed', error=f'{type(exc).__name__}: {exc}')
                            remaining = VIDEO_BUDGET_SEC - (time.monotonic() - started)
                            if remaining < (len(plans) - i - 1) * 42 + 35:
                                break
                    del frames
                    windows.append(w)
                    save_json(BASE / 'records' / (item['id'] + '_checkpoint.json'), {'id': item['id'], 'windows': windows})
                    print('WINDOW', item['id'], i + 1, '/', len(plans), start, end, w['status'], flush=True)
            except Exception as exc:
                windows.append({'start_sec': 0, 'end_sec': item['duration_sec'], 'status': 'failed',
                                'timeline': [], 'error': f'{type(exc).__name__}: {exc}'})
            result = {'id': item['id'], 'sha256': item['sha256'], 'duration_sec': item['duration_sec'],
                      'status': 'done' if windows and all(w['status'] == 'done' for w in windows) else 'partial',
                      'timeline': merge_windows(windows), 'windows': windows,
                      'elapsed_sec': time.monotonic() - started, 'synthetic_control_passed': passed}
            result['prompt_sha256'] = hashlib.sha256(config['prompt'].encode()).hexdigest()
            result['model_run_dir'] = str(folder.relative_to(root))
            save_json(path, result)
            records = [r for r in records if r['id'] != item['id']] + [result]
            write_reports(items, records)
            print('VIDEO_DONE', item['id'], result['status'], round(result['elapsed_sec'], 2), flush=True)
    finally:
        model.generate = original_generate
    status = 'done' if all(r['status'] == 'done' for r in records) else 'partial'
    write_reports(items, records, overall=status)
    save_json(folder / 'run_status.json', {'status': status, 'videos': len(records)})


def main():
    global VIDEO_BUDGET_SEC, MAX_NEW_TOKENS, TARGET_IDS, FORCE_REGENERATE
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--video-budget-sec', type=float, default=210)
    parser.add_argument('--max-new-tokens', type=int, default=1536)
    parser.add_argument('--ids', nargs='+', help='Only process these video IDs')
    parser.add_argument('--force', action='store_true', help='Regenerate selected IDs; requires --ids')
    args = parser.parse_args()
    if args.video_budget_sec < 10 or args.max_new_tokens < 128:
        parser.error('Budget must be at least 10 seconds and output at least 128 tokens')
    VIDEO_BUDGET_SEC = args.video_budget_sec
    MAX_NEW_TOKENS = args.max_new_tokens
    if args.force and not args.ids:
        parser.error('--force requires explicit --ids')
    items = prepare_inventory()
    TARGET_IDS = set(args.ids) if args.ids else None
    FORCE_REGENERATE = args.force
    if TARGET_IDS and TARGET_IDS - {item['id'] for item in items}:
        parser.error('Unknown video ID in --ids')
    if args.prepare_only:
        return
    run_dir = BASE / 'run'
    if args.force:
        import shutil
        run_id = str(time.time_ns())
        backup = BASE / 'backups' / run_id
        backup.mkdir(parents=True)
        for video_id in args.ids:
            for subdir, suffix in [('records', '.json'), ('outputs', '.md')]:
                path = BASE / subdir / (video_id + suffix)
                if path.exists():
                    (backup / subdir).mkdir(exist_ok=True)
                    shutil.copy2(path, backup / subdir / path.name)
        run_dir = BASE / 'runs' / run_id
    import timeline_inference
    import benchmark_vlm_v2
    timeline_inference.run = run_batch
    sys.argv = [sys.argv[0], '--model', 'qwen38_27b', '--task', 'timeline-only', '--full-video',
                '--sampling-fps', '5', '--frame-edge', '848', '--video-max-pixels', '56000000',
                '--video-manifest', str(BASE.relative_to(ROOT) / 'manifest.json'),
                '--prompt-file', str(BASE.relative_to(ROOT) / 'prompt.txt'),
                '--output-dir', str(run_dir.relative_to(ROOT))]
    benchmark_vlm_v2.main()


if __name__ == '__main__':
    main()
