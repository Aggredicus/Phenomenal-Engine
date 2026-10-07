import unittest

from phenomenal_engine.engine import Engine
from phenomenal_engine.memory import new_memory
from phenomenal_engine.mod_loader import load_mod
from phenomenal_engine.story import classify_action, visible_story_state


class TestLivingWorldStory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_mod("mods/concord_tournament.json")

    def test_action_modes_are_story_facing(self):
        self.assertEqual(classify_action("I search the berth for evidence."), "investigate")
        self.assertEqual(classify_action("I draw the sidearm and fight."), "combat")
        self.assertEqual(classify_action("I ride the Lantern Rail to the market."), "travel")

    def test_hidden_side_quests_stay_hidden_until_interest_promotes_thread(self):
        memory = new_memory(self.mod, "thread-test")
        self.assertEqual(memory["quests"]["side_tea"]["status"], "hidden")
        visible = visible_story_state(memory)
        self.assertNotIn("side_tea", {q["id"] for q in visible["quests"]})

        engine = Engine(self.mod, memory)
        engine.step("I look at the empty chair by the tea stall.")
        self.assertEqual(memory["story_state"]["threads"]["empty_tea"]["status"], "rumor")
        engine.step("I ask why the tea stall keeps an empty chair and place setting.")
        self.assertEqual(memory["story_state"]["threads"]["empty_tea"]["status"], "lead")
        engine.step("I sit near the absent guest's empty chair and ask who it is for.")
        self.assertEqual(memory["story_state"]["threads"]["empty_tea"]["status"], "active")
        self.assertEqual(memory["quests"]["side_tea"]["status"], "open")

    def test_world_advances_offscreen_during_play(self):
        memory = new_memory(self.mod, "world-test")
        engine = Engine(self.mod, memory)
        before = memory["story_state"]["world_pulse"]
        packet = engine.step("I ride the Lantern Rail toward the Market of Small Suns.")
        self.assertEqual(packet["story_update"]["action_mode"], "travel")
        self.assertGreater(memory["story_state"]["world_pulse"], before)
        self.assertIn("story_state", packet)

    def test_player_experience_is_local_activity_evidence_not_retention_scoring(self):
        memory = new_memory(self.mod, "experience-test")
        engine = Engine(self.mod, memory)
        engine.step("I search the dock for clues.")
        engine.step("I inspect the blank arrival listing.")
        engine.step("I investigate Juniper's berth.")
        xp = memory["player_experience"]
        self.assertGreaterEqual(xp["mode_counts"]["investigate"], 3)
        principles = " ".join(xp["principles"]).lower()
        self.assertIn("compulsive", principles)
        directives = " ".join(memory["last_scene_packet"]["story_update"]["experience_directives"]).lower()
        self.assertIn("investigate", directives)

    def test_scene_directives_keep_game_theory_submerged(self):
        memory = new_memory(self.mod, "presentation-test")
        packet = Engine(self.mod, memory).step("I talk to Sena about the missing courier.")
        directives = " ".join(packet["narrative_directives"]).lower()
        self.assertIn("submerged causality", directives)
        self.assertIn("do not lecture", directives)
        self.assertEqual(packet["presentation"]["mechanics_visibility"], "submerged")


if __name__ == "__main__":
    unittest.main()
