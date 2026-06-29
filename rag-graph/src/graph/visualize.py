"""Renders the fraud network graph to a PNG for a quick look without
needing an external tool like Gephi.

Usage:
    python -m src.graph.visualize
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx

GRAPHML_PATH = Path(__file__).resolve().parents[2] / "data" / "graph" / "network_graph.graphml"
OUTPUT_PATH = Path(__file__).resolve().parents[2] / "data" / "graph" / "network_graph.png"

NODE_COLORS = {
    "mule_account": "#e74c3c",
    "phone_number": "#3498db",
    "victim_region": "#2ecc71",
    "scammer_id": "#f39c12",
}


def main() -> None:
    if not GRAPHML_PATH.exists():
        raise RuntimeError(f"No graph found at {GRAPHML_PATH}. Run `python -m src.graph.run` first.")

    graph = nx.read_graphml(GRAPHML_PATH)

    colors = [NODE_COLORS.get(graph.nodes[n].get("type"), "#95a5a6") for n in graph.nodes]
    sizes = [300 + 200 * graph.degree(n) for n in graph.nodes]
    labels = {n: graph.nodes[n].get("value", n) for n in graph.nodes}

    plt.figure(figsize=(14, 10))
    pos = nx.spring_layout(graph, seed=42, k=0.8)
    nx.draw_networkx_edges(graph, pos, alpha=0.4)
    nx.draw_networkx_nodes(graph, pos, node_color=colors, node_size=sizes)
    nx.draw_networkx_labels(graph, pos, labels=labels, font_size=8)

    legend_handles = [
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=color, markersize=10, label=node_type)
        for node_type, color in NODE_COLORS.items()
    ]
    plt.legend(handles=legend_handles, loc="upper left")
    plt.title("Fraud Network Graph")
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(OUTPUT_PATH, dpi=150)
    print(f"Saved {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
