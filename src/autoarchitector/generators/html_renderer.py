"""
src/autoarchitector/generators/html_renderer.py

Full HTML renderer for AutoArchitector.

Produces a self-contained diagram.html with:
  - Interactive Mermaid diagram rendered in the browser
  - Filter panel: by source type, environment, tag, node type
  - Stats bar: node/edge counts by source
  - Light/dark mode toggle
  - Legend with source color coding
  - graph.json download button
  - Generated timestamp + source count footer
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from graph.model import InfraGraph

from src.autoarchitector.generators.mermaid import generate_from_graph


def render_html(graph: "InfraGraph", title: str = "Infrastructure Diagram") -> str:
    """
    Render InfraGraph to a self-contained HTML page string.
    Write the returned string to diagram.html.
    """
    mermaid_src = generate_from_graph(graph, title=title)
    stats = graph.stats()
    graph_json = _graph_to_json(graph)

    all_tags = sorted({t for e in graph.edges for t in e.tags})
    all_envs = sorted({
        n.metadata.get("environment") or ""
        for n in graph.nodes
        if n.metadata.get("environment")
    })
    all_sources = sorted({e.source_type for e in graph.edges if e.source_type})
    all_node_types = sorted({n.node_type for n in graph.nodes})

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    stats_html = "".join(
        f'<span class="stat-badge stat-{k.replace("edge_","").replace("node_","")}">{k}: {v}</span>'
        for k, v in stats.items()
    )

    def opts(items: list, label: str) -> str:
        return (
            f'<label>{label}<select data-filter="{label.lower()}" onchange="applyFilters()">'  
            f'<option value="">All</option>'
            + "".join(f'<option value="{i}">{i}</option>' for i in items)
            + "</select></label>"
        )

    filters_html = (
        opts(all_sources, "Source")
        + opts(all_envs, "Environment")
        + opts(all_tags, "Tag")
        + opts(all_node_types, "NodeType")
    )

    legend_html = "".join(
        f'<span class="legend-item"><span class="legend-dot" style="background:{c}"></span>{s}</span>'
        for s, c in {
            "networkpolicy": "#4f98a3",
            "acl": "#6daa45",
            "security_group": "#e8af34",
        }.items()
    )

    return _HTML_TEMPLATE.format(
        title=title,
        mermaid_src=mermaid_src.replace("`", "\\`"),
        stats_html=stats_html,
        filters_html=filters_html,
        legend_html=legend_html,
        graph_json=graph_json,
        generated_at=generated_at,
        node_count=stats.get("total_nodes", 0),
        edge_count=stats.get("total_edges", 0),
    )


def _graph_to_json(graph: "InfraGraph") -> str:
    data = {
        "nodes": [
            {
                "id": n.id,
                "label": n.label,
                "node_type": n.node_type,
                "metadata": n.metadata,
            }
            for n in graph.nodes
        ],
        "edges": [
            {
                "from": e.from_id,
                "to": e.to_id,
                "direction": e.direction,
                "protocol": e.protocol,
                "ports": e.ports,
                "description": e.description,
                "source_type": e.source_type,
                "source_ref": e.source_ref,
                "tags": e.tags,
            }
            for e in graph.edges
        ],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="ru" data-theme="light">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
  <style>
    :root {{
      --bg: #f7f6f2; --surface: #ffffff; --border: #dcd9d5;
      --text: #28251d; --text-muted: #7a7974; --text-faint: #bab9b4;
      --primary: #01696f; --radius: 8px;
      --shadow: 0 2px 8px rgba(0,0,0,.08);
    }}
    [data-theme="dark"] {{
      --bg: #171614; --surface: #1c1b19; --border: #393836;
      --text: #cdccca; --text-muted: #797876; --text-faint: #5a5957;
      --primary: #4f98a3;
      --shadow: 0 2px 8px rgba(0,0,0,.4);
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: var(--bg); color: var(--text); font-family: system-ui, sans-serif;
            font-size: 14px; min-height: 100vh; }}

    /* Header */
    header {{ background: var(--surface); border-bottom: 1px solid var(--border);
              padding: 12px 20px; display: flex; align-items: center;
              gap: 12px; flex-wrap: wrap; box-shadow: var(--shadow); position: sticky; top: 0; z-index: 100; }}
    header h1 {{ font-size: 16px; font-weight: 600; flex: 1; min-width: 200px; color: var(--text); }}
    .stats {{ display: flex; gap: 6px; flex-wrap: wrap; }}
    .stat-badge {{ background: var(--bg); border: 1px solid var(--border); border-radius: 12px;
                   padding: 2px 8px; font-size: 12px; color: var(--text-muted); }}
    .theme-btn {{ background: none; border: 1px solid var(--border); border-radius: var(--radius);
                  padding: 4px 10px; cursor: pointer; color: var(--text); font-size: 13px; }}
    .theme-btn:hover {{ background: var(--bg); }}
    .dl-btn {{ background: var(--primary); color: #fff; border: none; border-radius: var(--radius);
               padding: 5px 12px; cursor: pointer; font-size: 13px; }}
    .dl-btn:hover {{ opacity: .85; }}

    /* Filter bar */
    .filter-bar {{ background: var(--surface); border-bottom: 1px solid var(--border);
                   padding: 8px 20px; display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }}
    .filter-bar label {{ display: flex; flex-direction: column; gap: 2px;
                         font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: .05em; }}
    .filter-bar select {{ background: var(--bg); border: 1px solid var(--border); border-radius: 6px;
                          padding: 4px 8px; font-size: 13px; color: var(--text); cursor: pointer; }}
    .reset-btn {{ background: none; border: 1px solid var(--border); border-radius: 6px;
                  padding: 4px 10px; font-size: 12px; cursor: pointer; color: var(--text-muted); margin-top: 14px; }}
    .reset-btn:hover {{ color: var(--text); }}

    /* Legend */
    .legend {{ padding: 6px 20px; display: flex; gap: 16px; flex-wrap: wrap;
               align-items: center; font-size: 12px; color: var(--text-muted); }}
    .legend-item {{ display: flex; align-items: center; gap: 5px; }}
    .legend-dot {{ width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }}

    /* Diagram area */
    main {{ padding: 20px; overflow: auto; }}
    #diagram-container {{ background: var(--surface); border: 1px solid var(--border);
                          border-radius: var(--radius); padding: 20px;
                          min-height: 400px; box-shadow: var(--shadow); }}
    #diagram-container .mermaid {{ display: flex; justify-content: center; }}
    #diagram-container svg {{ max-width: 100%; height: auto; }}

    /* No-match state */
    #no-match {{ display: none; text-align: center; padding: 60px 20px;
                 color: var(--text-muted); font-size: 15px; }}

    /* Footer */
    footer {{ padding: 12px 20px; font-size: 12px; color: var(--text-faint);
              border-top: 1px solid var(--border); margin-top: 20px; }}
  </style>
</head>
<body>

<header>
  <h1>{title}</h1>
  <div class="stats">{stats_html}</div>
  <button class="theme-btn" onclick="toggleTheme()" title="Toggle dark/light mode">☀️ / 🌙</button>
  <button class="dl-btn" onclick="downloadJson()">JSON ↓</button>
</header>

<div class="filter-bar">
  {filters_html}
  <button class="reset-btn" onclick="resetFilters()">Reset filters</button>
</div>

<div class="legend">
  <strong>Source:</strong>
  {legend_html}
  <span style="margin-left:8px">Nodes: <strong>{node_count}</strong></span>
  <span>Edges: <strong>{edge_count}</strong></span>
</div>

<main>
  <div id="diagram-container">
    <div class="mermaid" id="mermaid-el"></div>
    <div id="no-match">🔍 No flows match the current filters. Try resetting.</div>
  </div>
</main>

<footer>Generated {generated_at} · AutoArchitector</footer>

<script>
mermaid.initialize({{ startOnLoad: false, theme: 'default', securityLevel: 'loose' }});

const FULL_GRAPH = {graph_json};
const MERMAID_BASE = `{mermaid_src}`;

let currentFilters = {{}};

function applyFilters() {{
  const selects = document.querySelectorAll('[data-filter]');
  currentFilters = {{}};
  selects.forEach(s => {{ if (s.value) currentFilters[s.dataset.filter] = s.value; }});

  const filteredEdges = FULL_GRAPH.edges.filter(e => {{
    if (currentFilters.source && e.source_type !== currentFilters.source) return false;
    if (currentFilters.environment) {{
      const srcNode = FULL_GRAPH.nodes.find(n => n.id === e.from);
      if (srcNode && srcNode.metadata.environment && srcNode.metadata.environment !== currentFilters.environment) return false;
    }}
    if (currentFilters.tag && !e.tags.includes(currentFilters.tag)) return false;
    return true;
  }});

  const activeNodeIds = new Set(filteredEdges.flatMap(e => [e.from, e.to]));
  const filteredNodes = FULL_GRAPH.nodes.filter(n => {{
    if (currentFilters.nodetype && n.node_type !== currentFilters.nodetype) return false;
    return activeNodeIds.has(n.id) || Object.keys(currentFilters).length === 0;
  }});

  if (filteredEdges.length === 0 && filteredNodes.length === 0) {{
    document.getElementById('mermaid-el').style.display = 'none';
    document.getElementById('no-match').style.display = 'block';
    return;
  }}
  document.getElementById('mermaid-el').style.display = '';
  document.getElementById('no-match').style.display = 'none';

  renderMermaid(buildFilteredMermaid(filteredNodes, filteredEdges));
}}

function buildFilteredMermaid(nodes, edges) {{
  const lines = ['flowchart LR'];
  const typeGroups = {{}};
  nodes.forEach(n => {{
    if (!typeGroups[n.node_type]) typeGroups[n.node_type] = [];
    typeGroups[n.node_type].push(n);
  }});
  Object.entries(typeGroups).forEach(([type, ns]) => {{
    lines.push(`  subgraph ${{type}}`);
    ns.forEach(n => {{
      const id = safeid(n.id);
      lines.push(`    ${{id}}["${{n.label}}"]`);
    }});
    lines.push('  end');
  }});
  const srcColors = {{ networkpolicy: '#4f98a3', acl: '#6daa45', security_group: '#e8af34' }};
  edges.forEach((e, i) => {{
    const src = safeid(e.from), dst = safeid(e.to);
    const port = e.ports.length ? e.ports.join(',') : '';
    const proto = (e.protocol && e.protocol !== 'TCP' && e.protocol !== 'ANY') ? e.protocol + ':' : '';
    const tag = proto + port;
    const desc = (e.description || '').slice(0, 40);
    const label = desc && tag ? `${{desc}} [${{tag}}]` : desc || (tag ? `[${{tag}}]` : '');
    const arrow = e.direction === 'egress' ? '-->' : '<--';
    lines.push(label ? `  ${{src}} ${{arrow}}|"${{label}}"| ${{dst}}` : `  ${{src}} ${{arrow}} ${{dst}}`);
  }});
  edges.forEach((e, i) => {{
    const c = srcColors[e.source_type] || '#aaa';
    lines.push(`  linkStyle ${{i}} stroke:${{c}},stroke-width:1.5px`);
  }});
  return lines.join('\n');
}}

async function renderMermaid(src) {{
  const el = document.getElementById('mermaid-el');
  el.removeAttribute('data-processed');
  el.innerHTML = src;
  try {{
    const {{ svg }} = await mermaid.render('mermaid-svg', src);
    el.innerHTML = svg;
  }} catch(err) {{
    el.innerHTML = '<pre style="color:red">' + err + '</pre>';
  }}
}}

function resetFilters() {{
  document.querySelectorAll('[data-filter]').forEach(s => s.value = '');
  currentFilters = {{}};
  renderMermaid(MERMAID_BASE);
  document.getElementById('mermaid-el').style.display = '';
  document.getElementById('no-match').style.display = 'none';
}}

function toggleTheme() {{
  const html = document.documentElement;
  const next = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
  html.setAttribute('data-theme', next);
  mermaid.initialize({{ startOnLoad: false, theme: next === 'dark' ? 'dark' : 'default', securityLevel: 'loose' }});
  renderMermaid(MERMAID_BASE);
}}

function downloadJson() {{
  const blob = new Blob([JSON.stringify(FULL_GRAPH, null, 2)], {{type: 'application/json'}});
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob);
  a.download = 'graph.json'; a.click();
}}

function safeid(s) {{ return s.replace(/[^a-zA-Z0-9]/g, '_'); }}

// Initial render
document.addEventListener('DOMContentLoaded', () => renderMermaid(MERMAID_BASE));
</script>
</body>
</html>
"""
