# run.py
"""TECS Meta-Research Engine — 진입점"""
import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="TECS Meta-Research Engine")
    parser.add_argument("--config", default="config.yaml", help="설정 파일 경로")
    parser.add_argument("--resume", default=None, help="체크포인트에서 복구 (run 디렉토리 경로)")
    args = parser.parse_args()

    from tecs.config import load_config
    cfg = load_config(args.config)
    print(f"TECS Engine loaded. Population: {cfg.search.population_size}, Seed: {cfg.search.seed}")
    print("Orchestrator not yet implemented.")
    sys.exit(0)

if __name__ == "__main__":
    main()
