from __future__ import annotations

from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import uuid

from .engine import Engine
from .memory import (
    find_event_by_idempotency_key,
    load_memory,
    new_memory,
    save_memory,
    validate_memory_for_mod,
)
from .mod_loader import load_mod
from .travel import plan_route, visible_map


MAX_BODY_BYTES = 16_384


def preview_route(mod: dict, memory: dict, destination_id: str, preference: str = "fastest") -> dict:
    """Return an authoritative route preview without mutating campaign state."""
    shadow = deepcopy(memory)
    plan = plan_route(mod, shadow, destination_id, preference=preference)
    nodes = {item["id"]: item for item in visible_map(mod, shadow)["nodes"]}
    if plan.get("destination") in nodes:
        plan["destination_name"] = nodes[plan["destination"]]["name"]
    if plan.get("origin") in nodes:
        plan["origin_name"] = nodes[plan["origin"]]["name"]
    return plan


def apply_map_action(
    mod: dict,
    memory: dict,
    *,
    kind: str,
    destination_id: str | None = None,
    preference: str = "fastest",
    action_id: str | None = None,
) -> dict:
    """Apply one authoritative map action to an in-memory campaign."""
    action_id = action_id or f"map-{uuid.uuid4()}"
    duplicate = find_event_by_idempotency_key(memory, action_id)
    if duplicate is not None:
        return {
            "status": "duplicate",
            "action_id": action_id,
            "scene_packet": duplicate.get("payload", {}).get("scene_packet"),
            "world_map": visible_map(mod, memory),
        }

    if preference not in {"fastest", "safest", "scenic"}:
        preference = "fastest"

    if kind == "travel_start":
        if not destination_id:
            return {"status": "error", "error": "destination_id is required"}
        action = f"I travel to {destination_id} using the {preference} route."
    elif kind == "travel_continue":
        action = "I continue journey to the next leg."
    elif kind == "travel_reroute":
        action = f"I reroute using the {preference} route."
    elif kind == "travel_cancel":
        action = "I cancel journey."
    else:
        return {"status": "error", "error": f"unsupported action kind: {kind}"}

    packet = Engine(mod, memory).step(action, idempotency_key=action_id)
    return {
        "status": "ok",
        "action_id": action_id,
        "scene_packet": packet,
        "travel": packet.get("story_update", {}).get("travel"),
        "world_map": packet.get("world_map", visible_map(mod, memory)),
    }


def _json_for_html(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False).replace("</", "<\/")


def render_interactive_map_html(map_state: dict) -> str:
    initial = _json_for_html(map_state)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Phenomenal Engine Map</title>
<style>
:root {{
  color-scheme: dark;
  --bg:#0b0d10;
  --panel:#12161b;
  --card:#171c22;
  --text:#edf2f5;
  --muted:#96a1aa;
  --line:#39434c;
  --line-active:#9ab7cc;
  --accent:#d8e6ef;
  --accent-bg:#28343d;
  --current:#d6c38d;
  --danger:#d4a0a0;
}}
* {{ box-sizing:border-box; }}
body {{
  margin:0;
  background:var(--bg);
  color:var(--text);
  font:16px/1.45 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
}}
main {{
  max-width:1100px;
  margin:0 auto;
  padding:16px;
}}
.header {{
  display:flex;
  align-items:flex-start;
  justify-content:space-between;
  gap:12px;
  flex-wrap:wrap;
  margin-bottom:12px;
}}
.header h1 {{ margin:0; font-size:1.25rem; }}
.header p {{ margin:.25rem 0 0; color:var(--muted); font-size:.92rem; }}
.layout {{
  display:grid;
  grid-template-columns:minmax(0,1.65fr) minmax(260px,.75fr);
  gap:14px;
}}
.panel {{
  background:var(--panel);
  border:1px solid #242c33;
  border-radius:14px;
  padding:14px;
}}
.map-wrap {{
  min-width:0;
  overflow:auto;
}}
svg {{
  width:100%;
  min-width:560px;
  height:auto;
  display:block;
  background:linear-gradient(180deg,#101419,#0c1014);
  border-radius:10px;
}}
.edge {{
  stroke:var(--line);
  stroke-width:.8;
  opacity:.8;
}}
.edge.preview {{
  stroke:var(--line-active);
  stroke-width:2.2;
  opacity:1;
}}
.edge.active {{
  stroke:var(--current);
  stroke-width:2.4;
  opacity:1;
}}
.node {{
  cursor:pointer;
  outline:none;
}}
.node circle {{
  fill:#222a31;
  stroke:#77838d;
  stroke-width:1.2;
}}
.node.current circle {{
  fill:#493f27;
  stroke:var(--current);
  stroke-width:2.4;
}}
.node.selected circle {{
  fill:var(--accent-bg);
  stroke:var(--accent);
  stroke-width:2.6;
}}
.node.destination circle {{
  stroke:var(--current);
  stroke-width:2.2;
}}
.node.next-stop circle {{
  stroke:#b9d6c1;
  stroke-width:2.5;
}}
.node:focus-visible circle {{
  stroke:#fff;
  stroke-width:3;
}}
.node text {{
  fill:var(--text);
  font-size:3.2px;
  text-anchor:middle;
  pointer-events:none;
}}
.controls {{
  display:grid;
  gap:12px;
  align-content:start;
}}
label {{
  display:grid;
  gap:5px;
  color:var(--muted);
  font-size:.9rem;
}}
select, button {{
  min-height:44px;
  border-radius:9px;
  border:1px solid #3a4650;
  font:inherit;
}}
select {{
  width:100%;
  padding:8px 10px;
  background:#10151a;
  color:var(--text);
}}
button {{
  padding:9px 12px;
  background:var(--accent-bg);
  color:var(--text);
  cursor:pointer;
}}
button:hover {{ border-color:#7f909d; }}
button:disabled {{ opacity:.45; cursor:not-allowed; }}
.secondary {{ background:#151b20; }}
.danger {{ color:#f2caca; border-color:#644; }}
.preview-card, .journey-card {{
  border-top:1px solid #2a333a;
  padding-top:12px;
}}
.preview-title {{
  display:flex;
  justify-content:space-between;
  align-items:baseline;
  gap:8px;
}}
.preview-title strong {{ font-size:1.05rem; }}
.muted {{ color:var(--muted); }}
.metrics {{
  display:grid;
  grid-template-columns:repeat(2,minmax(0,1fr));
  gap:8px;
  margin:10px 0;
}}
.metric {{
  background:var(--card);
  border-radius:9px;
  padding:9px;
}}
.metric b {{ display:block; font-size:1rem; }}
.metric span {{ color:var(--muted); font-size:.78rem; }}
.route-list {{
  margin:8px 0 0;
  padding-left:20px;
  color:var(--muted);
  font-size:.88rem;
}}
.actions {{
  display:flex;
  gap:8px;
  flex-wrap:wrap;
  margin-top:10px;
}}
.actions button {{ flex:1 1 130px; }}
.status {{
  min-height:1.5em;
  color:var(--muted);
  font-size:.88rem;
}}
.legend {{
  display:flex;
  flex-wrap:wrap;
  gap:10px;
  margin-top:10px;
  color:var(--muted);
  font-size:.78rem;
}}
.dot {{
  width:10px;
  height:10px;
  display:inline-block;
  border-radius:50%;
  margin-right:4px;
  border:1px solid #88949d;
}}
.dot.current {{ background:#493f27; border-color:var(--current); }}
.dot.selected {{ background:var(--accent-bg); border-color:var(--accent); }}
.dot.next {{ background:#222a31; border-color:#b9d6c1; }}
@media (max-width:760px) {{
  .layout {{ grid-template-columns:1fr; }}
  main {{ padding:10px; }}
}}
</style>
</head>
<body>
<main>
  <section class="header">
    <div>
      <h1>Travel Map</h1>
      <p>Tap a node to focus and preview. Movement begins only after Confirm Travel.</p>
    </div>
    <div id="where" class="muted"></div>
  </section>

  <section class="layout">
    <div class="panel map-wrap">
      <svg id="map" viewBox="0 0 100 90" role="img" aria-label="Known travel network"></svg>
      <div class="legend">
        <span><i class="dot current"></i>Current</span>
        <span><i class="dot selected"></i>Focused destination</span>
        <span><i class="dot next"></i>Next stop</span>
      </div>
    </div>

    <aside class="panel controls">
      <label>
        Destination
        <select id="destination"></select>
      </label>
      <label>
        Route preference
        <select id="preference">
          <option value="fastest">Fastest</option>
          <option value="safest">Safest</option>
          <option value="scenic">Scenic</option>
        </select>
      </label>

      <section class="preview-card">
        <div class="preview-title">
          <strong id="previewName">Choose a destination</strong>
          <span id="previewStatus" class="muted"></span>
        </div>
        <div class="metrics">
          <div class="metric"><b id="distance">—</b><span>Distance</span></div>
          <div class="metric"><b id="time">—</b><span>Travel time</span></div>
          <div class="metric"><b id="legs">—</b><span>Legs</span></div>
          <div class="metric"><b id="risk">—</b><span>Route risk</span></div>
        </div>
        <ol id="routeList" class="route-list"></ol>
        <div class="actions">
          <button id="confirm" type="button" disabled>Confirm Travel</button>
        </div>
      </section>

      <section id="journeyCard" class="journey-card" hidden>
        <strong id="journeyTitle">Journey</strong>
        <p id="journeyProgress" class="muted"></p>
        <div class="actions">
          <button id="continue" type="button">Continue to next node</button>
          <button id="reroute" class="secondary" type="button">Reroute</button>
          <button id="cancel" class="secondary danger" type="button">Cancel journey</button>
        </div>
      </section>

      <div id="status" class="status" aria-live="polite"></div>
    </aside>
  </section>
</main>

<script>
(() => {{
  const initial = {initial};
  let state = initial;
  let selectedId = null;
  let preview = null;
  let busy = false;

  const svg = document.getElementById("map");
  const destination = document.getElementById("destination");
  const preference = document.getElementById("preference");
  const confirmBtn = document.getElementById("confirm");
  const continueBtn = document.getElementById("continue");
  const rerouteBtn = document.getElementById("reroute");
  const cancelBtn = document.getElementById("cancel");
  const journeyCard = document.getElementById("journeyCard");
  const status = document.getElementById("status");

  function nodeById(id) {{
    return state.nodes.find(n => n.id === id);
  }}

  function formatDistance(m) {{
    if (m === null || m === undefined) return "Not surveyed";
    const n = Number(m);
    if (!Number.isFinite(n)) return "Not surveyed";
    if (n >= 1000000000) return (n / 1000000000).toFixed(1) + " million km";
    return n >= 1000 ? (n / 1000).toFixed(n >= 10000 ? 1 : 2) + " km" : Math.round(n) + " m";
  }}

  function formatTime(minutes) {{
    const n = Number(minutes);
    if (!Number.isFinite(n)) return "—";
    if (n < 60) return Math.round(n) + " min";
    if (n < 1440) {{
      const h = Math.floor(n / 60);
      const m = Math.round(n % 60);
      return h + " h" + (m ? " " + m + " min" : "");
    }}
    const d = Math.floor(n / 1440);
    const h = Math.round((n % 1440) / 60);
    return d + " d" + (h ? " " + h + " h" : "");
  }}

  function formatRisk(risk) {{
    const n = Number(risk);
    if (!Number.isFinite(n)) return "—";
    return (n * 100).toFixed(n < .1 ? 1 : 0) + "%";
  }}

  function actionId() {{
    if (globalThis.crypto && crypto.randomUUID) return "map-" + crypto.randomUUID();
    return "map-" + Date.now() + "-" + Math.random().toString(36).slice(2);
  }}

  async function api(path, body) {{
    const response = await fetch(path, {{
      method: body ? "POST" : "GET",
      headers: body ? {{"Content-Type":"application/json"}} : undefined,
      body: body ? JSON.stringify(body) : undefined
    }});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Request failed");
    return data;
  }}

  function buildDestinationSelect() {{
    const previous = selectedId || "";
    destination.replaceChildren();
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "Choose a known location";
    destination.appendChild(placeholder);
    for (const node of state.nodes) {{
      if (node.current) continue;
      const option = document.createElement("option");
      option.value = node.id;
      option.textContent = node.name;
      destination.appendChild(option);
    }}
    destination.value = [...destination.options].some(o => o.value === previous) ? previous : "";
  }}

  function renderMap() {{
    svg.replaceChildren();
    const previewEdges = new Set((preview && preview.segments || []).map(s => s.route_id));

    for (const edge of state.edges) {{
      const a = nodeById(edge.from), b = nodeById(edge.to);
      if (!a || !b || !a.map || !b.map) continue;
      const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
      line.setAttribute("x1", a.map.x);
      line.setAttribute("y1", a.map.y);
      line.setAttribute("x2", b.map.x);
      line.setAttribute("y2", b.map.y);
      line.classList.add("edge");
      if (edge.on_active_journey) line.classList.add("active");
      if (previewEdges.has(edge.id)) line.classList.add("preview");
      svg.appendChild(line);
    }}

    for (const node of state.nodes) {{
      if (!node.map || node.map.x === undefined || node.map.y === undefined) continue;
      const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
      g.classList.add("node");
      if (node.current) g.classList.add("current");
      if (node.id === selectedId) g.classList.add("selected");
      if (node.destination) g.classList.add("destination");
      if (node.next_stop) g.classList.add("next-stop");
      g.setAttribute("tabindex", "0");
      g.setAttribute("role", "button");
      g.setAttribute("aria-label", node.current ? node.name + ", current location" : "Focus " + node.name);

      const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      circle.setAttribute("cx", node.map.x);
      circle.setAttribute("cy", node.map.y);
      circle.setAttribute("r", node.current ? "2.7" : "2.2");
      const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
      text.setAttribute("x", node.map.x);
      text.setAttribute("y", Number(node.map.y) + 5.3);
      text.textContent = node.name;

      const activate = () => {{
        if (node.current) return;
        focusDestination(node.id);
      }};
      g.addEventListener("click", activate);
      g.addEventListener("keydown", e => {{
        if (e.key === "Enter" || e.key === " ") {{
          e.preventDefault();
          activate();
        }}
      }});

      g.append(circle, text);
      svg.appendChild(g);
    }}
  }}

  function renderJourney() {{
    const j = state.active_journey;
    journeyCard.hidden = !j;
    if (!j) return;
    const destinationNode = nodeById(j.destination);
    const nextNode = nodeById(j.next_node);
    document.getElementById("journeyTitle").textContent =
      "Journey to " + (destinationNode ? destinationNode.name : j.destination);
    document.getElementById("journeyProgress").textContent =
      j.completed_segments + " / " + j.total_segments + " legs complete" +
      (nextNode ? " • next: " + nextNode.name : "") +
      " • " + formatTime(j.remaining_minutes) + " remaining" +
      (j.remaining_distance_m === null || j.remaining_distance_m === undefined
        ? "" : " • " + formatDistance(j.remaining_distance_m));
    continueBtn.disabled = busy || j.status !== "active";
    rerouteBtn.disabled = busy;
    cancelBtn.disabled = busy;
  }}

  function renderPreview() {{
    const name = document.getElementById("previewName");
    const ps = document.getElementById("previewStatus");
    const list = document.getElementById("routeList");

    if (!selectedId || !preview) {{
      name.textContent = "Choose a destination";
      ps.textContent = "";
      document.getElementById("distance").textContent = "—";
      document.getElementById("time").textContent = "—";
      document.getElementById("legs").textContent = "—";
      document.getElementById("risk").textContent = "—";
      list.replaceChildren();
      confirmBtn.disabled = true;
      return;
    }}

    const node = nodeById(selectedId);
    name.textContent = node ? node.name : selectedId;
    ps.textContent = preview.status === "ok" ? "Preview only" : preview.status;
    document.getElementById("distance").textContent = formatDistance(preview.total_distance_m);
    document.getElementById("time").textContent = formatTime(preview.total_minutes);
    document.getElementById("legs").textContent = preview.segments ? String(preview.segments.length) : "—";
    document.getElementById("risk").textContent = formatRisk(preview.total_risk);
    list.replaceChildren();
    for (const seg of preview.segments || []) {{
      const li = document.createElement("li");
      const toNode = nodeById(seg.to);
      li.textContent = (toNode ? toNode.name : seg.to) + " — " +
        formatDistance(seg.distance_m) + ", " + formatTime(seg.minutes) +
        " by " + seg.mode + (seg.access && seg.access !== "public" ? " • " + seg.access : "");
      list.appendChild(li);
    }}
    confirmBtn.disabled = busy || preview.status !== "ok";
  }}

  function render() {{
    const current = nodeById(state.current_location);
    document.getElementById("where").textContent =
      "Current: " + (current ? current.name : state.current_location) +
      " • world time +" + Math.round(state.world_time_minutes || 0) + " min";
    buildDestinationSelect();
    renderMap();
    renderPreview();
    renderJourney();
  }}

  async function focusDestination(id) {{
    selectedId = id || null;
    destination.value = selectedId || "";
    preview = null;
    render();
    if (!selectedId) return;
    status.textContent = "Calculating route preview…";
    try {{
      preview = await api("/api/preview", {{
        destination_id: selectedId,
        preference: preference.value
      }});
      status.textContent = "Route preview ready. No movement has occurred.";
    }} catch (err) {{
      preview = {{status:"error"}};
      status.textContent = err.message;
    }}
    render();
  }}

  async function mutate(kind, extra={{}}) {{
    if (busy) return;
    busy = true;
    status.textContent = "Applying travel action…";
    render();
    try {{
      const result = await api("/api/action", {{
        kind,
        preference: preference.value,
        action_id: actionId(),
        ...extra
      }});
      state = result.world_map;
      const travel = result.travel || {{}};
      const current = nodeById(state.current_location);
      if (travel.status === "completed") {{
        status.textContent = "Arrived at " + (current ? current.name : state.current_location) + ".";
      }} else if (travel.status === "blocked") {{
        status.textContent = "Journey paused: " + (travel.blocked_reason || "route unavailable") + ".";
      }} else if (kind === "travel_cancel") {{
        status.textContent = "Journey cancelled. You remain at the current node.";
      }} else {{
        status.textContent = "Reached " + (current ? current.name : state.current_location) +
          (state.active_journey ? ". Journey remains active." : ".");
      }}
      if (kind === "travel_start") {{
        selectedId = state.active_journey ? state.active_journey.destination : null;
      }}
      if (selectedId) {{
        try {{
          preview = await api("/api/preview", {{
            destination_id:selectedId,
            preference:preference.value
          }});
        }} catch (_) {{
          preview = null;
        }}
      }}
    }} catch (err) {{
      status.textContent = err.message;
    }} finally {{
      busy = false;
      render();
    }}
  }}

  destination.addEventListener("change", () => focusDestination(destination.value));
  preference.addEventListener("change", () => {{
    if (selectedId) focusDestination(selectedId);
  }});
  confirmBtn.addEventListener("click", () => {{
    if (!selectedId || !preview || preview.status !== "ok") return;
    mutate("travel_start", {{destination_id:selectedId}});
  }});
  continueBtn.addEventListener("click", () => mutate("travel_continue"));
  rerouteBtn.addEventListener("click", () => mutate("travel_reroute"));
  cancelBtn.addEventListener("click", () => mutate("travel_cancel"));

  render();
}})();
</script>
</body>
</html>
"""


class MapApplication:
    def __init__(self, mod_path: str | Path, save_path: str | Path, seed: str = "map-ui"):
        self.mod_path = Path(mod_path)
        self.save_path = Path(save_path)
        self.mod = load_mod(self.mod_path)
        self.lock = threading.Lock()
        if self.save_path.exists():
            memory = load_memory(self.save_path)
            validate_memory_for_mod(memory, self.mod)
        else:
            memory = new_memory(self.mod, seed)
            save_memory(self.save_path, memory)

    def load(self) -> dict:
        memory = load_memory(self.save_path)
        validate_memory_for_mod(memory, self.mod)
        return memory

    def state(self) -> dict:
        with self.lock:
            return visible_map(self.mod, self.load())

    def preview(self, destination_id: str, preference: str) -> dict:
        with self.lock:
            return preview_route(self.mod, self.load(), destination_id, preference)

    def act(
        self,
        kind: str,
        destination_id: str | None,
        preference: str,
        action_id: str | None,
    ) -> dict:
        with self.lock:
            memory = self.load()
            result = apply_map_action(
                self.mod,
                memory,
                kind=kind,
                destination_id=destination_id,
                preference=preference,
                action_id=action_id,
            )
            if result.get("status") in {"ok", "duplicate"}:
                save_memory(self.save_path, memory)
            return result


def _handler(app: MapApplication):
    class Handler(BaseHTTPRequestHandler):
        server_version = "PhenomenalMap/1.0"

        def _send_json(self, status: int, payload: dict) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _send_html(self, html: str) -> None:
            body = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def _read_json(self) -> dict:
            if self.headers.get("Content-Type", "").split(";", 1)[0].strip() != "application/json":
                raise ValueError("Content-Type must be application/json")
            length = int(self.headers.get("Content-Length", "0"))
            if length < 0 or length > MAX_BODY_BYTES:
                raise ValueError("request body is too large")
            raw = self.rfile.read(length)
            data = json.loads(raw.decode("utf-8") or "{}")
            if not isinstance(data, dict):
                raise ValueError("JSON body must be an object")
            return data

        def do_GET(self) -> None:
            path = self.path.split("?", 1)[0]
            try:
                if path == "/":
                    self._send_html(render_interactive_map_html(app.state()))
                elif path == "/api/state":
                    self._send_json(200, app.state())
                else:
                    self._send_json(404, {"error": "not found"})
            except Exception as exc:
                self._send_json(500, {"error": str(exc)})

        def do_POST(self) -> None:
            path = self.path.split("?", 1)[0]
            try:
                data = self._read_json()
                if path == "/api/preview":
                    destination_id = str(data.get("destination_id", ""))
                    preference = str(data.get("preference", "fastest"))
                    self._send_json(200, app.preview(destination_id, preference))
                    return
                if path == "/api/action":
                    result = app.act(
                        str(data.get("kind", "")),
                        str(data["destination_id"]) if data.get("destination_id") else None,
                        str(data.get("preference", "fastest")),
                        str(data["action_id"]) if data.get("action_id") else None,
                    )
                    self._send_json(200 if result.get("status") != "error" else 400, result)
                    return
                self._send_json(404, {"error": "not found"})
            except (ValueError, json.JSONDecodeError) as exc:
                self._send_json(400, {"error": str(exc)})
            except Exception as exc:
                self._send_json(500, {"error": str(exc)})

        def log_message(self, fmt: str, *args) -> None:
            return

    return Handler


def serve_map_ui(
    mod_path: str | Path,
    save_path: str | Path,
    *,
    port: int = 8765,
    seed: str = "map-ui",
) -> None:
    app = MapApplication(mod_path, save_path, seed=seed)
    server = ThreadingHTTPServer(("127.0.0.1", int(port)), _handler(app))
    print(f"Phenomenal Engine map: http://127.0.0.1:{server.server_port}")
    print("Tap a node to preview; Confirm Travel is required before movement.")
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
