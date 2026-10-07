# Living-World Storytelling and Player Experience

Phenomenal Engine treats simulation as hidden causality and story as the player's lived experience.

## Narrative hierarchy

A strong adventure can carry several layers at once:

- **Main story** — a long arc with escalating consequences, but never a compulsory rail.
- **Faction arcs** — stories about groups with their own history, internal disagreement, resources, fears, and goals.
- **Side quests** — authored stories with meaningful characters, rewards, costs, and consequences.
- **Local stories** — small mysteries or human-scale problems rooted in a place.
- **Emergent threads** — stories that become important because simulation and player attention make them important.

The player may ignore the main story for extended periods. Side activity should still produce discovery, relationships, danger, beauty, humor, useful rewards, and lasting consequences.

## Breadcrumb rule

Do not turn every interesting detail into a quest marker.

A detail should normally begin as atmosphere: an empty chair, an argument overheard on transit, a repaired object, a recurring sound, a person behaving oddly, a door painted around instead of over.

If the player shows interest, the engine can promote a thread through:

`hidden -> rumor -> lead -> active`

Promotion is based on repeated attention to authored triggers. The system should not pretend that every prop has a secret quest behind it.

## Living world

NPCs have agendas that advance when world time advances. Public consequences may surface while the player is elsewhere.

This is **off-screen simulation**, not a claim that the application continues running while closed. The reference engine advances the living world during authoritative turns, with additional pulses for travel, waiting, or rest.

NPC agendas should include ordinary life as well as plot activity: work, friendships, debts, hobbies, care obligations, status, grief, curiosity, ritual, and boredom. Important characters should not exist only to wait for the player.


## Spatial continuity

Locations and travel use the persistent node-map graph described in `docs/travel_graph.md`. The narrator must respect current location, known routes, travel duration, route discoveries, and persistent closures. Exploration can reveal new edges, and long journeys advance more living-world time than short ones.

## Submerged mechanics

Probability, cooperation models, security dilemmas, reputation, and other formal systems remain available to the adjudicator.

Default presentation should be concrete:

- someone withholds access because trust was damaged;
- a defensive deployment frightens a neighbor;
- a copy disagrees with the obligations of its predecessor;
- an ecological system resists a locally efficient bargain;
- a witness protects privacy at the cost of transparency.

Do not interrupt an immersive scene with payoff matrices, strategy labels, raw rolls, or formal analysis unless the player explicitly asks to inspect them.

## Conflict

Combat and other conflicts should be entertaining because the situation is rich, not because violence appears on a timer.

When relevant, track:

- position and movement;
- cover, gravity, terrain, visibility, and hazards;
- equipment and improvised tools;
- allies and bystanders;
- morale and goals;
- retreat, surrender, bargaining, deception, rescue, and nonlethal options;
- persistent injuries, damage, witnesses, and faction consequences.

Opponents need motives and self-preservation. A successful attack may disable, disarm, separate, frighten, expose, or force movement without automatically becoming lethal.

## Player-experience adaptation

The reference engine records a small campaign-local activity profile: exploration, investigation, combat, social play, stealth, travel, crafting, and general actions.

These are **weak behavioral signals**, not psychological conclusions.

The engine may use them to keep repeatedly chosen styles well supported or to offer contrast after several similar actions. It must not say that the player “is” a type of person because of them.

### Ethical constraints

Player-experience adaptation must not optimize for:

- compulsive use;
- session length;
- fear of missing out;
- spending;
- emotional dependency;
- covert persuasion.

Prefer agency, authored variety, clarity, meaningful consequences, and player-controlled pacing.

The profile should remain inspectable, resettable, and local to the campaign unless a player explicitly chooses a different persistence model.

## Copyright-safe authorship

Phenomenal Engine should learn from broad craft principles, not copy protected expression.

Use original:

- names;
- characters;
- factions;
- dialogue;
- lore;
- maps and geography;
- visual motifs;
- interfaces;
- quest text and quest-specific sequences;
- creatures, items, symbols, and terminology.

It is fine to use general, non-exclusive storytelling ideas such as open exploration, faction politics, environmental storytelling, branching quests, optional combat, mysteries, companions, or a main story with side content.

Do not instruct a model to imitate a living author, a specific game, a specific fictional setting, or a recognizable commercial art direction. Describe the underlying craft goal instead.
