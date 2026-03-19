# TECS Experiment Results

This directory contains results from TECS Meta-Research Engine runs.

## Structure

- `runs/` — Individual run results (each in `run_YYYYMMDD_HHMMSS/`)
- `hall_of_fame/` — Best candidates across all runs

## Run Contents

Each run directory contains:
- `evolution.jsonl` — Generation-by-generation metrics
- `emergence_events.jsonl` — Emergence spike events
- `benchmarks.jsonl` — Benchmark results
- `phase_log.jsonl` — Phase transition log
- `causal_graph.json` — Causal analysis results
- `checkpoint.json` — Latest checkpoint for resume
- `REPORT.md` — Human-readable summary
