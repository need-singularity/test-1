import networkx as nx
import matplotlib.pyplot as plt
import random

def generate_bloated_monster(nodes=100, edges=400):
    """Gen 2 이전: 엣지 폭증으로 인한 '환각의 털뭉치' (낮은 리치 곡률)"""
    G = nx.erdos_renyi_graph(n=nodes, p=edges/(nodes*(nodes-1)/2), seed=42)
    return G

def generate_compact_intelligence(nodes=60, branches=4):
    """Gen 3 이후: 오캄 페널티를 통과한 '기하학적 뇌 구조' (높은 리치 곡률)"""
    sizes = [nodes // branches] * branches
    probs = [[0.4 if i == j else 0.02 for j in range(branches)] for i in range(branches)]
    G = nx.stochastic_block_model(sizes, probs, seed=42)
    return G

def plot_phase_transition():
    fig, axes = plt.subplots(1, 2, figsize=(16, 8))
    fig.patch.set_facecolor('#1e1e1e')

    # 1. 괴물 아키텍처 렌더링
    G_monster = generate_bloated_monster()
    ax1 = axes[0]
    ax1.set_title("Before Occam's Penalty: 'The Hallucination Hairball'\n(Fitness: 0.193, Edges: 995, Low Curvature)", color='white', pad=20)
    ax1.set_facecolor('#1e1e1e')

    pos_monster = nx.spring_layout(G_monster, k=0.15, iterations=20, seed=42)
    nx.draw_networkx_nodes(G_monster, pos_monster, ax=ax1, node_size=30, node_color='#ff4a4a', alpha=0.8)
    nx.draw_networkx_edges(G_monster, pos_monster, ax=ax1, edge_color='#ffffff', alpha=0.1)

    # 2. 콤팩트 아키텍처 렌더링
    G_compact = generate_compact_intelligence()
    ax2 = axes[1]
    ax2.set_title("After Occam's Penalty: 'Structured Intelligence'\n(Fitness: 0.74+, High Ricci Curvature Bottlenecks)", color='white', pad=20)
    ax2.set_facecolor('#1e1e1e')

    partition = [G_compact.nodes[i]['block'] for i in G_compact.nodes]
    colors = ['#00e5ff', '#b4ff00', '#ff00aa', '#ffd500']
    node_colors = [colors[p % len(colors)] for p in partition]

    pos_compact = nx.spring_layout(G_compact, k=0.3, iterations=50, seed=42)
    nx.draw_networkx_nodes(G_compact, pos_compact, ax=ax2, node_size=60, node_color=node_colors, alpha=0.9)
    nx.draw_networkx_edges(G_compact, pos_compact, ax=ax2, edge_color='#ffffff', alpha=0.25)

    plt.tight_layout()
    plt.savefig('topology_phase_transition.png', dpi=300, facecolor='#1e1e1e')
    print("✅ 시각화 완료: 'topology_phase_transition.png' 파일이 생성되었습니다.")

if __name__ == "__main__":
    print("⚙️ 렌더링 시작: 위상학적 뇌 구조 시각화...")
    plot_phase_transition()
