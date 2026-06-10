# Revision diff audit: before -> current manuscript

Дата аудита: 2026-06-05.

Этот файл нужен как рабочая карта для ручного переписывания статьи. Он не предлагает "обходить" детекторы. Идея другая: вернуть авторский голос и сохранить научно полезные уточнения из текущей версии, не превращая текст в стерильно сглаженный AI-polished академический регистр.

## 1. Источники сравнения

**Before source.** Основной before-текст: `1c6dafe:academic_paper/paper.tex`, коммит `1c6dafef94b7669b5ace4a1ee9929bdf84b930b2`, дата `2026-05-19`.

**PDF copy.** Файл `.tmp/before.pdf` был извлечен в `.tmp/before.txt` через `pdftotext`. Из-за IEEE двухколоночной верстки порядок строк в PDF-тексте частично ломается, поэтому проверка делалась не по полному порядку строк, а по редким фразам и n-граммам. PDF намного ближе к `1c6dafe`, чем к текущему `paper.tex`: 5-граммное покрытие old TeX токенами PDF около `0.517`, для current около `0.129`.

**Старый edit artifact.** `academic_paper/article_prose_edit.md` существовал в `bfa5c0b`, но был удален позже. Он полезен как ручной prose-edit черновик, однако не полностью совпадает с `.tmp/before.pdf`: например, в abstract у него было `kinds of content`, а в PDF и `1c6dafe` уже `types of content`. Поэтому главным before считается `1c6dafe`, а prose-edit - вспомогательным артефактом.

**After source.** Текущая статья: `academic_paper/paper.tex`, дата файла `2026-05-29`, подключается через `academic_paper/main.tex`.

**Объем изменения.** По `git diff 1c6dafe -- academic_paper/paper.tex academic_paper/references.bib`: `107 insertions`, `63 deletions`. В `paper.tex`: `57 insertions`, `52 deletions`. В `references.bib`: `50 insertions`, `11 deletions`.

**Рабочие before-файлы для ручной правки.**

- `academic_paper/rewrite_workspace/before_1c6dafe_paper.tex`: точный TeX из `1c6dafe:academic_paper/paper.tex`.
- `academic_paper/rewrite_workspace/before_1c6dafe_prose_edit.md`: сгенерированная prose-edit версия из того же `1c6dafe`, без LaTeX таблиц, фигур, формул, алгоритмов и преамбулы.
- `academic_paper/rewrite_workspace/historical_article_prose_edit_bfa5c0b.md`: старый исторический prose-edit artifact из `bfa5c0b`. Он удобен как reference, но не является точным before после мелких Overleaf/ручных исправлений.

## 2. Главный вывод

After-версия стала научно осторожнее и сильнее по validity, но почти везде поменяла фактуру авторского голоса на ровную, безопасную, обобщающую академическую прозу. Наиболее полезные новые идеи: ограничения метрик, различение temporal coverage и semantic quality, B0/B1 comparison, источник для reusable OER/accessibility metadata, W3C media requirements, ASR confidence not WER/CER, user-level validation caveats, source provenance limitation, hosted-service risks.

Наиболее рискованные для "AI-like" звучания места: abstract, related work, formal metrics, threats to validity, conclusion. Не потому что они плохие научно, а потому что они теперь слишком чисто формулируют ограничения и выводы, часто через одинаковую структуру: "X is not Y", "should not be interpreted as", "future work should". Это стоит переписать вручную, сохранив смысл.

## 2.1 Фидбек руководительницы как критерий after-правок

Фидбек руководительницы объясняет почти все полезные добавления в after-версии. То есть задача не в том, чтобы механически откатить after. Оптимальнее взять before-голос и вручную заново закрыть эти пункты:

1. **Заключение слишком короткое.**
   - After закрыло это хорошо: conclusion стало 3 абзаца и содержит ключевые результаты.
   - Риск: оно стало самым шаблонным местом статьи.
   - Что делать: сохранить трехчастную логику conclusion, но переписать от себя: artifact contribution, exact benchmark results, future validation.

2. **Осторожнее claims про accessibility, ADHD, dyslexia, neurodivergent learners.**
   - After закрыло это хорошо: добавлены `design affordances`, `not evidence of user-level benefit`, `future validation`, expanded threats.
   - Риск: слишком много одинаковых negative disclaimers.
   - Что делать: оставить ограничение один раз в abstract, один раз в metrics/threats, один раз в conclusion. В остальных местах писать короче.

3. **Подробнее описать corpus: duration, criteria, total duration, content types, sources, language distribution.**
   - After закрыло это лучше всего: добавлены total duration, minutes by language, buckets, content types, normalization and provenance limitation.
   - Что делать: сохранить почти полностью. Это конкретные данные, они не выглядят как пустое сглаживание.
   - Не пытаться полностью закрывать в текущем лимите: ~~полная source provenance / license table для каждого видео~~. After этого не сделал; достаточно явно назвать source provenance limitation и оставить полный provenance как future work.

4. **ASR confidence не полноценная метрика транскрипции.**
   - After частично закрыло: добавлен caveat и `Machacek2023`, но WER/CER или ручная проверка не добавлены как результат.
   - Что делать: честно писать, что WER/CER не reported due to no manually verified transcripts.
   - Не пытаться закрывать в текущем лимите: ~~добавить полноценные WER/CER~~ и ~~ручную проверку части данных как новый результат~~. After этого не сделал; без новой разметки это нельзя честно добавить. Достаточно limitation/future work.

5. **Coverage15s это temporal coverage, не quality of visual descriptions.**
   - After закрыло хорошо: coverage переименовано в temporal coverage и объяснен смысл метрики.
   - Что делать: сохранить, но не повторять `not quality` во всех секциях одинаковыми словами.
   - Не пытаться закрывать в текущем лимите: ~~добавить экспертную оценку visual descriptions~~ и ~~добавить полноценную qualitative evaluation как новый результат~~. After этого не сделал; можно только честно сказать, что selected cases illustrate failure modes, not description quality.

6. **Объяснить thresholds 15s and 30s.**
   - After закрыло частично: 30 s tolerance is guard against stale description; 15 s radius is half of 30 s uniform-grid reference.
   - Что делать: сохранить оба объяснения. Можно добавить одну авторскую фразу: 30 s выбран как conservative maximum for nearest-scene lookup in this prototype, а 15 s как evaluation radius aligned with that tolerance.

7. **Related Work усилить audio description, visual accessibility, accessible video players.**
   - After закрыло частично: добавлены W3C media requirements and `Natalie2021`.
   - Что делать: сохранить. Если есть место, раскрыть W3C как источник про player controls/navigation/configurable presentation.
   - Не пытаться закрывать в текущем лимите: ~~делать отдельный развернутый обзор accessible video players~~. After этого не сделал; для 6 страниц достаточно W3C + audio/scene description source.

8. **Убрать разговорные формулировки и заменить научными.**
   - After выполнило это чрезмерно.
   - Что делать: не возвращать явные ошибки и разговорность, но вернуть авторскую прямоту. Цель: academic, not sterile.

## 3. Полностью новое содержание, которое стоит сохранить

Ниже перечислены новые содержательные добавления, которых не было в before или которые были существенно расширены.

1. **Abstract: более честная интерпретация player features.**
   - Новая мысль: keyboard-first, ARIA, configurable text, word highlighting являются design affordances, а не доказательством user-level benefit.
   - Рекомендация: сохранить. Переписать менее шаблонно, например через "I treat these as implementation affordances, not as evidence that users benefited".

2. **Abstract: B0 mean RTF = 0.193.**
   - Новая мысль: after прямо сравнивает B1 mean RTF `0.433` с B0 mean RTF `0.193`.
   - Рекомендация: сохранить как конкретный числовой результат.

3. **Abstract: coverage is temporal coverage, not quality.**
   - Новая мысль: `91.7% 15-second scene coverage` теперь объясняется как temporal coverage of indexed scene anchors, not description quality or accessibility impact.
   - Рекомендация: обязательно сохранить. Это снижает риск overclaiming.

4. **Introduction: добавлен источник `IngavelezGuerra2022`.**
   - Новая мысль: end-to-end artifact generation связан с automatic adaptation of OER, special needs, AI and accessibility metadata.
   - Рекомендация: сохранить ссылку, но вручную вплести ее в более живой контекст.

5. **Related Work: W3C media accessibility sources.**
   - Новые ссылки: `W3CMediaReqs`, `W3CMediaAccessible`.
   - Новая мысль: требования включают descriptions, navigation, playback control, configurable presentation, а не только captions.
   - Рекомендация: сохранить, так как это делает related work точнее.

6. **Related Work: ASR confidence is not WER/CER.**
   - Новая ссылка: `Machacek2023`.
   - Новая мысль после проверки PDF: source is mainly about Whisper-Streaming, real-time transcription, latency, and WER-based evaluation on manually transcribed data. It supports WER as an ASR quality metric and the need for reference transcripts in that evaluation setup, but it is not a direct source for the generic claim "ASR confidence is not a substitute for WER/CER".
   - Рекомендация: do not force `Machacek2023` into `p013` unless discussing real-time/streaming Whisper. Put the WER/no-reference limitation in Formal Metrics or Threats, phrased as this study's methodological boundary.

7. **Related Work: scene description quality criteria.**
   - Новая ссылка: `Natalie2021`.
   - Новая мысль после проверки PDF: article evaluates ViScene, a collaborative scene-description authoring tool, and uses a nine-code quality codebook: Descriptive, Objective, Succinct, Learning, Sufficient, Accurate, Referable, Interest, and Clarity. Their results suggest novice authors with feedback can produce SDs strong in Descriptive, Objective, Referable, and Clear/Clarity dimensions, while some dimensions such as Learning and Sufficient remained lower.
   - Рекомендация: сохранить источник, но не писать, что он просто требует "accurate, objective, succinct, useful" descriptions. Более валидная мысль для нашей статьи: scene-description quality is multifaceted and cannot be inferred from temporal coverage alone.

8. **Methodology: corpus duration and composition.**
   - Новые данные: `11,856.82 s`, `197.61 min`, `3.29 h`, `99.28 min English`, `98.33 min Russian`, `8 videos per duration bucket`, `6 videos per content type`, detailed minutes by bucket and content type.
   - Рекомендация: сохранить почти полностью. Это конкретика, а конкретика обычно звучит человечески и научно.

9. **Methodology: source provenance limitation.**
   - Новая мысль: mixed public and curated educational sources, normalized to `1280x720` at `30 FPS`, clean-audio labels, source provenance is a limitation.
   - Рекомендация: сохранить. Но фразу `Source provenance is therefore a limitation` можно переписать менее автоматично.

10. **Formal Metrics: metrics are engineering proxies.**
    - Новая мысль: RTF, confidence and coverage are not direct learning/accessibility outcomes.
    - Рекомендация: сохранить, потому что это защищает статью от завышенных claim-ов.

11. **Formal Metrics: exact definition of coverage radius.**
    - Новая мысль: `coverage_15s` is proportion of evaluated video span within 15 s of indexed scene timestamp; 15 s is half of the 30 s uniform-grid reference.
    - Рекомендация: сохранить, возможно сделать короче.

12. **Automation protocol: run rejection and cache-aware evaluation.**
    - Новая мысль: driver rejects non-positive runtimes, missing rows, out-of-range coverage; valid artifacts are reused.
    - Рекомендация: сохранить как reproducibility detail.

13. **Qualitative case selection: failure modes, not validation.**
    - Новая мысль: selected cases illustrate failure modes but do not validate semantic correctness or accessibility benefit.
    - Рекомендация: сохранить.

14. **Results: temporal coverage language.**
    - Новая версия систематически заменяет `coverage` на `mean temporal coverage`.
    - Рекомендация: сохранить терминологическую точность, но не повторять `temporal` механически в каждом абзаце.

15. **Interactive TTS: micro-benchmark softened.**
    - Before утверждал median `2682.6 ms` и cache `0.06 ms` более прямо. After делает это spot-check, indicative, not rigorous benchmark.
    - Рекомендация: если цифры получены реальным скриптом, можно вернуть цифры, но оставить предупреждение, что это preliminary spot-check.

16. **Discussion: hosted-service risks.**
    - Новая мысль: hosted multimodal and TTS services introduce model drift, rate limits, cost, network latency; open-weight replacement needs separate evaluation.
    - Рекомендация: сохранить.

17. **Threats: user validity.**
    - Новая мысль: prototype was not evaluated with disabled, DHH, blind/low-vision, ADHD, dyslexic, or neurodivergent learners.
    - Рекомендация: обязательно сохранить, но можно сделать тон менее blanket-disclaimer.

18. **Conclusion: results and future work are now explicit.**
    - Новая мысль: conclusion now repeats exact B1/B0 RTF, coverage, fixed caps, semantic review needs, user group/expert evaluation, larger corpus provenance.
    - Рекомендация: сохранить skeleton, переписать живее и менее textbook-like.

## 4. Новые references

Добавлены:

- `@IEEEtranBSTCTL{IEEEexample:BSTcontrol}`: техническая настройка IEEE bibliography.
- `W3CMediaReqs`: W3C Media Accessibility User Requirements, 2015.
- `W3CMediaAccessible`: W3C Making Audio and Video Media Accessible, 2024.
- `IngavelezGuerra2022`: automatic adaptation of OER with preferences, special needs, AI and accessibility metadata.
- `Machacek2023`: Whisper real-time transcription system; useful for ASR/streaming context and for noting that WER-based evaluation relies on reference transcripts. It should not be treated as a direct source for "ASR confidence is not WER/CER".
- `Natalie2021`: collaborative authoring of video scene descriptions; useful for the claim that scene-description quality is multifaceted and can be evaluated through a codebook rather than inferred from temporal coverage.

Удален:

- `CastroAlonso2021`: cognitive load strategies. Если related work по cognitive load станет тоньше после ручной переписки, можно вернуть этот источник, но current version уже опирается на Mayer/Lange/Kruger/LeCunff/Horlin.

## 5. Подробная карта по секциям

### Abstract

**Current location:** `paper.tex:33-36`.

**Тип изменения:** heavy rewrite + new caveats.

**Before смысл:** широкое вступление про online learning, accessibility standards, people with disabilities, pipeline, player features, corpus, ASR confidence, RTF, coverage, adaptive heuristic.

**After смысл:** короче и точнее: educational videos are central; pipeline generates artifacts; player controls are affordances, not user benefit; B1 faster than real time; B0 mean RTF included; coverage is temporal, not quality; stronger claims need validation.

**Что сохранить:** B0 comparison, distinction between affordance and evidence, temporal coverage caveat, validation caveat.

**Что переписать вручную:** opening sentence and final sentence. Текущий abstract очень гладкий: `central to online learning`, `limited support`, `design affordances`, `stronger accessibility claims`. Это звучит академично, но без авторской шероховатости. Лучше начать ближе к конкретной проблеме: captions, visual context and navigation are generated separately or missing.

### Introduction

**Current location:** `paper.tex:42-54`.

**Тип изменения:** old text cleaned; one new citation and reframing.

**Перефразированные места:**

- `professional growth` -> `professional development`
- `video-centric format of education became dominant` -> `video-centric learning has become routine`
- `unfairly accessible` -> `accessibility barriers`
- `accessibility as an end-to-end pipeline problem` -> `artifact generation as an end-to-end pipeline problem`
- `stable timing quality` -> `stable timing behavior`
- `complete coverage` -> `temporal coverage of low-variance content`

**Новое содержание:** `IngavelezGuerra2022` citation; contribution 3 now says user-level validation is future work.

**Что сохранить:** framing around artifact generation and future user validation.

**Что вернуть ближе к before:** current version is semantically safer, but it removed your more direct problem statement. Good compromise: use a human sentence with a concrete reason: "The prototype does not try to prove that these controls improve learning; it asks whether the artifacts needed for such controls can be produced consistently."

### Related Work: Captions and Learning Accessibility

**Current location:** `paper.tex:58-59`.

**Тип изменения:** heavy rewrite + new W3C sources.

**Before смысл:** captions benefit not only neurodivergent or impaired learners; auto subtitles work; alignment matters; WCAG guidance; gap is isolated captions.

**After смысл:** captions benefit diverse users; automated subtitles can be useful; W3C requirements include captions, descriptions, navigation, playback control, configurable presentation; gap is isolated player features instead of reusable artifacts generated in one pass.

**Новое содержание:** `W3CMediaReqs`, `W3CMediaAccessible`.

**Риск:** phrase `these requirements are often implemented as isolated player features rather than...` is clean but generic. It can read like a default related-work gap sentence.

**Ручная rewrite target:** keep W3C expansion, but ground the gap in the prototype: "For this prototype, the relevant gap is not only whether a player can show captions, but whether the processing step can generate the caption, navigation and description artifacts together."

### Related Work: Cognitive Load and Neurodiversity

**Current location:** `paper.tex:61-62`.

**Тип изменения:** strong smoothing + stronger limitation.

**Before смысл:** pacing, signaling, learner control; media quality affects learning; cognitive load is hard to measure; neurodiversity-focused research mentions transcription and navigation barriers; gap is automatic generation of supports.

**After смысл:** same literature but gap changed: literature motivates control and structure, but does not validate this prototype for ADHD, dyslexia, or neurodivergent learners.

**Что сохранить:** explicit validation limit. It is scientifically important.

**Что проверить:** old gap about "generated automatically as reusable artifacts" is useful and got lost. Consider combining both: literature motivates the controls, while this paper only tests artifact generation, not learner benefit.

### Related Work: ASR and Timestamping

**Current location:** `paper.tex:64-65`.

**Тип изменения:** new caveat inserted.

**Новое содержание:** After inserted an ASR confidence/WER caveat with `Machacek2023`, but the source is primarily about Whisper-Streaming and evaluates ASR quality with WER on manually transcribed data.

**Что сохранить:** keep the caveat somewhere, because it protects metric interpretation. But `p013` should stay focused on ASR/timestamping foundations; the no-WER limitation belongs in Formal Metrics or Threats.

**Риск:** the paragraph now has two different jobs: literature review and metric warning. It may be better to keep a short ASR related-work paragraph and put the confidence/WER caveat in Formal Metrics plus Threats.

### Related Work: Visual Accessibility and Audio Description

**Current location:** `paper.tex:67-68`.

**Тип изменения:** new paragraph opening + reference.

**Новое содержание:** Audio/scene description gives access to visual information absent from the audio track. After cited `Natalie2021`, but the PDF shows a more specific contribution: ViScene, a collaborative SD authoring tool, a nine-code quality codebook, and findings that novice-authored SDs with feedback can be strong on Descriptive, Objective, Referable, and Clarity while other dimensions such as Learning and Sufficient may remain weak.

**Что сохранить:** keep `Natalie2021`, but use it as evidence that scene-description quality is multifaceted and needs separate evaluation. Do not reduce it to a generic "accurate, objective, succinct, useful" sentence.

**Риск:** phrase `provide access to visual information that is not available from the primary audio track` is true but very textbook. Можно оставить, но лучше добавить why it matters for this prototype: descriptions are linked to indexed scenes and requested on demand, not authored as professional AD.

### System Design: Pipeline Architecture

**Current location:** `paper.tex:70-82`.

**Тип изменения:** mainly terminology cleanup.

**Перефразировки:**

- `follows a Hybrid Multimodal Architecture` -> `uses a Hybrid Multimodal Architecture`
- `cognitively intensive tasks` -> `model-dependent visual description`
- `utilizing deterministic algorithms` -> `using deterministic algorithms`
- `enhance performance` -> `improve performance`

**Что сохранить:** `model-dependent visual description` is more precise than `cognitively intensive tasks`.

**Что можно вернуть:** this section is okay. It is not a main AI-detector risk because it is technical and specific.

### System Design: Interaction Layer

**Current location:** `paper.tex:86-91`.

**Тип изменения:** heavy rewrite.

**Before смысл:** midpoint word grouper used for karaoke highlighting; no overlap errors found, no generalization claim; custom subtitle renderer; on-demand AD finds nearest scene and uses TTS/cache.

**After смысл:** clearer algorithm: assign each word to segment containing temporal midpoint; no adjacent overlaps in corpus but diagnostic may not generalize; HTML5 track insufficient; custom renderer; 30 s tolerance avoids stale descriptions.

**Новое содержание:** exact explanation of midpoint assignment; 30 s tolerance as stale-description guard.

**Что сохранить:** midpoint definition and 30 s guard.

**Что переписать:** current text is concise but generic. You can keep it almost as is; add one human detail only if true, such as "This rule was chosen because the renderer needs one active segment per word, not because it solves every alignment case."

### Methodology: Prototype Configuration

**Current location:** `paper.tex:122-128`.

**Тип изменения:** caveat-oriented rewrite.

**Новое содержание:** reference transcription accuracy not evaluated; visual extraction describes visible text, layout and scene structure; adaptive uniform sampling targets temporal density, not semantic quality.

**Что сохранить:** all three caveats are valuable.

**Риск:** repeated `not evaluated`, `not semantic description quality` contributes to the after-version's cautious-machine tone. Keep the facts, vary the rhythm.

### Technical Evaluation: Corpus Benchmark

**Current location:** `paper.tex:131-159`.

**Тип изменения:** major new empirical detail.

**Новое содержание:** total duration, language minutes, duration/content balance, minute distribution, source provenance, normalization parameters.

**Что сохранить:** almost everything. This is concrete and defensible.

**Что переписать:** avoid over-smoothing phrases like `Source provenance is therefore a limitation of the current internal benchmark.` A more authorial version: "The corpus is useful for engineering comparison, but it is still an internal benchmark; I did not yet attach full source provenance and license metadata to every item."

### Technical Evaluation: Formal Metrics

**Current location:** `paper.tex:183-210`.

**Тип изменения:** new metric interpretation.

**Новое содержание:** engineering proxies; RTF is offline preprocessing throughput; confidence and low-confidence ratio are internal diagnostics; coverage is scene-anchor temporal proximity, not description quality; 15 s radius chosen as half of 30 s reference.

**Что сохранить:** all metric caveats. This is one of the strongest scientific improvements in after.

**AI-like risk:** this section has a cluster of detector-triggering academic caution formulas: `not direct measures`, `should not be interpreted`, `does not measure`, `should be read only as`. These are legitimate but repetitive.

**Ручная rewrite target:** combine caveats into fewer sentences with more concrete nouns. Example direction: "I use these metrics as engineering diagnostics. RTF says whether preprocessing is fast enough to be practical. Coverage says how often the player has a nearby scene anchor. Neither metric says whether a blind viewer would judge the description useful."

### Automation and Reproducibility Protocol

**Current location:** `paper.tex:212-215`.

**Тип изменения:** style smoothing + new validation details.

**Новое содержание:** driver rejects bad runs and reuses valid artifacts.

**Что сохранить:** yes. It is concrete and helps reproducibility.

**Риск:** low. This section can remain fairly technical.

### Post-hoc Scene-Selection Ablation

**Current location:** `paper.tex:217-218`.

**Тип изменения:** wording cleanup.

**Перефразировки:** `determine whether adaptive scene number selection behaviour would differ` -> `compare adaptive indexing with fixed scene budgets`.

**Что сохранить:** after wording is clearly better.

### Qualitative Case Selection

**Current location:** `paper.tex:220-223`.

**Тип изменения:** limitation added.

**Новое содержание:** cases illustrate failure modes but do not validate semantic correctness or accessibility benefit.

**Что сохранить:** yes.

**Риск:** similar to other caveats. If the same disclaimer appears too often, make this one shorter.

### Results: Aggregate Performance

**Current location:** `paper.tex:226-228`.

**Тип изменения:** minor but useful.

**Перефразировки:** `ASR component remains stable` -> `ASR diagnostic confidence remains stable`; `B1 adds slight overhead but remains practical` -> `B1 adds visual-processing overhead but remains below RTF=1.0`.

**Что сохранить:** `diagnostic confidence` and `below RTF=1.0`.

### Results: Baseline Overhead and Throughput

**Current location:** `paper.tex:248-291`.

**Тип изменения:** clarity cleanup.

**Перефразировки:** `highest overhead ratio is observed` -> `highest B1/B0 overhead ratio appears`; `full pipeline remains below real-time` -> `below RTF=1.0`.

**Что сохранить:** current is better and more specific.

**Риск:** low.

### Results: Failure Cases and Practical Constraints

**Current location:** `paper.tex:295-347`.

**Тип изменения:** mostly improved interpretation.

**Новые/changed points:**

- `coverage` consistently becomes `temporal coverage`.
- Uniform 30 s coverage is explicitly not better description quality.
- Weakest case described as risk of rare transitions in slide-centric videos.
- Talking-head case was removed from the qualitative sentence in current version.

**Что сохранить:** temporal coverage warning, uniform 30 s caveat, failure-mode framing.

**Что проверить:** if the talking-head case was a useful qualitative example, consider restoring it. Its removal reduces evidence variety.

### Interactive Latency and TTS

**Current location:** `paper.tex:351-352`.

**Тип изменения:** exact micro-benchmark softened into indicative spot-check.

**Before data:** `median latency of 2682.6 ms`, cached fetch `0.06 ms`.

**After wording:** several prompts, network-bound synthesis dominates, cached response avoids repeated work, not rigorous benchmark.

**Что сохранить:** keep the caveat, but consider restoring exact values if they are real and reproducible. Concrete measurements read less generic than `suggested that network-bound synthesis latency dominates`.

### Discussion: Baseline Overhead

**Current location:** `paper.tex:354-358`.

**Тип изменения:** clarity and stronger result sentence.

**Новое содержание:** full pipeline doubles B0 while remaining below RTF=1.0 in this corpus.

**Что сохранить:** yes.

**Что переписать:** `The duration distribution suggests an amortization effect` is okay, but can sound canned. A more direct version: short videos pay the fixed setup/API cost more visibly; longer videos spread it out.

### Discussion: Deployment Implications

**Current location:** `paper.tex:360-361`.

**Тип изменения:** new risk analysis.

**Before смысл:** dependency manageable, open-weight multimodal possible but quality not guaranteed.

**After смысл:** hosted services simplify prototype but introduce model drift, rate limit, cost, network latency; open-weight replacement needs separate evaluation.

**Что сохранить:** current version is much stronger.

**AI-like risk:** list of four risks is a classic "rule of many", but here it is concrete. Keep it, maybe make it a sentence with cause/effect instead of a list-like cadence.

### Threats to Validity

**Current location:** `paper.tex:363-368`.

**Тип изменения:** major scientific improvement.

**Новые/changed points:**

- External validity now names video genres and difficult speech cases.
- Construct validity separates RTF, ASR confidence, coverage and user outcomes.
- Internal validity becomes internal and user validity.
- New user groups explicitly listed: disabled, DHH, blind/low-vision, ADHD, dyslexic, neurodivergent learners.

**Что сохранить:** this is important. Do not lose these caveats.

**Что переписать:** current version is very detector-friendly because it is clean, exhaustive, and evenly structured. It can stay academic, but make it less mechanical by reducing repeated negative forms. Example direction: "The benchmark says something about engineering throughput, not about learner outcomes. That boundary matters most for the interface claims."

### Conclusion

**Current location:** `paper.tex:370-375`.

**Тип изменения:** before had one short paragraph; after has three more complete paragraphs.

**Новое содержание:** exact artifact list, integrated workflow, engineering feasibility vs user impact, exact B0/B1 metrics, adaptive indexing vs caps, future work list.

**Что сохранить:** structure and exact numbers.

**Что переписать:** conclusion is currently the most AI-polished section after abstract. It uses a common template: `This paper presented...`, `The benchmark shows...`, `Future work should...`. This is acceptable in academic writing, but if detectors are aggressive, write it manually with a little less symmetry.

## 6. Per-section rewrite priorities

**Priority 1: rewrite manually from before, preserving after additions.**

- Abstract.
- Formal Metrics caveats.
- Threats to Validity.
- Conclusion.

**Priority 2: lightly edit current after text to restore author voice.**

- Introduction.
- Related Work, especially gap sentences.
- Interactive TTS.
- Deployment Implications.

**Priority 3: keep current wording mostly as is.**

- Corpus Benchmark details.
- Tables/figures/captions, except cosmetic style.
- Post-hoc ablation setup.
- Automation protocol.
- System Design artifact definitions.

## 7. AI-like pattern checklist for this article

This checklist combines the local `humanizer` skill and independent source review. Use it as a diagnostic, not as a rulebook.

**High-risk clusters in the current after version:**

- Repeated caution formulas: `not as evidence of`, `not a measure of`, `should not be interpreted`, `not direct measures`, `before stronger claims`.
- Very smooth abstract/conclusion paragraph symmetry.
- Generic academic verbs when a concrete method verb is available: `presents`, `supports`, `defines`, `motivates`.
- Evenly balanced "X, Y, and Z" lists, especially in conclusion and threats.
- Gap sentences that read like a template: `this literature motivates..., but it does not...`.
- Repeated nominalizations: `artifact generation`, `validation work`, `deployment dependencies`, `processing latency`.
- Over-clean replacement of your before voice with cautious institutional voice.

**False positives to avoid overreacting to:**

- Formal academic style.
- Passive voice in methods/results.
- Correct grammar.
- Repeated technical terms.
- One or two words like `however`, `therefore`, `pipeline`, `configuration`.
- A high detector score by itself. Turnitin says AI reports should not be used as the sole basis for adverse action, and scores require human review.

**Rewrite rules for this paper:**

1. Keep numbers, corpus details, exact metric definitions and limitations.
2. Prefer concrete method verbs: `measured`, `computed`, `excluded`, `cached`, `sampled`, `indexed`, `compared`.
3. Do not replace technical terms with synonyms just for variation. Repeat `coverage`, `RTF`, `scene anchor` when they are the correct terms.
4. Reduce repeated disclaimers by grouping them once per section.
5. Keep claims proportional: engineering feasibility yes, accessibility/user benefit no.
6. Let a few sentences be slightly uneven if they are yours, but do not insert artificial mistakes. Natural specificity is better than deliberate errors.
7. In abstract and conclusion, avoid broad openings. Start from the artifact problem, corpus and result boundary.
8. When a sentence sounds like a vendor report, add the actual constraint, number, or decision that came from your prototype.

## 8. Suggested manual rewrite strategy

1. Use `academic_paper/rewrite_workspace/before_1c6dafe_prose_edit.md` as the main human-editing surface.
2. Keep `academic_paper/rewrite_workspace/before_1c6dafe_paper.tex` as the exact TeX source to map edits back later.
3. Use `academic_paper/rewrite_workspace/historical_article_prose_edit_bfa5c0b.md` only as an older voice/reference artifact, because it predates a few later fixes.
4. Insert the new references and new scientific caveats from sections 3, 4, and 2.1 of this audit.
5. For each changed paragraph, read before and after, then rewrite from memory into the before prose file. Editing the after sentence in place tends to preserve its rhythm.
6. Keep the before version's directness where it reflects your own work, but remove unclear grammar that changes meaning.
7. Run a final claim audit: every mention of accessibility benefit should be either literature-motivated or explicitly future validation.

## 9. External source notes on detectors and style

- Turnitin documentation says its AI model may misidentify human-written, AI-generated and AI-paraphrased text, and should not be the sole basis for adverse action. Source: https://guides.turnitin.com/hc/en-us/articles/22774058814093-Using-the-AI-Writing-Report
- Turnitin also frames the report as one data point requiring educator judgment and institutional policy, not a definitive answer. Source: https://guides.turnitin.com/hc/en-us/articles/27139000787853-How-should-I-review-the-AI-Writing-report
- Wikipedia's "Signs of AI writing" emphasizes clusters such as undue significance, promotional tone, superficial `-ing` analysis, vague attribution, AI vocabulary, copula avoidance, negative parallelism and rule-of-three overuse. Source: https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing
- Liang et al. report that GPT detectors can misclassify non-native English writing and warn about evaluative use, especially for non-native speakers. Source: https://arxiv.org/abs/2304.02819
- Purdue OWL's APA style guidance supports clarity, specificity, concision and active voice where the actor matters. Source: https://owl.purdue.edu/owl/research_and_citation/apa_style/apa_formatting_and_style_guide/apa_stylistics_basics.html

## 10. Quick implementation notes

- The current article is not "bad". It is scientifically safer than before.
- The practical problem is that safety was added in a very uniform voice.
- Best path: restore before as base, manually re-add after's empirical details and caveats, then smooth only grammar that blocks meaning.
- Do not intentionally add mistakes. It is safer to preserve your actual sentence rhythm, specific implementation decisions, and exact limitations.
