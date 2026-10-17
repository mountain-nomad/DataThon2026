"""Build label-free inventories from recipient-owned videos; install runtime config seeds."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2))


def main():
    import av
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--video-dir', type=Path, default=Path('open/videos'))
    parser.add_argument('--ids', nargs='+')
    args = parser.parse_args()
    source = args.video_dir.resolve()
    paths = [p for p in source.iterdir() if p.suffix.lower() in {'.mov','.mp4','.mkv','.avi'}]
    paths.sort(key=lambda p: (int(re.search(r'\d+',p.stem)[0]) if re.search(r'\d+',p.stem) else 10**9, p.name))
    if args.ids:
        missing = set(args.ids) - {p.stem for p in paths}
        if missing:
            raise ValueError(f'Videos missing: {sorted(missing)}')
        paths = [p for p in paths if p.stem in args.ids]
    seen, rows = set(), []
    for p in paths:
        with p.open('rb') as handle:
            sha = hashlib.file_digest(handle, 'sha256').hexdigest()
        if sha in seen:
            print('Skip duplicate video:',p.name)
            continue
        seen.add(sha)
        with av.open(str(p)) as container:
            stream = container.streams.video[0]
            if stream.duration is None:
                raise ValueError(f'No stream duration for {p}; inspect source metadata before reproducing')
            duration = float(stream.duration * stream.time_base)
            fps = float(stream.base_rate or stream.average_rate)
            rows.append({'id':p.stem,'path':str(p),'sha256':sha,'duration_sec':duration,
                         'source_fps':fps,'total_num_frames':stream.frames or round(duration*fps),
                         'width':stream.width,'height':stream.height})
    if not rows:
        raise ValueError('No input videos found')
    if len({r['id'] for r in rows}) != len(rows):
        raise ValueError('Video stems must be unique')
    write(ROOT/'artifacts/video_manifest.json', rows)
    write(ROOT/'artifacts/all_videos_full_frame_usage_rule/manifest.json', rows)
    reference = json.loads((ROOT/'configs/router_reference.json').read_text())
    prompt = (ROOT/'prompts/router_v2.txt').read_text()
    if hashlib.sha256(prompt.encode()).hexdigest() != reference['prompt_sha256']:
        raise ValueError('Router prompt changed from the recorded checkpoint configuration')
    for name in ('prompt.txt','classes.json'):
        source_file = ROOT/('prompts/router_v2.txt' if name=='prompt.txt' else 'configs/classes.json')
        dest = ROOT/'artifacts/routing_prompt_v2'/name
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source_file,dest)
    write(ROOT/'artifacts/routing_prompt_v2/qwen38_27b/config.json',reference)
    write(ROOT/'artifacts/vlm_v2_download_manifest.json',[json.loads((ROOT/'configs/model.json').read_text())])
    print('Prepared label-free metadata for',len(rows),'unique videos')


if __name__=='__main__':
    main()
