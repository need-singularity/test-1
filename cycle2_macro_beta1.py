import json
import numpy as np
import networkx as nx
from itertools import combinations

np.random.seed(42)

def build_cot_graph(N, b, p_xref, p_back, topology='random'):
    G = nx.DiGraph()
    G.add_nodes_from(range(N))
    depth = {0: 0}
    queue = [0]
    next_id = 1
    while queue and next_id < N:
        parent = queue.pop(0)
        children_count = min(b, N - next_id)
        for _ in range(children_count):
            if next_id >= N:
                break
            G.add_edge(parent, next_id)
            depth[next_id] = depth[parent] + 1
            queue.append(next_id)
            next_id += 1

    max_depth = max(depth.values()) if depth else 0
    half_depth = max_depth / 2.0
    nodes_by_depth = {}
    for node, d in depth.items():
        nodes_by_depth.setdefault(d, []).append(node)

    for d, nodes in nodes_by_depth.items():
        if len(nodes) < 2:
            continue
        for i, j in combinations(nodes, 2):
            if np.random.random() < p_xref:
                G.add_edge(i, j)

    if topology == 'hub_feedback':
        hub_nodes = [n for n, d in depth.items() if d <= 1]
        deep_nodes = [n for n, d in depth.items() if d > half_depth]
        for dn in deep_nodes:
            for hn in hub_nodes:
                if np.random.random() < p_back:
                    G.add_edge(dn, hn)
    elif topology == 'full_feedback':
        all_nodes = list(depth.keys())
        for i in all_nodes:
            for j in all_nodes:
                if i != j and depth[i] - depth[j] > half_depth:
                    if np.random.random() < p_back and not G.has_edge(i, j):
                        G.add_edge(i, j)
    else:
        all_nodes = list(depth.keys())
        for i in all_nodes:
            for j in all_nodes:
                if i != j and abs(depth[i] - depth[j]) > half_depth:
                    if np.random.random() < p_back * 0.3 and not G.has_edge(i, j):
                        G.add_edge(i, j)

    return G, depth, max_depth

def compute_macro_beta1(G, depth, max_depth):
    U = G.to_undirected()
    half_depth = max_depth / 2.0

    macro_edges = []
    for u, v in U.edges():
        if u in depth and v in depth:
            if abs(depth[u] - depth[v]) > half_depth:
                macro_edges.append((u, v))

    if not macro_edges:
        return 0

    E_full = U.number_of_edges()
    V_full = U.number_of_nodes()
    C_full = nx.number_connected_components(U)
    beta1_full = E_full - V_full + C_full

    U_no_macro = U.copy()
    U_no_macro.remove_edges_from(macro_edges)
    E_reduced = U_no_macro.number_of_edges()
    V_reduced = U_no_macro.number_of_nodes()
    C_reduced = nx.number_connected_components(U_no_macro)
    beta1_reduced = E_reduced - V_reduced + C_reduced

    macro_beta1 = beta1_full - beta1_reduced
    return max(0, macro_beta1)

def theoretical_upper_bound(b, max_depth):
    return max(1, b * (b - 1) * max(1, max_depth - 1) // 2)

POP_SIZE = 40
GENERATIONS = 50
N = 30

def random_individual():
    return {
        'b': np.random.randint(2, 7),
        'p_xref': np.random.uniform(0.0, 1.0),
        'p_back': np.random.uniform(0.0, 1.0),
        'topology': np.random.choice(['random', 'hub_feedback', 'full_feedback']),
    }

def evaluate(ind, trials=3):
    scores = []
    for _ in range(trials):
        G, depth, max_depth = build_cot_graph(N, ind['b'], ind['p_xref'], ind['p_back'], ind['topology'])
        mb1 = compute_macro_beta1(G, depth, max_depth)
        scores.append(mb1)
    return np.mean(scores)

def crossover(a, b_ind):
    child = {}
    for key in a:
        child[key] = a[key] if np.random.random() < 0.5 else b_ind[key]
    return child

def mutate(ind):
    ind = dict(ind)
    key = np.random.choice(['b', 'p_xref', 'p_back', 'topology'])
    if key == 'b':
        ind['b'] = np.clip(ind['b'] + np.random.randint(-1, 2), 2, 6)
    elif key == 'p_xref':
        ind['p_xref'] = np.clip(ind['p_xref'] + np.random.normal(0, 0.15), 0, 1)
    elif key == 'p_back':
        ind['p_back'] = np.clip(ind['p_back'] + np.random.normal(0, 0.15), 0, 1)
    else:
        ind['topology'] = np.random.choice(['random', 'hub_feedback', 'full_feedback'])
    return ind

population = [random_individual() for _ in range(POP_SIZE)]
best_fitness = 0
best_ind = None

for gen in range(GENERATIONS):
    fitnesses = [evaluate(ind) for ind in population]
    ranked = sorted(zip(fitnesses, population), key=lambda x: -x[0])

    if ranked[0][0] > best_fitness:
        best_fitness = ranked[0][0]
        best_ind = dict(ranked[0][1])

    survivors = [ind for _, ind in ranked[:POP_SIZE // 3 + 1]]

    new_pop = list(survivors)
    while len(new_pop) < POP_SIZE:
        p1, p2 = survivors[np.random.randint(len(survivors))], survivors[np.random.randint(len(survivors))]
        child = crossover(p1, p2)
        if np.random.random() < 0.3:
            child = mutate(child)
        new_pop.append(child)
    population = new_pop

final_scores = []
baseline_scores = []

for trial in range(10):
    np.random.seed(1000 + trial)
    G, depth, max_depth = build_cot_graph(N, best_ind['b'], best_ind['p_xref'], best_ind['p_back'], best_ind['topology'])
    mb1 = compute_macro_beta1(G, depth, max_depth)
    final_scores.append(mb1)

    G_base, d_base, md_base = build_cot_graph(N, 1, 0.0, 0.0, 'random')
    mb1_base = compute_macro_beta1(G_base, d_base, md_base)
    baseline_scores.append(mb1_base)

avg_macro_beta1 = np.mean(final_scores)
avg_baseline = np.mean(baseline_scores)
upper = theoretical_upper_bound(best_ind['b'], max_depth)

achievement_ratio = avg_macro_beta1 / upper if upper > 0 else 0
threshold = 0.6

topo_scores = {}
for topo in ['random', 'hub_feedback', 'full_feedback']:
    ind_test = dict(best_ind)
    ind_test['topology'] = topo
    topo_scores[topo] = evaluate(ind_test, trials=5)

dominant_topo = max(topo_scores, key=topo_scores.get)

verdict = 'PASS' if (achievement_ratio >= threshold and avg_baseline == 0 and avg_macro_beta1 > 0) else 'FAIL'
error = abs(achievement_ratio - 1.0)

result = {
    'hypothesis': 'EA-optimized CoT graph achieves >=60% of theoretical macro-beta1 upper bound b(b-1)(d-1)/2 via hub-feedback topology dominance',
    'result': {
        'best_params': best_ind,
        'avg_macro_beta1': avg_macro_beta1,
        'baseline_macro_beta1': avg_baseline,
        'theoretical_upper_bound': upper,
        'achievement_ratio': round(achievement_ratio, 4),
        'topology_scores': {k: round(v, 2) for k, v in topo_scores.items()},
        'dominant_topology': dominant_topo,
    },
    'expected': {
        'achievement_ratio_min': threshold,
        'baseline_zero': True,
        'dominant_topology': 'hub_feedback or full_feedback',
    },
    'error': round(error, 4),
    'verdict': verdict
}

print(json.dumps(result))
