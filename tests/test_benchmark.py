import unittest
import os
from unittest.mock import patch

from agent_theme.themes import huawei_bloom as intro
from tools import benchmark


class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        env = patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)

    def test_home_workload_has_real_geometry_and_frames(self):
        result = benchmark.measure(benchmark.ROOT, 'home', 1)
        self.assertGreater(result['geometry']['logo'][0], 0)
        for phase in ('intro', 'ambient'):
            self.assertGreater(result['runs'][phase][0]['bytes'], 0)

    def test_ambient_workload_exercises_the_current_effect(self):
        with patch.object(intro.Bloom, 'ambient_frame', autospec=True,
                          side_effect=intro.Bloom.ambient_frame) as render:
            result = benchmark.measure(benchmark.ROOT, 'full', 1)
        self.assertEqual(render.call_count, 60)
        self.assertGreater(result['runs']['ambient'][0]['bytes'], 0)
