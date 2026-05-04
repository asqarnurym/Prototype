# Prototype Vision

## Product Direction

This platform should evolve from a research prototype into a structured accessibility product for educational video. The core value is not just subtitle generation or chapter extraction in isolation, but a unified multimodal accessibility workflow that combines:

- speech transcription
- scene-aware visual descriptions
- on-demand audio description playback
- structured summaries and chapters
- an accessible player experience

The long-term goal is a platform where a user can upload a video, process it once, and receive a complete accessibility-ready package with reusable artifacts, auditable metadata, and a stable playback interface.

## Architecture Direction

The most practical architectural direction is to separate platform concerns from inference and media-processing concerns.

The current Python stack is a strong fit for:

- ASR
- video and frame processing
- Gemini-based scene understanding
- summary generation
- TTS orchestration
- evaluation and benchmarking scripts

Rewriting the entire backend into Go is technically possible, but it is not the best first move. The inference-heavy part of the system already sits in a Python ecosystem that is much better aligned with media tooling, ML libraries, and current Google SDK usage.

The strongest long-term architecture is:

- Go as the platform and orchestration layer
- Python as the worker and inference layer

In that model, Go would be responsible for:

- API gateway behavior
- authentication and authorization
- upload lifecycle management
- job orchestration
- queue coordination
- database access
- WebSocket or SSE updates
- product-level usage controls, quotas, and billing logic

Python would remain responsible for:

- ASR and alignment
- scene detection and frame extraction
- Gemini scene description generation
- summary and chapter generation
- evaluation routines
- TTS generation paths tightly coupled to current SDKs and media code

If the project needs to mature quickly without splitting languages yet, a very solid near-term path is:

- keep the backend in Python
- formalize it into a cleaner service architecture
- add PostgreSQL, Redis, and background workers
- isolate the processing pipeline into worker processes

That path is lower risk than a full rewrite and still supports real productization.

## Frontend Direction

The frontend should be built as a full product surface, not a collection of experimental pages. The main requirement is not only developer productivity but layout reliability and visual consistency, especially under AI-assisted development.

The best fit is:

- Next.js
- TypeScript
- App Router
- a strict, opinionated UI system

Next.js is the strongest choice because it supports a structured application shell, nested layouts, mature ecosystem tooling, and a predictable full-stack model. It is better suited to a product platform than a lightweight demo frontend.

## UI Stability Strategy

Framework choice alone will not prevent layout drift. The real protection comes from an opinionated design system and a constrained page composition model.

The frontend should not rely on free-form styling scattered across pages. Instead, the interface should be composed from a small set of layout and UI primitives, for example:

- `AppShell`
- `PageHeader`
- `Section`
- `Card`
- `DataPanel`
- `FormSection`
- `EmptyState`
- `StatusBadge`

This makes it much harder for adjacent cards or sections to drift apart stylistically. It also gives AI-generated code less room to invent inconsistent spacing, dimensions, or component behavior.

For this reason, a more opinionated component library is preferable to a raw utility-first approach. The strongest candidates are:

- MUI for maximum enterprise-style discipline
- Mantine for a slightly lighter but still strongly structured system

The preferred frontend stack is therefore:

- Next.js
- TypeScript
- MUI or Mantine
- Storybook
- Playwright with visual regression
- Zod for schema validation
- TanStack Query where client-side async state is genuinely needed

This combination gives the project a better chance of maintaining stable layouts, consistent styling, and reusable page patterns over time.

## Product Modules

As a full platform, the system should grow into clear product modules:

### Frontend

- authentication
- dashboard
- upload flow
- job list and job detail views
- accessible player
- artifact explorer
- chapter and summary views
- accessibility preferences
- usage analytics and operational status

### API / Platform Layer

- auth
- users
- projects
- uploads
- jobs
- artifacts
- scene descriptions
- TTS requests
- usage statistics
- operational audit endpoints

### Worker Layer

- ingest
- ASR
- scene detection
- Gemini description generation
- summary and chapter generation
- TTS cache generation
- evaluation and benchmarking jobs

### Persistence and Storage

- relational database for jobs, uploads, artifacts, and runtime metadata
- object storage for raw uploads and generated artifacts
- cache storage for pre-generated TTS and temporary media outputs

## Data Model Direction

The platform should treat the database as the source of truth for platform state, not the filesystem.

The filesystem or object storage should hold blobs and generated artifacts, but the database should track:

- users
- projects
- uploads
- jobs
- artifacts
- TTS cache entries
- model runtime metadata
- evaluation runs
- audit records

For paper-oriented evaluation, saved artifacts should remain reusable for
post-hoc diagnostics that do not call hosted models again. The current example
is `evaluation/paper_extensions/`, which stores scene-selection ablations and
qualitative case notes derived from the pinned manuscript run.

For near-term implementation, SQLite plus SQLAlchemy is a perfectly good starting point for upload persistence. Later, PostgreSQL can replace SQLite without changing the conceptual model.

## Innovative Extensions

The project already has a strong base. The most promising innovations are not superficial features but adaptive behaviors that make the system meaningfully smarter.

High-value directions include:

### Predictive Audio Description Prefetch

Pre-generate likely next scene descriptions and TTS outputs based on the user’s playback position and navigation behavior.

### Adaptive Audio Description Granularity

Support short, medium, and detailed description modes depending on the user profile, content type, and playback context.

### Semantic Scene Retrieval

Allow users to search for scenes by meaning, not just by timecode.

### Quality-Aware Regeneration

Score generated scene descriptions and summaries automatically. Weak artifacts can be re-generated with a fallback policy or escalated to a stronger model.

### Hybrid Model Routing

Use a cheaper model for simple scenes and escalate only difficult scenes to a more expensive model when needed.

### Personalized Accessibility Profiles

Support user-specific settings for:

- subtitle behavior
- AD verbosity
- TTS speed and voice
- simplified summaries
- dyslexia-oriented presentation modes
- low-vision playback preferences

### Explainable Chaptering and Summary

Expose why chapters or summary points were created, especially in educational scenarios where interpretability can matter.

### Accessibility Usage Telemetry

Track which accessibility functions are actually used in the player, such as subtitles, summaries, audio description, or keyboard navigation.

These features can turn the platform from a batch processor into a user-adaptive accessibility system.

## Observability and Reliability

The platform should be designed around traceability. Every run should clearly record:

- model
- region
- authentication mode
- runtime provider
- fallback reason
- artifact status

This is already partially in place and should be treated as a core architectural requirement, not just a debugging convenience.

Strong observability should include:

- structured logs
- per-job runtime snapshots
- model and provider metadata in artifacts
- clear fallback classification
- latency breakdowns for on-demand operations
- visual regression testing for the frontend

## Publication Quality Gate

Because this project is used in academic deliverables, publication-readiness
checks should be treated as a first-class workflow, not an ad-hoc manual step.

The near-term baseline is:

- manuscript sanity scan for local/internal leakage;
- deterministic PDF build with bibliography and page-limit checks;
- a single preflight command before submission.

Operational details and commands belong in `README.md`, `USAGE.md`, and
`TESTING.md`; this vision document only captures the architectural principle:
academic output quality gates are part of the platform's reliability model.

## Recommended Technical Stack

If the goal is to turn this into a full product with the least architectural regret, the best target stack is:

### Frontend

- Next.js
- TypeScript
- MUI or Mantine
- Storybook
- Playwright

### Backend / API

- FastAPI in the near term
- optional Go platform layer later if the control plane grows significantly

### Workers

- Python workers for all inference and media processing

### Infrastructure

- PostgreSQL
- Redis
- Celery, Dramatiq, or a similar queue system
- S3-compatible object storage

### Testing and Quality

- integration tests for API and pipeline
- golden artifact tests for processing outputs
- visual regression for UI
- runtime metadata audits

## Final Position

The best long-term version of this project is not a monolithic script collection and not a full rewrite into a single “faster” language. It is a structured accessibility platform with:

- a disciplined frontend
- a reliable orchestration layer
- a Python-based inference core
- a real persistence model
- strong runtime observability
- adaptive multimodal accessibility features

If built this way, the project can grow from a prototype into a serious educational accessibility platform with both research value and product potential.
