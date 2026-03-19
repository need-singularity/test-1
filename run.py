# run.py
"""TECS Meta-Research Engine — 진입점"""
import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="TECS Meta-Research Engine")
    parser.add_argument("--config", default="config.yaml", help="설정 파일 경로")
    parser.add_argument("--resume", default=None, help="체크포인트에서 복구 (run 디렉토리 경로)")
    parser.add_argument("--results-dir", default="results", help="결과 저장 디렉토리")
    args = parser.parse_args()

    from tecs.config import load_config
    from tecs.orchestrator import Orchestrator

    cfg = load_config(args.config)

    if args.resume:
        orch = Orchestrator.from_checkpoint(args.resume, cfg)
        print(f"Resuming from {args.resume}, phase={orch.current_phase}, gen={orch.generation}")
    else:
        orch = Orchestrator(cfg, results_dir=args.results_dir)
        print(f"TECS Engine started. Population: {cfg.search.population_size}, Seed: {cfg.search.seed}")

    orch.run()
    print(f"Done. Results: {orch.logger.run_dir}")

if __name__ == "__main__":
    main()
