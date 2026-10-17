"""Scenario specialists: immutable source quotes, strict output validation, no labels."""
import hashlib
import json
import math
from pathlib import Path
import re
import time

from routing_codes import parse_labels

# Router v2 IDs are NOT the section numbers in the supplied regulation.
ROUTES = {'1': [1], '2': [2, 6], '3': [2], '4': [3], '5': [4], '6': [5], '7': [7]}
SCOPES = {
    '1': 'Проверяй вход кассира в кабинет по разделу 1.',
    '2': 'Проверяй только самостоятельный подсчет (вариант Б раздела 2) и внесение без клиента (раздел 6). Клиентские этапы и клиентские нарушения неприменимы. Внесение не обязательно при одном лишь подсчете.',
    '3': 'Проверяй операцию с клиентом: вариант А раздела 2. При самостоятельном подсчете без клиента этот специалист неприменим.',
    '4': 'Проверяй извлечение денег ИЗ сейфа и переход к подсчету по разделу 3.',
    '5': 'Проверяй получение денег из мешка по разделу 4.',
    '6': 'Проверяй получение мешка от клиента по разделу 5.',
    '7': 'Проверяй выход кассира по разделу 7. Различай окончательный уход и кратковременный выход.',
}

INSTRUCTIONS = '''Ты проверяешь видео кассовой операции по приложенному регламенту.
Результат роутера — гипотеза о сценарии, а не доказательство нарушения.
Сначала убедись, что твой сценарий применим к наблюдаемой операции.
Проверяй только свой сценарий. Другие специалисты независимо проверяют свои сценарии.
Текст регламента ниже передан без изменений. Следуй идеальному сценарию,
типичным нарушениям и ВСЕМ условиям предотвращения ложных срабатываний.
Не превращай каждый невидимый шаг в нарушение. Не выдумывай обязательные действия.
Не делай выводов о намерениях, личности, содержимом документа, подлинности купюр,
внутреннем состоянии устройств и иных невидимых фактах.
Если начало/конец операции обрезаны, действие могло произойти за кадром,
или съемка не позволяет проверить условие, укажи insufficient_evidence.
Видео представлено выборкой кадров. Между кадрами могут быть пропущены действия:
само отсутствие действия на кадрах не доказывает его пропуск. Для нарушения
порядка или пропущенного шага нужны видимый переход между этапами, наблюдаемые
необходимые условия и исключение допустимых объяснений из регламента.
Для каждого подтвержденного нарушения выбери правило из каталога, скопируй
его quote ПОСИМВОЛЬНО и укажи абсолютные секунды исходного видео, где нарушение
становится видимым/подтвержденным. Это не время идеального шага и не номер кадра.
Цитата описывает правило из документа; evidence описывает отдельно то, что видно.
Объясни в false_positive_check, почему условия предотвращения ложных срабатываний
не отменяют именно это нарушение. Если исключение невозможно проверить, нарушение
не подтверждено. Не добавляй неподтвержденные нарушения в violations.
Проверяй все применимые шаги и ошибки; отсутствие перечисленных типичных нарушений
не разрешает выдумывать ошибки. Допустима точная ссылка на применимый идеальный шаг.
status: violations — есть подтвержденные нарушения; no_violation — применимую
операцию удалось проверить и нарушений не найдено; insufficient_evidence — сценарий
возможен, но данных недостаточно; not_applicable — видно, что это другой сценарий.
При частичной проверке можно вернуть violations с подтвержденными событиями,
а непроверяемые условия перечислить в limitations. no_violation не гарантирует
соблюдение непроверяемых условий. При существенной неопределенности используй
insufficient_evidence, а не no_violation.
Верни ТОЛЬКО один JSON-объект без markdown. Все описания — по-русски.
Формат:
{"status":"violations|no_violation|insufficient_evidence|not_applicable",
 "summary":"обоснование применимости и результата",
 "limitations":["что нельзя установить"],
 "violations":[{"rule_id":"идентификатор из каталога",
   "quote":"дословный текст правила из каталога",
   "start_sec":0.0,"end_sec":0.0,
   "evidence":"конкретное видимое событие",
   "false_positive_check":"почему исключены допустимые объяснения"}]}
При status, отличном от violations, массив violations должен быть пустым.
'''

TIMELINE_INSTRUCTIONS = '''ЗАДАЧА: {scope} Проверяй только этот сценарий.
Кадры подписаны Fномер=t секунд исходного видео.
ПОРЯДОК: 1) timeline: только видимые события по времени; 2) применимость;
3) нарушение = видно на кадрах И не отменено условиями ложных срабатываний;
4) пробелы между кадрами и обрезка ≠ пропуск шага; 5) одно событие = одно нарушение.
Если допустимое объяснение нельзя исключить, нарушение не подтверждено.
'''
TIMELINE_FORMAT = '''
Верни один JSON без markdown. Статусы: violations — есть подтвержденное нарушение;
no_violation — применимый сценарий проверен; insufficient_evidence — мало данных;
not_applicable — другой сценарий. При трех последних статусах violations=[].
applicability — краткое обоснование. why_not_fp — наблюдаемые основания исключить
допустимые объяснения. Выбирай rule_id только из каталога; цитату добавит программа.
JSON: {"timeline":[{"t":0.0,"event":"видимое событие"}],"applicability":"обоснование",
"violations":[{"rule_id":"ID_из_каталога","start_sec":0.0,"end_sec":0.0,
"evidence":"что видно","why_not_fp":"почему исключены допустимые объяснения"}],
"limitations":[],"status":"violations"}
'''
DETAILED_TIMELINE = '''
Сделай timeline подробнее по событиям: отдельно начало, изменение и завершение
действия, открытие/закрытие двери, подход/посадка, каждая различимая передача
и прием предмета, работа с оборудованием. Ориентир 10–16 точек для короткого
ролика, только если столько событий действительно видно. Не добавляй повторов
и не выдумывай события ради количества. Важный переход отмечай по ближайшему
подписанному кадру; описания короткие. Не нужен отчет на каждую секунду.
Уточняй направление передачи. Называй предмет деньгами или документом только
при различимых признаках; иначе пиши «неразличимый предмет». Отсутствие видимого
действия само по себе не доказывает отсутствие проверки.
'''


def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def source_sections(text):
    headings=list(re.finditer(r'^# (\d+)\. (.+)$',text,re.M))
    sections={int(m[1]): text[m.start():headings[i+1].start() if i+1<len(headings) else len(text)]
              for i,m in enumerate(headings)}
    if set(sections)!=set(range(1,8)):
        raise ValueError('Expected exactly seven numbered regulation sections')
    return sections


def rule_catalog(text,section_ids):
    """Quotes are exact source substrings; line numbers refer to the original file."""
    section=None
    mode=None
    rules={}
    for line_number,line in enumerate(text.splitlines(),1):
        heading=re.match(r'^# (\d+)\.',line)
        if heading:section=int(heading[1]);mode=None
        if line.startswith('### '):mode=line[4:]
        if section not in section_ids or mode not in ('Идеальный сценарий','Типичные нарушения'):
            continue
        match=re.match(r'^(?:\d+\. |\\?- )(.*\S)\s*$',line)
        if not match:continue
        quote=match[1]
        if mode=='Типичные нарушения' and not quote.startswith('Нарушение:'):continue
        rules[f's{section}:L{line_number}']={'quote':quote,'line':line_number,'section':section}
    return rules


def scoped_rules(source,rules,label):
    """Client rules must not be available to the standalone-counting specialist."""
    if label not in ('2','3'):return rules
    variant_b=next(i for i,line in enumerate(source.splitlines(),1) if line.startswith('## Вариант Б.'))
    scoped={}
    for key,rule in rules.items():
        if rule['section']==2:
            quote=rule['quote']
            if quote.startswith('Нарушение:'):
                if label=='2' and re.search(r'клиент',quote,re.I):continue
            elif (label=='2' and rule['line']<variant_b) or (label=='3' and rule['line']>variant_b):
                continue
        scoped[key]=rule
    return scoped


def load_protocol(root,source_file,max_frames,frame_time_labels=False,prompt_style='legacy'):
    if max_frames<2:raise ValueError('audit-max-frames must be at least 2')
    source=(root/source_file).read_text()
    sections=source_sections(source)
    specialists={}
    for label,ids in ROUTES.items():
        rules=rule_catalog(source,ids)
        if prompt_style in ('timeline','timeline-detailed'):
            rules=scoped_rules(source,rules,label)
            catalog='\n'.join(key+' — '+rule['quote'] for key,rule in rules.items())
            prompt=(TIMELINE_INSTRUCTIONS.format(scope=SCOPES[label])
                    +(DETAILED_TIMELINE if prompt_style=='timeline-detailed' else '')
                    +'\nИСХОДНЫЙ РЕГЛАМЕНТ\n'+''.join(sections[i] for i in ids)
                    +'\nКАТАЛОГ (только правила в scope)\n'+catalog+TIMELINE_FORMAT)
        else:
            prompt=(INSTRUCTIONS+'\nТВОЯ ОБЛАСТЬ ПРОВЕРКИ\n'+SCOPES[label]
                +'\n\nИСХОДНЫЙ РЕГЛАМЕНТ\n'+''.join(sections[i] for i in ids)
                +'\nКАТАЛОГ ДОПУСТИМЫХ ССЫЛОК\n'+json.dumps(rules,ensure_ascii=False))
        specialists[label]={'sections':ids,'rules':rules,'prompt':prompt,'prompt_sha256':sha(prompt)}
        if prompt_style in ('timeline','timeline-detailed'):specialists[label]['output_schema']='timeline'
    reference=json.loads((root/'artifacts/routing_prompt_v2/qwen38_27b/config.json').read_text())
    protocol={'version':1,'source_file':str(source_file),'source_sha256':sha(source),
            'router_prompt_sha256':reference['prompt_sha256'],
            'audit_max_frames':max_frames,'audit_max_new_tokens':4096,'specialists':specialists}
    if frame_time_labels:protocol['frame_time_labels']=True
    if prompt_style in ('timeline','timeline-detailed'):protocol.update(version=2,prompt_style=prompt_style)
    return protocol


def validate_result(raw,specialist,duration):
    value=json.loads(raw)
    if not isinstance(value,dict):raise ValueError('Expected one JSON object')
    if specialist.get('output_schema')=='timeline':
        timeline=value.get('timeline')
        if not isinstance(timeline,list):raise ValueError('Missing timeline array')
        previous=-1
        for point in timeline:
            if not isinstance(point,dict):raise ValueError('Invalid timeline event')
            t=point.get('t')
            if type(t) not in (int,float) or not math.isfinite(t) or not previous<=t<=duration or t<0:
                raise ValueError('Invalid or unordered timeline time')
            if not isinstance(point.get('event'),str) or not point['event'].strip():raise ValueError('Missing timeline event text')
            previous=t
        if not isinstance(value.get('applicability'),str) or not value['applicability'].strip():
            raise ValueError('Missing applicability')
        value['summary']=value['applicability']
        if not isinstance(value.get('violations'),list):raise ValueError('Missing violations array')
        seen=set()
        for event in value['violations']:
            if not isinstance(event,dict):raise ValueError('Invalid violation')
            rule=specialist['rules'].get(event.get('rule_id'))
            if rule is None:raise ValueError('Rule outside specialist scope')
            if 'quote' in event and event['quote']!=rule['quote']:raise ValueError('Fabricated quote')
            event['quote']=rule['quote']
            event['false_positive_check']=event.get('why_not_fp')
            signature=json.dumps([event.get(k) for k in ('rule_id','start_sec','end_sec')],sort_keys=True)
            if signature in seen:raise ValueError('Duplicate event')
            seen.add(signature)
    status=value.get('status')
    if status not in ('violations','no_violation','insufficient_evidence','not_applicable'):
        raise ValueError('Unknown audit status')
    if not isinstance(value.get('summary'),str) or not value['summary'].strip():
        raise ValueError('Missing summary')
    if not isinstance(value.get('limitations'),list) or any(not isinstance(x,str) for x in value['limitations']):
        raise ValueError('Expected limitations array of strings')
    events=value.get('violations')
    if not isinstance(events,list) or bool(events)!=(status=='violations'):
        raise ValueError('Audit status and violations disagree')
    for event in events:
        if not isinstance(event,dict):raise ValueError('Expected event object')
        rule=specialist['rules'].get(event.get('rule_id'))
        if rule is None or event.get('quote')!=rule['quote']:
            raise ValueError('Quote must exactly match a rule in this specialist source')
        for key in ('start_sec','end_sec'):
            stamp=event.get(key)
            if type(stamp) not in (int,float) or not math.isfinite(stamp) or not 0<=stamp<=duration:
                raise ValueError('Invalid absolute timestamp')
        if event['end_sec']<event['start_sec']:raise ValueError('Reversed event interval')
        for key in ('evidence','false_positive_check'):
            if not isinstance(event.get(key),str) or not event[key].strip():
                raise ValueError(f'Missing {key}')
        event['source_line']=rule['line']
        event['source_section']=rule['section']
    return value


def select_samples(samples,maximum):
    if len(samples)>maximum:
        samples=[samples[round(i*(len(samples)-1)/(maximum-1))] for i in range(maximum)]
    if len(samples)%2:samples=samples+[samples[-1]]
    return samples


def load_routes(root,manifest_file,results_dir,limit=None,routing_manifest_file=None):
    """Check provenance before a different specialist model consumes frozen routes."""
    folder=root/results_dir
    actual=json.loads((folder/'config.json').read_text())
    reference=json.loads((root/'artifacts/routing_prompt_v2/qwen38_27b/config.json').read_text())
    for key in ('key','repo','revision','quantization','prompt_sha256','sampling_fps',
                'frame_longest_edge','linear_attention','max_labels','max_frames'):
        if actual.get(key)!=reference[key]:raise ValueError(f'Cached router setting changed: {key}')
    if actual.get('task')!='routing':raise ValueError('Expected a routing-only run')
    if sha(actual['prompt'])!=reference['prompt_sha256']:raise ValueError('Cached routing prompt hash mismatch')
    data=(root/(routing_manifest_file or manifest_file)).read_bytes()
    if actual.get('input_manifest_sha256')!=hashlib.sha256(data).hexdigest():
        raise ValueError('Cached routes use a different video manifest')
    originals={x['sha256']:x for x in json.loads(data)}
    items=json.loads((root/manifest_file).read_bytes())
    if limit:items=items[:limit]
    for item in items:
        original=originals.get(item['sha256'])
        if original is None or any(original.get(k)!=item.get(k) for k in ('id','path','duration_sec')):
            raise ValueError('Audit and routing manifests contain different source videos')
    routes={}
    for item in items:
        record=json.loads((folder/(item['sha256']+'.json')).read_text())
        if (record.get('status')!='done' or record.get('model')!='qwen38_27b'
                or record.get('sha256')!=item['sha256'] or record.get('id')!=item['id']
                or record.get('synthetic_control_passed') is not True):
            raise ValueError('Invalid cached routing record: '+item['id'])
        parse_labels(record['raw_output'],ROUTES,2)
        routes[item['sha256']]=record
    return routes


def audit_video(item,protocol,router_prompt,call,cached_route=None):
    """call receives samples, prompt and output budget. Every route gets its own call."""
    samples=select_samples(item['samples'],48)
    if cached_route is None:
        raw,stats=call(samples,router_prompt,2)
    else:
        raw=cached_route['raw_output']
        stats={'reused_verified_route':True,'router_model':'qwen38_27b',
               'router_elapsed_sec':cached_route['elapsed_sec']}
    routing={'raw_output':raw,'stats':stats,'sample_timestamps_sec':[s['timestamp_sec'] for s in samples]}
    result={'routing':routing,'specialists':[]}
    try:labels=parse_labels(raw,ROUTES,2)
    except ValueError as exc:
        result.update(status='invalid_routing',error=str(exc),has_violation=None)
        return result
    routing['labels']=labels
    samples=select_samples(item['samples'],protocol['audit_max_frames'])
    timing=('\nДлительность исходного видео, секунд: '+str(item['duration_sec'])
            +'\nАбсолютные секунды показанных кадров: '+', '.join(str(s['timestamp_sec']) for s in samples))
    if protocol.get('frame_time_labels'):
        timing=frame_timing(samples,item['duration_sec'])
        result['frame_time_map']=[{'frame':i,'sec':s['timestamp_sec']} for i,s in enumerate(samples)]
        result['timing_prompt']=timing
    for label in labels:
        specialist=protocol['specialists'][label]
        record={'router_label':label,'source_sections':specialist['sections'],
                'sample_timestamps_sec':[s['timestamp_sec'] for s in samples]}
        try:
            raw,stats=call(samples,specialist['prompt']+timing,protocol['audit_max_new_tokens'])
            record.update(raw_output=raw,stats=stats)
            record.update(result=validate_result(raw,specialist,item['duration_sec']),status='done')
        except Exception as exc:
            record.update(status='failed',error_class=type(exc).__name__,error=str(exc))
        result['specialists'].append(record)
    complete=all(s['status']=='done' for s in result['specialists'])
    confirmed=any(s.get('result',{}).get('violations') for s in result['specialists'])
    inconclusive=any(s.get('result',{}).get('status') in ('insufficient_evidence','not_applicable') for s in result['specialists'])
    # Unknown is not silently turned into a negative classification.
    result.update(status='done' if complete else 'partial',
                  has_violation=True if confirmed else None if not complete or inconclusive else False)
    return result


def frame_timing(samples,duration):
    mapping=','.join(f"F{i}={s['timestamp_sec']:.3f}".rstrip('0').rstrip('.') for i,s in enumerate(samples))
    return (f'\nВидео {duration:.3f} с. F0 — первый переданный кадр; далее кадры по порядку. '
            'Ниже Fn=абсолютная секунда исходного видео. Привязывай события к этим кадрам; '
            'в start_sec/end_sec возвращай секунды, не номера F.\n'+mapping)


def run(args,folder,config,infer,passed,root):
    import numpy as np
    from PIL import Image
    import torch
    from transformers.video_utils import VideoMetadata

    items=json.loads((root/args.video_manifest).read_text())
    if any('label' in x or 'operation_label' in x for x in items):
        raise ValueError('Audit manifest must not contain ground-truth labels')
    fingerprint=sha(json.dumps({'config':config,'manifest':items},ensure_ascii=False,sort_keys=True))
    if args.limit:items=items[:args.limit]
    records=[]
    for item in items:
        path=folder/(item['sha256']+'.json')
        if path.exists():
            previous=json.loads(path.read_text())
            if previous.get('fingerprint')!=fingerprint:raise RuntimeError('Inputs changed; use a new output folder')
            if previous.get('status')=='done':records.append(previous);continue
        started=time.monotonic()
        torch.cuda.reset_peak_memory_stats()
        def call(samples,prompt,budget):
            frames=np.stack([np.asarray(Image.open(root/s['path']).convert('RGB')) for s in samples])
            metadata=VideoMetadata(total_num_frames=round(item['duration_sec']*item['source_fps']),
                fps=item['source_fps'],frames_indices=[s['source_index'] for s in samples],duration=item['duration_sec'])
            return infer(frames,metadata,prompt,max_new_tokens=budget)
        try:
            output=audit_video(item,config['audit_protocol'],config['prompt'],call,
                               config.get('cached_routes',{}).get(item['sha256']))
        except Exception as exc:
            output={'status':'failed','has_violation':None,'error_class':type(exc).__name__,'error':str(exc)}
            torch.cuda.empty_cache()
        output.update(id=item['id'],sha256=item['sha256'],model=args.model,fingerprint=fingerprint,
                      synthetic_control_passed=passed,elapsed_sec=time.monotonic()-started,
                      peak_allocated_bytes=torch.cuda.max_memory_allocated())
        path.write_text(json.dumps(output,ensure_ascii=False,indent=2))
        records.append(output)
        print('AUDIT',item['id'],output['status'],'has_violation',output['has_violation'],flush=True)
    state='done' if all(r['status']=='done' for r in records) else 'partial'
    if args.limit and state=='done':state='partial'
    (folder/'run_status.json').write_text(json.dumps({'status':state,'videos':len(records),
        'completed':sum(r['status']=='done' for r in records),'model':args.model},indent=2))
    write_report(folder,records,config['audit_protocol']['source_file'])


def write_report(folder,records,source_file):
    lines=['# Проверка сценариев','',f'Регламент: {source_file}. Таймкоды — секунды исходного видео.',
           'Проверка формата и цитат автоматическая; правильность визуальных выводов требует оценки.',
           'Положительный ответ означает заявление модели о нарушении, а не экспертное подтверждение.','']
    for record in records:
        verdict={True:'заявлено нарушение',False:'нарушений не заявлено',None:'неопределенный'}[record['has_violation']]
        lines.extend([f"## {record['id']}",'',f"Обработка: {record['status']}. Результат модели: {verdict}.",''])
        for specialist in record.get('specialists',[]):
            lines.append(f"Класс роутера {specialist['router_label']}, разделы {specialist['source_sections']}.")
            if specialist['status']!='done':
                lines.extend([f"Ошибка проверки: {specialist['error']}",'']);continue
            result=specialist['result']
            lines.extend([f"{result['status']}: {result['summary']}",''])
            for point in result.get('timeline',[]):lines.append(f"- {point['t']:g} с: {point['event']}")
            if result.get('timeline'):lines.append('')
            for event in result['violations']:
                lines.extend([f"- {event['start_sec']:.2f}–{event['end_sec']:.2f} с: «{event['quote']}» (строка {event['source_line']}).",
                              f"  Наблюдение: {event['evidence']}",f"  Проверка исключений: {event['false_positive_check']}"])
            lines.extend(['Ограничение: '+x for x in result['limitations']])
            lines.append('')
    (folder/'report.md').write_text('\n'.join(lines)+'\n')
