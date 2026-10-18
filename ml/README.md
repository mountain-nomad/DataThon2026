# Qwen3.8 cashier-video pipeline: minimal reproduction

This folder contains source code, exact prompt snapshots, regulation text, model configuration and environment pins. Supply your own videos and checkpoint. No video, image, model weight, ground truth, prediction, base64 evidence or access token is included.

The pipeline is an offline CLI. It does not change the existing backend/frontend or start an HTTP service.

## Model and environment

- Official checkpoint: `Qwen/Qwen3.8-27B`, revision `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`.
- Place the original checkpoint, processor, tokenizer, chat template and generation configuration at `ml/models/qwen38_27b/`. A symlink to an existing local checkpoint is sufficient. The inference scripts use `local_files_only=True`.
- Original weights are quantized **at load time** with bitsandbytes: 4-bit NF4, double quantization, BF16 compute. This is not an AWQ/GPTQ/GGUF checkpoint. `AutoModelForImageTextToText`, BF16, CUDA, SDPA, `.eval()`.
- Reference: Python 3.12.3, Torch runtime `2.12.0+cu130`, Transformers 5.11.0, RTX 5090 32 GB. `requirements.txt` records installed package metadata; Torch's distribution metadata reports 2.12.0 while its runtime includes `+cu130`. Use the matching CUDA-enabled wheel, not a CPU wheel. Allow VRAM headroom for video inputs.
- One process, no batching, 8 CPU threads, seed 0, greedy generation (`do_sample=False`), no thinking. Temperature/top_p/top_k are not explicitly supplied. Do not substitute `temperature=0` for the recorded call.
- `linear_attention=auto`; the reference machine used the Torch fallback. Do not add FLA/causal-conv1d/torch.compile for the first reproduction.

The checkpoint can be downloaded separately, outside inference:

```python
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id="Qwen/Qwen3.8-27B",
    revision="1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0",
    local_dir="models/qwen38_27b",
)
```

## Run

All commands below run from this `ml/` directory. Prepare Python 3.12 and the recorded CUDA-enabled Torch wheel, then install the remaining dependencies into an isolated environment:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -c 'import torch; print(torch.__version__, torch.version.cuda); assert torch.cuda.is_available()'
.venv/bin/python scripts/run_pipeline.py --video-dir /absolute/path/to/your/videos --output-dir artifacts/repro_run_01
```

To run only selected files, add `--ids` with their exact filename stems (Latin `X` and Cyrillic `Х` differ):

```bash
.venv/bin/python scripts/run_pipeline.py --video-dir /absolute/path/to/videos --ids clip_a clip_b --output-dir artifacts/repro_run_02
```

Use a **new output folder** for every comparison. The historical router runner skips completed records. The bootstrap generates local runtime metadata from your videos and configuration seeds; generated `artifacts/`, caches, frames and models are ignored by Git. Byte-identical video duplicates are processed once. There are no labels or filename-specific expected answers.

Outputs:

- `artifacts/repro_run_01/router/`: raw operation codes and checkpoint/config provenance.
- `artifacts/repro_run_01/timelines/current_outputs.md`: final observation timelines.
- `artifacts/repro_run_01/final/current_outputs.md`: readable audit.
- `artifacts/repro_run_01/final/results/*.json`: API results with one actual JPEG/base64 evidence frame per finding.
- `raw/`, `prompts/` and `records/` inside stage directories preserve model outputs, actual prompts and metadata.

The model loader runs a red-to-blue synthetic video check before real video inference. It must pass.

## Exact stages and sampling

1. **Router v2:** decode with PyAV, first video stream, `thread_type="AUTO"`; sample 1 fps using original PTS relative to `stream.start_time`; resize proportionally to at most 768×768 without enlargement; JPEG quality 95. If more than 48 samples, select `np.linspace(0,n-1,48).round().astype(int)`; duplicate the final sample if the count is odd. Whole video in one request. Native `VideoMetadata` contains original fps, original decoded indices, original duration and `round(duration*fps)`. `do_sample_frames=False`. Greedy, 2 new tokens, one/two class digits. `prompts/router_v2.txt` is byte-exact and hash-checked.
2. **Video → observations:** full-frame PNG cache at 5 fps, no crop or thumbnail; timestamps relative to the first decoded frame. At most 130 evenly selected samples per request, even padding. Processor total video pixel budget 56,000,000 (`shortest_edge=4096`); native processor still resizes/normalizes. Greedy, 4096 new tokens. Long clips (>30 sec) receive extra dense reviews around *detected* client arrivals: 1.5 sec before to 24 sec after, bounded by the next arrival and clip end. Whole-video observations are supplied as fallible context. Outside-window observations are retained; reviewed events replace events within the window; source times are preserved. No client detected means no arrival review, including for a long clip. This is not exhaustive sliding-window coverage of every long video.
3. **Object reconciliation (txt2txt):** one text request after each video pass, 4096-token budget; preserve event count, times, actions and directions. General prompt convention per client: two separate incoming transfers → ID then money; one → money; counter-loaded object → money. Returns/repeated movements/bundle portions are not new incoming transfers. This is an explicit domain assumption, not visual proof of identity. Code does not relabel objects from counts. Nearby movement is not automatically placement inside the safe. Use “client” without unnecessary numbering.
4. **Final audit (txt2txt):** combine all rules for the one/two routed categories in one input. Preserve excerpt handling, rule scopes and false-positive exceptions. JSON schema constrains structure; original catalogue IDs and event times constrain references. A brief service `evidence_check` precedes findings; verdict is generated last. Descriptions have a **prompt-only** target of about 150 tokens; no hard description-length limit or silent truncation. `enable_thinking=False` remains in effect; the service summary is not a hidden thinking mode.
5. **On-demand quality repair:** default `--review-mode on-demand` first produces the usual single audit response. If its description contains self-dialogue markers (for example rhetorical questions or “давайте проверим”), save that initial answer and run a short candidate pass (512 tokens), then a separate evidence review (1536). Ordinary outputs stay on the one-call path. This textual detector is a heuristic: it does not detect every semantic error. `--review-mode always` is available for diagnostics. Rules about money do not apply to keys simply because both are valuable; missing evidence of device shutdown does not prove the device was left on.
6. **Evidence/export:** code attaches exactly one real JPEG, selected nearest to the first finding event (earlier sample wins ties). Public `timecode_sec` equals its `timestamp_sec`. Public JSON has `job_id`, `status`, `verdict`, `violations`; each finding has `type`, `timecode_sec`, `description`, `evidence_frames`. Warnings use `ПРЕДУПРЕЖДЕНИЕ:` and also produce `verdict=violation` per the API contract. Internal evidence summaries, rule IDs and limitations stay in records/readable reports, outside the public JSON.

## Prompt locations and scope

`prompts/` contains the router, video observations, object reconciliation, final audit and optional candidate/review instructions. `scenario (2).md` contains all seven regulation sections, exact ideal steps, typical violations and false-positive exceptions. `configs/runtime.json` lists settings; `configs/source_sha256.json` identifies the source snapshot.

For the non-router stages, Python constants in `scripts/context_object_timelines.py` and `scripts/final_text_audit.py` are the executable prompts. The text files are reviewable snapshots, not runtime overrides. If changing them, update the source constants and snapshots together. Router text is copied by bootstrap and hash-checked against the recorded reference.

Supporting historical source files are included because the current implementation imports their model loader, frame utilities and rule catalogue functions. Run the Qwen commands above, not the unrelated legacy benchmark/model modes.

## Reproduce a final audit only

After a complete run, reuse its saved timelines and router provenance:

```bash
.venv/bin/python scripts/final_text_audit.py --ids clip_a clip_b --timeline-dir artifacts/repro_run_01/timelines --router-dir artifacts/repro_run_01/router --output-dir artifacts/final_only_run_02 --review-mode on-demand
```

## Validation and limits

```bash
.venv/bin/python -m unittest discover -s scripts -p 'test_*.py' -q
```

The router historically scored **39/40 (97.5%)** on one dataset. Those videos, labels and predictions are excluded, so this package alone cannot verify that percentage. The timeline/final-audit prompts and on-demand quality repair are later experiments, not the historical routing metric. Two-pass review tests removed the long self-dialogue and money/keys confusion in the observed problematic output, but a residual warning based on an unobserved counting step remained questionable. Do not treat JSON validity, brevity or repair as proof of factual accuracy. Report actual outputs and differences without editing answers to match expectations.

## Local API catalogue and legal formatting (18 October 2026)

The deployed local integration adds a reviewed fixed catalogue in `configs/finding_types.json` for all 70 scenario rules. Final `type` generation is constrained to catalogue strings; validation rejects a type that belongs to a different rule. The backend validates the same pair again. This prevents arbitrary type names; it does not establish factual correctness of a finding. Free observation text remains model-generated.

The operation router now masks generation to the seven class tokens, allows EOS only after a class and forbids repeated class digits. This is a decoding change from the historical router; its old accuracy figure has not been re-evaluated for this implementation. Synthetic video control remains enabled.

Internal rule IDs and model limitations are passed to the backend without changing the public JSON shape. The backend adds blank lines before `Ограничения:` and, only if a suitable verified official source is mapped, `Источник:`. Unmapped types remain valid and get no source line. See `../deploy/legal_mapping_review.md` and `../backend/legal_source_checks.json`. Historical runs were preserved.
