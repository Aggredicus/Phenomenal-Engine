# Persistent Node-Map Travel

Phenomenal Engine represents explorable geography as a persistent graph.

## Core model

- **Locations are nodes.**
- **Travel connections are edges.**
- A location has a stable `id`, display name, aliases, and optional schematic map coordinates.
- A route has stable endpoints, travel time, mode, risk, access description, directionality, visibility, and optional scenic value.
- The player's current location lives in `world_state.location`.
- Discoveries, visited nodes, dynamic locations, dynamic routes, route delays, and closures live in `travel_state`.

The language model may describe the trip, but it does not decide topology. Route planning is authoritative engine state.

## Arbitrary known-location travel

A player can issue natural commands such as:

- “Go to the Market of Small Suns.”
- “Take the safest route to Wildtype Delta.”
- “Head back to the Arrival Spindle.”
- “Find a scenic way to the Mirror Cloister.”

The engine resolves the destination from stable IDs, names, and aliases, then computes a multi-hop path through currently known and available edges.

The default route preference is fastest. `safest` weights route risk more strongly; `scenic` gives modest preference to authored scenic edges while still accounting for time and risk.

## Interactive destination selection

The reference map UI uses a deliberate two-step interaction:

1. **Tap or focus a node** — highlight the destination and calculate a read-only route preview.
2. **Confirm Travel** — commit the journey and traverse the first edge.

Focusing a location never moves the player, advances world time, changes RNG state, or writes the campaign save.

The preview shows, when route data is available:

- total authored physical distance;
- estimated travel time;
- number of graph legs;
- each intermediate stop;
- travel mode for each edge;
- route risk and non-public access notes.

Changing Fastest / Safest / Scenic recalculates the preview without committing movement.

After confirmation, travel becomes a persistent `active_journey`. Each ordinary Continue action advances **one edge**. This creates natural interruption points for encounters, delays, dialogue, discoveries, or player decisions at intermediate nodes.

A player may cancel at the current node or reroute from the current node. Neither action teleports the player.

### Distance rule

Schematic map coordinates are for rendering only and must not be presented as physical distance. Routes may define `distance_m`, which is summed for distance previews. If one or more legs lack authored physical distance, the UI reports distance as unsurveyed rather than inventing it from the diagram.

### Reference browser UI

Run:

```bash
python -m phenomenal_engine map-ui \
  mods/concord_tournament.json \
  runtime/concord.json
```

Then open the loopback URL printed by the command. The server binds only to `127.0.0.1`.

The browser page and other future clients use the same interaction contract exposed in `world_map.interaction`:

- `travel_start` — destination selection already previewed; explicit confirmation required;
- `travel_continue` — traverse the next graph edge;
- `travel_reroute` — recompute the remaining journey from the current node;
- `travel_cancel` — stop at the current node.

Mutating UI requests carry idempotency keys so retries or accidental double submissions do not advance two legs.

## Consistency

The graph prevents narrative teleportation.

If A connects to B in 8 minutes and B connects to C in 12 minutes, traveling from A to C must use those edges or another valid known path. A narrator cannot invent a five-minute direct tunnel unless the world state actually gains that route.

Route overrides are persistent. A delay, closure, destroyed bridge, opened checkpoint, repaired lift, or political access change can modify an edge and future routing will use the changed graph.

## Discovery

Routes may be public or hidden.

Hidden edges are absent from the player's visible map and cannot be used by automatic route planning until discovered. Story breadcrumbs can call `discover_route` when a clue becomes sufficiently established.

This makes exploration mechanically meaningful: finding an old service stair can permanently shorten future travel instead of existing only as flavor text.

## World time

Each route carries travel minutes. Successful travel adds those minutes to `world_state.world_time_minutes`.

The mod chooses `minutes_per_world_pulse`. Longer trips advance more living-world pulses, which gives NPC agendas and world events more opportunity to change while the player is in transit.

The reference implementation advances world simulation only during authoritative turns. It does not claim that the world continues executing while the application is closed.

## Dynamic locations

Stories may create places that were not authored in the original mod.

`register_dynamic_node` and `register_dynamic_route` attach runtime discoveries to the same persistent graph. This is useful for:

- temporary camps;
- newly opened rooms;
- wrecks;
- hidden workshops;
- player-built structures;
- portals or transit links created by story consequences.

Dynamic geography is campaign state rather than a rewrite of the canonical mod.

## Visible map packet

Every scene packet may include `world_map`:

- current location;
- elapsed world time;
- known nodes and stable schematic coordinates;
- known edges and travel properties;
- visited/current markers;
- persistent closures and delays.

Coordinates are a rendering aid. A mod may use literal coordinates when appropriate, but Concord uses a stable schematic projection rather than pretending its 2D map is literal station geometry.

## CLI inspection

Preview the known map without creating a save:

```bash
python -m phenomenal_engine map mods/concord_tournament.json
```

Inspect a campaign's actual discovered map:

```bash
python -m phenomenal_engine map mods/concord_tournament.json --save runtime/concord.json
```

Plan a route:

```bash
python -m phenomenal_engine route mods/concord_tournament.json "Wildtype Delta" \
  --save runtime/concord.json \
  --preference safest
```

These commands inspect state; they do not move the player.

## Authoring rules

Travel graphs should support story rather than become busywork.

Prefer a readable number of meaningful districts and routes. Give edges character: public rail, a wet garden ferry, a slow checkpoint, a dangerous maintenance tunnel. Time and access should help places feel situated.

Do not expose every secret path at campaign start. Conversely, do not make routine travel frustrating merely to simulate realism. A player should usually be able to reach any known public destination through at least one valid route.

Keep map names, geography, route descriptions, and visual expression original.
