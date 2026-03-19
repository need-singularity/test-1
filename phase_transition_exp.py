import numpy as np
import networkx as nx
import json

def compute_beta1(G):
    return G.number_of_edges() - G.number_of_nodes() + nx.number_connected_components(G)

def multihop_fidelity(G, noise_std=0.15, n_trials=200, signal_dim=8):
    nodes = list(G.nodes())
    n = len(nodes)
    if n < 2:
        return 0.0
    fidelities = []
    rng = np.random.default_rng(42)
    for _ in range(n_trials):
        src, tgt = rng.choice(n, size=2, replace=False)
        try:
            path = nx.shortest_path(G, source=nodes[src], target=nodes[tgt])
        except nx.NetworkXNoPath:
            fidelities.append(0.0)
            continue
        signal = rng.standard_normal(signal_dim)
        signal = signal / np.linalg.norm(signal)
        current = signal.copy()
        for _ in range(len(path) - 1):
            current = current + rng.normal(0, noise_std, signal_dim)
            current = current / (np.linalg.norm(current) + 1e-12)
        cos_sim = np.dot(signal, current)
        fidelities.append(max(cos_sim, 0.0))
    return float(np.mean(fidelities))

def global_efficiency(G):
    n = G.number_of_nodes()
    if n < 2:
        return 0.0
    lengths = dict(nx.all_pairs_shortest_path_length(G))
    total = 0.0
    count = 0
    for u in lengths:
        for v, d in lengths[u].items():
            if u != v and d > 0:
                total += 1.0 / d
                count += 1
    return total / count if count > 0 else 0.0

N = 60
K = 6
p_values = np.concatenate([
    np.linspace(0.0, 0.02, 6),
    np.linspace(0.03, 0.15, 15),
    np.linspace(0.2, 1.0, 6)
])

results = []
for p in p_values:
    fids = []
    b1s = []
    effs = []
    for seed in range(5):
        G = nx.watts_strogatz_graph(N, K, p, seed=seed)
        fid = multihop_fidelity(G, noise_std=0.15, n_trials=150, signal_dim=8)
        b1 = compute_beta1(G)
        eff = global_efficiency(G)
        fids.append(fid)
        b1s.append(b1)
        effs.append(eff)
    results.append({
        'p': round(float(p), 4),
        'fidelity_mean': round(float(np.mean(fids)), 4),
        'fidelity_std': round(float(np.std(fids)), 4),
        'beta1_mean': round(float(np.mean(b1s)), 2),
        'global_efficiency': round(float(np.mean(effs)), 4),
        'clustering': round(float(np.mean([nx.average_clustering(
            nx.watts_strogatz_graph(N, K, p, seed=s)) for s in range(5)])), 4)
    })

fid_at_0 = results[0]['fidelity_mean']
fid_at_01 = None
fid_at_05 = None
for r in results:
    if abs(r['p'] - 0.1) < 0.015 and fid_at_01 is None:
        fid_at_01 = r['fidelity_mean']
    if abs(r['p'] - 0.5) < 0.05 and fid_at_05 is None:
        fid_at_05 = r['fidelity_mean']

max_fid = max(r['fidelity_mean'] for r in results)
max_fid_p = [r['p'] for r in results if r['fidelity_mean'] == max_fid][0]
jump = fid_at_01 - fid_at_0 if fid_at_01 else 0
relative_jump = jump / (fid_at_0 + 1e-9)

p_c_candidates = []
for i in range(1, len(results)):
    delta = results[i]['fidelity_mean'] - results[i-1]['fidelity_mean']
    dp = results[i]['p'] - results[i-1]['p']
    if dp > 0:
        deriv = delta / dp
        p_c_candidates.append((results[i]['p'], deriv))
p_c_candidates.sort(key=lambda x: -x[1])
p_c_est = p_c_candidates[0][0] if p_c_candidates else 0
max_deriv = p_c_candidates[0][1] if p_c_candidates else 0

beta1_at_0 = results[0]['beta1_mean']
beta1_at_peak = [r['beta1_mean'] for r in results if r['p'] == max_fid_p][0]

expected_jump = 0.15
error_rate = abs(relative_jump - expected_jump) / expected_jump if expected_jump != 0 else 0
verdict = "PASS" if relative_jump > 0.08 and p_c_est < 0.2 else "FAIL"

output = {
    'hypothesis': 'WS 그래프의 rewiring 확률 p가 ~0.05를 넘으면 다중홉 추론 충실도가 급격히 상전이한다',
    'X_var': 'rewiring_probability_p',
    'Y_var': 'multihop_signal_fidelity',
    'result': round(relative_jump, 4),
    'expected': expected_jump,
    'error': round(error_rate, 4),
    'beta1_observed': {'p=0': beta1_at_0, 'p=peak': beta1_at_peak},
    'verdict': verdict,
    'details': {
        'p_critical_estimated': round(p_c_est, 4),
        'max_derivative_at_pc': round(max_deriv, 4),
        'fidelity_p0': fid_at_0,
        'fidelity_p01': fid_at_01,
        'fidelity_p05': fid_at_05,
        'peak_fidelity': max_fid,
        'peak_fidelity_p': max_fid_p,
        'curve': [{'p': r['p'], 'fid': r['fidelity_mean'], 'clust': r['clustering'],
                    'beta1': r['beta1_mean'], 'eff': r['global_efficiency']} for r in results]
    }
}
print(json.dumps(output, ensure_ascii=False, indent=2))
