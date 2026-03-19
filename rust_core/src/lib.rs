use pyo3::prelude::*;
use rayon::prelude::*;
use rand::prelude::*;
use rand_chacha::ChaCha8Rng;
use std::collections::HashSet;

// ============================================================
// 1. Ricci Flow — edge weight update (hottest loop)
// ============================================================

/// Compute simplified Ollivier-Ricci curvature for all edges.
/// Returns curvature per edge as (u, v, curvature).
fn compute_ollivier_ricci(
    n_nodes: usize,
    edges: &[(usize, usize)],
    adj: &[Vec<usize>],
) -> Vec<f64> {
    edges
        .par_iter()
        .map(|&(u, v)| {
            let nu: HashSet<usize> = adj[u].iter().copied().collect();
            let nv: HashSet<usize> = adj[v].iter().copied().collect();
            let overlap = nu.intersection(&nv).count();
            let total = nu.union(&nv).count();
            if total > 0 {
                overlap as f64 / total as f64
            } else {
                0.0
            }
        })
        .collect()
}

/// Run n_steps of Ricci flow on edge weights.
/// edges: list of (u, v) pairs
/// weights: current edge weights
/// Returns: new weights after flow
#[pyfunction]
fn ricci_flow_step(
    n_nodes: usize,
    edges: Vec<(usize, usize)>,
    weights: Vec<f64>,
    n_steps: usize,
    step_size: f64,
) -> Vec<f64> {
    // Build adjacency list
    let mut adj = vec![vec![]; n_nodes];
    for &(u, v) in &edges {
        if u < n_nodes && v < n_nodes {
            adj[u].push(v);
            adj[v].push(u);
        }
    }

    let mut w = weights;
    for _ in 0..n_steps {
        let curvatures = compute_ollivier_ricci(n_nodes, &edges, &adj);
        w = w
            .par_iter()
            .zip(curvatures.par_iter())
            .map(|(&wi, &ci)| (wi - step_size * ci * wi).max(0.01))
            .collect();
    }
    w
}

/// Compute per-node curvature from edge curvatures.
#[pyfunction]
fn node_curvatures(
    n_nodes: usize,
    edges: Vec<(usize, usize)>,
    adj_list: Vec<Vec<usize>>,
) -> Vec<f64> {
    let edge_curvatures = compute_ollivier_ricci(n_nodes, &edges, &adj_list);

    // Map edge index by (min, max) pair
    let mut edge_map = std::collections::HashMap::new();
    for (idx, &(u, v)) in edges.iter().enumerate() {
        edge_map.insert((u.min(v), u.max(v)), edge_curvatures[idx]);
    }

    (0..n_nodes)
        .into_par_iter()
        .map(|n| {
            let neighbors = &adj_list[n];
            if neighbors.is_empty() {
                return 0.0;
            }
            let sum: f64 = neighbors
                .iter()
                .map(|&nb| *edge_map.get(&(n.min(nb), n.max(nb))).unwrap_or(&0.0))
                .sum();
            sum / neighbors.len() as f64
        })
        .collect()
}

// ============================================================
// 2. Kuramoto Oscillator — coupled phase dynamics
// ============================================================

/// Run Kuramoto oscillator dynamics.
/// phases: initial phases (N,)
/// frequencies: natural frequencies (N,)
/// adj_matrix: flattened NxN adjacency (1.0 or 0.0)
/// Returns: final phases after n_steps
#[pyfunction]
fn kuramoto_step(
    phases: Vec<f64>,
    frequencies: Vec<f64>,
    adj_flat: Vec<f64>,
    n: usize,
    coupling_k: f64,
    dt: f64,
    n_steps: usize,
) -> Vec<f64> {
    let mut theta = phases;
    let k_over_n = coupling_k / n as f64;

    for _ in 0..n_steps {
        let new_theta: Vec<f64> = (0..n)
            .into_par_iter()
            .map(|i| {
                let mut coupling_sum = 0.0;
                for j in 0..n {
                    let a = adj_flat[i * n + j];
                    if a > 0.0 {
                        coupling_sum += (theta[j] - theta[i]).sin();
                    }
                }
                theta[i] + dt * (frequencies[i] + k_over_n * coupling_sum)
            })
            .collect();
        theta = new_theta;
    }
    theta
}

/// Compute Kuramoto order parameter r = |1/N sum(e^(i*theta))|
#[pyfunction]
fn kuramoto_order_parameter(phases: Vec<f64>) -> f64 {
    let n = phases.len() as f64;
    let (sum_cos, sum_sin): (f64, f64) = phases
        .par_iter()
        .map(|&t| (t.cos(), t.sin()))
        .reduce(|| (0.0, 0.0), |(ac, as_), (c, s)| (ac + c, as_ + s));
    ((sum_cos / n).powi(2) + (sum_sin / n).powi(2)).sqrt()
}

// ============================================================
// 3. Ising Model — Monte Carlo Metropolis
// ============================================================

/// Run Ising model Monte Carlo sweeps.
/// spins: initial spins (+1 or -1) as f64
/// adj_flat: flattened NxN adjacency
/// Returns: final spins
#[pyfunction]
fn ising_monte_carlo(
    spins: Vec<f64>,
    adj_flat: Vec<f64>,
    n: usize,
    temperature: f64,
    n_sweeps: usize,
    seed: u64,
) -> Vec<f64> {
    let mut s = spins;
    let mut rng = ChaCha8Rng::seed_from_u64(seed);
    let beta = if temperature > 0.0 { 1.0 / temperature } else { 1e10 };

    for _ in 0..n_sweeps {
        for _ in 0..n {
            let i = rng.random_range(0..n);
            // Compute delta E for flipping spin i
            let mut neighbor_sum = 0.0;
            for j in 0..n {
                if adj_flat[i * n + j] > 0.0 {
                    neighbor_sum += s[j];
                }
            }
            let delta_e = 2.0 * s[i] * neighbor_sum;

            if delta_e <= 0.0 || rng.random::<f64>() < (-beta * delta_e).exp() {
                s[i] = -s[i];
            }
        }
    }
    s
}

/// Compute Ising magnetization and energy.
#[pyfunction]
fn ising_observables(spins: Vec<f64>, adj_flat: Vec<f64>, n: usize) -> (f64, f64) {
    // Magnetization = |mean(spins)|
    let mag = (spins.iter().sum::<f64>() / n as f64).abs();

    // Energy = -sum(s_i * s_j) for edges
    let energy: f64 = (0..n)
        .into_par_iter()
        .map(|i| {
            let mut e = 0.0;
            for j in (i + 1)..n {
                if adj_flat[i * n + j] > 0.0 {
                    e -= spins[i] * spins[j];
                }
            }
            e
        })
        .sum();

    (mag, energy)
}

// ============================================================
// 4. Graph conversion helpers
// ============================================================

/// Convert edge list to adjacency flat matrix (NxN).
#[pyfunction]
fn edges_to_adj_flat(n_nodes: usize, edges: Vec<(usize, usize)>) -> Vec<f64> {
    let mut adj = vec![0.0f64; n_nodes * n_nodes];
    for (u, v) in edges {
        if u < n_nodes && v < n_nodes {
            adj[u * n_nodes + v] = 1.0;
            adj[v * n_nodes + u] = 1.0;
        }
    }
    adj
}

/// Compute shortest path distances for all pairs (BFS, unweighted).
#[pyfunction]
fn all_pairs_bfs(n_nodes: usize, edges: Vec<(usize, usize)>) -> Vec<f64> {
    let mut adj = vec![vec![]; n_nodes];
    for (u, v) in edges {
        if u < n_nodes && v < n_nodes {
            adj[u].push(v);
            adj[v].push(u);
        }
    }

    let dists: Vec<Vec<f64>> = (0..n_nodes)
        .into_par_iter()
        .map(|src| {
            let mut dist = vec![f64::INFINITY; n_nodes];
            dist[src] = 0.0;
            let mut queue = std::collections::VecDeque::new();
            queue.push_back(src);
            while let Some(u) = queue.pop_front() {
                for &v in &adj[u] {
                    if dist[v] == f64::INFINITY {
                        dist[v] = dist[u] + 1.0;
                        queue.push_back(v);
                    }
                }
            }
            dist
        })
        .collect();

    // Flatten
    let mut flat = vec![0.0f64; n_nodes * n_nodes];
    for i in 0..n_nodes {
        for j in 0..n_nodes {
            flat[i * n_nodes + j] = dists[i][j];
        }
    }
    flat
}

// ============================================================
// Python module
// ============================================================

#[pymodule]
fn tecs_rust(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(ricci_flow_step, m)?)?;
    m.add_function(wrap_pyfunction!(node_curvatures, m)?)?;
    m.add_function(wrap_pyfunction!(kuramoto_step, m)?)?;
    m.add_function(wrap_pyfunction!(kuramoto_order_parameter, m)?)?;
    m.add_function(wrap_pyfunction!(ising_monte_carlo, m)?)?;
    m.add_function(wrap_pyfunction!(ising_observables, m)?)?;
    m.add_function(wrap_pyfunction!(edges_to_adj_flat, m)?)?;
    m.add_function(wrap_pyfunction!(all_pairs_bfs, m)?)?;
    Ok(())
}
