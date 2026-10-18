"""Upload the longest inventoried video through public API and measure the full request cycle."""
from pathlib import Path
from datetime import datetime, timezone
import base64
import json
import time
import uuid
import httpx
import cv2
import numpy as np

ROOT=Path(__file__).resolve().parents[1]

def main():
    access=json.loads((ROOT/'local/api_access.json').read_text())
    inventory=json.loads((ROOT/'local/video_duration_inventory.json').read_text())
    video=max(inventory,key=lambda row:row['duration_sec'])
    folder=ROOT/'local/api_benchmarks'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid.uuid4().hex[:8])
    folder.mkdir(parents=True)
    report={'video':video,'base_url':access['base_url'],'started_at_utc':datetime.now(timezone.utc).isoformat(),
            'status':'uploading','jury_budget_sec':300,'folder':str(folder)}
    def save():
        temp=folder/'report.tmp';temp.write_text(json.dumps(report,ensure_ascii=False,indent=2));temp.replace(folder/'report.json')
    save();print('REPORT',folder/'report.json',flush=True)
    started=time.monotonic()
    headers={'X-API-Key':access['api_key'],'ngrok-skip-browser-warning':'1'}
    try:
        with httpx.Client(base_url=access['base_url'],headers=headers,timeout=120) as client:
            path=Path(video['path'])
            with path.open('rb') as source:
                response=client.post('/api/v1/analyze',files={'file':(path.name,source,'video/quicktime')})
            response.raise_for_status()
            job=response.json()['job_id'];uploaded=time.monotonic()
            report.update(job_id=job,upload_sec=round(uploaded-started,3),status='processing')
            save();print('UPLOADED',job,'seconds',report['upload_sec'],flush=True)
            failures=0;last_print=0
            while True:
                elapsed=time.monotonic()-started
                if elapsed>1900:raise TimeoutError('Benchmark polling exceeded 1900 seconds')
                try:
                    response=client.get('/api/v1/jobs/'+job,timeout=30)
                    response.raise_for_status();result=response.json();failures=0
                except (httpx.HTTPError,ValueError) as error:
                    failures+=1;report['poll_errors']=report.get('poll_errors',0)+1
                    report['last_poll_error']=type(error).__name__;save()
                    if failures>=6:raise
                    time.sleep(5);continue
                report.update(status=result['status'],observed_elapsed_sec=round(time.monotonic()-started,3))
                save()
                if elapsed-last_print>=30:
                    print('POLL',result['status'],'elapsed_sec',round(elapsed),flush=True);last_print=elapsed
                if result['status'] in ('done','failed'):break
                time.sleep(5)
            finished=time.monotonic()
            (folder/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
            report.update(total_sec=round(finished-started,3),after_upload_sec=round(finished-uploaded,3),
                          within_5_minutes=finished-started<=300,finished_at_utc=datetime.now(timezone.utc).isoformat())
            if result['status']=='done':
                assert set(result)=={'job_id','status','verdict','violations'}
                assert result['job_id']==job
                assert result['verdict'] in ['violation','no_violation']
                assert isinstance(result['violations'],list)
                assert bool(result['violations']) == (result['verdict']=='violation')
                frames=0
                for finding in result['violations']:
                    assert set(finding)=={'type','timecode_sec','description','evidence_frames'}
                    assert finding['type'] and finding['description']
                    assert 0<=finding['timecode_sec']<=video['duration_sec']
                    assert 1<=len(finding['evidence_frames'])<=3
                    for frame in finding['evidence_frames']:
                        assert set(frame)=={'timestamp_sec','image_base64'}
                        assert 0<=frame['timestamp_sec']<=video['duration_sec']
                        data=base64.b64decode(frame['image_base64'],validate=True)
                        assert data.startswith(b'\xff\xd8')
                        decoded=cv2.imdecode(np.frombuffer(data,dtype=np.uint8),cv2.IMREAD_COLOR)
                        assert decoded is not None and decoded.size
                        frames+=1
                report.update(contract_valid=True,findings=len(result['violations']),jpeg_frames=frames,verdict=result['verdict'])
            else:report['error']=result.get('error')
            save();print('FINISHED',json.dumps(report,ensure_ascii=False),flush=True)
    except Exception as error:
        report.update(benchmark_error=str(error),observed_elapsed_sec=round(time.monotonic()-started,3));save();raise

if __name__=='__main__':main()
