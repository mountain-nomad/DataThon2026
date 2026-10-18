"""Video-only observations: model selects local frame IDs; code supplies source seconds."""
import hashlib
import json
import time

PROMPT='''Просмотри весь ролик кассового кабинета от начала до конца. Составь краткую
хронологию видимых событий на русском языке. Нарушения и намерения не оценивай.

ВРЕМЯ: t — реальные секунды от начала исходного видео. Это не номер кадра,
не номер события и не номер пары кадров. Используй временные метки видео и
список допустимых секунд ниже. Не дели и не умножай секунды на FPS.
При 5 FPS соседние кадры идут примерно через 0.2 с. Событие на 20-й секунде
имеет t=20.0. Просмотри также вторую половину и конец ролика.
Не растягивай события искусственно до длительности видео.

Роли: кассир работает с оборудованием за столом, клиент приходит на обслуживание.
Определи роли по всему эпизоду и сохраняй их при перемещениях. Если клиентов
несколько, нумеруй по первому появлению. Отражения не являются новыми людьми.
Отслеживай деньги и документы; счетчик и детектор банкнот, ноутбук; сейф, ключи,
дверь; печати, тетради, черный блокнот; зеленую тканевую инкассаторскую сумку;
личную сумку, куртку; еду, упаковку и напитки. Счетчик — высокая машинка с лотком,
детектор — низкая с прорезью, сейф — металлический шкаф. Отличай личную сумку
от инкассаторской.

ДЕНЬГИ И УДОСТОВЕРЕНИЕ могут выглядеть одинаково: светлые прямоугольники.
Различай их прежде всего по использованию и непрерывному движению в соседних
кадрах, затем по виду. Купюры перебирают, разделяют, складывают пачкой,
загружают в счетчик или проводят через детектор. Удостоверение обычно
рассматривают как отдельную жесткую карточку и возвращают владельцу.
Если видна загрузка купюр в счетчик, проследи их назад до получения и вперед
после обработки. Не называй эту цепочку удостоверением из-за первой догадки.
При новой передаче проверь, тот ли это предмет: документ и деньги могут
передаваться последовательно. При сомнении пиши «вероятно, купюры» или
«тип предмета неразличим». Не придумывай действия для объяснения своей догадки.

ПЕРЕДАЧИ: укажи отправителя, получателя и предмет. Различай «протягивает»,
«получатель принимает», «кладет перед получателем» и «держит в руках».
Не пиши «достает из счетчика», если видно лишь удержание денег без извлечения.
Разделяй короткие действия при смене владельца или места предмета.

ОСОБО ПРОВЕРЬ ЧАСТИ ДЕНЕГ: передается вся видимая пачка или только часть?
Проследи обе руки кассира и клиента, остаток на столе и отделенные купюры.
Если видно разделение, отдельно опиши переданную часть и оставшуюся часть:
у кого она осталась и куда переместилась. Отмечай удержание другой рукой,
откладывание, помещение в карман/сумку только при видимом подтверждении.
Не считай передачу пачки автоматически передачей всех денег. Если остаток
скрыт, укажи, что дальнейшее положение не видно. Не утверждай удержание части,
если его не видно. Не выдумывай количество, номиналы, суммы и присвоение денег.

При t=0 кратко опиши исходную обстановку: участников, только видимые объекты,
состояние двери, сейфа и крышки ноутбука. Далее — действия и изменения:
вход/выход, посадка, передачи, перемещения предметов, работа с оборудованием,
записи, штампы, еда/напитки, открытие/закрытие. Не повторяй неизменное состояние.
Не пропускай короткие передачи и разделение денег. Интервалы между событиями
не обязаны быть одинаковыми. В конце отметь видимое итоговое положение денег
и документов, включая оставшиеся части, если оно отличается от уже описанного.
Проследи замеченный ключ; при уходе отметь известное положение ключа, двери,
сейфа и крышки ноутбука. Закрытие крышки не означает выключение компьютера.
Не придумывай уход, скрытые действия, содержимое сумок и выполненные проверки.

Верни только JSON-массив в хронологическом порядке без Markdown и пояснений:
[{"t":0.0,"event":"Исходная обстановка..."},{"t":1.2,"event":"Видимое действие..."}]
Для t выбирай секунду из списка ниже. Не возвращай номера кадров.
'''


def convert(raw,samples,requested=None,*,seconds=False):
    events=json.loads(raw)
    if not isinstance(events,list):raise ValueError('Expected an events array')
    result=[]
    previous=-1
    for event in events:
        if not isinstance(event,dict):raise ValueError('Invalid event')
        if seconds:
            stamp=event.get('t')
            if type(stamp) not in (int,float):raise ValueError('Expected source seconds in t')
            distances=[abs(s['timestamp_sec']-stamp) for s in samples]
            index=min(range(len(samples)),key=distances.__getitem__)
            if not distances[index]<=0.051:raise ValueError('Time does not match a source timestamp')
        else:
            index=event.get('кадр',event.get('frame'))
        if type(index) is not int or not previous<=index<len(samples) or index<0:
            raise ValueError('Invalid or unordered frame index')
        description=event.get('событие',event.get('event'))
        if not isinstance(description,str) or not description.strip():raise ValueError('Missing event text')
        result.append({'t':samples[index]['timestamp_sec'],'event':description})
        previous=index
    if requested is not None and [event.get('кадр',event.get('frame')) for event in events]!=requested:
        raise ValueError('Response does not cover the requested observation frames')
    return result


def write_output(folder,records):
    lines=['## '+records[0]['model'] if records else '## Timeline','']
    for record in records:
        lines += ['### '+record['id'],'','```json',json.dumps(record['timeline'],ensure_ascii=False,indent=2),'```','']
    (folder/'current_outputs.md').write_text('\n'.join(lines)+'\n')


def run(args,folder,config,infer,passed,root):
    import numpy as np
    from PIL import Image
    from transformers.video_utils import VideoMetadata
    items=json.loads((root/args.video_manifest).read_text())
    if args.limit:items=items[:args.limit]
    signature=hashlib.sha256(json.dumps({'config':config,'items':items,'protocol':'russian-source-seconds-v2'},sort_keys=True).encode()).hexdigest()
    records=[]
    task_prompt=config.get('prompt',PROMPT)
    (folder/'prompt.txt').write_text(task_prompt)
    (folder/'prompt.md').write_text('# Промпт таймлайна\n\n```text\n'+task_prompt+'```\n')
    for item in items:
        path=folder/(item['sha256']+'.json')
        if path.exists():
            previous=json.loads(path.read_text())
            if previous.get('signature')!=signature:raise RuntimeError('Inputs changed; use a new folder')
            if previous.get('status')=='done':records.append(previous);continue
        started=time.monotonic()
        windows=[]
        timeline=[]
        if config['timeline_window_sec']:
            raise ValueError('Timeline requires full-video context (timeline_window_sec=0)')
        samples=list(item['samples'])
        if not samples:raise ValueError('Video contains no sampled frames')
        if len(samples)%2:samples=samples+[samples[-1]]
        labels=', '.join(f"{s['timestamp_sec']:.3f}" for s in samples)
        prompt=task_prompt+'\nДопустимые значения t в секундах исходного видео: '+labels
        prompt+=f"\nДлительность ролика: {item['duration_sec']:g} с."
        record={'start_sec':0,'samples':samples,'prompt':prompt}
        try:
            frames=np.stack([np.asarray(Image.open(root/s['path']).convert('RGB')) for s in samples])
            metadata=VideoMetadata(total_num_frames=round(item['duration_sec']*item['source_fps']),fps=item['source_fps'],
                frames_indices=[s['source_index'] for s in samples],duration=item['duration_sec'])
            inference_started=time.monotonic()
            raw,stats=infer(frames,metadata,prompt,max_new_tokens=config['max_new_tokens'])
            stats['inference_sec']=time.monotonic()-inference_started
            record.update(raw_output=raw,stats=stats)
            events=convert(raw,samples,seconds=True)
            if not events or events[0]['t']!=samples[0]['timestamp_sec']:
                raise ValueError('Timeline must start with the initial frame')
            record.update(status='done',timeline=events)
            timeline=events
        except Exception as exc:
            record.update(status='failed',error_class=type(exc).__name__,error=str(exc))
        windows.append(record)
        (folder/(item['sha256']+'_full.json')).write_text(json.dumps(record,ensure_ascii=False,indent=2))
        print('TIMELINE',item['id'],'full_video',record['status'],flush=True)
        result={'id':item['id'],'model':args.model,'signature':signature,'synthetic_control_passed':passed,
                'duration_sec':item['duration_sec'],'timeline':timeline,'windows':windows,
                'status':'done' if all(w['status']=='done' for w in windows) else 'partial',
                'elapsed_sec':time.monotonic()-started}
        path.write_text(json.dumps(result,ensure_ascii=False,indent=2))
        records.append(result)
        write_output(folder,records)
    write_output(folder,records)
    (folder/'run_status.json').write_text(json.dumps({'status':'done' if all(r['status']=='done' for r in records) else 'partial',
                                                  'videos':len(records),'model':args.model},indent=2))
