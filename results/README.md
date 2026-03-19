# TECS Experiment Results

## Current Version: v4 (Verification Pipeline)

All results from v1-v3 have been archived to `archive_v1_v3/` (gitignored).
v4 includes 4-stage verification: formal, counterexample, reproducibility, predictive.

## Structure

- `runs/` — Individual run results (each in `run_YYYYMMDD_HHMMSS/`)
- `hall_of_fame/` — Best candidates across all runs
- `run_history.jsonl` — Cumulative round history (auto-generated)

## Run Contents

Each run directory contains:
- `evolution.jsonl` — Generation-by-generation metrics (includes verification scores)
- `emergence_events.jsonl` — Emergence spike events
- `benchmarks.jsonl` — Benchmark results
- `phase_log.jsonl` — Phase transition log
- `causal_graph.json` — Causal analysis results
- `checkpoint.json` — Latest checkpoint for resume
- `REPORT.md` — Human-readable summary

## Version History

| Version | Description | Archived |
|---------|------------|----------|
| v1 | Initial engine, 28/243 compatible combos | archive_v1_v3/ |
| v2 | Type conversion, 243/243 combos, absolute fitness | archive_v1_v3/ |
| v3 | Inference connected, homology upgrade | archive_v1_v3/ |
| **v4** | **4-stage verification pipeline, Wasserstein distance** | **current** |
