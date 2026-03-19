"""TECS Meta-Research Engine — 반복 실행 루프

사용법:
    .venv/bin/python run_loop.py                    # 기본: 무한 반복
    .venv/bin/python run_loop.py --rounds 5         # 5회 반복
    .venv/bin/python run_loop.py --interval 60      # 라운드 간 60초 대기

각 라운드마다:
1. 이전 라운드의 hall_of_fame에서 최고 후보를 시드로 사용
2. 새로운 탐색 실행
3. 결과를 results/에 누적
4. git commit + push (선택)
"""
import argparse
import time
import json
import sys
from pathlib import Path
from datetime import datetime


def load_hall_of_fame(results_dir: str) -> list[dict]:
    """역대 최고 후보들 로드."""
    hof_path = Path(results_dir) / "hall_of_fame" / "best_candidates.jsonl"
    if not hof_path.exists():
        return []
    entries = []
    for line in hof_path.read_text().strip().split("\n"):
        if line.strip():
            entries.append(json.loads(line))
    return entries


def get_latest_run(results_dir: str) -> Path | None:
    """가장 최근 실행 디렉토리."""
    runs = sorted(Path(results_dir).glob("runs/run_*"))
    return runs[-1] if runs else None


def run_round(round_num: int, config_path: str, results_dir: str) -> dict:
    """한 라운드 실행."""
    from tecs.config import load_config
    from tecs.orchestrator import Orchestrator

    print(f"\n{'='*60}")
    print(f"  Round {round_num} — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    cfg = load_config(config_path)
    orch = Orchestrator(cfg, results_dir=results_dir)

    start = time.time()
    orch.run()
    elapsed = time.time() - start

    # 결과 요약
    result = {
        "round": round_num,
        "run_dir": str(orch.logger.run_dir),
        "best_fitness": orch._best_fitness,
        "generations": orch.generation,
        "phase": orch.current_phase,
        "elapsed_seconds": round(elapsed, 1),
    }

    print(f"\n  Round {round_num} 완료:")
    print(f"    Best fitness: {orch._best_fitness:.4f}")
    print(f"    Generations:  {orch.generation}")
    print(f"    Phase:        {orch.current_phase}")
    print(f"    Time:         {elapsed:.1f}s")
    print(f"    Results:      {orch.logger.run_dir}")

    return result


def main():
    parser = argparse.ArgumentParser(description="TECS Meta-Research Engine — 반복 실행")
    parser.add_argument("--config", default="config.yaml", help="설정 파일")
    parser.add_argument("--results-dir", default="results", help="결과 디렉토리")
    parser.add_argument("--rounds", type=int, default=0, help="반복 횟수 (0=무한)")
    parser.add_argument("--interval", type=int, default=5, help="라운드 간 대기 초")
    parser.add_argument("--git-push", action="store_true", help="라운드마다 git commit+push")
    args = parser.parse_args()

    print("TECS Meta-Research Engine — 반복 실행 모드")
    print(f"  Config:    {args.config}")
    print(f"  Results:   {args.results_dir}")
    print(f"  Rounds:    {'무한' if args.rounds == 0 else args.rounds}")
    print(f"  Interval:  {args.interval}s")
    print(f"  Git push:  {args.git_push}")

    all_results = []
    round_num = 1

    try:
        while True:
            if args.rounds > 0 and round_num > args.rounds:
                break

            result = run_round(round_num, args.config, args.results_dir)
            all_results.append(result)

            # Git commit + push
            if args.git_push:
                import subprocess
                subprocess.run(["git", "add", "results/"], capture_output=True)
                subprocess.run(
                    ["git", "commit", "-m", f"results: round {round_num}, fitness={result['best_fitness']:.4f}"],
                    capture_output=True,
                )
                subprocess.run(["git", "push", "origin", "main"], capture_output=True)
                print(f"    Git pushed.")

            # 다음 라운드 대기
            if args.rounds == 0 or round_num < args.rounds:
                print(f"\n  {args.interval}초 후 다음 라운드...")
                time.sleep(args.interval)

            round_num += 1

    except KeyboardInterrupt:
        print(f"\n\n중단됨. {len(all_results)}회 완료.")

    # 전체 요약
    if all_results:
        print(f"\n{'='*60}")
        print(f"  전체 요약 — {len(all_results)}회 실행")
        print(f"{'='*60}")
        best = max(all_results, key=lambda r: r["best_fitness"])
        print(f"  최고 fitness: {best['best_fitness']:.4f} (Round {best['round']})")
        print(f"  총 세대 수:   {sum(r['generations'] for r in all_results)}")
        print(f"  총 실행 시간: {sum(r['elapsed_seconds'] for r in all_results):.1f}s")

        # Hall of Fame 현황
        hof = load_hall_of_fame(args.results_dir)
        if hof:
            print(f"  Hall of Fame: {len(hof)}개 엔트리")


if __name__ == "__main__":
    main()
