import copy
import unittest

from phenomenal_engine.engine import Engine
from phenomenal_engine.map_ui import apply_map_action, preview_route, render_interactive_map_html
from phenomenal_engine.memory import new_memory
from phenomenal_engine.mod_loader import load_mod
from phenomenal_engine.travel import (
    discover_route,
    plan_route,
    register_dynamic_node,
    register_dynamic_route,
    set_route_override,
    visible_map,
)


class TestTravelGraph(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_mod("mods/mirror_delivery.json")

    def test_known_locations_have_stable_multi_hop_routes_with_distance_and_time(self):
        memory = new_memory(self.mod, "route-test")
        first = plan_route(self.mod, memory, "Mercury High Orbit")
        second = plan_route(self.mod, memory, "Mercury High Orbit")
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "ok")
        self.assertEqual(first["origin"], "cislunar_exchange")
        self.assertEqual(first["destination"], "mercury_high_orbit")
        self.assertEqual(first["nodes"][0], "cislunar_exchange")
        self.assertEqual(first["nodes"][-1], "mercury_high_orbit")
        self.assertGreater(len(first["segments"]), 1)
        self.assertGreater(first["total_minutes"], 10000)
        self.assertGreater(first["total_distance_m"], 1000000)
        self.assertTrue(all(seg["distance_m"] is not None for seg in first["segments"]))

    def test_preview_is_non_mutating_and_shows_distance_time_and_legs(self):
        memory = new_memory(self.mod, "preview-test")
        before = copy.deepcopy(memory)
        preview = preview_route(self.mod, memory, "mercury_high_orbit", "fastest")
        self.assertEqual(memory, before)
        self.assertEqual(preview["status"], "ok")
        self.assertEqual(preview["destination_name"], "Mercury High Orbit")
        self.assertGreater(preview["total_distance_m"], 0)
        self.assertGreater(preview["total_minutes"], 0)
        self.assertGreater(len(preview["segments"]), 1)

    def test_confirmed_travel_advances_only_one_edge(self):
        memory = new_memory(self.mod, "journey-test")
        preview = preview_route(self.mod, memory, "mercury_high_orbit", "fastest")
        first_stop = preview["segments"][0]["to"]

        result = apply_map_action(
            self.mod,
            memory,
            kind="travel_start",
            destination_id="mercury_high_orbit",
            preference="fastest",
            action_id="journey-start-1",
        )
        self.assertEqual(result["status"], "ok")
        self.assertEqual(memory["world_state"]["location"], first_stop)
        self.assertNotEqual(memory["world_state"]["location"], "mercury_high_orbit")
        self.assertIsNotNone(memory["travel_state"]["active_journey"])
        self.assertEqual(
            memory["travel_state"]["active_journey"]["destination"],
            "mercury_high_orbit",
        )
        self.assertEqual(result["world_map"]["active_journey"]["completed_segments"], 1)

    def test_continue_journey_moves_node_by_node_until_arrival(self):
        memory = new_memory(self.mod, "continue-test")
        preview = preview_route(self.mod, memory, "mercury_high_orbit", "fastest")
        expected_nodes = preview["nodes"]

        apply_map_action(
            self.mod,
            memory,
            kind="travel_start",
            destination_id="mercury_high_orbit",
            preference="fastest",
            action_id="continue-start",
        )
        visited_in_order = [memory["world_state"]["location"]]

        i = 0
        while memory["travel_state"]["active_journey"] is not None:
            i += 1
            self.assertLess(i, 20)
            apply_map_action(
                self.mod,
                memory,
                kind="travel_continue",
                action_id=f"continue-{i}",
            )
            visited_in_order.append(memory["world_state"]["location"])

        self.assertEqual(memory["world_state"]["location"], "mercury_high_orbit")
        self.assertEqual(visited_in_order, expected_nodes[1:])

    def test_scene_map_exposes_confirm_before_movement_contract(self):
        memory = new_memory(self.mod, "contract-test")
        packet = Engine(self.mod, memory).step("I inspect the mission route map.")
        interaction = packet["world_map"]["interaction"]
        self.assertEqual(interaction["selection_behavior"], "focus_and_preview_only")
        self.assertTrue(interaction["movement_requires_confirmation"])
        self.assertEqual(interaction["start"]["label"], "Confirm Travel")
        self.assertEqual(interaction["default_advance"], "one_edge_per_authoritative_turn")

    def test_reference_ui_contains_focus_preview_and_confirm_controls(self):
        memory = new_memory(self.mod, "ui-test")
        html = render_interactive_map_html(visible_map(self.mod, memory))
        self.assertIn("Tap a node to focus and preview", html)
        self.assertIn("Confirm Travel", html)
        self.assertIn("Distance", html)
        self.assertIn("Travel time", html)
        self.assertIn("Continue to next node", html)

    def test_hidden_redoubt_routes_appear_only_after_discovery(self):
        memory = new_memory(self.mod, "shortcut-test")
        visible_before = visible_map(self.mod, memory)
        self.assertNotIn("redoubt_asteroid", {n["id"] for n in visible_before["nodes"]})
        self.assertNotIn("shelter_redoubt", {e["id"] for e in visible_before["edges"]})

        engine = Engine(self.mod, memory)
        engine.step("I ask about the unregistered habitat.")
        engine.step("I inspect the unknown client's sealed workshop records.")
        engine.step("I recover the off chart Redoubt coordinates.")

        visible_after = visible_map(self.mod, memory)
        self.assertIn("redoubt_asteroid", {n["id"] for n in visible_after["nodes"]})
        self.assertIn("shelter_redoubt", {e["id"] for e in visible_after["edges"]})
        route = plan_route(
            self.mod, memory, "redoubt_asteroid", origin="perihelic_shelter"
        )
        self.assertEqual(route["status"], "ok")

    def test_route_overrides_persist_world_changes(self):
        memory = new_memory(self.mod, "delay-test")
        before = plan_route(
            self.mod,
            memory,
            "earth_escape_gate",
            origin="cislunar_exchange",
        )
        self.assertEqual(before["total_minutes"], 480.0)
        set_route_override(
            self.mod,
            memory,
            "exchange_escapegate",
            minutes=900,
            closed=False,
        )
        after = plan_route(
            self.mod,
            memory,
            "earth_escape_gate",
            origin="cislunar_exchange",
        )
        self.assertEqual(after["total_minutes"], 900.0)

    def test_runtime_locations_can_join_the_same_graph(self):
        memory = new_memory(self.mod, "dynamic-node-test")
        register_dynamic_node(
            self.mod,
            memory,
            "mercury_observatory",
            "Mercury Observatory",
            map_position={"x": 90, "y": 28, "projection": "inner-system-route-v1"},
        )
        register_dynamic_route(
            self.mod,
            memory,
            "orbit_observatory",
            "mercury_high_orbit",
            "mercury_observatory",
            minutes=90,
            distance_m=4200000,
            mode="orbital shuttle",
        )
        result = plan_route(self.mod, memory, "Mercury Observatory")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["destination"], "mercury_observatory")
        self.assertEqual(result["nodes"][-1], "mercury_observatory")
        self.assertIsNotNone(result["total_distance_m"])


if __name__ == "__main__":
    unittest.main()
