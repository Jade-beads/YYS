"""Real-frame regressions. Device input is replaced so these never touch the game."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'yys'))
import action
from yys import Worker, _Stop


class QilingTests(unittest.TestCase):
    def replay(self, name, frames=4, limit=1):
        screen = name if isinstance(name, np.ndarray) else cv2.cvtColor(
            cv2.imread(str(ROOT / 'tests/fixtures/qiling' / name)), cv2.COLOR_BGR2RGB)
        worker = Worker(0)
        clicks, logs = [], []
        snapshots = iter([screen.copy() for _ in range(frames)])

        def grab():
            try:
                return next(snapshots)
            except StopIteration:
                raise _Stop

        worker.grab = grab
        worker.sleep_fast = lambda t=0: not worker.isRunning
        worker.message_output = logs.append
        with patch.object(action, 'scalar', False), \
             patch.object(action, 'touch', side_effect=lambda xy, tid: clicks.append(xy)):
            worker.run(14, limit)
        self.assertFalse(any('任务出错' in line for line in logs), logs)
        return clicks, logs

    def test_success_confirmation_variants_are_closed_once(self):
        #Synthetic result controls: tests dispatch/transition, not a claim of live success-page coverage.
        templates = action.load_imgs('yys')
        for name in ['jixu', 'queren', 'queren2', 'queren3', 'queding']:
            with self.subTest(name=name):
                screen = np.zeros((640, 1136, 3), dtype=np.uint8)
                tpl = templates[name][0]
                h, w = tpl.shape[:2]
                screen[550:550+h, 500:500+w] = tpl
                clicks, _ = self.replay(screen)
                self.assertEqual(len(clicks), 1, 'result controls should be confirmed once')
                x, y = clicks[0]
                self.assertTrue(500 <= x < 500+w and 550 <= y < 550+h, clicks)

    def test_disabled_challenge_stops_without_clicking(self):
        image = cv2.cvtColor(cv2.imread(str(ROOT/'tests/fixtures/qiling/challenge.png')),
                             cv2.COLOR_BGR2RGB)
        #Model a disabled (desaturated) button; leave the rest of the real page intact.
        button = image[500:590, 1000:1110]
        image[500:590, 1000:1110] = cv2.cvtColor(cv2.cvtColor(button, cv2.COLOR_RGB2GRAY),
                                               cv2.COLOR_GRAY2RGB)
        clicks, logs = self.replay(image)
        self.assertEqual(clicks, [], 'a disabled challenge must not consume attempts')
        self.assertTrue(any('不可用' in line or '无法挑战' in line for line in logs), logs)

    def test_zero_budget_does_not_report_a_phantom_challenge(self):
        clicks, logs = self.replay('challenge.png', limit=0)
        self.assertEqual(clicks, [])
        self.assertFalse(any('挑战次数：1/' in line for line in logs), logs)

    def test_available_challenge_starts_once(self):
        clicks, _ = self.replay('challenge.png')
        self.assertEqual(len(clicks), 1)
        x, y = clicks[0]
        self.assertTrue(1000 <= x <= 1110 and 500 <= y <= 590, clicks)

    def test_abandon_requires_failed_contract_heading(self):
        image = cv2.cvtColor(cv2.imread(str(ROOT/'tests/fixtures/qiling/contract_failed.png')),
                             cv2.COLOR_BGR2RGB)
        image[200:350, 380:800] = 0
        clicks, _ = self.replay(image)
        self.assertEqual(clicks, [], 'an abandon button alone must not trigger abandoning')

    def test_three_rejected_challenges_stop_even_with_confirmation_dialogs(self):
        board = cv2.cvtColor(cv2.imread(str(ROOT/'tests/fixtures/qiling/challenge.png')),
                             cv2.COLOR_BGR2RGB)
        confirm = np.zeros_like(board)
        tpl = action.load_imgs('yys')['queding'][0]
        h, w = tpl.shape[:2]
        confirm[400:400+h, 500:500+w] = tpl
        worker = Worker(0)
        scene, attempts, reads = 0, 0, 0
        logs = []

        def grab():
            nonlocal reads
            reads += 1
            if reads > 60: raise _Stop
            return (board if scene == 0 else confirm).copy()

        def tap(xy, tid):
            nonlocal scene, attempts
            if scene == 0:
                self.assertTrue(xy[0] > 1000 and xy[1] > 500, xy)
                attempts += 1
            else:
                self.assertTrue(500 <= xy[0] < 500+w and 400 <= xy[1] < 400+h, xy)
            scene = 1-scene

        worker.grab = grab
        worker.sleep_fast = lambda t=0: not worker.isRunning
        worker.message_output = logs.append
        with patch.object(action, 'scalar', False), patch.object(action, 'touch', side_effect=tap):
            worker.run(14, 100)
        self.assertFalse(any('任务出错' in line for line in logs), logs)
        self.assertEqual(attempts, 3, logs)
        self.assertTrue(any('未能进入战斗' in line for line in logs), logs)

    def test_failed_contract_abandons_instead_of_retrying(self):
        clicks, _ = self.replay('contract_failed.png')
        self.assertEqual(len(clicks), 1, 'failure must click abandon once, then wait for transition')
        x, y = clicks[0]
        self.assertTrue(334 <= x <= 536 and 533 <= y <= 579, clicks)

    def test_ready_page_starts_battle_once(self):
        clicks, _ = self.replay('ready.png')
        self.assertEqual(len(clicks), 1, 'the ready page must not stall or double tap')
        x, y = clicks[0]
        self.assertTrue(1000 <= x <= 1090 and 488 <= y <= 552, clicks)

    def test_stuck_abandon_page_stops_instead_of_clicking_forever(self):
        clicks, logs = self.replay('contract_failed.png', frames=60)
        self.assertLessEqual(len(clicks), 3, 'unresponsive abandon must stop after bounded retries')
        self.assertTrue(any('停止' in line or '上限' in line for line in logs), logs)

    def test_failed_contract_collects_both_reward_pages_and_respects_limit(self):
        names = ['contract_failed.png', 'reward_open.png', 'reward_items.png', 'challenge.png']
        images = [cv2.cvtColor(cv2.imread(str(ROOT / 'tests/fixtures/qiling' / name)),
                              cv2.COLOR_BGR2RGB) for name in names]
        boxes = [(334, 533, 536, 579), (500, 365, 650, 480), (500, 440, 650, 550)]
        worker = Worker(0)
        page, stale, reads = 0, 0, 0
        clicks, logs = [], []

        def grab():
            nonlocal reads, stale
            reads += 1
            if reads > 40:
                raise _Stop
            if stale:
                stale -= 1
                return images[page-1].copy()
            return images[page].copy()

        def tap(xy, tid):
            nonlocal page, stale
            clicks.append(tuple(xy))
            if page >= 3:
                self.fail('a zero budget must not start the next challenge')
            left, top, right, bottom = boxes[page]
            self.assertTrue(left <= xy[0] <= right and top <= xy[1] <= bottom,
                            (names[page], xy))
            page += 1
            stale = 2

        worker.grab = grab
        worker.sleep_fast = lambda t=0: not worker.isRunning
        worker.message_output = logs.append
        with patch.object(action, 'scalar', False), patch.object(action, 'touch', side_effect=tap):
            worker.run(14, 0)
        self.assertFalse(any('任务出错' in line for line in logs), logs)
        self.assertEqual(page, 3, (clicks, logs))
        self.assertEqual(len(clicks), 3, (clicks, logs))


if __name__ == '__main__':
    unittest.main()
