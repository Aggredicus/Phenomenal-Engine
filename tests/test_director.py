import json
import unittest
from pathlib import Path

from phenomenal_engine.director import build_director_state, validate_director_command
from phenomenal_engine.memory import new_memory
from phenomenal_engine.mod_loader import load_mod


class TestDirectorInterface(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.mod = load_mod(cls.root / "mods" / "mirror_delivery.json")

    def fresh_memory(self):
        return new_memory(self.mod, "director-test")

    def test_projection_has_four_couriers_and_four_mir_copies(self):
        state = build_director_state(self.mod, self.fresh_memory())
        self.assertEqual(state["schema_version"], "1.0.0")
        self.assertTrue(state["authority"]["director_state_is_projection"])
        self.assertFalse(state["authority"]["rng_state_exported"])
        self.assertEqual(len(state["fleet"]), 4)
        self.assertEqual(len(state["mir_copies"]), 4)
        self.assertEqual(state["mission"]["current_location_id"], "cislunar_exchange")
        local = next(x for x in state["mir_copies"] if x["copy_id"] == "mir_morrowglass")
        self.assertEqual(local["payload_state"], "sealed_pristine")
        self.assertTrue(all(x["payload_state"] == "unknown_remote" for x in state["mir_copies"] if x["copy_id"] != "mir_morrowglass"))

    def test_mir_activation_requires_explicit_human_approval(self):
        memory = self.fresh_memory()
        command = {
            "schema_version":"1.0.0","command_id":"CMD-1","type":"activate_mir","requested_by":"ai_director",
            "target_id":"mir_morrowglass","payload":{"mode":"diagnostics"},
            "approval":{"required":True,"status":"pending_human","approved_by":None,"approved_at":None},
        }
        self.assertEqual(validate_director_command(command, self.mod, memory)["status"], "rejected")
        command["approval"]["status"] = "approved"
        command["approval"]["approved_by"] = "human_gm"
        allowed = validate_director_command(command, self.mod, memory)
        self.assertEqual(allowed["status"], "allowed")
        self.assertFalse(allowed["execution_performed"])

    def test_non_activation_command_is_allowed(self):
        command = {
            "schema_version":"1.0.0","command_id":"CMD-2","type":"set_destination","requested_by":"player",
            "target_id":"venus_tangent","payload":{"destination_id":"venus_tangent"},
            "approval":{"required":False,"status":"not_required","approved_by":None,"approved_at":None},
        }
        self.assertEqual(validate_director_command(command, self.mod, self.fresh_memory())["status"], "allowed")

    def test_json_support_files_parse(self):
        for rel in [
            "schemas/director_state.schema.json",
            "schemas/director_command.schema.json",
            "examples/mirror_delivery_director_state.json",
            "examples/mirror_delivery_activate_command.json",
            "adapters/google_sheets/appsscript.json",
        ]:
            self.assertIsInstance(json.loads((self.root / rel).read_text(encoding="utf-8")), dict)


if __name__ == "__main__":
    unittest.main()
