"""Topological analysis of transformer attention graphs.

Extract attention weight matrices from each layer of a transformer,
build graphs, compute persistent homology (β₀, β₁, β₂),
and track how topological structure evolves across layers.

This is under-explored territory — TDA on attention is sparse in literature.
"""
from __future__ import annotations
import numpy as np
import json
import time
from pathlib import Path


def load_model_and_get_attention(text: str, model_name: str = "gpt2"):
    """Load a transformer model and extract attention weights for given text."""
    import torch
    from transformers import AutoTokenizer, AutoModel

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name, output_attentions=True)
    model.eval()

    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=128)

    with torch.no_grad():
        outputs = model(**inputs)

    # attentions: tuple of (batch, heads, seq_len, seq_len) per layer
    attentions = outputs.attentions
    n_layers = len(attentions)
    n_heads = attentions[0].shape[1]
    seq_len = attentions[0].shape[2]

    print(f"  Model: {model_name}")
    print(f"  Layers: {n_layers}, Heads: {n_heads}, Seq length: {seq_len}")

    # Convert to numpy: list of (heads, seq, seq) per layer
    attention_matrices = []
    for layer_attn in attentions:
        # Average over heads for this analysis
        avg_attn = layer_attn[0].mean(dim=0).numpy()  # (seq, seq)
        attention_matrices.append(avg_attn)

    return attention_matrices, n_layers, n_heads, seq_len


def attention_to_graph(attn_matrix: np.ndarray, threshold: float = 0.0):
    """Convert attention matrix to graph adjacency.

    Edges exist where attention weight > threshold.
    Weight = attention value.
    """
    import networkx as nx

    n = attn_matrix.shape[0]
    G = nx.Graph()

    for i in range(n):
        G.add_node(i)

    for i in range(n):
        for j in range(i + 1, n):
            # Symmetrize: max of A[i,j] and A[j,i]
            w = max(attn_matrix[i, j], attn_matrix[j, i])
            if w > threshold:
                G.add_edge(i, j, weight=float(w))

    return G


def compute_graph_homology(G, max_dim: int = 2) -> dict:
    """Compute persistent homology of a graph."""
    import networkx as nx

    n = len(G.nodes)
    if n < 2:
        return {"betti": [1, 0, 0], "n_nodes": n, "n_edges": 0, "persistence_pairs": []}

    n_edges = len(G.edges)

    # Distance matrix from edge weights (invert: high attention = short distance)
    nodes = list(G.nodes)
    node_idx = {n: i for i, n in enumerate(nodes)}
    dist = np.full((n, n), 10.0)  # default large distance

    for u, v, data in G.edges(data=True):
        w = data.get("weight", 0.5)
        d = 1.0 / max(w, 0.001)  # invert: high weight = close
        i, j = node_idx[u], node_idx[v]
        dist[i][j] = d
        dist[j][i] = d

    np.fill_diagonal(dist, 0)

    # Compute persistent homology
    persistence_pairs = []
    betti = [0, 0, 0]

    try:
        import gudhi
        rips = gudhi.RipsComplex(distance_matrix=dist.tolist(), max_edge_length=12.0)
        stree = rips.create_simplex_tree(max_dimension=max_dim)
        stree.compute_persistence()

        betti_raw = stree.betti_numbers()
        for i in range(min(3, len(betti_raw))):
            betti[i] = betti_raw[i]

        for dim in range(min(max_dim + 1, 3)):
            for interval in stree.persistence_intervals_in_dimension(dim):
                b, d = float(interval[0]), float(interval[1])
                if d == float('inf'):
                    d = 12.0
                persistence_pairs.append({"dim": dim, "birth": b, "death": d, "lifetime": d - b})

    except ImportError:
        # Fallback: basic computation
        components = nx.number_connected_components(G)
        betti[0] = components
        betti[1] = max(0, n_edges - n + components)  # Euler formula

    return {
        "betti": betti,
        "n_nodes": n,
        "n_edges": n_edges,
        "persistence_pairs": persistence_pairs,
        "clustering": float(nx.average_clustering(G, weight="weight")) if n_edges > 0 else 0,
    }


def analyze_attention_topology(text: str, model_name: str = "gpt2",
                                thresholds: list[float] = None):
    """Full analysis: extract attention → build graphs → compute homology per layer."""

    if thresholds is None:
        thresholds = [0.01, 0.05, 0.1]

    print("=" * 70)
    print(f"  Transformer Attention Topology Analysis")
    print(f"  Text: '{text[:50]}...'")
    print("=" * 70)

    # Step 1: Get attention matrices
    print(f"\n[1/3] Loading model and extracting attention...")
    attn_matrices, n_layers, n_heads, seq_len = load_model_and_get_attention(text, model_name)

    results = {
        "model": model_name,
        "text": text,
        "n_layers": n_layers,
        "n_heads": n_heads,
        "seq_len": seq_len,
        "layers": {},
    }

    # Step 2: For each layer, compute topology at each threshold
    print(f"\n[2/3] Computing topology per layer...")

    for threshold in thresholds:
        print(f"\n  Threshold: {threshold}")
        print(f"  {'Layer':>6} | {'β₀':>4} {'β₁':>4} {'β₂':>4} | {'Edges':>6} | {'Clustering':>10} | {'Persistence':>10}")
        print(f"  {'─'*6}─┼─{'─'*4}─{'─'*4}─{'─'*4}─┼─{'─'*6}─┼─{'─'*10}─┼─{'─'*10}")

        for layer_idx, attn in enumerate(attn_matrices):
            G = attention_to_graph(attn, threshold=threshold)
            topo = compute_graph_homology(G)

            layer_key = f"layer_{layer_idx}_t{threshold}"
            results["layers"][layer_key] = {
                "layer": layer_idx,
                "threshold": threshold,
                **topo,
            }

            b = topo["betti"]
            n_persist = len([p for p in topo["persistence_pairs"] if p["lifetime"] > 0.1])
            print(f"  L{layer_idx:4d} | {b[0]:4d} {b[1]:4d} {b[2]:4d} | {topo['n_edges']:6d} | "
                  f"{topo['clustering']:10.4f} | {n_persist:10d}")

    # Step 3: Track β₁ evolution across layers
    print(f"\n[3/3] β₁ evolution across layers...")

    for threshold in thresholds:
        beta1_trajectory = []
        for layer_idx in range(n_layers):
            key = f"layer_{layer_idx}_t{threshold}"
            if key in results["layers"]:
                beta1_trajectory.append(results["layers"][key]["betti"][1])

        results[f"beta1_trajectory_t{threshold}"] = beta1_trajectory

        # Print trajectory
        print(f"\n  Threshold {threshold}:")
        print(f"  β₁: {beta1_trajectory}")

        # Trend analysis
        if len(beta1_trajectory) >= 2:
            first_half = np.mean(beta1_trajectory[:len(beta1_trajectory)//2])
            second_half = np.mean(beta1_trajectory[len(beta1_trajectory)//2:])
            if second_half > first_half * 1.1:
                trend = "INCREASING (β₁ grows with depth)"
            elif second_half < first_half * 0.9:
                trend = "DECREASING (β₁ collapses with depth)"
            else:
                trend = "STABLE (β₁ roughly constant)"
            print(f"  Trend: {trend}")
            print(f"  First half mean: {first_half:.1f}, Second half mean: {second_half:.1f}")
            results[f"beta1_trend_t{threshold}"] = trend

    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Transformer attention topology analysis")
    parser.add_argument("--text", default="The Riemann hypothesis states that all nontrivial zeros of the zeta function have real part one half.",
                        help="Input text to analyze")
    parser.add_argument("--model", default="gpt2", help="Model name (default: gpt2)")
    parser.add_argument("--output", default="results/attention_topology.json")
    args = parser.parse_args()

    result = analyze_attention_topology(args.text, args.model)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\n결과 저장: {args.output}")
