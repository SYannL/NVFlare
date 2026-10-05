# Copyright (c) 2026, NVIDIA CORPORATION.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import importlib.util
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("memco_collab_job", PROJECT_ROOT / "job.py")
COLLAB_JOB = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COLLAB_JOB)


class CollabJobTest(unittest.TestCase):
    def test_canonical_configs_preserve_domain_order_and_limits(self):
        expected = {
            "pddl": ["gripper", "blockworld", "barman", "tyreworld"],
            "fever": ["A_film_tv", "B_music"],
            "alfworld": ["bathroom", "bedroom", "kitchen", "living"],
        }
        for family, domains in expected.items():
            config = COLLAB_JOB._load_config(PROJECT_ROOT / "configs" / f"{family}.json", None, None)
            self.assertEqual(domains, config["domains"])
            self.assertEqual(30, config["max_trials"])
            self.assertEqual(0.35, config["promotion_threshold"])
            self.assertEqual("wilson", config["promotion_policy"])
            self.assertEqual(0.05, config["wilson_alpha"])
            self.assertEqual(0.35, config["wilson_threshold"])

    def test_site_domain_mapping_preserves_canonical_order(self):
        config = {"domains": ["gripper", "blockworld", "barman", "tyreworld"]}

        self.assertEqual("gripper", COLLAB_JOB._domain_for_site(config, "site-1"))
        self.assertEqual("tyreworld", COLLAB_JOB._domain_for_site(config, "site-4"))

    def test_average_metrics_is_weighted(self):
        result = COLLAB_JOB._average_metrics(
            {
                "site-1": {"avg_reward": 0.2, "num_completed": 10, "num_success": 5, "num_tasks": 10},
                "site-2": {"avg_reward": 0.8, "num_completed": 20, "num_success": 20, "num_tasks": 20},
            }
        )

        self.assertAlmostEqual(25 / 30, result["accuracy"])
        self.assertAlmostEqual(0.6, result["avg_reward"])

    def test_alfworld_evaluation_command_uses_all_domains(self):
        with tempfile.TemporaryDirectory() as directory:
            config = {
                "dataset_family": "alfworld",
                "data_root": directory,
                "alfworld_game_root": f"{directory}/games",
                "domains": ["bathroom", "bedroom", "kitchen", "living"],
                "output_root": "artifacts/alfworld",
                "max_evaluate_tasks": 0,
                "max_trials": 30,
            }
            command = COLLAB_JOB._worker_command(config, "bathroom", "evaluate", Path(directory))

        self.assertIn("--alfworld-domains", command)
        self.assertIn("bathroom,bedroom,kitchen,living", command)
        self.assertIn("30", command)
        self.assertIn("--promotion-policy", command)
        self.assertIn("wilson", command)
        self.assertIn("--wilson-alpha", command)
        self.assertIn("--wilson-threshold", command)

    def test_recipe_uses_released_collab_objects(self):
        config = COLLAB_JOB._load_config(PROJECT_ROOT / "configs" / "fever.json", None, None)
        recipe = COLLAB_JOB.make_recipe(config)

        self.assertIsInstance(recipe.server, COLLAB_JOB.MemCoServer)
        self.assertIsInstance(recipe.client, COLLAB_JOB.MemCoClient)
        self.assertEqual("memco-fever", recipe.job_name)


if __name__ == "__main__":
    unittest.main()
