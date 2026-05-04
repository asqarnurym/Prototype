# Article Prose Editing Draft

Source: `academic_paper/paper_ieee_full.tex`.

This file intentionally excludes LaTeX tables, figures, formulas, algorithms, bibliography, and raw layout commands. Inline citation/reference commands are preserved so edited prose can be mapped back into TeX later.

Edit prose inside the marked blocks. Please keep the `<!-- PROSE ... -->` markers intact.

## Abstract

<!-- PROSE id=p001 kind=paragraph source=paper_ieee_full.tex lines=34-34 -->
The online learning format and educational videos have become an integral part of modern learning at all stages. Still, despite the deep integration across the world, the problem is more serious than ever before, and although inclusivity on the Internet has long been defined by accessibility standards, not all platforms provide an adequately wide set of features for the most numerous groups of people with disabilities. This research provides a single multimodal pipeline for processing source video for future educational applications. The system blends automated speech recognition (ASR) with scene indexing to perform visual analysis and generate written and audio descriptions. All source video processing artifacts are reusable and separate from the video. The platform's prototype player integrates keyboard-first controls, ARIA semantics, and word-by-word subtitling as functionality aimed at increasing accessibility. A bilingual test corpus evaluation was conducted on 24 instructional videos (12 English, 12 Russian) of various lengths and kinds of content using two configurations: ASR-only baseline (B0) and with extra scene description (B1). As for results or processing, ASR confidence stayed stable (mean 0.942), while full pipeline run time achieved a mean real-time factor (RTF) of 0.433 and median RTF of 0.424. Results of the conducted experiment show faster-than-realtime processing in every video across the corpus and 15-second scene coverage of 91.7\%, which directly indicates practical prototype-stage performance under resource constraints and suggests that the adaptive scene-density heuristic remained effective within the evaluated corpus.
<!-- /PROSE id=p001 -->

## Keywords

<!-- PROSE id=p002 kind=paragraph source=paper_ieee_full.tex lines=39-39 -->
Accessibility, e-learning, educational video, multimodal pipeline, automatic speech recognition, captions, audio description, cognitive load.
<!-- /PROSE id=p002 -->

## Introduction

<!-- PROSE id=p003 kind=paragraph source=paper_ieee_full.tex lines=43-43 -->
In higher education and professional growth, the video-centric format of education became dominant, but despite that, pre-recorded lessons and screen-captured records remain unfairly accessible across student groups. Studies show that captions, playback control, and navigational structure advance accessibility and support learning in video-based education environments \cite{Gernsbacher2015,Mayer2020,Horlin2024}. This prototype therefore, targets synchronized captions, scene-linked descriptions, and structured navigation within a single playback workflow.
<!-- /PROSE id=p003 -->

<!-- PROSE id=p004 kind=paragraph source=paper_ieee_full.tex lines=45-45 -->
Existing practice often treats these needs as separate product features, to solve that problem, the proposed work frames accessibility as an end-to-end pipeline problem: one processing flow should produce synchronized artifacts that can be reused by the playback layer and downstream tools. This framing is especially relevant under constrained deployment settings where the compute and API quota. Implementation complexity is a practical limitation.
<!-- /PROSE id=p004 -->

<!-- PROSE id=p005 kind=paragraph source=paper_ieee_full.tex lines=47-47 -->
The research question is: Can a resource-constrained multimodal pipeline produce synchronized accessibility artifacts with stable timing quality and practical processing latency across bilingual educational video content while using adaptive scene selection rather than a manually fixed scene budget?
<!-- /PROSE id=p005 -->

<!-- PROSE id=p006 kind=paragraph source=paper_ieee_full.tex lines=49-49 -->
Contributions of research:
<!-- /PROSE id=p006 -->

<!-- PROSE id=p007 kind=item source=paper_ieee_full.tex lines=51-51 -->
- Implementation of a unified multimodal pipeline that simultaneously generates captions with word-level alignment and scene-indexed visual descriptions and structured summary.
<!-- /PROSE id=p007 -->

<!-- PROSE id=p008 kind=item source=paper_ieee_full.tex lines=52-52 -->
- Development of adaptive scene indexing that ensures complete coverage of content even with little difference between scenes, without predefining a fixed number of scenes.
<!-- /PROSE id=p008 -->

<!-- PROSE id=p009 kind=item source=paper_ieee_full.tex lines=53-53 -->
- Design of a system with an efficient on-demand scene audio-description mechanism, caching to reduce latency in case of repetitive local playbacks after the first request, support of accessibility for people with ADHD and dyslexia through fonts and captioning features.
<!-- /PROSE id=p009 -->

<!-- PROSE id=p010 kind=item source=paper_ieee_full.tex lines=54-54 -->
- Benchmarking on a balanced and normalized set of 24 educational videos in English and Russian languages.
<!-- /PROSE id=p010 -->

## Related Work

### Captions and Learning Accessibility

<!-- PROSE id=p011 kind=paragraph source=paper_ieee_full.tex lines=59-59 -->
Captions do not support neurodivergent or people with impairments only, latest studies show captions as universally beneficial for attention holding, comprehension of material and recall for diverse user groups \cite{Gernsbacher2015}. In educational environments, automated subtitles are effective under realistic conditions, however, the quality of captions also depends on time alignment and segmentation \cite{Malakul2023}. This claim is further supplemented by research of partial and fully synchronized captions, transcript quality alone is insufficient without temporal alignment \cite{Mirzaei2018}. Accessibility requirements are also published in WCAG guidance \cite{WCAG21}. \textbf{Gap:} inspection of most modern solutions shows isolated implementation of captions rather than integrated artifacts with use for navigation and multimodal support.
<!-- /PROSE id=p011 -->

### Cognitive Load and Neurodiversity in Video Learning

<!-- PROSE id=p012 kind=paragraph source=paper_ieee_full.tex lines=62-62 -->
Instructional video effectiveness is defined by factors like pacing, signaling and learner control. Challenges related to media quality in online video lectures, including pace and speech intelligibility, directly affect the learning process \cite{Lange2020}. Measuring cognitive load of students during educational videos is dependent on context and difficult to reflect by a single metric \cite{Kruger2016},  and recent neurodiversity-focused researches highlight challenges related to transcription errors and limited playback/navigation control can create additional barriers for neurodivergent learners \cite{LeCunff2024,Horlin2024}. \textbf{Gap:} literatures motivates control and structure as learning supports, but it does not address how such supports can be generated automatically as reusable artifacts from raw educational video in a single processing pass.
<!-- /PROSE id=p012 -->

### ASR and Timestamping Foundations

<!-- PROSE id=p013 kind=paragraph source=paper_ieee_full.tex lines=65-65 -->
Modern ASR systems have accomplished strong practical utility through deep-learning pipelines \cite{Malik2020} and large-scale weakly supervised models like Whisper \cite{Radford2022}. Augmented methods such as WhisperX and CrisperWhisper target improvements of timestamp precision through forced alignment and attention-based refinement \cite{Bain2023,Wagner2024}. \textbf{Gap:} timestamping advances are often presented as standalone transcription advancements rather than components inside a deployable accessibility pipeline that also handles visual scene understanding and interactive rendering.
<!-- /PROSE id=p013 -->

### Visual Accessibility and Audio Description

<!-- PROSE id=p014 kind=paragraph source=paper_ieee_full.tex lines=68-68 -->
In this prototype, scene-linked descriptions are exposed as optional on-demand spoken output within the same processing pipeline rather than pre-rendered into the source media. The focus of the present study is systems integration and timing behavior, not a user-study evaluation of description quality.
<!-- /PROSE id=p014 -->

## System Design

### Pipeline Architecture and Artifacts

<!-- PROSE id=p015 kind=paragraph source=paper_ieee_full.tex lines=72-72 -->
The proposed system follows a \emph{Hybrid Multimodal Architecture}, which calls multimodal remote LLM for cognitively intensive tasks while utilizing deterministic algorithms for high-throughput media processing. To enhance performance on consumer-grade hardware, the acoustic (ASR) and visual (scene detection) branches execute concurrently. Given an input video, the system emits three artifact groups:
<!-- /PROSE id=p015 -->

<!-- PROSE id=p016 kind=item source=paper_ieee_full.tex lines=74-74 -->
- \textbf{Subtitle artifacts} A_sub: word-level timestamps, segment timeline, and WebVTT export.
<!-- /PROSE id=p016 -->

<!-- PROSE id=p017 kind=item source=paper_ieee_full.tex lines=75-75 -->
- \textbf{Scene artifacts} A_scene: time-indexed visual scenes with text-aware natural-language descriptions.
<!-- /PROSE id=p017 -->

<!-- PROSE id=p018 kind=item source=paper_ieee_full.tex lines=76-76 -->
- \textbf{Structure artifacts} A_sum: summary points and chapter markers derived from scene descriptions.
<!-- /PROSE id=p018 -->

### Interaction Layer and Artifact Rendering

<!-- PROSE id=p019 kind=paragraph source=paper_ieee_full.tex lines=87-87 -->
To implement karaoke highlighting we used a midpoint-based word grouper, which is intended to provide more stable word choice in the algorithm, avoiding temporal overlapping. Although in the evaluated corpus we have not detected any overlapping errors across adjacent words, we do not claim this to be fair for every other case.
<!-- /PROSE id=p019 -->

<!-- PROSE id=p020 kind=paragraph source=paper_ieee_full.tex lines=89-89 -->
Native HTML5 \texttt{<track>} elements do not fully satisfy the requirements selected for prototype player features such as granular, stateful word-by-word highlighting, including current, previous and upcoming states, and for this reason, we have implemented a custom web player subtitle renderer with user customizable font and contrast settings.
<!-- /PROSE id=p020 -->

<!-- PROSE id=p021 kind=paragraph source=paper_ieee_full.tex lines=91-91 -->
Audio description is played via on-demand mechanism reflected in Algorithm~\ref{alg:ad}: Player looks for the nearest indexed scene within 30 second threshold, then returns cached audio or calls TTS function to synthesize speech from stored description and caches audio for later usage, then pauses the generated audio description and resumes original video playback.
<!-- /PROSE id=p021 -->

## Methodology

### Prototype Configuration

<!-- PROSE id=p022 kind=paragraph source=paper_ieee_full.tex lines=124-124 -->
Prototype implementation is currently focused on Russian and English languages support and instantiates the architecture described in Fig.~\ref{fig:architecture} with the following components:
<!-- /PROSE id=p022 -->

<!-- PROSE id=p023 kind=item source=paper_ieee_full.tex lines=126-126 -->
- \textbf{Transcribing:} system utilizes Whisper model optimized for \texttt{int8\_float16} compute type \cite{Radford2022}. This provides a balance between transcription accuracy and RTF.
<!-- /PROSE id=p023 -->

<!-- PROSE id=p024 kind=item source=paper_ieee_full.tex lines=127-127 -->
- \textbf{Visual Semantic Extraction:} Visual transitions are detected via an algorithm utilizing PySceneDetect library with pre-determined pixel difference threshold \cite{PySceneDetect}. In the next step, we utilize hosted \texttt{gemini-2.5-flash} multimodal model \cite{GeminiTeam2025} to generate a semantic description that encapsulates both textual and structural visual data from each identified scene.
<!-- /PROSE id=p024 -->

<!-- PROSE id=p025 kind=item source=paper_ieee_full.tex lines=128-128 -->
- \textbf{Adaptive Scene Indexing:} Because heuristic detection occasionally falls short on visually static content such as screencasts, we handle these low-variance scenarios by falling back to \emph{Adaptive Uniform Sampling}. This guarantees a baseline density of at least two descriptions per minute.
<!-- /PROSE id=p025 -->

## Technical Evaluation

### Experimental Design and Corpus Benchmark

<!-- PROSE id=p026 kind=paragraph source=paper_ieee_full.tex lines=133-133 -->
We evaluated the pipeline using a  \emph{Bilingual Multimodal Corpus Benchmark} containing 24 educational videos, 12 of which are in English, the other half is in Russian. For both languages we selected educational videos of various durations (short, medium, long) and types of content (talking-head, slide-centric, screencast, and practical demo).
<!-- /PROSE id=p026 -->

<!-- PROSE id=p027 kind=paragraph source=paper_ieee_full.tex lines=135-135 -->
Conducted evaluation has utilized a minimal scene per minute threshold to minimize the risk of scene omissions in low variability content and scene transition detection to allow the process to scale with visual complexity and duration of the content properly. Processing was conducted on a local workstation (AMD Ryzen 9 5900HX,
NVIDIA RTX 3050 Notebook, 16 GB of RAM) to establish a baseline for consumer-grade deployability.
<!-- /PROSE id=p027 -->

<!-- PROSE id=p028 kind=paragraph source=paper_ieee_full.tex lines=153-153 -->
Two configurations were compared:
<!-- /PROSE id=p028 -->

<!-- PROSE id=p029 kind=item source=paper_ieee_full.tex lines=155-155 -->
- \textbf{B0 (ASR-only):} transcript and subtitle artifacts without visual branch.
<!-- /PROSE id=p029 -->

<!-- PROSE id=p030 kind=item source=paper_ieee_full.tex lines=156-156 -->
- \textbf{B1 (Full):} ASR + visual scene indexing + multimodal descriptions + summary/chapter generation.
<!-- /PROSE id=p030 -->

<!-- PROSE id=p031 kind=paragraph source=paper_ieee_full.tex lines=158-158 -->
Chosen configurations characterize offline artifact generation. User-triggered text-to-speech call is not included in the full run process because of dependence on the network, the current user-grade test workstation is not enough to handle local multimodal LLM such as \texttt{gemini-2.5-flash}.
<!-- /PROSE id=p031 -->

### Formal Metrics

<!-- PROSE id=p032 kind=paragraph source=paper_ieee_full.tex lines=183-183 -->
The study reports engineering proxy metrics:
<!-- /PROSE id=p032 -->

<!-- PROSE id=p033 kind=paragraph source=paper_ieee_full.tex lines=193-193 -->
where RTF < 1 indicates faster-than-realtime processing.
<!-- /PROSE id=p033 -->

<!-- PROSE id=p034 kind=paragraph source=paper_ieee_full.tex lines=195-195 -->
For implementation, the denominators for both RTF and coverage are derived from the same effective video span: the end time of the generated timeline for each video. Thus, $T_{\text{video}}$ denotes the scalar duration used for RTF, while $s_{\text{video}}$ denotes the length of the evaluated timeline span used for coverage. This keeps B0/B1 denominators consistent for each video. In this definition, $T_{\text{processing}}$ includes offline preprocessing stages only; RTF is therefore interpreted as batch preprocessing throughput rather than end-to-end playback latency.
<!-- /PROSE id=p034 -->

<!-- PROSE id=p035 kind=paragraph source=paper_ieee_full.tex lines=197-197 -->
We added diagnostics to be used to characterize alignment stability and visual indexing behavior:
<!-- /PROSE id=p035 -->

<!-- PROSE id=p036 kind=paragraph source=paper_ieee_full.tex lines=207-207 -->
where n_overlap is the number of overlapping adjacent word timestamps, and t_last_scene is the timestamp of the final indexed scene.
<!-- /PROSE id=p036 -->

### Automation and Reproducibility Protocol

<!-- PROSE id=p037 kind=paragraph source=paper_ieee_full.tex lines=210-210 -->
All runs are conducted via a single driver script, which reads the corpus manifest and processes every video consecutively in B0 and B1 configurations, for single video processing, applies a multithreaded pipeline scheme to optimize the total time of run. Driver saves pipeline output artifacts and computes summaries and metrics in machine-readable format, including baseline comparisons and a JSON report for further analysis. Tables and figures in this paper that are related to metrics are based on a corpus of 24 videos.
<!-- /PROSE id=p037 -->

<!-- PROSE id=p038 kind=paragraph source=paper_ieee_full.tex lines=212-212 -->
System rejects runs before tables and summary metrics are generated, it looks for non-positive runtimes, missing rows and out-of-range coverage values. If there exist valid artifacts for the current set configuration, the driver will reuse them, which supports the cache-aware design of the pipeline. However, we cannot deny that hosted model calls can return unexpectedly various results depending on model patches and network conditions.
<!-- /PROSE id=p038 -->

### Post-hoc Scene-Selection Ablation

<!-- PROSE id=p039 kind=paragraph source=paper_ieee_full.tex lines=215-215 -->
We conducted post-hoc scene selection ablation on a frozen evaluation snapshot to determine whether adaptive scene number selection behaviour would differ from fixed scene budget. As a base of test, the same cached B1 scene timestamps were used without rerunning the pipeline. Three variants of scene budget were selected (10, 20 and 30 scenes allowed) and two uniform time-grid references were added with anchors every 60 s and 30 s. For each variant, we recomputed the same within-15 s coverage metric. These comparisons are intended as coverage-oriented diagnostics of scene-selection policy, not as an alternative semantic scene detection method.
<!-- /PROSE id=p039 -->

### Qualitative Case Selection

<!-- PROSE id=p040 kind=paragraph source=paper_ieee_full.tex lines=218-218 -->
In addition to obtained aggregate metrics, we selected four artifact sets from cached B1 outputs: the lowest coverage case, screencast reference, the densest practical demo and talking-head reference. These cases are used exclusively for surface-level checkups and do not serve to support semantic correctness or accessibility indicators for real users.
<!-- /PROSE id=p040 -->

<!-- PROSE id=p041 kind=paragraph source=paper_ieee_full.tex lines=220-220 -->
The selected cases are presented in the results section to link aggregate metrics with specific failure modes and design implications.
<!-- /PROSE id=p041 -->

## Results and Analysis

### Aggregate Performance

<!-- PROSE id=p042 kind=paragraph source=paper_ieee_full.tex lines=225-225 -->
Table~\ref{tab:lang_overall} shows language-level and overall aggregates. The ASR component remains stable across languages (overall confidence mean 0.942 and low-confidence ratio mean 0.026). Baseline B0 is consistently fast (overall mean RTF 0.193), B1 adds slight overhead but remains practical (overall mean 0.433, median 0.424).
<!-- /PROSE id=p042 -->

### Baseline Overhead and Throughput Behavior

<!-- PROSE id=p043 kind=paragraph source=paper_ieee_full.tex lines=246-246 -->
Table~\ref{tab:duration_baseline} compares B0/B1 across short, medium and long videos. When comparing B0 mean RTF to B1 mean RTF, the highest overhead ratio is observed in the short videos set. Table~\ref{tab:stage_latency} shows the split absolute processing time (seconds) into the audio-only pipeline (B0) and visual semantic extraction overhead. The overhead increases with both scene count and video duration.
<!-- /PROSE id=p043 -->

<!-- PROSE id=p044 kind=paragraph source=paper_ieee_full.tex lines=283-283 -->
Figure~\ref{fig:rtf} visualizes B0 and B1 RTF across content types using boxplots. Full pipeline processing remains below real-time for all 24 videos in the corpus.
<!-- /PROSE id=p044 -->

### Failure Cases and Practical Constraints

<!-- PROSE id=p045 kind=paragraph source=paper_ieee_full.tex lines=293-293 -->
Coverage variation is driven by visual characteristics. Low-variance screencasts remain a stress case for motion-based scene detection, so the pipeline applies fallback sampling when heuristic triggers are sparse. In the evaluated corpus, this kept screencast mean coverage at 94.58\%, while the overall mean coverage reached 91.7\%. Figure~\ref{fig:coverage} shows the resulting content-type coverage distribution; the error bars summarize uncertainty within each six-video content-type group.
<!-- /PROSE id=p045 -->

<!-- PROSE id=p046 kind=paragraph source=paper_ieee_full.tex lines=314-314 -->
According to results presented in table~\ref{tab:content_sensitivity}, screencast-type content appears to have the highest overall coverage when fallback sampling is used, while slide-centric content shows the lowest mean coverage, presumably because of rare slide transitions, which is typical for this type of content. Practical demos are the most saturated in terms of the mean detected scene count. All content types achieved coverage above 87\%.
<!-- /PROSE id=p046 -->

<!-- PROSE id=p047 kind=paragraph source=paper_ieee_full.tex lines=337-337 -->
Table~\ref{tab:scene_ablation} presents a trade-off comparison with ablation outcomes. Adaptive scene indexing shows the highest mean scene count (38.58 scenes) and the second-highest mean coverage, which hints at a loss in quality in ablated approaches. Post-hoc caps of 10, 20 and 30 scenes reduced mean coverage 63.79\%, 80.25\%, and 87.18\%, respectively. The uniform 30 s interval achieved 98.74\% mean coverage because of a 15 s coverage radius, but this does not mean any quality improvements.
<!-- /PROSE id=p047 -->

<!-- PROSE id=p048 kind=paragraph source=paper_ieee_full.tex lines=339-339 -->
Qualitative metrics notes illustrate why coverage should not be interpreted separately from content type. Example of weakest case (\texttt{ru\_medium\_slide-centric}) proves exactly that, 48.0\% coverage with 8 scenes and 143.20 s of the longest detected interval between scenes, this is specific to contents with rare transitions, which slide-centric videos exactly are. Screencast (\texttt{en\_short\_screencast}) reached 94.8\% coverage with 12 scenes, while the dense practical demonstration (\texttt{en\_long\_practical\_demo}) reached 100.0\% coverage with 123 scenes and B1 total processing time of 429.17 s. A talking-head case (\texttt{ru\_medium\_talking\_head}) appears to be comparatively stable, showing near-mean results (90.3\% coverage, 23 scenes, and B1 RTF 0.4558).
<!-- /PROSE id=p048 -->

### Interactive Latency and TTS

<!-- PROSE id=p049 kind=paragraph source=paper_ieee_full.tex lines=349-349 -->
Separating Text-to-Speech (TTS) generation from the main pipeline and corpus test runs allows the system to prepare most of the artifacts faster and avoid huge additional network-bound overhead. Therefore, we conducted a separate micro-benchmark using Google Cloud Neural TTS on five sentence-level description prompts. In this benchmark, API calls showed a median latency of 2682.6~ms, while cached TTS audio fetching processed almost instantly (0.06~ms). Although the cached file request indicated only local storage lookup and needs to be added with network latency (ping) of the client at the production stage, it still reflects the latency and cost optimization benefits.
<!-- /PROSE id=p049 -->

## Discussion

### Interpretation of Baseline Overhead

<!-- PROSE id=p050 kind=paragraph source=paper_ieee_full.tex lines=353-353 -->
The B0/B1 ratio should be interpreted as an ablation-style system analysis. B0 captures a minimum viable subtitling mechanism using Whisper ASR wrapped with utility code and B1 adds visual transition indexing and visual context extraction. The measured overhead estimates the additional cost of accessibility improvements. The overall overhead ratio of 2.25 times means that the full multimodal pipeline approximately doubles the B0 processing time.
<!-- /PROSE id=p050 -->

<!-- PROSE id=p051 kind=paragraph source=paper_ieee_full.tex lines=355-355 -->
The results across duration distribution suggest a predictable amortization effect. Presumably, initialization costs and API call latencies affect more significantly in short videos, in longer videos, initialization costs remain the same, thus, B0/B1 ratio is lower.
<!-- /PROSE id=p051 -->

### Deployment Implications

<!-- PROSE id=p052 kind=paragraph source=paper_ieee_full.tex lines=358-358 -->

<!-- /PROSE id=p052 -->

<!-- PROSE id=p053 kind=paragraph source=paper_ieee_full.tex lines=360-360 -->
The main dependencies remain hosted multimodal LLM and TTS services. This dependency is manageable; it is possible to replace Gemini 2.5 Flash with open-weighted Multimodal models, but quality isn't guaranteed.
<!-- /PROSE id=p053 -->

## Threats to Validity

<!-- PROSE id=p054 kind=paragraph source=paper_ieee_full.tex lines=363-363 -->
\textbf{External validity:} Balanced the 24-video corpus may not represent all possible real-world cases (heavy overlap speech, severe noise, extreme accents).
<!-- /PROSE id=p054 -->

<!-- PROSE id=p055 kind=paragraph source=paper_ieee_full.tex lines=365-365 -->
\textbf{Construct validity:} reported metrics are engineering proxies (timing quality, coverage, throughput), not direct measures of learning gains or cognitive outcomes from human studies. The post-hoc ablation is coverage-oriented and does not compare semantic quality across scene-selection strategies.
<!-- /PROSE id=p055 -->

<!-- PROSE id=p056 kind=paragraph source=paper_ieee_full.tex lines=367-367 -->
\textbf{Internal validity:} the visual context extraction stage utilizes a hosted LLM through API calls. This introduces network, rate-limit and model-drift dependencies. On-demand TTS functionality faces the same problem because it shares the same provider. Latency may vary depending on server deployment and the client's network. Additionally, we cannot claim the proposed prototype to have more or less benefit for targeted user groups, instead we heavily rely on existing studies that have proven the effect of analogs of what our system employs. We mitigate these risks through artifact persistence and explicit stage-aware reporting.
<!-- /PROSE id=p056 -->

## Conclusion

<!-- PROSE id=p057 kind=paragraph source=paper_ieee_full.tex lines=370-370 -->
This paper demonstrates a viable unified processing pipeline that can produce reusable accessibility artifacts for educational video. The evaluation supports prototype-stage feasibility. Future work should therefore move from artifact generation toward semantic quality assessment, user-study-based validation and a self-hosted model as an alternative.
<!-- /PROSE id=p057 -->
