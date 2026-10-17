"""Label-blind operation classification. Reads only video frames and class definitions."""
import hashlib,json,time,traceback
from pathlib import Path
import numpy as np
from PIL import Image
import torch
from transformers.video_utils import VideoMetadata
from routing_codes import parse_labels
ROOT=Path(__file__).resolve().parents[1]

def run(args,folder,config,processor,infer,passed):
 tokenizer=processor.tokenizer
 label_tokens={label:tokenizer.encode(label,add_special_tokens=False) for label in config['class_labels']}
 assert all(len(v)==1 for v in label_tokens.values()),label_tokens
 config['label_tokens']=label_tokens
 items=json.loads((ROOT/args.video_manifest).read_text())
 if args.limit:items=items[:args.limit]
 # This manifest has no ground-truth labels or operation names.
 assert not any('operation_label' in x or 'label' in x for x in items)
 config['input_manifest_sha256']=hashlib.sha256((ROOT/args.video_manifest).read_bytes()).hexdigest()
 (folder/'config.json').write_text(json.dumps(config,indent=2))
 for index,item in enumerate(items):
  target=folder/(item['sha256']+'.json')
  if target.exists() and json.loads(target.read_text()).get('status')=='done':continue
  start=time.monotonic();torch.cuda.reset_peak_memory_stats()
  record=dict(id=item['id'],sha256=item['sha256'],model=args.model,synthetic_control_passed=passed)
  try:
   samples=item['samples']
   if len(samples)>48:
    samples=[samples[i] for i in np.linspace(0,len(samples)-1,48).round().astype(int)]
   if len(samples)%2:samples=samples+[samples[-1]]
   array=np.stack([np.asarray(Image.open(ROOT/f['path']).convert('RGB')) for f in samples])
   metadata=VideoMetadata(total_num_frames=round(item['duration_sec']*item['source_fps']),fps=item['source_fps'],frames_indices=[f['source_index'] for f in samples],duration=item['duration_sec'])
   raw,stats=infer(array,metadata,config['prompt'],max_new_tokens=config['max_new_tokens'])
   torch.cuda.synchronize()
   label=raw.strip()
   try:
    labels=parse_labels(label,label_tokens,config['max_labels']);valid=True
   except ValueError:
    labels=[];valid=False
   record.update(raw_output=raw,predicted_label=label[0] if valid else None,
       predicted_labels=labels,predicted_code=''.join(labels) if valid else None,
       status='done' if valid else 'invalid_output',**stats)
   record['sample_timestamps_sec']=[f['timestamp_sec'] for f in samples]
  except Exception as exc:
   record.update(status='failed',error_class=type(exc).__name__,error=str(exc),traceback=traceback.format_exc())
   torch.cuda.empty_cache()
  record.update(elapsed_sec=time.monotonic()-start,peak_allocated_bytes=torch.cuda.max_memory_allocated())
  target.write_text(json.dumps(record,ensure_ascii=False,indent=2))
  print('ROUTING',args.model,f'{index+1}/{len(items)}',item['id'],record['status'],'label',record.get('predicted_label'),'seconds',round(record['elapsed_sec'],2),flush=True)
  if index==0 and record['status']!='done':raise RuntimeError('First classification failed; inspect local record')
 (folder/'run_status.json').write_text(json.dumps(dict(status='partial' if args.limit else 'done',model=args.model)))
