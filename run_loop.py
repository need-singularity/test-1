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

    # emergence_events.jsonl에서 상세 이벤트 로드
    ee_path = run_dir / "emergence_events.jsonl"
    result["emergence_details"] = []
    if ee_path.exists():
        for line in ee_path.read_text().strip().split("\n"):
            if line.strip():
                try:
                    result["emergence_details"].append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    return result


def load_all_emergence_events(results_dir: str) -> list[dict]:
    """모든 실행에서 창발 이벤트 수집."""
    events = []
    for run_dir in sorted(Path(results_dir).glob("runs/run_*")):
        ee_path = run_dir / "emergence_events.jsonl"
        if ee_path.exists():
            for line in ee_path.read_text().strip().split("\n"):
                if line.strip():
                    try:
                        ev = json.loads(line)
                        ev["_run"] = run_dir.name
                        events.append(ev)
                    except json.JSONDecodeError:
                        pass
    return events


def generate_analysis(result: dict, run_details: dict) -> str:
    """Claude Code CLI로 라운드 결과를 자연어 분석."""
    try:
        data = {
            "round": result["round"],
            "best_fitness": result["best_fitness"],
            "generations": result["generations"],
            "phase_reached": result["phase"],
            "emergence_events": result["emergence_events"],
            "best_architecture": result.get("best_components", {}),
            "key_metrics": {k: v for k, v in result.get("best_metrics", {}).items()
                          if isinstance(v, (int, float))},
            "emergence_details": run_details.get("emergence_details", []),
        }
        data_str = json.dumps(data, indent=2, default=str, ensure_ascii=False)
        prompt = (
            "아래는 Post-LLM 아키텍처 자율 탐색 엔진의 1라운드 실행 결과야. "
            "이걸 읽고 비전문가도 이해할 수 있는 한국어 2-4문장으로 핵심을 요약해줘. "
            "구체적 수치를 포함하고, 발견된 패턴이나 창발 이벤트가 있으면 그 의미를 설명해. "
            "기술 용어는 괄호 안에 쉬운 설명을 붙여줘. "
            "마크다운 서식 없이 평문으로만 써줘.\n\n"
            f"{data_str}"
        )
        import subprocess
        r = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True, text=True, timeout=120,
        )
        output = r.stdout.strip() if r.returncode == 0 else ""
        # 제어 문자 제거
        output = "".join(c for c in output if c.isprintable() or c in "\n ")
        if output:
            return output
    except Exception as e:
        print(f"    [분석 생성 실패: {e}]")
    return ""


def generate_overall_insight(all_results: list[dict], results_dir: str) -> str:
    """Claude Code CLI로 전체 진행 상황 종합 분석."""
    try:
        rounds_summary = []
        for r in all_results[-10:]:  # 최근 10개만
            rounds_summary.append({
                "round": r["round"],
                "fitness": r["best_fitness"],
                "emergence": r["emergence_events"],
                "architecture": r.get("best_components", {}),
            })

        all_emergence = load_all_emergence_events(results_dir)
        emergence_summary = []
        for ev in all_emergence[-5:]:
            emergence_summary.append({
                "metric": ev.get("metric"),
                "value": ev.get("value"),
                "type": ev.get("type"),
                "architecture": ev.get("candidate_components", {}),
            })

        data = {
            "total_rounds": len(all_results),
            "recent_rounds": rounds_summary,
            "fitness_trend": [r["best_fitness"] for r in all_results[-20:]],
            "total_emergence_events": sum(r.get("emergence_events", 0) for r in all_results),
            "recent_emergence": emergence_summary,
        }
        data_str = json.dumps(data, indent=2, default=str, ensure_ascii=False)
        prompt = (
            "아래는 Post-LLM 아키텍처 자율 탐색 엔진의 누적 실행 데이터야. "
            "전체 진행 상황을 비전문가도 이해할 수 있는 한국어 3-5문장으로 요약해줘. "
            "다음을 포함해: (1) 전체 진행 추이 (개선되고 있는지), "
            "(2) 가장 유망한 아키텍처 조합과 그 이유, "
            "(3) 창발 패턴에서 발견된 흥미로운 점, "
            "(4) 다음에 기대할 수 있는 것. "
            "기술 용어는 괄호 안에 쉬운 설명을 붙여줘. "
            "마크다운 서식 없이 평문으로만 써줘.\n\n"
            f"{data_str}"
        )
        import subprocess
        r = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True, text=True, timeout=120,
        )
        output = r.stdout.strip() if r.returncode == 0 else ""
        output = "".join(c for c in output if c.isprintable() or c in "\n ")
        if output:
            return output
    except Exception as e:
        print(f"    [종합 분석 생성 실패: {e}]")
    return ""


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

    # 추론 사용법 (최상단)
    lines.append("## 추론 엔진 사용법")
    lines.append("")
    lines.append("```bash")
    lines.append("# 유추 추론 — \"gravity와 경제학의 유사 구조는?\"")
    lines.append('.venv/bin/python3 infer.py --topics "Gravity" "Economics" --analogy gravity economics')
    lines.append("")
    lines.append("# 구조 비교 — \"gravity와 price의 공통 구조는?\"")
    lines.append('.venv/bin/python3 infer.py --topics "Gravity" "Price" --compare gravity price')
    lines.append("")
    lines.append("# 지식 질의 — \"고양이는 무엇인가?\"")
    lines.append('.venv/bin/python3 infer.py --topics "Cat" "Mammal" "cat IsA"')
    lines.append("")
    lines.append("# 대화형 모드")
    lines.append('.venv/bin/python3 infer.py --topics "Riemann hypothesis" "Quantum mechanics" --interactive')
    lines.append("# >> analogy gravity economics")
    lines.append("# >> compare gravity price")
    lines.append("# >> riemann hypothesis ProposedBy")
    lines.append("```")
    lines.append("")
    lines.append("> 아무 Wikipedia 주제든 `--topics`로 로드하면 실시간 지식 추출 → 위상 추론이 작동합니다.")
    lines.append("")

    # Claude 종합 분석
    overall_insight = generate_overall_insight(all_results, results_dir)
    if overall_insight:
        lines.append("## 현재 상황 요약")
        lines.append("")
        lines.append(f"> {overall_insight}")
        lines.append("")

    # 최신 라운드 분석
    latest = all_results[-1] if all_results else None
    if latest and latest.get("analysis"):
        lines.append("## 최신 라운드 분석")
        lines.append("")
        lines.append(f"**Round {latest['round']}:** {latest['analysis']}")
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

    # 창발 분석 섹션
    all_emergence = load_all_emergence_events(results_dir)
    if all_emergence:
        lines.append("## 창발 급등 이벤트")
        lines.append("")

        # 지표별 집계
        metric_counts: dict[str, int] = {}
        metric_max_sigma: dict[str, float] = {}
        for ev in all_emergence:
            m = ev.get("metric", "unknown")
            metric_counts[m] = metric_counts.get(m, 0) + 1
            sigma = ev.get("sigma", ev.get("delta", ev.get("value", 0)))
            if m not in metric_max_sigma or sigma > metric_max_sigma[m]:
                metric_max_sigma[m] = sigma

        lines.append("### 지표별 급등 빈도")
        lines.append("")
        lines.append("| 지표 | 횟수 | 최대 강도 | 비율 |")
        lines.append("|------|------|----------|------|")
        for m in sorted(metric_counts, key=metric_counts.get, reverse=True):
            pct = metric_counts[m] / len(all_emergence) * 100
            bar = "█" * max(1, int(pct / 5))
            lines.append(f"| `{m}` | {metric_counts[m]} | {metric_max_sigma[m]:.2f} | {bar} {pct:.0f}% |")
        lines.append("")

        # 조합별 창발 빈도
        combo_counts: dict[str, int] = {}
        for ev in all_emergence:
            comps = ev.get("candidate_components", {})
            if comps:
                key = " + ".join(f"{comps.get(l, '?')}" for l in ["representation", "emergence"])
                combo_counts[key] = combo_counts.get(key, 0) + 1

        if combo_counts:
            lines.append("### 창발이 잘 일어나는 조합")
            lines.append("")
            lines.append("| 표현 + 창발 조합 | 횟수 |")
            lines.append("|-----------------|------|")
            for combo in sorted(combo_counts, key=combo_counts.get, reverse=True)[:5]:
                lines.append(f"| `{combo}` | {combo_counts[combo]} |")
            lines.append("")

        # 최근 창발 이벤트 (최신 10개)
        lines.append("### 최근 창발 이벤트")
        lines.append("")
        lines.append("| 세대 | 지표 | 값 | 유형 | 강도 | 아키텍처 |")
        lines.append("|------|------|----|------|------|---------|")
        for ev in reversed(all_emergence[-10:]):
            gen = ev.get("generation", "?")
            metric = ev.get("metric", "?")
            value = ev.get("value", 0)
            etype = ev.get("type", "?")
            sigma = ev.get("sigma", ev.get("delta", "-"))
            comps = ev.get("candidate_components", {})
            arch_short = ", ".join(f"{v}" for v in list(comps.values())[:2]) if comps else "-"
            sigma_str = f"{sigma:.2f}" if isinstance(sigma, (int, float)) else str(sigma)
            lines.append(f"| {gen} | `{metric}` | {value:.4f} | {etype} | {sigma_str} | `{arch_short}` |")
        lines.append("")

        # 창발 타임라인 (mermaid)
        if len(all_emergence) >= 2:
            lines.append("### 창발 타임라인")
            lines.append("")
            lines.append("```mermaid")
            lines.append("timeline")
            lines.append("    title 창발 급등 이벤트 타임라인")
            seen_gens = set()
            for ev in all_emergence[-15:]:
                gen = ev.get("generation", 0)
                if gen not in seen_gens:
                    metric = ev.get("metric", "?")
                    etype = ev.get("type", "")
                    lines.append(f"    Gen {gen} : {metric} ({etype})")
                    seen_gens.add(gen)
            lines.append("```")
            lines.append("")
    else:
        lines.append("## 창발 급등 이벤트")
        lines.append("")
        lines.append("아직 창발 급등이 감지되지 않았습니다.")
        lines.append("")

    # 라운드별 기록 (최신이 위)
    lines.append("## 라운드 기록")
    lines.append("")
    for r in reversed(all_results):
        ts = r.get("timestamp", "")
        emergence = r.get("emergence_events", 0)
        emergence_icon = "🔥" if emergence > 0 else "⚪"
        lines.append(f"### {emergence_icon} Round {r['round']} — {ts}")
        lines.append("")
        lines.append(f"Fitness: **{r['best_fitness']:.4f}** | "
                     f"세대: {r['generations']} | Phase: {r['phase']} | "
                     f"시간: {r['elapsed_seconds']:.0f}s | 창발: {emergence}건")
        if r.get("analysis"):
            lines.append("")
            lines.append(f"> {r['analysis']}")
        lines.append("")
    lines.append("---")
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

    # 업데이트 이력
    lines.append("## 업데이트 이력")
    lines.append("")
    changelog = [
        ("2026-03-19 12:50", "v2: 타입 자동 변환 + 절대 fitness 평가", "243개 전 조합 실행 가능, fitness 1.0 고정 문제 해결"),
        ("2026-03-19 12:41", "v1: claude 자연어 분석 추가", "매 라운드 + 종합 분석 README 자동 기록"),
        ("2026-03-19 12:15", "v0: 초기 엔진 가동", "15개 구성요소, 진화+인과 분석, 28/243 호환 조합"),
    ]
    for date, version, desc in changelog:
        lines.append(f"- **{date}** — `{version}`: {desc}")
    lines.append("")

    # 버전별 라운드 구분
    v1_rounds = [r for r in all_results if r.get("version", "").startswith("v1")]
    v2_rounds = [r for r in all_results if not r.get("version", "").startswith("v1")]
    if v1_rounds and v2_rounds:
        lines.append(f"> v1 라운드 (호환성 제한): {len(v1_rounds)}회 | "
                     f"v2 라운드 (전 조합 가능): {len(v2_rounds)}회")
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
        "version": "v2_full_compat",
        "run_dir": str(orch.logger.run_dir),
        "best_fitness": orch._best_fitness,
        "generations": orch.generation,
        "phase": orch.current_phase,
        "elapsed_seconds": round(elapsed, 1),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "emergence_events": run_details.get("emergence_events", 0),
        "best_components": run_details.get("best_components", {}),
        "best_metrics": run_details.get("best_metrics", {}),
    }

    # Claude Code로 자연어 분석 생성
    result["analysis"] = generate_analysis(result, run_details)

    print(f"\n  Round {round_num} 완료:")
    print(f"    Best fitness: {orch._best_fitness:.4f}")
    print(f"    Generations:  {orch.generation}")
    print(f"    Phase:        {orch.current_phase}")
    print(f"    Emergence:    {result['emergence_events']}개 이벤트")
    print(f"    Time:         {elapsed:.1f}s")
    print(f"    Results:      {orch.logger.run_dir}")
    if result["analysis"]:
        print(f"    분석:         생성됨 ({len(result['analysis'])}자)")
    else:
        print(f"    분석:         생성 실패 (claude CLI)")

    return result


def main():
    parser = argparse.ArgumentParser(description="TECS Meta-Research Engine — 반복 실행")
    parser.add_argument("--config", default="config.yaml", help="설정 파일")
    parser.add_argument("--results-dir", default="results", help="결과 디렉토리")
    parser.add_argument("--rounds", type=int, default=0, help="반복 횟수 (0=무한, 기본)")
    parser.add_argument("--interval", type=int, default=0, help="라운드 간 대기 초 (기본 0)")
    parser.add_argument("--git-push", action="store_true", default=True, help="라운드마다 git commit+push (기본 ON)")
    parser.add_argument("--no-git-push", action="store_false", dest="git_push", help="git push 비활성화")
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

        # 이전 기록에 분석이 없으면 소급 생성
        backfill_needed = [r for r in all_results if not r.get("analysis")]
        if backfill_needed:
            print(f"  분석 소급 생성: {len(backfill_needed)}건...")
            for r in backfill_needed:
                run_dir = Path(r["run_dir"])
                if run_dir.exists():
                    details = load_run_results(run_dir)
                    r["best_components"] = r.get("best_components") or details.get("best_components", {})
                    r["best_metrics"] = r.get("best_metrics") or details.get("best_metrics", {})
                    r["emergence_details"] = details.get("emergence_details", [])
                    analysis = generate_analysis(r, details)
                    if analysis:
                        r["analysis"] = analysis
                        print(f"    Round {r['round']}: 생성됨 ({len(analysis)}자)")
            # 히스토리 파일 다시 저장
            with open(history_path, "w") as f:
                for r in all_results:
                    f.write(json.dumps(r, default=str) + "\n")

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
            if round_num < target and args.interval > 0:
                print(f"\n  {args.interval}초 후 다음 라운드...")
                time.sleep(args.interval)

            round_num += 1

    except KeyboardInterrupt:
        print(f"\n\n  ⏹ 중단 요청 감지. 안전하게 종료 중...")

    # 안전한 종료 처리 (Ctrl+C 추가 입력 무시)
    import signal
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    try:
        if all_results:
            print(f"  히스토리 저장 중...")
            # 히스토리 파일 최종 저장
            with open(history_path, "w") as f:
                for r in all_results:
                    f.write(json.dumps(r, default=str) + "\n")

            print(f"  README.md 갱신 중...")
            update_readme(all_results, args.results_dir)

            if args.git_push:
                print(f"  Git push 중...")
                sp.run(["git", "add", "results/", "README.md"], capture_output=True, timeout=10)
                sp.run(["git", "commit", "-m", f"중단 시점 저장: {len(all_results)}회 완료"],
                       capture_output=True, timeout=10)
                sp.run(["git", "push", "origin", "main"], capture_output=True, timeout=30)

            best = max(all_results, key=lambda r: r["best_fitness"])
            print(f"\n{'='*60}")
            print(f"  전체 요약 — {len(all_results)}회 실행")
            print(f"{'='*60}")
            print(f"  최고 fitness: {best['best_fitness']:.4f} (Round {best['round']})")
            print(f"  총 세대 수:   {sum(r['generations'] for r in all_results)}")
            print(f"  총 실행 시간: {sum(r['elapsed_seconds'] for r in all_results):.1f}s")
            print(f"\n  ✅ 안전하게 종료됨.")
        else:
            print(f"  실행 결과 없음. 종료.")
    except Exception as e:
        print(f"  종료 중 오류 (무시됨): {e}")
        print(f"  ✅ 종료됨.")


if __name__ == "__main__":
    main()
