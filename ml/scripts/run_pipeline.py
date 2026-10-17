"""Run the supplied local-weight pipeline without labels or historical predictions."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--video-dir', type=Path, required=True)
    parser.add_argument('--ids', nargs='+')
    parser.add_argument('--output-dir', default='artifacts/repro')
    args=parser.parse_args()
    output=Path(args.output_dir)
    if output.is_absolute():
        output=output.relative_to(ROOT)
    if (ROOT/output).exists():
        raise ValueError('Choose a NEW output folder; historical runners can skip completed results')
    if not (ROOT/'models/qwen38_27b/config.json').exists():
        raise ValueError('Place the recorded checkpoint at ml/models/qwen38_27b first; see README')
    def run(*arguments):
        print('Run:',*arguments,flush=True)
        subprocess.run([sys.executable,*arguments],cwd=ROOT,check=True)
    flags=['--ids',*args.ids] if args.ids else []
    run('scripts/bootstrap_repro.py','--video-dir',str(args.video_dir.resolve()),*flags)
    rows=json.loads((ROOT/'artifacts/video_manifest.json').read_text())
    ids=[r['id'] for r in rows]
    run('scripts/prepare_vlm_v2.py')
    run('scripts/benchmark_vlm_v2.py','--model','qwen38_27b','--task','routing',
        '--max-labels','2','--routing-classes','artifacts/routing_prompt_v2/classes.json',
        '--prompt-file','artifacts/routing_prompt_v2/prompt.txt',
        '--video-manifest','artifacts/video_v2_manifest.json','--full-video',
        '--linear-attention','auto','--output-dir',str(output/'router'))
    run('scripts/context_object_timelines.py','--ids',*ids,'--output-dir',str(output/'timelines'))
    run('scripts/final_text_audit.py','--ids',*ids,'--timeline-dir',str(output/'timelines'),
        '--router-dir',str(output/'router'),'--output-dir',str(output/'final'),
        '--review-mode','on-demand')
    print('Final report:',ROOT/output/'final/current_outputs.md',flush=True)


if __name__=='__main__':
    main()
