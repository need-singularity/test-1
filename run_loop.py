"""TECS Meta-Research Engine — 반복 실행 루프

사용법:
    .venv/bin/python run_loop.py                    # 기본: 무한 반복
    .venv/bin/python run_loop.py --rounds 5         # 5회 반복
    .venv/bin/python run_loop.py --interval 60      # 라운드 간 60초 대기

각 라운드마다:
1. 새로운 탐색 실행
2. 결과를 results/에 누적
3. README.md 자동 갱신 (최신이 위)
4. git commit + push (선택)
"""
import argparse
import time
import json
import subprocess as sp
from pathlib import Path
from datetime import datetime


def load_hall_of_fame(results_dir: str) -> list[dict]:
    hof_path = Path(results_dir) / "hall_of_fame" / "best_candidates.jsonl"
    if not hof_path.exists():
        return []
    entries = []
    for line in hof_path.read_text().strip().split("\n"):
        if line.strip():
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return entries


def load_run_results(run_dir: Path) -> dict:
    """실행 디렉토리에서 상세 결과 로드."""
    result = {"run_dir": str(run_dir)}

    # evolution.jsonl에서 마지막 세대
    evo_path = run_dir / "evolution.jsonl"
    if evo_path.exists():
        lines = [l for l in evo_path.read_text().strip().split("\n") if l.strip()]
        if lines:
            last = json.loads(lines[-1])
            result["best_components"] = last.get("best_components", {})
            result["best_metrics"] = last.get("best_metrics", {})

    # emergence_events.jsonl
    ee_path = run_dir / "emergence_events.jsonl"
    if ee_path.exists():
        lines = [l for l in ee_path.read_text().strip().split("\n") if l.strip()]
        result["emergence_events"] = len(lines)
    else:
        result["emergence_events"] = 0

    return result


def make_sparkline(values: list[float], width: int = 20) -> str:
    """값 리스트를 텍스트 스파크라인으로 변환."""
    if not values:
        return ""
    blocks = " ▁▂▃▄▅▆▇█"
    mn, mx = min(values), max(values)
    rng = mx - mn if mx != mn else 1
    return "".join(blocks[min(8, int((v - mn) / rng * 8))] for v in values[-width:])


def make_mermaid_chart(all_results: list[dict]) -> str:
    """Mermaid xychart로 fitness 추이 생성."""
    if len(all_results) < 2:
        return ""
    rounds = [str(r["round"]) for r in all_results]
    fitness = [f'{r["best_fitness"]:.4f}' for r in all_results]
    return f"""```mermaid
xychart-beta
    title "Fitness Progression"
    x-axis "Round" [{", ".join(rounds)}]
    y-axis "Best Fitness" 0 --> 1
    line [{", ".join(fitness)}]
```"""


def update_readme(all_results: list[dict], results_dir: str):
    """README.md를 최신 결과로 갱신 (최신이 위)."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    hof = load_hall_of_fame(results_dir)

    # 전체 통계
    total_rounds = len(all_results)
    if not all_results:
        return

    best_overall = max(all_results, key=lambda r: r["best_fitness"])
    total_gens = sum(r["generations"] for r in all_results)
    total_time = sum(r["elapsed_seconds"] for r in all_results)
    fitness_values = [r["best_fitness"] for r in all_results]
    sparkline = make_sparkline(fitness_values)

    # 최고 후보 아키텍처
    best_run_dir = Path(best_overall["run_dir"])
    best_details = load_run_results(best_run_dir)
    best_components = best_details.get("best_components", {})

    # README 작성
    lines = []
    lines.append("# TECS Meta-Research Engine")
    lines.append("")
    lines.append("> Post-LLM 아키텍처를 자율 탐색하는 연구 가속 엔진")
    lines.append("")
    lines.append(f"**마지막 업데이트:** {now}")
    lines.append("")

    # 전체 요약
    lines.append("## 전체 요약")
    lines.append("")
    lines.append(f"| 항목 | 값 |")
    lines.append(f"|------|------|")
    lines.append(f"| 총 라운드 | {total_rounds} |")
    lines.append(f"| 총 세대 수 | {total_gens} |")
    lines.append(f"| 총 실행 시간 | {total_time:.0f}s ({total_time/3600:.1f}h) |")
    lines.append(f"| 최고 fitness | {best_overall['best_fitness']:.4f} (Round {best_overall['round']}) |")
    lines.append(f"| 창발 이벤트 | {sum(r.get('emergence_events', 0) for r in all_results)}개 |")
    lines.append(f"| Hall of Fame | {len(hof)}개 |")
    lines.append("")

    # Fitness 추이 그래프
    lines.append("## Fitness 추이")
    lines.append("")
    lines.append(f"스파크라인: `{sparkline}`")
    lines.append("")
    mermaid = make_mermaid_chart(all_results)
    if mermaid:
        lines.append(mermaid)
        lines.append("")

    # 현재 최고 아키텍처
    if best_components:
        lines.append("## 현재 최고 아키텍처")
        lines.append("")
        lines.append("| 계층 | 구성요소 |")
        lines.append("|------|---------|")
        layer_names = {
            "representation": "표현",
            "reasoning": "추론",
            "emergence": "창발",
            "verification": "검증",
            "optimization": "최적화",
        }
        for layer, comp in best_components.items():
            kr_name = layer_names.get(layer, layer)
            lines.append(f"| {kr_name} | `{comp}` |")
        lines.append("")

    # 라운드별 기록 (최신이 위)
    lines.append("## 라운드 기록")
    lines.append("")
    lines.append("| Round | Fitness | 세대 | Phase | 시간 | 창발 | 날짜 |")
    lines.append("|-------|---------|------|-------|------|------|------|")
    for r in reversed(all_results):
        ts = r.get("timestamp", "")
        emergence = r.get("emergence_events", 0)
        emergence_str = f"🔥 {emergence}" if emergence > 0 else "-"
        lines.append(
            f"| {r['round']} | {r['best_fitness']:.4f} | {r['generations']} | "
            f"{r['phase']} | {r['elapsed_seconds']:.0f}s | {emergence_str} | {ts} |"
        )
    lines.append("")

    # 사용법 링크
    lines.append("## 사용법")
    lines.append("")
    lines.append("자세한 사용법은 [USAGE.md](USAGE.md) 참조.")
    lines.append("")
    lines.append("```bash")
    lines.append("# 설치")
    lines.append("python3 -m venv .venv && .venv/bin/pip install -r requirements.txt")
    lines.append("")
    lines.append("# 1회 실행")
    lines.append(".venv/bin/python run.py")
    lines.append("")
    lines.append("# 반복 실행 (10회, GitHub push)")
    lines.append(".venv/bin/python run_loop.py --rounds 10 --git-push")
    lines.append("```")
    lines.append("")

    # 문서 링크
    lines.append("## 문서")
    lines.append("")
    lines.append("- [설계 명세서](docs/superpowers/specs/2026-03-19-tecs-meta-research-engine-design.md)")
    lines.append("- [구현 계획](docs/superpowers/plans/2026-03-19-tecs-meta-research-engine.md)")
    lines.append("- [사용법](USAGE.md)")
    lines.append("- [원본 아키텍처 문서](docs/original/)")
    lines.append("")

    Path("README.md").write_text("\n".join(lines))


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

    # 상세 결과 수집
    run_details = load_run_results(orch.logger.run_dir)

    result = {
        "round": round_num,
        "run_dir": str(orch.logger.run_dir),
        "best_fitness": orch._best_fitness,
        "generations": orch.generation,
        "phase": orch.current_phase,
        "elapsed_seconds": round(elapsed, 1),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "emergence_events": run_details.get("emergence_events", 0),
    }

    print(f"\n  Round {round_num} 완료:")
    print(f"    Best fitness: {orch._best_fitness:.4f}")
    print(f"    Generations:  {orch.generation}")
    print(f"    Phase:        {orch.current_phase}")
    print(f"    Emergence:    {result['emergence_events']}개 이벤트")
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

    # 이전 실행 결과 로드 (이어서 기록)
    history_path = Path(args.results_dir) / "run_history.jsonl"
    all_results = []
    if history_path.exists():
        for line in history_path.read_text().strip().split("\n"):
            if line.strip():
                try:
                    all_results.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        print(f"  이전 기록: {len(all_results)}회 로드됨")

    round_num = len(all_results) + 1

    try:
        target = round_num + args.rounds - 1 if args.rounds > 0 else float("inf")
        while round_num <= target:
            result = run_round(round_num, args.config, args.results_dir)
            all_results.append(result)

            # 히스토리 저장
            with open(history_path, "a") as f:
                f.write(json.dumps(result, default=str) + "\n")

            # README.md 갱신
            update_readme(all_results, args.results_dir)
            print(f"    README.md 갱신됨")

            # Git commit + push
            if args.git_push:
                sp.run(["git", "add", "results/", "README.md"], capture_output=True)
                sp.run(
                    ["git", "commit", "-m",
                     f"Round {round_num}: fitness={result['best_fitness']:.4f}, "
                     f"gen={result['generations']}, emergence={result['emergence_events']}"],
                    capture_output=True,
                )
                sp.run(["git", "push", "origin", "main"], capture_output=True)
                print(f"    Git pushed.")

            # 다음 라운드 대기
            if round_num < target:
                print(f"\n  {args.interval}초 후 다음 라운드...")
                time.sleep(args.interval)

            round_num += 1

    except KeyboardInterrupt:
        print(f"\n\n중단됨. 이번 세션 {len(all_results) - (round_num - len(all_results) - 1)}회 완료.")

    # README 최종 갱신
    if all_results:
        update_readme(all_results, args.results_dir)
        print(f"\n  README.md 최종 갱신됨")

        best = max(all_results, key=lambda r: r["best_fitness"])
        print(f"\n{'='*60}")
        print(f"  전체 요약 — {len(all_results)}회 실행")
        print(f"{'='*60}")
        print(f"  최고 fitness: {best['best_fitness']:.4f} (Round {best['round']})")
        print(f"  총 세대 수:   {sum(r['generations'] for r in all_results)}")
        print(f"  총 실행 시간: {sum(r['elapsed_seconds'] for r in all_results):.1f}s")


if __name__ == "__main__":
    main()
