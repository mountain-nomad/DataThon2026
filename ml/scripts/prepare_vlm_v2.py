"""Cache 1 fps frames with source indices, independent of labels."""
import argparse
import json
from pathlib import Path
import av

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--fps',type=float,default=1)
    parser.add_argument('--edge',type=int,default=768)
    parser.add_argument('--quality',type=int,default=95)
    parser.add_argument('--cache-name',default='video_v2')
    parser.add_argument('--limit',type=int)
    parser.add_argument('--format',choices=['jpg','png'],default='jpg')
    args=parser.parse_args()
    source = json.loads((ROOT/'artifacts/video_manifest.json').read_text())
    items = []
    for item in source:
        if item.get('duplicate_of'):
            continue
        if args.limit and len(items)>=args.limit:break
        dest = ROOT/'artifacts'/args.cache_name/item['sha256']
        dest.mkdir(parents=True, exist_ok=True)
        cache = dest/'manifest.json'
        if cache.exists():
            items.append(json.loads(cache.read_text()))
            continue
        with av.open(str(ROOT/item['path'])) as container:
            stream = container.streams.video[0]
            stream.thread_type = 'AUTO'
            fps = float(stream.average_rate)
            start_pts = stream.start_time or 0
            samples, next_time = [], 0.0
            for index, frame in enumerate(container.decode(stream)):
                stamp = float((frame.pts-start_pts)*stream.time_base)
                if stamp+1e-6 < next_time:
                    continue
                image = frame.to_image()
                if args.edge>0:image.thumbnail((args.edge,args.edge))
                path = dest/f'{len(samples):04d}.{args.format}'
                image.save(path,**({'quality':args.quality} if args.format=='jpg' else {}))
                samples.append(dict(path=str(path.relative_to(ROOT)),timestamp_sec=stamp,source_index=index))
                next_time += 1.0/args.fps
        windows=[]
        start=0.0
        while start < item['duration_sec']:
            end=min(start+40.0,item['duration_sec'])
            indices=[i for i,f in enumerate(samples) if start <= f['timestamp_sec'] < end]
            if indices:
                windows.append(dict(start_sec=start,end_sec=end,sample_indices=indices))
            if end>=item['duration_sec']:
                break
            start+=36.0
        record={k:v for k,v in item.items() if k!='frames'}
        record.update(samples=samples,windows=windows,source_fps=fps)
        cache.write_text(json.dumps(record,indent=2,ensure_ascii=False))
        items.append(record)
    (ROOT/'artifacts'/(args.cache_name+'_manifest.json')).write_text(json.dumps(items,indent=2,ensure_ascii=False))
    print(json.dumps(dict(unique_videos=len(items),windows=sum(len(x['windows']) for x in items),
                         cached_frames=sum(len(x['samples']) for x in items),fps=args.fps,longest_edge=args.edge),indent=2))


if __name__=='__main__':
    main()
