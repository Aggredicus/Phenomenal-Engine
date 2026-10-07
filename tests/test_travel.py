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
        cls.mod = load_mod("mods/concord_tournament.json")

    def test_known_locations_have_stable_multi_hop_routes_with_distance_and_time(self):
        memory = new_memory(self.mod, "route-test")
        first = plan_route(self.mod, memory, "Wildtype Delta")
        second = plan_route(self.mod, memory, "Wildtype Delta")
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "ok")
        self.assertEqual(first["origin"], "arrival_spindle")
        self.assertEqual(first["destination"], "wildtype_delta")
        self.assertEqual(first["nodes"][0], "arrival_spindle")
        self.assertEqual(first["nodes"][-1], "wildtype_delta")
        self.assertGreater(len(first["segments"]), 1)
        self.assertGreater(first["total_minutes"], 0)
        self.assertGreater(first["total_distance_m"], 0)
        self.assertTrue(all(seg["distance_m"] is not None for seg in first["segments"]))

    def test_preview_is_non_mutating_and_shows_distance_time_and_legs(self):
        memory = new_memory(self.mod, "preview-test")
        before = copy.deepcopy(memory)
        preview = preview_route(self.mod, memory, "wildtype_delta", "fastest")
        self.assertEqual(memory, before)
        self.assertEqual(preview["status"], "ok")
        self.assertEqual(preview["destination_name"], "Wildtype Delta")
        self.assertGreater(preview["total_distance_m"], 0)
        self.assertGreater(preview["total_minutes"], 0)
        self.assertGreater(len(preview["segments"]), 1)

    def test_confirmed_travel_advances_only_one_edge(self):
        memory = new_memory(self.mod, "journey-test")
        preview = preview_route(self.mod, memory, "wildtype_delta", "fastest")
        first_stop = preview["segments"][0]["to"]

        result = apply_map_action(
            self.mod,
            memory,
            kind="travel_start",
            destination_id="wildtype_delta",
            preference="fastest",
            action_id="journey-start-1",
        )
        self.assertEqual(result["status"], "ok")
        self.assertEqual(memory["world_state"]["location"], first_stop)
        self.assertNotEqual(memory["world_state"]["location"], "wildtype_delta")
        self.assertIsNotNone(memory["travel_state"]["active_journey"])
        self.assertEqual(
            memory["travel_state"]["active_journey"]["destination"],
            "wildtype_delta",
        )
        self.assertEqual(
            result["world_map"]["active_journey"]["completed_segments"],
            1,
        )

    def test_continue_journey_moves_node_by_node_until_arrival(self):
        memory = new_memory(self.mod, "continue-test")
        preview = preview_route(self.mod, memory, "wildtype_delta", "fastest")
        expected_nodes = preview["nodes"]

        apply_map_action(
            self.mod,
            memory,
            kind="travel_start",
            destination_id="wildtype_delta",
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

        self.assertEqual(memory["world_state"]["location"], "wildtype_delta")
        self.assertEqual(visited_in_order, expected_nodes[1:])
        self.assertIsNone(memory["travel_state"]["active_journey"])

    def test_scene_map_exposes_confirm_before_movement_contract(self):
        memory = new_memory(self.mod, "contract-test")
        packet = Engine(self.mod, memory).step("I inspect the station map.")
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

    def test_hidden_shortcut_changes_route_only_after_discovery(self):
        memory = new_memory(self.mod, "shortcut-test")
        before = plan_route(
            self.mod,
            memory,
            "hushworks",
            origin="market_small_suns",
        )
        self.assertEqual(before["status"], "ok")
        self.assertNotIn(
            "market_hushworks_service",
            {edge["id"] for edge in visible_map(self.mod, memory)["edges"]},
        )

        self.assertTrue(discover_route(self.mod, memory, "market_hushworks_service"))
        after = plan_route(
            self.mod,
            memory,
            "hushworks",
            origin="market_small_suns",
        )
        self.assertIn(
            "market_hushworks_service",
            {edge["id"] for edge in visible_map(self.mod, memory)["edges"]},
        )
        self.assertLess(after["total_minutes"], before["total_minutes"])
        self.assertEqual(after["segments"][0]["route_id"], "market_hushworks_service")

    def test_story_breadcrumb_can_unlock_a_real_map_edge(self):
        memory = new_memory(self.mod, "map-clue-test")
        engine = Engine(self.mod, memory)
        engine.step("I inspect the paper map.")
        engine.step("I ask the map dealer about the unmarked deck on the paper map.")
        engine.step("I follow the paper map toward the painted-over corridor.")
        self.assertIn(
            "market_hushworks_service",
            memory["travel_state"]["known_routes"],
        )

    def test_route_overrides_persist_world_changes(self):
        memory = new_memory(self.mod, "delay-test")
        before = plan_route(
            self.mod,
            memory,
            "market_small_suns",
            origin="lantern_rail",
        )
        self.assertEqual(before["total_minutes"], 8.0)
        set_route_override(
            self.mod,
            memory,
            "lantern_market",
            minutes=14,
            closed=False,
        )
        after = plan_route(
            self.mod,
            memory,
            "market_small_suns",
            origin="lantern_rail",
        )
        self.assertEqual(after["total_minutes"], 14.0)

    def test_runtime_locations_can_join_the_same_graph(self):
        memory = new_memory(self.mod, "dynamic-node-test")
        register_dynamic_node(
            self.mod,
            memory,
            "quiet_observatory",
            "Quiet Observatory",
            map_position={"x": 96, "y": 30, "projection": "station-schematic-v1"},
        )
        register_dynamic_route(
            self.mod,
            memory,
            "oldspine_observatory",
            "old_spine",
            "quiet_observatory",
            minutes=7,
            distance_m=640,
            mode="ladder lift",
        )
        result = plan_route(self.mod, memory, "Quiet Observatory")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["destination"], "quiet_observatory")
        self.assertEqual(result["nodes"][-1], "quiet_observatory")
        self.assertIsNotNone(result["total_distance_m"])


if __name__ == "__main__":
    unittest.main()
