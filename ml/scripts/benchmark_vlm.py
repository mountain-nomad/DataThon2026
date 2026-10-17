"""Local offline VLM inference. This process never opens ground-truth labels.

Raw scene descriptions stay in local artifacts; stdout contains only IDs/status.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import time

os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
os.environ['HF_MODULES_CACHE'] = str(Path(__file__).resolve().parents[1] / '.cache/hf_modules')
import torch
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PROMPT = '''You are screening silent staged bank cash-counter surveillance video for visually observable cash-handling security irregularities. The supplied images are chronologically ordered samples with timestamps in seconds from one video. There is a cashier, possibly customers or cash collectors. The camera is usually overhead but may vary.
Return positive=true only if a concrete visible action provides evidence of a possible cash-discipline/security violation. Consider visible unauthorized access to the cashier work area or cash, cash left unattended/unsecured while the cashier leaves, concealment of cash in personal clothing/belongings, visibly unsafe transfer of cash or collection bags, or an observable skipped security procedure. These are screening hypotheses, not a complete legal rulebook. Ordinary customer handovers, normal counting and working with documents are not automatically violations. Do not infer account balances, transaction posting, identity, intent, authenticity of banknotes, or off-camera facts. Do not identify faces. If the evidence is not visible, do not invent a violation.
Analyze the sequence, then return ONLY a JSON object with this schema:
{"positive": true or false, "timecode_sec": seconds of strongest visible evidence or null, "event_type": "short observable event label or none", "observation": "brief visible evidence, or no concrete visible violation"}.
Use a single strongest event for this baseline. A positive is a cue for human review, not a legal conclusion.'''


def parse_result(text, duration):
    match = re.search(r'\{.*\}', text, re.S)
    if not match:
        raise ValueError('No JSON object')
    result = json.loads(match.group())
    if type(result.get('positive')) is not bool:
        raise ValueError('positive must be boolean')
    stamp = result.get('timecode_sec')
    if result['positive']:
        result['timecode_valid'] = isinstance(stamp, (int, float)) and not isinstance(stamp, bool) and 0 <= stamp <= duration
    else:
        result['timecode_sec'] = None
        result['timecode_valid'] = True
    return result


def load_qwen():
    from transformers import Qwen3VLForConditionalGeneration, AutoProcessor
    path = ROOT / 'models/qwen3-vl-8b'
    model = Qwen3VLForConditionalGeneration.from_pretrained(path, dtype=torch.bfloat16, device_map='cuda', attn_implementation='sdpa', local_files_only=True).eval()
    processor = AutoProcessor.from_pretrained(path, local_files_only=True)

    def infer(item):
        content = [{'type': 'text', 'text': PROMPT}]
        for frame in item['frames']:
            content.extend([{'type': 'text', 'text': f"Timestamp {frame['timestamp_sec']:.2f} sec:"},
                            {'type': 'image', 'image': Image.open(ROOT / frame['path']).convert('RGB')}])
        inputs = processor.apply_chat_template([{'role': 'user', 'content': content}], tokenize=True, add_generation_prompt=True, return_dict=True, return_tensors='pt').to(model.device)
        with torch.inference_mode():
            generated = model.generate(**inputs, do_sample=False, max_new_tokens=256)
        return processor.batch_decode(generated[:, inputs['input_ids'].shape[1]:], skip_special_tokens=True)[0]
    return infer


def load_internvideo():
    from transformers import AutoModel, AutoTokenizer
    from torchvision import transforms as T
    path = ROOT / 'models/internvideo25_8b'
    tokenizer = AutoTokenizer.from_pretrained(path, trust_remote_code=True, local_files_only=True)
    model = AutoModel.from_pretrained(path, torch_dtype=torch.bfloat16, low_cpu_mem_usage=True, trust_remote_code=True,
                                      use_flash_attn=False, local_files_only=True).eval().cuda()
    transform = T.Compose([T.Resize((448, 448), interpolation=T.InterpolationMode.BICUBIC), T.ToTensor(),
                           T.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225))])

    def infer(item):
        frames = item['frames']
        pixels = torch.stack([transform(Image.open(ROOT / f['path']).convert('RGB')) for f in frames]).to(device='cuda', dtype=torch.bfloat16)
        prefix = ''.join(f"Frame{i+1}, timestamp {f['timestamp_sec']:.2f} sec: <image>\n" for i, f in enumerate(frames))
        with torch.inference_mode():
            return model.chat(tokenizer, pixels, prefix + PROMPT,
                              dict(do_sample=False, max_new_tokens=256, num_beams=1), num_patches_list=[1] * len(frames))
    return infer


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', choices=['qwen', 'internvideo'], required=True)
    parser.add_argument('--limit', type=int)
    args = parser.parse_args()
    torch.set_num_threads(8)
    manifest = json.loads((ROOT / 'artifacts/video_manifest.json').read_text())
    items = [x for x in manifest if not x.get('duplicate_of')]
    if args.limit:
        items = items[:args.limit]
    folder = ROOT / 'artifacts/benchmark' / args.model
    folder.mkdir(parents=True, exist_ok=True)
    config = {'model': args.model, 'prompt': PROMPT, 'prompt_sha256': hashlib.sha256(PROMPT.encode()).hexdigest(),
              'frames_per_video': 48, 'sampling': 'uniform, independent of labels', 'dtype': 'bfloat16',
              'max_new_tokens': 256, 'do_sample': False, 'offline': True}
    import transformers
    config.update(torch_version=torch.__version__, transformers_version=transformers.__version__,
                  checkpoint_revision={'qwen': '0c351dd01ed87e9c1b53cbc748cba10e6187ff3b',
                                       'internvideo': '87680fe232af8681b55322f68541679b91f99df1'}[args.model])
    (folder / 'config.json').write_text(json.dumps(config, indent=2))
    infer = load_qwen() if args.model == 'qwen' else load_internvideo()
    print('MODEL_READY', args.model, flush=True)
    for index, item in enumerate(items):
        target = folder / (item['sha256'] + '.json')
        if target.exists() and json.loads(target.read_text()).get('status') == 'done':
            continue
        start = time.monotonic()
        record = {'id': item['id'], 'sha256': item['sha256'], 'model': args.model}
        try:
            raw = infer(item)
            record['raw_output'] = raw
            record['prediction'] = parse_result(raw, item['duration_sec'])
            record['status'] = 'done'
        except Exception as exc:
            record['status'] = 'failed'
            record['error_class'] = type(exc).__name__
            record['error'] = str(exc)
            torch.cuda.empty_cache()
        record['elapsed_sec'] = time.monotonic() - start
        target.write_text(json.dumps(record, ensure_ascii=False, indent=2))
        print(f"PROGRESS {args.model} {index+1}/{len(items)} {item['id']} {record['status']} {record['elapsed_sec']:.1f}s", flush=True)
        if record['status'] == 'failed' and index == 0:
            raise RuntimeError('First inference failed; see local error artifact')


if __name__ == '__main__':
    main()
