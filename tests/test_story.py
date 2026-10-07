import unittest

from phenomenal_engine.engine import Engine
from phenomenal_engine.memory import new_memory
from phenomenal_engine.mod_loader import load_mod
from phenomenal_engine.story import classify_action, visible_story_state


class TestLivingWorldStory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_mod("mods/mirror_delivery.json")

    def test_action_modes_are_story_facing(self):
        self.assertEqual(classify_action("I search the berth for evidence."), "investigate")
        self.assertEqual(classify_action("I draw the sidearm and fight."), "combat")
        self.assertEqual(classify_action("I go to Nacre Station."), "travel")

    def test_hidden_side_quest_promotes_from_repeated_attention(self):
        memory = new_memory(self.mod, "thread-test")
        self.assertEqual(memory["quests"]["side_pax"]["status"], "hidden")
        visible = visible_story_state(memory)
        self.assertNotIn("side_pax", {q["id"] for q in visible["quests"]})

        engine = Engine(self.mod, memory)
        engine.step("I ask Pax about crew privacy.")
        self.assertEqual(memory["story_state"]["threads"]["pax_place"]["status"], "rumor")
        engine.step("I ask Pax how ship intelligences are treated after missions.")
        self.assertEqual(memory["story_state"]["threads"]["pax_place"]["status"], "lead")
        engine.step("I ask Pax whether Mir makes Pax feel replaceable.")
        self.assertEqual(memory["story_state"]["threads"]["pax_place"]["status"], "active")
        self.assertEqual(memory["quests"]["side_pax"]["status"], "open")

    def test_world_advances_offscreen_during_travel(self):
        memory = new_memory(self.mod, "world-test")
        engine = Engine(self.mod, memory)
        before = memory["story_state"]["world_pulse"]
        packet = engine.step("I travel to Earth Escape Gate.")
        self.assertEqual(packet["story_update"]["action_mode"], "travel")
        self.assertGreater(memory["story_state"]["world_pulse"], before)
        self.assertIn("story_state", packet)

    def test_long_travel_background_simulation_is_capped(self):
        memory = new_memory(self.mod, "long-trip-test")
        memory["world_state"]["location"] = "nacre_station"
        memory["travel_state"]["visited_nodes"].append("nacre_station")
        packet = Engine(self.mod, memory).step("I travel to Perihelic Shelter Nine.")
        self.assertLessEqual(
            packet["story_update"]["elapsed_world_pulses"],
            self.mod["travel_network"]["max_world_pulses_per_leg"],
        )
        self.assertGreater(memory["world_state"]["world_time_minutes"], 10000)

    def test_player_experience_remains_non_compulsive(self):
        memory = new_memory(self.mod, "experience-test")
        engine = Engine(self.mod, memory)
        engine.step("I inspect the Mir vault seal.")
        engine.step("I investigate why four copies are isolated.")
        engine.step("I search the mission contract for the activation clause.")
        xp = memory["player_experience"]
        self.assertGreaterEqual(xp["mode_counts"]["investigate"], 3)
        principles = " ".join(xp["principles"]).lower()
        self.assertIn("compulsive", principles)

    def test_mir_activation_requires_two_deliberate_steps(self):
        memory = new_memory(self.mod, "activation-test")

        armed = Engine(self.mod, memory).step(
            "I use the challenge token and activate Mir."
        )
        self.assertTrue(armed["simulation_outcome"]["success"])
        self.assertTrue(armed["simulation_outcome"]["deterministic"])
        self.assertEqual(memory["world_state"]["mirror_activation_stage"], "armed")
        self.assertEqual(memory["world_state"]["mirror_payload_status"], "sealed_pristine")
        self.assertFalse(memory["world_state"]["mirror_divergent"])
        self.assertEqual(memory["world_state"]["mirror_activation_count"], 0)

        confirmed = Engine(self.mod, memory).step("I confirm Mir activation.")
        self.assertTrue(confirmed["simulation_outcome"]["deterministic"])
        self.assertEqual(memory["world_state"]["mirror_activation_stage"], "complete")
        self.assertEqual(memory["world_state"]["mirror_payload_status"], "activated_divergent")
        self.assertTrue(memory["world_state"]["mirror_divergent"])
        self.assertEqual(memory["world_state"]["mirror_activation_count"], 1)
        self.assertEqual(memory["characters"]["mirror_instance"]["status"], "active_divergent")
        self.assertEqual(memory["quests"]["main_activation"]["status"], "open")
        self.assertEqual(memory["quests"]["main_mercury_hearing"]["status"], "open")
        developments = confirmed["story_update"]["choice_developments"]
        self.assertTrue(any(item["source_id"] == "confirm_mir_activation" for item in developments))

        Engine(self.mod, memory).step("I confirm Mir activation again.")
        self.assertEqual(memory["world_state"]["mirror_activation_count"], 1)

    def test_activation_can_be_aborted_before_final_confirmation(self):
        memory = new_memory(self.mod, "activation-abort-test")
        engine = Engine(self.mod, memory)
        engine.step("I activate Mir.")
        self.assertEqual(memory["world_state"]["mirror_activation_stage"], "armed")
        engine.step("I abort Mir activation.")
        self.assertEqual(memory["world_state"]["mirror_activation_stage"], "unarmed")
        self.assertEqual(memory["world_state"]["mirror_payload_status"], "sealed_pristine")
        self.assertEqual(memory["world_state"]["mirror_activation_count"], 0)

    def test_negative_activation_language_does_not_arm_the_vault(self):
        memory = new_memory(self.mod, "activation-negative-test")
        Engine(self.mod, memory).step("I do not activate Mir.")
        self.assertEqual(memory["world_state"]["mirror_activation_stage"], "unarmed")
        self.assertEqual(memory["world_state"]["mirror_payload_status"], "sealed_pristine")
        self.assertEqual(memory["world_state"]["mirror_activation_count"], 0)

    def test_scene_directives_keep_mechanics_submerged(self):
        memory = new_memory(self.mod, "presentation-test")
        packet = Engine(self.mod, memory).step("I talk to Juno about the other couriers.")
        directives = " ".join(packet["narrative_directives"]).lower()
        self.assertIn("submerged causality", directives)
        self.assertIn("do not lecture", directives)
        self.assertEqual(packet["presentation"]["mechanics_visibility"], "submerged")


if __name__ == "__main__":
    unittest.main()
