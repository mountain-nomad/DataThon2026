"""Offline native-video benchmark. No ground-truth reads; private text stays local."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time
import traceback
import sys

ROOT=Path(__file__).resolve().parents[1]
os.environ['HF_HUB_OFFLINE']='1'
os.environ['TRANSFORMERS_OFFLINE']='1'
os.environ['HF_HUB_DISABLE_TELEMETRY']='1'
os.environ['HF_MODULES_CACHE']=str(ROOT/'.cache/hf_modules')
os.environ['TOKENIZERS_PARALLELISM']='false'
if '--linear-attention' in sys.argv and sys.argv[sys.argv.index('--linear-attention')+1]=='fla':
    # FLA's Triton JIT remains enabled; disable only the incompatible optional
    # Torch Inductor graph compiler used by ancillary FLA helper functions.
    os.environ['TORCHDYNAMO_DISABLE']='1'
import numpy as np
from PIL import Image
import torch
import transformers
from transformers import AutoProcessor, AutoModelForImageTextToText, AutoModelForCausalLM, BitsAndBytesConfig
from transformers.video_utils import VideoMetadata
from benchmark_vlm import PROMPT


def extract_json(text):
    decoder=json.JSONDecoder()
    objects=[]
    for i,char in enumerate(text):
        if char!='{':continue
        try:
            value,_=decoder.raw_decode(text[i:])
            if isinstance(value,dict):objects.append(value)
        except json.JSONDecodeError:pass
    return objects


def prediction(text,duration):
    objects=[x for x in extract_json(text) if type(x.get('positive')) is bool]
    if not objects:raise ValueError('No JSON with boolean positive')
    result=objects[-1]
    stamp=result.get('timecode_sec')
    result['timecode_valid']=not result['positive'] or (type(stamp) in (int,float) and np.isfinite(stamp) and 0<=stamp<=duration)
    if not result['positive']:result['timecode_sec']=None
    return result


def processor_inputs(processor,frames,metadata,text):
    message=[{'role':'user','content':[{'type':'video','video':'local_video'}, {'type':'text','text':text}]}]
    template=processor.apply_chat_template(message,tokenize=False,add_generation_prompt=True,enable_thinking=False)
    # Native video processor sees actual source indices/fps, without re-sampling.
    return processor(text=[template],videos=[frames],video_metadata=[metadata],do_sample_frames=False,return_tensors='pt')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--model',required=True)
    parser.add_argument('--limit',type=int)
    parser.add_argument('--gptq-backend',choices=['torch','marlin'],default='marlin')
    parser.add_argument('--output-dir')
    parser.add_argument('--what-changed',default='')
    parser.add_argument('--linear-attention',choices=['auto','fla'],default='auto')
    parser.add_argument('--video-manifest',default='artifacts/video_v2_manifest.json')
    parser.add_argument('--sampling-fps',type=float,default=1)
    parser.add_argument('--frame-edge',type=int,default=768)
    parser.add_argument('--video-max-pixels',type=int,help='Qwen total video pixel budget; increasing FPS otherwise reduces each frame')
    parser.add_argument('--full-video',action='store_true')
    parser.add_argument('--task',choices=['violation','routing','scenario-audit','timeline-only'],default='violation')
    parser.add_argument('--scenario-file',default='scenario (2).md')
    parser.add_argument('--audit-max-frames',type=int,default=160)
    parser.add_argument('--routing-results-dir',help='Reuse verified Qwen3.8 v2 routes; selected model runs specialists only')
    parser.add_argument('--routing-video-manifest',help='Original manifest used by cached router when audit sampling differs')
    parser.add_argument('--frame-time-labels',action='store_true',help='Explicit compact frame-index to seconds map')
    parser.add_argument('--audit-prompt-style',choices=['legacy','timeline','timeline-detailed'],default='legacy')
    parser.add_argument('--routing-classes',default='artifacts/routing/classes.json')
    parser.add_argument('--max-labels',type=int,choices=[1,2],default=1)
    parser.add_argument('--prompt-file')
    parser.add_argument('--timeline-window-sec',type=int,default=0,help='Timeline context window; 0 supplies the whole video')
    parser.add_argument('--timeline-max-tokens',type=int,default=4096)
    args=parser.parse_args()
    if args.task=='scenario-audit':
        if args.output_dir is None:args.output_dir='artifacts/scenario_audit'
        if args.model!='qwen38_27b' and not args.routing_results_dir:
            parser.error('Other specialists require --routing-results-dir from the verified router')
        from scenario_audit import load_protocol, load_routes
        audit_protocol=load_protocol(ROOT,args.scenario_file,args.audit_max_frames,args.frame_time_labels,args.audit_prompt_style)
        if args.routing_results_dir:
            cached_routes=load_routes(ROOT,args.video_manifest,args.routing_results_dir,args.limit,args.routing_video_manifest)
        args.routing_classes='artifacts/routing_prompt_v2/classes.json'
        args.max_labels=2
        args.prompt_file='artifacts/routing_prompt_v2/prompt.txt'
    task_prompt=PROMPT
    if args.task=='timeline-only':
        from timeline_inference import PROMPT as task_prompt
        if args.prompt_file:task_prompt=(ROOT/args.prompt_file).read_text()
    if args.task in ('routing','scenario-audit'):
        classes=json.loads((ROOT/args.routing_classes).read_text())
        task_prompt=('Classify the main operation in this complete surveillance video. '
            +('Choose the closest matching operation from the eight classes below. ' if args.max_labels==1 and len(classes)==8 else f'Choose from the {len(classes)} classes below. ')
            +'The descriptions summarize typical workflows; some steps may be outside the recording. '
            'Focus on client presence, cash versus bag, direction of money movement, and arrival versus departure.\n'
            +'\n'.join(c['label']+'. '+c['name']+': '+c['description'] for c in classes)
            +('\nReturn exactly ONE digit (1 through 8). No explanation, punctuation or JSON.' if args.max_labels==1 and len(classes)==8 else
              '\nReturn exactly ONE class digit. No explanation, punctuation or JSON.' if args.max_labels==1 else
              '\nReturn ONE or TWO distinct class digits from the list, concatenated without separators. '
              'Choose one class when a single operation fits. Choose two when two operations are supported or two classes are plausible. '
              'Order them by confidence, most likely first. No class has automatic priority over another. '
              'Do not repeat a digit. No explanation, spaces, punctuation or JSON.'))
        if args.prompt_file:
            task_prompt=(ROOT/args.prompt_file).read_text()
    row=next(x for x in json.loads((ROOT/'artifacts/vlm_v2_download_manifest.json').read_text()) if x['key']==args.model)
    if row['quantization']=='gptq_int4':
        target=ROOT/'.venv-gptq/bin/python'
        os.environ['PATH']=str(target.parent)+os.pathsep+os.environ.get('PATH','')
        os.environ.setdefault('GPTQMODEL_TORCH_EXTENSIONS_DIR',str(ROOT/'.cache/gptq_extensions'))
        os.environ.setdefault('TORCH_EXTENSIONS_DIR',str(ROOT/'.cache/torch_extensions'))
        os.environ.setdefault('TORCH_CUDA_ARCH_LIST','12.0')
        os.environ.setdefault('MAX_JOBS','4')
        if Path(sys.prefix).resolve()!=(ROOT/'.venv-gptq').resolve():
            os.execv(str(target),[str(target),str(Path(__file__).resolve()),*sys.argv[1:]])
        download_status=json.loads((ROOT/'artifacts/downloads'/(args.model+'.json')).read_text())
        if download_status['status']!='done':raise RuntimeError('GPTQ checkpoint is not downloaded yet')
    folder=ROOT/args.output_dir if args.output_dir else ROOT/'artifacts/benchmark_v2'/args.model
    folder.mkdir(parents=True,exist_ok=True)
    (folder/'run_status.json').write_text(json.dumps(dict(status='running',model=args.model)))
    torch.set_num_threads(8)
    torch.manual_seed(0)
    config=dict(row,prompt=task_prompt,prompt_sha256=hashlib.sha256(task_prompt.encode()).hexdigest(),
                sampling_fps=args.sampling_fps,window_sec=None if args.full_video else 40,overlap_sec=0 if args.full_video else 4,frame_longest_edge=args.frame_edge,native_video=True,
                do_sample=False,max_new_tokens=512,enable_thinking=False,torch_version=torch.__version__,
                transformers_version=transformers.__version__,offline=True)
    config.update(full_video=args.full_video,video_manifest=args.video_manifest)
    if args.video_max_pixels is not None:
        if args.video_max_pixels<4096:parser.error('--video-max-pixels must be at least 4096')
        if not args.model.startswith('qwen'):parser.error('--video-max-pixels currently supports Qwen only')
        config['video_max_pixels']=args.video_max_pixels
    config['task']=args.task
    if args.prompt_file:config['prompt_file']=args.prompt_file
    if args.task in ('routing','scenario-audit'):config.update(max_new_tokens=args.max_labels,max_labels=args.max_labels,
        routing_classes=args.routing_classes,class_labels=[c['label'] for c in classes],
        max_frames=48,full_video=True,window_sec=None,overlap_sec=0)
    config.update(what_changed=args.what_changed,linear_attention=args.linear_attention)
    if args.task=='timeline-only':
        if args.timeline_window_sec<0 or args.timeline_max_tokens<1:parser.error('Invalid timeline window or token budget')
        config.update(max_new_tokens=args.timeline_max_tokens,timeline_window_sec=args.timeline_window_sec)
        if args.routing_results_dir:
            from scenario_audit import load_routes
            config['cached_routes']=load_routes(ROOT,args.video_manifest,args.routing_results_dir,args.limit,args.routing_video_manifest)
    if args.task=='scenario-audit':
        config['audit_protocol']=audit_protocol
        if config['prompt_sha256']!=audit_protocol['router_prompt_sha256']:
            raise RuntimeError('Routing prompt differs from the verified 97.5% configuration')
        reference=json.loads((ROOT/'artifacts/routing_prompt_v2/qwen38_27b/config.json').read_text())
        if args.routing_results_dir:
            config['routing_results_dir']=args.routing_results_dir
            if args.routing_video_manifest:config['routing_video_manifest']=args.routing_video_manifest
            config['cached_routes']=cached_routes
        else:
            for key in ('repo','revision','quantization','sampling_fps','frame_longest_edge','linear_attention'):
                if config[key]!=reference[key]:raise RuntimeError(f'Router setting changed: {key}')
    if args.linear_attention=='fla':config['torchdynamo_disabled']=True
    config_path=folder/'config.json'
    if config_path.exists():
        previous=json.loads(config_path.read_text())
        if previous.get('task')!=config['task'] or previous.get('audit_protocol')!=config.get('audit_protocol'):
            raise RuntimeError('Task or audit protocol changed; use a new output folder')
        if previous['prompt_sha256']!=config['prompt_sha256']:raise RuntimeError('Prompt changed; use a new output folder')
        if previous.get('linear_attention','auto')!=args.linear_attention:
            raise RuntimeError('Attention implementation changed; use a new output folder')
    config_path.write_text(json.dumps(config,indent=2))
    start=time.monotonic()
    custom=args.model=='internvideo3'
    processor=AutoProcessor.from_pretrained(ROOT/row['path'],local_files_only=True,trust_remote_code=custom)
    if args.video_max_pixels is not None:
        processor.video_processor.size={'shortest_edge':4096,'longest_edge':args.video_max_pixels}
    if args.model=='internvl35_38b':
        # Published HF video config defaults to 384/CLIP stats, but the vision
        # checkpoint and 256-token frame placeholders require 448/ImageNet.
        processor.video_processor.size={'height':448,'width':448}
        processor.video_processor.image_mean=processor.image_processor.image_mean
        processor.video_processor.image_std=processor.image_processor.image_std
        config['video_processor_correction']={'size':448,'normalization':'match official image processor',
            'reason':'published video config inconsistent with vision checkpoint and image_seq_length=256'}
        config_path.write_text(json.dumps(config,indent=2))
    if args.frame_edge < 768 and custom:
        processor.video_processor.size={'shortest_edge':4096,'longest_edge':args.frame_edge**2}
    load_kwargs=dict(dtype=torch.bfloat16,device_map='cuda',attn_implementation='sdpa',local_files_only=True)
    if row['quantization']=='nf4':
        load_kwargs['quantization_config']=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',
            bnb_4bit_use_double_quant=True,bnb_4bit_compute_dtype=torch.bfloat16,
            llm_int8_skip_modules=['lm_head','model.vision_tower','model.embed_vision'] if args.model=='gemma4_31b' else None)
        if args.model=='gemma4_31b':
            config['quantization_skip_modules']=['lm_head','model.vision_tower','model.embed_vision']
            config_path.write_text(json.dumps(config,indent=2))
    if row['quantization']=='gptq_int4':
        from gptqmodel import GPTQModel, BACKEND
        from gptqmodel.utils import torch as gptq_torch_utils
        gptq_torch_utils.TORCH_HAS_COMPILE=False
        backend=BACKEND.GPTQ_MARLIN if args.gptq_backend=='marlin' else BACKEND.GPTQ_TORCH
        from torch import _dynamo
        # GPTQModel unconditionally resets compiler caches while loading.
        # This is a fresh eager-only process: no compiled graphs exist. Avoid
        # importing the broken optional CuteDSL compiler in this Torch build.
        original_reset=_dynamo.reset
        _dynamo.reset=lambda: None
        try:
            model=GPTQModel.load(str(ROOT/row['path']),device='cuda',backend=backend,
                                 dtype=torch.bfloat16,attn_implementation='sdpa').eval()
        finally:
            _dynamo.reset=original_reset
        config['gptq_compiler_reset_skipped']='fresh eager-only process; optional CuteDSL CSE typing incompatibility'
        config['gptq_backend']=args.gptq_backend
        config_path.write_text(json.dumps(config,indent=2))
    else:
        cls=AutoModelForCausalLM if custom else AutoModelForImageTextToText
        model=cls.from_pretrained(ROOT/row['path'],trust_remote_code=custom,**load_kwargs).eval()
    load_sec=time.monotonic()-start
    kernel_calls={}
    if args.linear_attention=='fla':
        import importlib
        import inspect
        from fla.ops.gated_delta_rule import chunk_gated_delta_rule, fused_recurrent_gated_delta_rule
        from causal_conv1d import causal_conv1d_fn, causal_conv1d_update
        module=importlib.import_module('transformers.models.qwen3_5_moe.modeling_qwen3_5_moe')
        kernels={'torch_chunk_gated_delta_rule':chunk_gated_delta_rule,
                 'torch_recurrent_gated_delta_rule':fused_recurrent_gated_delta_rule,
                 'causal_conv1d_fn':causal_conv1d_fn,'causal_conv1d_update':causal_conv1d_update}
        def instrument(name,fn):
            params=inspect.signature(fn).parameters
            def wrapped(*a,**kw):
                kernel_calls[name]=kernel_calls.get(name,0)+1
                return fn(*a,**{k:v for k,v in kw.items() if k in params})
            return wrapped
        for name,fn in kernels.items():setattr(module,name,instrument(name,fn))
        from importlib.metadata import version
        config['fast_kernel_versions']={name:version(name) for name in ['flash-linear-attention','causal-conv1d']}
        config_path.write_text(json.dumps(config,indent=2))
    if args.model=='gemma4_31b':
        quantized_vision=[name for name,module in model.named_modules()
            if name.startswith(('model.vision_tower.','model.embed_vision.'))
            and type(module).__name__ in ('Linear4bit','Linear8bitLt')]
        if quantized_vision:
            raise RuntimeError('Vision quantization exclusions were not applied')
    # Hook the actual vision tower, not only processor tensor creation.
    vision_module=None
    for name,module in model.named_modules():
        if name.split('.')[-1] in ['visual','vision_tower','vision_model']:
            vision_module=module;break
    calls=[]
    handle=vision_module.register_forward_hook(lambda m,a,o:calls.append(1)) if vision_module is not None else None

    def infer(frames,metadata,text,max_new_tokens=512):
        before=len(calls)
        inputs=processor_inputs(processor,frames,metadata,text).to('cuda')
        input_shapes={k:list(v.shape) for k,v in inputs.items() if hasattr(v,'shape')}
        with torch.inference_mode():
            output=model.generate(**inputs,do_sample=False,max_new_tokens=max_new_tokens,use_cache=True)
        new_ids=output[:,inputs['input_ids'].shape[1]:]
        raw=processor.batch_decode(new_ids,skip_special_tokens=True)[0]
        return raw,dict(input_shapes=input_shapes,input_tokens=inputs['input_ids'].shape[1],
                        output_tokens=new_ids.shape[1],sampled_frames=len(frames),vision_forward_calls=len(calls)-before,
                        video_grid_thw=inputs['video_grid_thw'].tolist() if 'video_grid_thw' in inputs else None)

    frames=np.zeros((12,432,768,3),dtype=np.uint8)
    frames[:6,:,:,0]=255;frames[6:,:,:,2]=255
    metadata=VideoMetadata(total_num_frames=360,fps=30,frames_indices=list(range(0,360,30)),duration=12)
    raw,stats=infer(frames,metadata,'The video has a solid color that changes once. Return ONLY JSON with keys first_color and last_color, using English color names.')
    checks=extract_json(raw)
    passed=any(str(x.get('first_color','')).lower()=='red' and str(x.get('last_color','')).lower()=='blue' for x in checks)
    smoke=dict(passed=passed,expected={'first_color':'red','last_color':'blue'},raw_output=raw,**stats,
               model_load_sec=load_sec,model_memory_bytes=model.get_memory_footprint(),vision_hook_available=handle is not None)
    if args.linear_attention=='fla':
        smoke['fast_kernel_calls']=dict(kernel_calls)
        smoke['passed']=passed=passed and all(kernel_calls.get(name,0)>0 for name in kernels)
    (folder/'synthetic_control.json').write_text(json.dumps(smoke,indent=2))
    print('READY',args.model,'synthetic_passed',passed,'model_GiB',round(smoke['model_memory_bytes']/2**30,2),flush=True)
    if not passed:
        (folder/'run_status.json').write_text(json.dumps(dict(status='failed_control',model=args.model)))
        raise RuntimeError('Synthetic video control failed; real-video benchmark stopped')
    if args.task=='scenario-audit':
        from scenario_audit import run
        run(args,folder,config,infer,passed,ROOT)
        if handle:handle.remove()
        return
    if args.task=='timeline-only':
        from timeline_inference import run
        run(args,folder,config,infer,passed,ROOT)
        if handle:handle.remove()
        return
    if args.task=='routing':
        from routing_inference import run
        run(args,folder,config,processor,infer,passed)
        if handle:handle.remove()
        return
    items=json.loads((ROOT/args.video_manifest).read_text())
    if args.limit:items=items[:args.limit]
    for item_index,item in enumerate(items):
        if args.full_video:
            item=dict(item,windows=[dict(start_sec=0,end_sec=item['duration_sec'],sample_indices=list(range(len(item['samples']))))])
        result_path=folder/(item['sha256']+'.json')
        if result_path.exists() and json.loads(result_path.read_text()).get('status')=='done':continue
        start=time.monotonic()
        torch.cuda.reset_peak_memory_stats()
        windows=[]
        for win_index,window in enumerate(item['windows']):
            win_path=folder/(item['sha256']+f'_window{win_index}.json')
            if win_path.exists() and json.loads(win_path.read_text()).get('status')=='done':
                windows.append(json.loads(win_path.read_text()));continue
            record=dict(window_index=win_index,start_sec=window['start_sec'],end_sec=window['end_sec'])
            win_start=time.monotonic()
            try:
                samples=[item['samples'][i] for i in window['sample_indices']]
                if len(samples)%2:samples.append(samples[-1])
                array=np.stack([np.asarray(Image.open(ROOT/f['path']).convert('RGB')) for f in samples])
                metadata=VideoMetadata(total_num_frames=round(item['duration_sec']*item['source_fps']),
                    fps=item['source_fps'],frames_indices=[f['source_index'] for f in samples],duration=item['duration_sec'])
                timing=f"\nThis is a video excerpt covering original-video seconds {window['start_sec']:.2f} through {window['end_sec']:.2f}. The video timestamps are absolute seconds from the beginning of the original video. Return an absolute timecode_sec, not a frame number. The sampled frames have these absolute times: "+', '.join(f"{f['timestamp_sec']:.2f}" for f in samples)+'.'
                raw,stats=infer(array,metadata,PROMPT+timing)
                record.update(raw_output=raw,**stats)
                record.update(prediction=prediction(raw,item['duration_sec']),status='done')
            except Exception as exc:
                record.update(status='failed',error_class=type(exc).__name__,error=str(exc),traceback=traceback.format_exc())
                torch.cuda.empty_cache()
            record['elapsed_sec']=time.monotonic()-win_start
            win_path.write_text(json.dumps(record,indent=2,ensure_ascii=False))
            windows.append(record)
        valid=[w for w in windows if w['status']=='done']
        positives=[w['prediction'] for w in valid if w['prediction']['positive']]
        # Earliest valid event is deterministic and independent of ground truth.
        positives.sort(key=lambda p:p['timecode_sec'] if p['timecode_valid'] else float('inf'))
        pred=positives[0] if positives else {'positive':False,'timecode_sec':None,'timecode_valid':True}
        result=dict(id=item['id'],sha256=item['sha256'],model=args.model,
            status='done' if len(valid)==len(windows) else 'failed',prediction=pred,
            events=positives,elapsed_sec=sum(w['elapsed_sec'] for w in windows),
            wall_sec=time.monotonic()-start,windows_total=len(windows),windows_done=len(valid),
            peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved(),
            synthetic_control_passed=passed)
        result_path.write_text(json.dumps(result,indent=2,ensure_ascii=False))
        print('PROGRESS',args.model,f'{item_index+1}/{len(items)}',item['id'],result['status'],
              'windows',f'{len(valid)}/{len(windows)}','seconds',round(result['elapsed_sec'],1),flush=True)
        if item_index==0 and result['status']=='failed':raise RuntimeError('First video failed; inspect local window error')
    if handle:handle.remove()
    (folder/'run_status.json').write_text(json.dumps(dict(status='partial' if args.limit else 'done',model=args.model,model_load_sec=load_sec),indent=2))


if __name__=='__main__':
    import fcntl
    # Independent launcher/retries must never load two large models on the GPU.
    with (ROOT/'artifacts/benchmark_v2_gpu.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        try:
            main()
        except Exception as exc:
            if '--model' in sys.argv:
                key=sys.argv[sys.argv.index('--model')+1]
                out=sys.argv[sys.argv.index('--output-dir')+1] if '--output-dir' in sys.argv else 'artifacts/benchmark_v2/'+key
                status_path=ROOT/out/'run_status.json'
                status_path.parent.mkdir(parents=True,exist_ok=True)
                status_path.write_text(json.dumps(dict(status='failed',model=key,
                    error_class=type(exc).__name__,error=str(exc)),indent=2))
            raise
