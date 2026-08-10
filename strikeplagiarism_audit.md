# Аудит отчетов Strikeplagiarism и стратегия ручной переработки

Дата аудита: 2026-06-24

## 1. Соответствие файлов и отчетов

### Главный вывод

`blind report (3rd).pdf` не выглядит как отдельный отчет по `blind (3rd).pdf`. После нормализации разницы в дате `blind report (2nd).pdf` и `blind report (3rd).pdf` дают один и тот же текстовый хэш и одинаковое содержимое.

| Файл статьи | Файл отчета | Вердикт |
|---|---|---|
| `C:\Users\asqar\Desktop\prev\blind (1st).pdf` | `C:\Users\asqar\Desktop\prev\blind report (1st).pdf` | Похоже на отдельный прогон первой версии. |
| `C:\Users\asqar\Desktop\prev\blind (2nd).pdf` | `C:\Users\asqar\Desktop\prev\blind report (2nd).pdf` | Похоже на прогон второй версии. |
| `C:\Users\asqar\Desktop\prev\blind (3rd).pdf` | `C:\Users\asqar\Desktop\prev\blind report (3rd).pdf` | Почти наверняка не отдельный прогон. Это дубликат отчета второй версии с измененной датой/экспортом. |

### Доказательства

| Отчет | AI probability | AI content indicator | Words | Characters | Document ID | Дата в отчете |
|---|---:|---:|---:|---:|---|---|
| `blind report (1st).pdf` | 33% | 64% | 3933 | 26199 | `333884650` | `5/15/2026` |
| `blind report (2nd).pdf` | 69% | 100% | 3473 | 23130 | `334294737` | `6/12/2026` |
| `blind report (3rd).pdf` | 69% | 100% | 3473 | 23130 | `334294737` | `2026-06-12` |

Дополнительно:

- `blind report (2nd).pdf` и `blind report (3rd).pdf` имеют одинаковый список красных фрагментов, одинаковые проценты, одинаковое число слов/символов и один document ID.
- Нормализованный текстовый хэш report 2 и report 3 одинаковый: `78be0e70e789293c201d2a6dbf4cfc3336683d45c9e5943dc9427ca3c271b1f2`.
- `blind (3rd).pdf` отличается от `blind (2nd).pdf`: он создан позже, длиннее, содержит шапку конференции и ссылки вида `[1]-[3]`, тогда как report 2/3 отражает прогон с признаками версии 2.
- Вывод: report 3 нельзя использовать как доказательство процента для третьей версии. Нужен новый прогон именно актуального `main_blind.pdf`.

## 2. Текущее состояние статьи

Основной файл текущей статьи: `C:\Users\asqar\Desktop\Prototype\academic_paper\paper_blind.tex`.

`C:\Users\asqar\Desktop\Rewrite.docx` содержит только черновик для `Abstract`, `Keywords` и `Introduction`. Эти фрагменты уже перенесены в `paper_blind.tex`, поэтому старый отчет 2/3 не отражает текущий abstract/intro.

Практический вывод:

- abstract и introduction уже не нужно оценивать по report 2/3 напрямую;
- их надо проверять только после нового компиляционного PDF и нового отчета Strikeplagiarism;
- неизмененные секции после introduction все еще можно оценивать по report 2/3, потому что основная структура и формулировки там совпадают с текущей статьей.

## 3. Карта красных зон по секциям

### Abstract и Introduction

Что было красным в report 2/3:

- item 11: `This paper presents a prototype multimodal pipelin...` - 86%, 135 words;
- item 15: `Our proposed approach embeds word-level transcript...` - 86%, 191 words;
- item 5: `INTRODUCTION In education and professional trainin...` - 86%, 25 words;
- item 22: `Studies show that captions, playback control, and ...` - 77%, 20 words.

Сейчас эти зоны частично переписаны из `Rewrite.docx`, поэтому старые проценты к ним не применяются напрямую.

Почему срабатывало:

- стандартное академическое начало: `This paper presents`, `Our proposed approach`, `Studies show`;
- слишком гладкая структура: проблема, подход, корпус, метрики, ограничения;
- abstract был похож на машинно собранный summary: много корректных технических фактов, но мало авторского выбора и причин, почему именно так построено исследование.

Что делать руками:

- не возвращать старый abstract из версии 1 или 2;
- после нового прогона смотреть, остались ли красные зоны именно в новом abstract/intro;
- если останутся, переписывать не отдельные слова, а логику абзаца: сначала фактическая причина задачи, затем твое инженерное решение, затем только самые важные метрики;
- не добавлять лишней "красивой" академичности, потому что она часто повышает риск.

### Related Work

Красные фрагменты report 2/3:

- item 21: `II. RELATED WORK A. Captions and Learning Accessi...` - 79%;
- item 22: `Studies show that captions, playback control, and ...` - 77%;
- item 24: `B. Cognitive Load and Neurodiversity in Video Lea...` - 76%;
- item 25: `Gap: This literature motivates control and structu...` - 76%;
- item 30: `Work on partial and fully synchronized captions ad...` - 69%;
- item 36: `In e-learning platforms, automated subtitles can b...` - 59%;
- item 43: `Augmented methods such as WhisperX and CrisperWh...` - 51%;
- item 67: `Challenges re- lated to media quality in online vi...` - 24%.

Почему срабатывает:

- раздел написан как обзор "по шаблону": источник A доказывает важность captions, источник B добавляет timing, источник C добавляет W3C, затем `Gap`;
- слово `Gap:` в каждом подразделе выглядит очень механически;
- многие предложения говорят не о том, что конкретно ты взял из источника для своей системы, а о том, что "литература мотивирует" тему;
- часть срабатываний может быть слабым сигналом, потому что related work по природе содержит стандартные формулы и цитаты.

Что делать руками:

- перепроверить каждый абзац по вопросу: "зачем этот источник нужен именно моей pipeline?";
- оставить меньше общих утверждений о пользе captions и больше связи с конкретными decisions в системе;
- убрать повторяемый ритм `source says X -> gap says Y`;
- `Gap:` лучше заменить на нормальную авторскую связку внутри абзаца, но без вставки заготовленных фраз;
- не трогать сами ссылки, если они нужны для научной опоры.

### System Design и Methodology

Красные фрагменты report 2/3:

- item 10: `TABLE II KEY EXPERIMENTAL PARAMETERS...` - 86%;
- item 16: `In this prototype, scene-linked descriptions are ...` - 85%;
- item 17: `In the next step, the system calls the hosted gemi...` - 85%;
- item 28: `METHODOLOGY A. Prototype Configuration...` - 72%;
- item 40: `1 with the following components: 1) Transcribing: ...` - 52%;
- item 42: `Audio description is played through the on-demand...` - 51%;
- item 44: `For single-video processing, the system applies a ...` - 51%;
- item 55: `For this reason, we implemented a custom web playe...` - 36%;
- item 56: `Algorithm 1 On-Demand Audio Description Resolutio...` - 34%.

Почему срабатывает:

- много "pipeline language": `the system emits`, `the current prototype`, `the system calls`, `this provides a balance`;
- разделы выглядят как техническая документация, автоматически превращенная в paper prose;
- таблицы, алгоритмы и `Algorithm 1` частично являются parser artifact, не обязательно реальная проблема текста;
- настоящая проблема не в названиях компонентов, а в окружающих объяснениях, где предложения слишком ровные и без следов авторского решения.

Что делать руками:

- таблицы параметров, названия моделей и алгоритм не переписывать ради процента;
- переписывать окружающие абзацы: почему выбран такой компонент, какое ограничение было реальным, что именно делает prototype;
- избегать повторяющегося начала `The system...`, `The current prototype...`, `In the next step...`;
- не делать раздел слишком "идеальным": техническая правда важнее гладкости.

### Evaluation Metrics, таблицы, формулы, captions

Красные фрагменты report 2/3:

- item 7: `A lower RTF indicates faster processing...` - 86%;
- item 9: `This metric does not indicate whether the generate...` - 86%;
- item 13: `For implementation, the denominators for both RTF...` - 86%;
- item 18: `TABLE V BASELINE COMPARISON...` - 83%;
- item 29: `TABLE I CORPUS COMPOSITION...` - 71%;
- item 31: `Evaluation Metrics This paper reports engineering ...` - 67%;
- item 46: `3. Mean coverage within 15 s of indexed scenes...` - 51%;
- item 49: `RTFmean RTFmean RTFmed conf. 15s...` - 49%;
- item 51: `ASR confidence is an internal diagnostic...` - 49%;
- item 52: `The 15-second radius was selected...` - 48%;
- item 53: `Table IV shows the split...` - 46%;
- item 61: `The coverage15s metric shows...` - 29%;
- item 62: `15s Scenes Zero mean mean mean scene...` - 28%;
- item 64: `Tables and figures in this paper...` - 26%.

Почему срабатывает:

- таблицы и подписи ломаются при парсинге PDF, поэтому `RTFmean RTFmean`, `TABLE`, `Fig.` и строки таблиц часто выглядят подозрительно;
- формульные определения метрик почти всегда имеют шаблонный стиль;
- часть срабатываний здесь является ложным или слабым сигналом;
- реальная зона риска - не формулы, а объяснения вокруг них: `This metric does not indicate...`, `This paper reports engineering proxy metrics...`, `For implementation...`.

Что делать руками:

- не тратить время на table headers, formulas и units;
- переписать объяснения метрик так, чтобы было ясно, почему именно ты выбрал `coverage15s`, RTF и ASR confidence;
- limitations по метрикам оставить, но сделать менее boilerplate;
- подписи figures держать короткими и фактическими.

### Results, Discussion, Threats to Validity, Conclusion

Красные фрагменты report 2/3:

- item 1: `Construct validity: The reported metrics are engi...` - 86%;
- item 2: `Internal validity: The visual context extraction ...` - 86%;
- item 3: `B0 captures a minimum subtitling path around Whisp...` - 86%;
- item 4: `The study is limited to proving engineering feasib...` - 86%;
- item 8: `In the evaluated corpus, this kept screencast mean...` - 86%;
- item 14: `The full B1 processing pipeline stayed below real-...` - 86%;
- item 19: `The corpus manifest preserves neither detailed sou...` - 81%;
- item 20: `Processing was conducted on a local workstation...` - 79%;
- item 27: `A Google Cloud Neural TTS micro-benchmark...` - 73%;
- item 32: `IX. CONCLUSION This paper proposed a viable unifi...` - 64%;
- item 33: `B. Deployment Implications...` - 63%;
- item 34: `The evaluation of a bilingual corpus...` - 62%;
- item 35: `ASR confidence does not indicate actual transcrip...` - 62%;
- item 37: `All content types achieved coverage above 87%...` - 57%;
- item 39: `D. Interactive Latency and Speech Synthesis...` - 53%;
- item 41: `The weakest case...` - 52%;
- item 47: `B. Baseline Overhead and Throughput Behavior...` - 50%;
- item 48: `Open-weight replacements are possible...` - 49%;
- item 50: `These comparisons are coverage-oriented diagnostic...` - 49%;
- item 54: `In contrast, en_short_screencast...` - 40%;
- item 57: `Practical demos are the most saturated...` - 34%;
- item 58: `A uniform 30 s interval achieved...` - 32%;
- item 59: `Full pipeline processing remains below real-time...` - 30%;
- item 60: `In the current prototype, ASR and timestamping...` - 30%;
- item 63: `When comparing B0 mean RTF to B1 mean RTF...` - 27%;
- item 65: `We compared fixed caps of 10, 20 and 30 scenes...` - 24%;
- item 66: `VIII. THREATS TO VALIDITY External validity...` - 24%.

Почему срабатывает:

- `Threats to Validity` написан почти как готовый шаблон: external/construct/internal validity, then engineering proxy disclaimer;
- conclusion повторяет abstract/results в максимально стандартной академической форме;
- discussion использует безопасные, гладкие фразы: `captures a minimum path`, `deployment dependencies remain`, `future work should include`;
- detector особенно сильно реагирует на ограничения и future work, потому что LLM часто пишет их именно таким ритмом.

Что делать руками:

- это главный приоритет после нового прогона abstract/intro;
- начать с `Threats to Validity`, потому что item 1 и item 2 являются самыми красными;
- затем переработать `Conclusion`, чтобы он не звучал как пересказ abstract;
- в `Results` отделить фактические результаты от интерпретации: цифры оставить, объяснение переписать через реальные наблюдения из эксперимента;
- не расширять future work списком "правильных" пунктов, если они уже есть; лучше оставить только то, что реально вытекает из ограничений твоего эксперимента.

## 4. Ложные или слабые сигналы

Не все красное нужно переписывать.

С высокой вероятностью parser/format artifacts:

- `TABLE I`, `TABLE II`, `TABLE V`;
- `RTFmean RTFmean RTFmed conf. 15s`;
- `Fig. 2`, `Fig. 3`;
- строки таблиц с числами;
- `Algorithm 1`;
- bibliography/references;
- IEEE/LaTeX переносы вроде `transcrip- tion`, `re- lated`, склейки слов и разрывы строк.

Что с ними делать:

- не ломать научную структуру ради процента;
- если отчет красит только table header или caption, считать это слабым сигналом;
- если отчет красит абзац перед/после таблицы, работать именно с объяснением, а не с таблицей.

## 5. Можно ли брать куски из первой версии

Короткий ответ: целыми кусками брать не стоит.

Почему первая версия получила ниже процент:

- она менее гладкая и менее "идеальная" по английскому;
- в ней больше неровных авторских формулировок;
- часть низкого процента могла возникнуть из-за другого парсинга, другого объема и другого набора секций;
- report 1 тоже красил существенные места: `The focus of the present study...`, `The system blends...`, methodology, references, adaptive scene indexing, prototype player.

Что можно взять из первой версии:

- не текст, а принцип: меньше шаблонной академической упаковки, больше прямого объяснения того, что сделано;
- отдельные авторские решения, если они точнее выражают ход исследования;
- более "ручной" ритм, где видно, что мысль не собрана по универсальному paper template.

Что нельзя брать целиком:

- abstract: он ниже по проценту, но слабее научно и тоже содержит flagged фразы;
- references и related work: report 1 красил references и источники;
- фразы вроде `The focus of the present study...`, `This research provides...`, `The system blends...`;
- старые claims, которые были уточнены во второй/текущей версии;
- любые куски, которые ухудшат точность ради процента.

Практическое правило:

- если первая версия помогает вспомнить, как ты сам объяснял идею, используй ее как заметку;
- если хочется скопировать абзац, не копируй: заново восстанови мысль по фактам эксперимента, коду, таблицам и ограничениям.

## 6. Приоритет ручной переработки

### Приоритет 0: запросить корректный отчет

Нельзя делать окончательные выводы по третьей версии на основе `blind report (3rd).pdf`. Он дублирует report 2.

Перед финальной переработкой надо прогнать заново актуальный PDF, собранный из `academic_paper/paper_blind.tex`. В новом отчете должны измениться хотя бы document ID, дата, число слов/символов и список фрагментов.

### Приоритет 1: не трогать уже переписанное вслепую

Abstract и Introduction уже обновлены по `Rewrite.docx`. Их не нужно переписывать на основании старого report 2/3. Сначала нужен новый отчет.

### Приоритет 2: Threats to Validity и Conclusion

Это самая явная зона шаблонного академического boilerplate. Report 2/3 ставит 86% на construct/internal validity и 64% на conclusion.

Работа руками:

- оставить научные ограничения;
- убрать ощущение универсального шаблона;
- связать ограничения с конкретными условиями эксперимента: корпус, hosted APIs, отсутствие WER/CER, отсутствие user study, source provenance.

### Приоритет 3: System Design и Methodology

Report 2/3 сильно красит описание prototype, hosted Gemini, scene-linked descriptions и параметры.

Работа руками:

- таблицы и названия компонентов оставить;
- переписать связующий текст вокруг них;
- в каждом абзаце показать инженерную причину выбора, а не просто перечисление pipeline steps.

### Приоритет 4: Evaluation Metrics и Results

Метрики частично красные из-за формул и таблиц, но explanatory prose вокруг них можно улучшить.

Работа руками:

- оставить RTF, coverage15s, ASR confidence;
- сделать пояснения более привязанными к эксперименту;
- не превращать limitations в список стандартных disclaimers.

### Приоритет 5: Related Work

Здесь не надо искусственно "очеловечивать" источники. Нужно убрать повторяемость `source -> benefit -> gap`.

Работа руками:

- каждый источник должен выполнять конкретную функцию;
- меньше универсальных фраз о пользе captions;
- больше связи с твоими artifact groups, player controls, timing, scene descriptions.

## 7. Контрольный чеклист для нового отчета

После нового Strikeplagiarism-прогона проверить:

- изменился ли document ID;
- совпадает ли количество слов/символов с актуальной версией;
- исчезли ли старые красные фрагменты из abstract/intro;
- остались ли top-10 фрагментов в `Threats`, `Conclusion`, `System Design`, `Methodology`;
- красит ли отчет таблицы/формулы или именно prose;
- есть ли красные зоны в bibliography/reference list, которые можно игнорировать как parser artifact.

Главная метрика для ручной работы: не общий процент, а top fragments. Если top-10 уходит из нормального prose в таблицы, captions и references, это уже хороший знак, даже если общий показатель падает не идеально.
