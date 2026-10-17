# Task for the receiving AI agent

Read README.md. Reproduce the provided Qwen3.8 pipeline with recipient-owned videos and the exact checkpoint revision. Use the recorded NF4/BF16 load configuration, native video metadata, sampling, prompts and greedy generation. Do not train, tune against labels, add expected answers by filename, or substitute a prequantized checkpoint.

1. Inspect the local GPU, Python/CUDA and installed package versions; report differences from configs/runtime.json and requirements.txt.
2. Point models/qwen38_27b at the supplied checkpoint or download the pinned official revision separately.
3. Run the local tests and scripts/run_pipeline.py in a fresh output directory.
4. Confirm synthetic color control, JSON validity, source timestamps and one real JPEG per finding. Keep raw responses and exact prompts.
5. Compare outputs on the user's videos; distinguish observable facts from missing observations. Never infer a safe deposit solely from movement near a safe, or device power state solely from lid position. Do not turn an unsupported violation into a generic warning.
6. Return paths to the readable report and public JSON files, actual statuses and remaining errors. Do not claim the historical 97.5% unless evaluated on the original deduplicated dataset and labels supplied separately.

No video, model, frame, base64 result or token should be committed. This package is an offline reproduction CLI, not the backend HTTP integration.
