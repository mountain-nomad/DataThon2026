"""Fresh sequential run. Run with ../.venv/bin/python run_all.py. Never resumes."""
from pathlib import Path
import subprocess, sys, json, time, hashlib, base64, io
ROOT = Path(__file__).resolve().parent
state = {'source_commit': 'f31e6209fb923735d46766e0255222a1d737db33', 'started_at': time.time(), 'status': 'running', 'steps': []}
def save():
    (ROOT/'run_status.json').write_text(json.dumps(state, ensure_ascii=False, indent=2))
def run(name, *args):
    step = {'name': name, 'command': [sys.executable, *args], 'started_at': time.time(), 'status': 'running'}
    state['steps'].append(step); save()
    print('START', name, flush=True)
    with (ROOT/'logs'/f'{name}.log').open('w') as log:
        result = subprocess.run([sys.executable, *args], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    step.update(returncode=result.returncode, finished_at=time.time(), status='done' if result.returncode==0 else 'failed'); save()
    if result.returncode: raise RuntimeError(f'{name} failed; see logs/{name}.log')
    print('DONE', name, flush=True)
def main():
    if (ROOT/'artifacts').exists(): raise RuntimeError('Fresh run required: artifacts already exists. Create a new copy of this folder.')
    save()
    run('00_tests', '-m', 'unittest', 'discover', '-s', 'scripts', '-p', 'test_*.py', '-q')
    run('01_inventory', 'scripts/bootstrap_repro.py', '--video-dir', '/home/artur/video/open/videos')
    run('02_frames', 'scripts/prepare_vlm_v2.py')
    rows=json.loads((ROOT/'artifacts/video_manifest.json').read_text()); ids=[r['id'] for r in rows]
    run('stage1_classification', 'scripts/benchmark_vlm_v2.py', '--model','qwen38_27b','--task','routing','--max-labels','2','--routing-classes','artifacts/routing_prompt_v2/classes.json','--prompt-file','artifacts/routing_prompt_v2/prompt.txt','--video-manifest','artifacts/video_v2_manifest.json','--full-video','--linear-attention','auto','--output-dir','artifacts/stage1_classification')
    for row in rows:
        value=json.loads((ROOT/'artifacts/stage1_classification'/f"{row['sha256']}.json").read_text())
        assert value['status']=='done' and value['synthetic_control_passed'], value
    run('stage2_timesteps','scripts/context_object_timelines.py','--ids',*ids,'--output-dir','artifacts/stage2_timesteps')
    run('stage3_json','scripts/final_text_audit.py','--ids',*ids,'--timeline-dir','artifacts/stage2_timesteps','--router-dir','artifacts/stage1_classification','--output-dir','artifacts/stage3_json','--review-mode','on-demand')
    from PIL import Image
    findings=0
    for row in rows:
        value=json.loads((ROOT/'artifacts/stage3_json/results'/f"{row['id']}.json").read_text())
        assert value['status']=='done'
        for finding in value['violations']:
            findings+=1
            assert len(finding['evidence_frames'])==1
            frame=finding['evidence_frames'][0]
            assert finding['timecode_sec']==frame['timestamp_sec']
            with Image.open(io.BytesIO(base64.b64decode(frame['image_base64'],validate=True))) as image:
                assert image.format=='JPEG'; image.verify()
    state.update(status='done',finished_at=time.time(), videos=len(rows), findings=findings); save()
    print('ALL DONE',len(rows),'videos;',findings,'findings',flush=True)
if __name__=='__main__':
    try: main()
    except Exception as exc:
        state.update(status='failed',error=f'{type(exc).__name__}: {exc}'); save(); raise
