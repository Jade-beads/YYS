"""Regression coverage for controls shared by the device tabs."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main


class TaskControlTests(unittest.TestCase):
    def test_invalid_count_does_not_block_stopping_another_device(self):
        tabs = []
        for value in ('30', 'abc'):
            tab = SimpleNamespace(textBrowser=Mock(), listWidget=Mock(),
                                  lineEdit=Mock(), pushButton_start=Mock(),
                                  pushButton_restart=Mock())
            tab.lineEdit.text.return_value = value
            tab.listWidget.selectedItems.return_value = [object()]
            tab.listWidget.currentRow.return_value = 7
            tabs.append(tab)
        window = SimpleNamespace(tab=tabs, threads=[object(), object()],
                                 isRunning=[True, False],
                                 workers=[SimpleNamespace(isRunning=True), None])

        main.MainWindow.start_stop(window, 1)
        tabs[1].textBrowser.append.assert_any_call('请输入数字')
        # Probe before calling stop, so the broken implementation fails instead of hanging.
        available = main.mutex.tryLock(50)
        # Both the probe and the old leaking path hold this lock on this same test thread.
        main.mutex.unlock()
        self.assertTrue(available, 'invalid count left the shared controls locked')

        main.MainWindow.start_stop(window, 0)
        self.assertFalse(window.workers[0].isRunning)
        self.assertFalse(window.isRunning[0])


if __name__ == '__main__':
    unittest.main()
