import copy
import math
import unittest
import io
import json
import tempfile
from pathlib import Path
from contextlib import redirect_stdout
from unittest.mock import Mock

from phenomenal_engine.adjudication import AdjudicationError, prepare_adjudication
from phenomenal_engine.engine import Engine
from phenomenal_engine.memory import new_memory, verify_ledger
from phenomenal_engine.memory import save_memory
from phenomenal_engine.cli import main
from phenomenal_engine.mod_loader import load_mod
from phenomenal_engine.probability import sample_skill_check


def check(skill="diplomacy", difficulty=0, modifiers=None, target=None):
    spec = {"mode": "check", "skill_id": skill, "difficulty": difficulty,
            "difficulty_reason": "A willing, available counterpart with an ordinary request",
            "modifiers": modifiers or [],
            "stakes": {"success": "The request is accepted", "partial_success": "A conditional counteroffer",
                       "failure": "The counterpart declines this proposal"}}
    if target:
        spec["target_id"] = target
    return spec


class AdjudicationTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_mod("mods/mirror_delivery.json")
        self.memory = new_memory(self.mod, "adjudication-test")

    def test_trained_and_expert_ordinary_tasks_usually_succeed(self):
        trained = prepare_adjudication(self.mod, self.memory, "I negotiate", check())
        expert = prepare_adjudication(self.mod, self.memory, "I pilot", check("piloting"))
        hard = prepare_adjudication(self.mod, self.memory, "I pilot", check("piloting", 2))
        prepared = prepare_adjudication(self.mod, self.memory, "I pilot", check("piloting", 2, [
            {"value": 0.5, "reason": "Juno verified the maneuver plan", "source": "crew_assistance"}]))
        self.assertAlmostEqual(trained["success_probability"], 0.8004148013)
        self.assertAlmostEqual(expert["success_probability"], 0.9414630971)
        self.assertEqual(hard["success_probability"], 0.5)
        self.assertGreater(prepared["success_probability"], hard["success_probability"])

    def test_preview_does_not_change_memory_or_rng(self):
        before = copy.deepcopy(self.memory)
        prepare_adjudication(self.mod, self.memory, "I negotiate", check())
        self.assertEqual(before, self.memory)

    def test_automatic_request_uses_no_action_rng_and_does_not_service_ship(self):
        engine = Engine(self.mod, self.memory)
        before_rng = engine.streams["actions"].state_dict()
        before_world = copy.deepcopy(self.memory["world_state"])
        packet = engine.step("I request service before our journey to Mercury.", adjudication={
            "mode": "automatic", "task": "request_service",
            "reason": "The staffed dock accepts routine service inquiries"})
        result = packet["simulation_outcome"]
        self.assertEqual(result["success_probability"], 1)
        self.assertIsNone(result["uniform_draw"])
        self.assertEqual(result["consequence_severity"], 0)
        self.assertEqual(before_rng, engine.streams["actions"].state_dict())
        self.assertEqual(packet["story_update"]["action_mode"], "social")
        self.assertIsNone(packet["story_update"]["travel"])
        for key in ("location", "morrowglass_hull", "morrowglass_propellant_margin", "world_time_minutes"):
            self.assertEqual(before_world[key], self.memory["world_state"][key])
        self.assertIn("ambient_hazard", result)

    def test_invalid_assessment_refused_before_turn_rng_or_profile_changes(self):
        engine = Engine(self.mod, self.memory)
        before = copy.deepcopy(self.memory)
        rng_before = engine.streams["actions"].state_dict()
        for spec in (check("nonexistent"), check(difficulty=float("nan")),
                     dict(check(), difficulty=True), {"mode": "automatic", "task": "repair_ship", "reason": "just do it"}):
            with self.subTest(spec=spec):
                with self.assertRaises(AdjudicationError):
                    engine.step("I act", adjudication=spec)
                self.assertEqual(before, self.memory)
                self.assertEqual(rng_before, engine.streams["actions"].state_dict())

    def test_modifiers_are_explained_bounded_and_not_double_counted(self):
        mods = [{"value": 0.5, "reason": "Useful preparation", "source": f"evidence-{i}"} for i in range(3)]
        self.assertEqual(prepare_adjudication(self.mod, self.memory, "I act", check(modifiers=mods))["context"], 1)
        for mods in ([{"value": 0.5}],
                     [{"value": 0.75, "reason": "Huge bonus", "source": "plan"}],
                     [{"value": 0.5, "reason": "Plan", "source": "plan"}] * 2):
            with self.assertRaises(AdjudicationError):
                prepare_adjudication(self.mod, self.memory, "I act", check(modifiers=mods))

    def test_group_keeps_each_npc_assessment_and_result_separate(self):
        specs = [check(target="ren_ivo", difficulty=2), check(target="sister_cairn", difficulty=0)]
        spec = {"mode": "group", "success_policy": "all", "checks": [{k:v for k,v in c.items() if k != "mode"} for c in specs]}
        preview = prepare_adjudication(self.mod, self.memory, "I offer a convoy", spec)
        self.assertNotEqual(*[c["success_probability"] for c in preview["checks"]])
        self.assertAlmostEqual(preview["success_probability"], math.prod(c["success_probability"] for c in preview["checks"]))
        engine = Engine(self.mod, self.memory)
        rng = Mock()
        rng.random.side_effect = [0.01, 0.95]
        rng.normal.return_value = 0.0
        rng.state_dict.return_value = engine.streams["actions"].state_dict()
        engine.streams["actions"] = rng
        packet = engine.step("I propose that we travel together", adjudication=spec)
        result = packet["simulation_outcome"]
        self.assertFalse(result["success"])
        self.assertEqual(result["degree"], "partial_success")
        self.assertEqual([c["success"] for c in result["checks"]], [True, False])
        self.assertEqual([c["target_id"] for c in result["checks"]], ["ren_ivo", "sister_cairn"])
        self.assertEqual(packet["story_update"]["action_mode"], "social")
        self.assertEqual(self.memory["world_state"]["world_time_minutes"], 0)
        self.assertTrue(verify_ledger(self.memory))

    def test_old_save_profile_is_adopted_without_rewriting_events(self):
        del self.memory["player_profile"]
        old_ledger = copy.deepcopy(self.memory["event_ledger"])
        preview = prepare_adjudication(self.mod, self.memory, "I negotiate", check())
        self.assertEqual(preview["profile_source"], "mod_default_for_legacy_save")
        self.assertNotIn("player_profile", self.memory)
        Engine(self.mod, self.memory).step("I negotiate", adjudication=check())
        self.assertEqual(self.memory["player_profile"]["skills"]["diplomacy"], 1)
        self.assertEqual(old_ledger, self.memory["event_ledger"][:-1])
        self.assertTrue(verify_ledger(self.memory))

    def test_authored_interlock_cannot_be_overridden(self):
        before = copy.deepcopy(self.memory)
        with self.assertRaises(AdjudicationError):
            Engine(self.mod, self.memory).step("I activate Mir", adjudication={
                "mode": "automatic", "task": "send_message", "reason": "override interlock"})
        self.assertEqual(before, self.memory)

    def test_degree_and_margin_follow_the_same_actual_roll(self):
        for skill, difficulty in ((0, 0), (100, 0), (0, 100)):
            for u in (0, 0.01, 0.49, 0.5, 0.55, 0.95, 0.999999):
                rng = Mock()
                rng.random.return_value = u
                r = sample_skill_check(rng, skill, difficulty, temperature=0.72)
                self.assertEqual(r["success"], u < r["success_probability"])
                self.assertEqual(r["success"], r["margin"] > 0)
                rng.normal.assert_not_called()
        rng = Mock(); rng.random.return_value = 0.55
        self.assertEqual(sample_skill_check(rng, 0, 0)["degree"], "partial_success")

    def test_unassessed_uncertain_action_has_no_strict_fallback(self):
        before = copy.deepcopy(self.memory)
        with self.assertRaisesRegex(AdjudicationError, "adjudication_required"):
            Engine(self.mod, self.memory).step("I persuade Ren", require_adjudication=True)
        self.assertEqual(before, self.memory)

    def test_cli_preview_is_read_only_and_play_uses_assessment(self):
        with tempfile.TemporaryDirectory() as tmp:
            save = Path(tmp) / 'save.json'
            save_memory(save, self.memory)
            before = save.read_bytes()
            args = ['mods/mirror_delivery.json', str(save), 'I negotiate']
            assessment = json.dumps(check())
            buf = io.StringIO()
            with redirect_stdout(buf):
                main(['preview-action', *args, '--adjudication', assessment])
            preview = json.loads(buf.getvalue())
            self.assertEqual(before, save.read_bytes())
            self.assertFalse(Path(str(save)+'.consent.json').exists())
            with redirect_stdout(io.StringIO()):
                main(['accept-covenant', str(save), '--account-id','fixture', '--repository','fixture/repo',
                      '--visibility','private','--storage-choice','private', '--publication-understood',
                      '--rules-accepted','--agree','--adult'])
            buf = io.StringIO()
            with redirect_stdout(buf):
                main(['play', *args, '--adjudication',assessment,'--idempotency-key','test-1'])
            result = json.loads(buf.getvalue())
            self.assertEqual(result['scene_packet']['simulation_outcome']['success_probability'],
                             preview['adjudication']['success_probability'])

    def test_group_targets_and_numeric_bounds_are_validated(self):
        good = {k:v for k,v in check(target='ren_ivo').items() if k != 'mode'}
        for checks in ([good, good], [dict(good, target_id='missing')], [dict(good, target_id=None)]):
            with self.assertRaises(AdjudicationError):
                prepare_adjudication(self.mod, self.memory, 'I act',
                                     {'mode':'group','success_policy':'any','checks':checks})
        for value in (float('inf'), -3, 5):
            with self.assertRaises(AdjudicationError):
                prepare_adjudication(self.mod, self.memory, 'I act',check(difficulty=value))
        preview=prepare_adjudication(self.mod,self.memory,'I act',
            {'mode':'group','success_policy':'any','checks':[good]})
        self.assertEqual(preview['success_probability'],preview['checks'][0]['success_probability'])


if __name__ == "__main__":
    unittest.main()
