# Qualitative Scene-Indexing Case Notes

Source run: `run_001`

These notes are selected from saved B1 artifacts and are intended for paper drafting. They are qualitative engineering observations, not human judgments of accessibility quality.

## lowest_coverage

- Video: `ru_medium_slide-centric`
- Content type: `slide-centric`; duration bucket: `medium`; language: `ru`
- Selection rule: Minimum coverage_15s_pct in the corpus.
- Metrics: B1 total=100.13s, B1 RTF=0.3246, coverage=48.0%, scenes=8, density=1.56/min, tail=0s
- Scene spacing: median=20.27s, max=143.20s
- Observation: The weakest coverage case occurs where visual transitions leave larger uncovered gaps.
- Method implication: Slide-centric or low-transition material may need periodic anchors, OCR-aware cues, or a lower scene-detection threshold when coverage is prioritized.
- Representative snippets: @0.0s: На тёмно-синем фоне с мелкой сеткой виден текст: «Начало речи». В левом нижнем углу расположена серая эмблема с короной и деревом. В правом нижнем... | @98.0s: Женщина в черной одежде стоит перед флипчартом, указывая правой рукой на схему. Схема описывает этапы: "НАЧАЛО РЕЧИ", "ВЫХОД", "ПАУЗА", "ПРИВЕТСТВИ... | @308.8s: Экран полностью белый. Посередине, в самом центре, расположен небольшой черный горизонтальный штрих.

## screencast_reference

- Video: `en_short_screencast`
- Content type: `screencast`; duration bucket: `short`; language: `en`
- Selection rule: Screencast case closest to 95% coverage with sparse scene density.
- Metrics: B1 total=75.28s, B1 RTF=0.4053, coverage=94.8%, scenes=12, density=3.88/min, tail=6.95s
- Scene spacing: median=13.10s, max=39.53s
- Observation: Coverage remains high in a low-motion content type, consistent with the role of fallback anchors when detector triggers are sparse.
- Method implication: Adaptive density is useful for avoiding long uncovered spans, but it should be reported as a coverage mechanism rather than a semantic-quality guarantee.
- Representative snippets: @0.0s: The screen shows a grid of eight game listings, each featuring a thumbnail, title, creator, vote count, and spin-off count. Visible titles include... | @98.1s: A Khan Academy "COMPUTER PROGRAMMING" page for "Jello Muncher" is displayed, showing "7 Votes". On the left, JavaScript code defines game levels, s... | @178.8s: A Khan Academy page for "kill the X robot!!!" displays a code editor on the left and a game preview on the right. The code defines game variables l...

## dense_practical_demo

- Video: `en_long_practical_demo`
- Content type: `practical_demo`; duration bucket: `long`; language: `en`
- Selection rule: Practical-demo video with the largest scene count.
- Metrics: B1 total=429.17s, B1 RTF=0.3657, coverage=100.0%, scenes=123, density=6.29/min, tail=0s
- Scene spacing: median=9.05s, max=21.63s
- Observation: The richest visual content produces many indexed scenes and a high absolute processing workload.
- Method implication: Static scene caps risk removing anchors from visually dense content; this motivates a coverage-cost trade-off analysis rather than a single fixed scene budget.
- Representative snippets: @0.0s: A person in a white lab coat and blue gloves is actively working inside a lab fume hood. Their gloved hands, blurred from motion, are positioned ne... | @576.4s: A very dark and blurry image features a central mass of swirling light brown and dark blue, appearing like an abstract figure in rapid motion. The... | @1183.4s: The screen is completely black. There is no visible content, text, or any visual demonstration.

## talking_head_reference

- Video: `ru_medium_talking_head`
- Content type: `talking_head`; duration bucket: `medium`; language: `ru`
- Selection rule: Talking-head video closest to the content-type mean B1 RTF.
- Metrics: B1 total=157.47s, B1 RTF=0.4558, coverage=90.3%, scenes=23, density=3.99/min, tail=16.57s
- Scene spacing: median=11.00s, max=47.97s
- Observation: The conversational format behaves as a relatively stable reference case for the pipeline.
- Method implication: The main stress cases are not generic speech videos but low-transition slides and high-variation demonstrations.
- Representative snippets: @0.0s: В кадре молодой мужчина с бородой в фиолетовой клетчатой рубашке, он смотрит прямо. За ним два монитора с изображением хвойного леса, а по бокам —... | @195.9s: На экране темно-серый фон с неровными, более темными областями, создающими легкую текстуру. Немного выше центра расположена одна маленькая, ярко-же... | @328.9s: В кадре крупным планом мужчина со светлой кожей, бородой и короткими темными волосами, он улыбается. На нем фиолетово-белая клетчатая рубашка. За н...
