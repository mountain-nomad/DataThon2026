## Update `/demo-inference` — AI Inference Flow

Update the existing page without redesigning its overall style. Use the existing design skills and components.

### 1. Video Upload

After uploading a `.mov` file, immediately display the original CCTV video.

Below it, show **4 circles connected by a horizontal line**:

`Uploaded Video → Scenario Recognition → Violation Recognition → Violation Localization`

The first circle represents the input. The remaining three are AI inference stages.

### 2. Correct Scenario Classification

Stage 1 must use exactly these 7 scenario classes from the actual AI router:

1. **ENTRY** — Вход в кабинет
2. **COUNTING / DEPOSIT WITHOUT CLIENT** — Самостоятельный подсчёт и внесение без клиента
3. **CLIENT CASH DEPOSIT** — Подсчёт суммы и внесение с клиентом
4. **COUNTING FROM SAFE** — Подсчёт суммы из сейфа
5. **OPENING A CASH BAG** — Получение денег из мешка
6. **RECEIVING A BAG FROM CLIENT** — Получение мешка от клиента
7. **EXIT / CLOSING** — Выход из кабинета

The router may return one or two candidate classes. Display the primary scenario and secondary candidate if available.

### 3. Correct Violation Recognition

Stage 2 must only display violations applicable to the classified scenario, based on the provided specialist prompts.

Examples:

- **ENTRY:** Client enters restricted area; door left open after entry; personal belongings placed on work desk.
- **COUNTING / DEPOSIT WITHOUT CLIENT:** No predefined confirmed violation types in the provided examples. Do not invent violations.
- **CLIENT CASH DEPOSIT:** Missing mandatory document check; cash not placed into safe; client leaves before cash is secured; skipped required banknote verification; other violations explicitly supported by the specialist.
- **COUNTING FROM SAFE:** Safe remains open after the cashier takes money and proceeds to counting.
- **OPENING A CASH BAG:** Money placed in safe without mandatory prior counting; bag requiring secure storage left outside the safe when cashier leaves.
- **RECEIVING A BAG FROM CLIENT:** Cashier accepts bag without mandatory document verification.
- **EXIT / CLOSING:** Equipment left on; key left in safe lock; cash, stamps or accounting notebook left on desk when cashier departs.

Use the exact returned specialist results, including `rule_id`, `quote`, `evidence`, `start_sec`, `end_sec` and `status`.

Do not invent violations, descriptions or timestamps. If the result is `no_violation` or `insufficient_evidence`, display that outcome instead.

### 4. Progress Animation

Keep the **4-circle horizontal progress indicator**.

- Initially, only Uploaded Video is completed.
- Each stage activates sequentially, from left to right.
- The thin connecting line becomes thicker with an animated flowing wave.
- The completed line fills with a **white → forte-red gradient**.
- Completed circles transition to forte-red backgrounds with white text.
- Inactive circles have white backgrounds and black text.

**Strict design principles:**
- Forte-red background = white text.
- White background = black text.

Show the three inference results **vertically stacked, one below another**, appearing progressively:

**01 — Scenario Recognition**

Result: `CLIENT CASH DEPOSIT`

**02 — Violation Recognition**

Result: `Cashier failed to place received cash into the safe before completing the operation.`

**03 — Violation Localization**

Result: `00:44.2`

These are illustrative UI values, not fixed inference outputs.

Keep all previous results visible as new stages complete.

If backend stage-by-stage progress is unavailable, the sequential animation may visualize presentation of the completed result, but must not imply actual processing milestones.

### 5. Final Video Transformation

Once Stage 3 completes **and a violation is detected**, animate the video container into a two-column layout.

**Left:** Original uploaded video, smoothly shrinking while preserving its aspect ratio.

**Right:** New mini-video showing the localized violation episode.

- Use the detected `start_sec` / `end_sec` to identify the relevant segment.
- Display the violation timestamp.
- Highlight the relevant moment on the video timeline.
- Both videos remain playable independently.
- If multiple violations exist, allow selecting the violation to preview.
- If a localized clip is unavailable, display the evidence frame instead.

If no violation is detected, keep the original single-video layout and show the clean result.

### 6. Important UX Requirements

- Preserve the existing page structure and design system.
- Do not redesign unrelated pages.
- Prioritize horizontal CCTV video aspect ratios, using `object-fit: contain`.
- Make the three AI stages visually clear and progressive.
- Use actual scenario names and violation types from the provided pipeline.
- Preserve the animated gradient, wave-like line thickening and circle color transitions.
- Keep the video transformation smooth and visually polished.

**The intended experience: Upload Video → Watch AI Progress → See Three Stacked Results → View Original and Localized Violation Side by Side.**