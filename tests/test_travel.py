import unittest

from phenomenal_engine.engine import Engine
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

    def test_known_locations_have_stable_multi_hop_routes(self):
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

    def test_travel_action_updates_location_clock_and_scene_map(self):
        memory = new_memory(self.mod, "journey-test")
        packet = Engine(self.mod, memory).step("I travel to Wildtype Delta.")
        travel = packet["story_update"]["travel"]
        self.assertEqual(travel["status"], "ok")
        self.assertEqual(memory["world_state"]["location"], "wildtype_delta")
        self.assertEqual(packet["world_map"]["current_location"], "wildtype_delta")
        self.assertGreater(memory["world_state"]["world_time_minutes"], 0)
        self.assertGreaterEqual(packet["story_update"]["elapsed_world_pulses"], 2)

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
            mode="ladder lift",
        )
        result = plan_route(self.mod, memory, "Quiet Observatory")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["destination"], "quiet_observatory")
        self.assertEqual(result["nodes"][-1], "quiet_observatory")


if __name__ == "__main__":
    unittest.main()
