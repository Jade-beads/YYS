"""Exploration regressions using real frames from the second emulator."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import cv2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'yys'))
import action
from yys import Worker, _Stop


class ExploreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.images = {p.stem: cv2.cvtColor(cv2.imread(str(p)), cv2.COLOR_BGR2RGB)
                      for p in (ROOT / 'tests/fixtures/explore').glob('*.png')}

    def replay(self, stages, limit=float('inf'), stale_frames=2):
        """Each real page accepts only its expected click; stale frames model fade-out."""
        worker = Worker(1)
        page = reads = stale = 0
        clicks, logs = [], []

        def grab():
            nonlocal reads, stale
            reads += 1
            self.assertLessEqual(reads, 60, f'replay stalled on page {page}: {logs}')
            if page >= len(stages):
                raise _Stop
            if stale:
                stale -= 1
                return self.images[stages[page-1][0]].copy()
            return self.images[stages[page][0]].copy()

        def tap(xy, tid):
            nonlocal page, stale
            self.assertEqual(tid, 1, 'must not send inputs to the first instance')
            self.assertLess(page, len(stages), (xy, logs))
            name, box = stages[page]
            self.assertIsNotNone(box, f'unexpected click on {name}: {xy}, logs={logs}')
            left, top, right, bottom = box
            self.assertTrue(left <= xy[0] <= right and top <= xy[1] <= bottom,
                            f'{name} expected {box}, got {xy}, logs={logs}')
            clicks.append((name, tuple(xy)))
            page += 1
            stale = stale_frames

        worker.grab = grab
        worker.sleep_fast = lambda t=0: not worker.isRunning
        worker.message_output = logs.append
        worker.isRunning = True
        worker.cishu_max = limit
        with patch.object(action, 'scalar', False), patch.object(action, 'touch', side_effect=tap):
            #Call the task directly so errors/assertions are not swallowed by the Qt boundary.
            try:
                worker.gouliang3()
            except _Stop:
                pass
        return clicks, logs

    def test_exit_confirmation_waits_for_entry_instead_of_clicking_old_map(self):
        clicks, _ = self.replay([
            ('exit_confirm', (610, 332, 770, 390)),
            ('entry', (850, 490, 995, 625)),
        ])
        self.assertEqual([name for name, _ in clicks], ['exit_confirm', 'entry'])

    def test_boss_exit_reenters_without_repeating_the_back_arrow(self):
        for stale_frames in (0, 2):
            with self.subTest(stale_frames=stale_frames):
                clicks, _ = self.replay([
                    ('boss', (540, 205, 610, 270)),
                    ('cleared', (15, 5, 75, 65)),
                    ('exit_confirm', (610, 332, 770, 390)),
                    ('entry', (850, 490, 995, 625)),
                    ('map', (790, 205, 885, 300)),
                ], stale_frames=stale_frames)
                self.assertEqual([name for name, _ in clicks],
                                 ['boss', 'cleared', 'exit_confirm', 'entry', 'map'])

    def test_limit_stops_at_chapter_entry_without_entering_or_backing_out(self):
        for limit in (0, 1):
            with self.subTest(limit=limit):
                completed_chapter = [
                    ('entry', (850, 490, 995, 625)),
                    ('boss', (540, 205, 610, 270)),
                    ('cleared', (15, 5, 75, 65)),
                    ('exit_confirm', (610, 332, 770, 390)),
                ] if limit else []
                clicks, logs = self.replay(completed_chapter + [('entry', None)], limit=limit)
                self.assertEqual([name for name, _ in clicks],
                                 [name for name, _ in completed_chapter])
                self.assertIn('探索次数已达上限，停在章节入口', logs)


if __name__ == '__main__':
    unittest.main()
