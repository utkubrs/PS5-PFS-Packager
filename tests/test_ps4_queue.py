"""Headless regression tests for the PS4 live FIFO queue."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ps5_pfs_packager import App


class PS4QueueTests(unittest.TestCase):
    def make_app(self):
        # No Tk root / Windows desktop needed to exercise dispatch decisions.
        app = App.__new__(App)
        app._ps4_pending_jobs = []
        app._ps4_active_job = None
        app._ps4_history = []
        app._ps4_queue_paused = False
        app._ps4_merge_busy = False
        app.is_running = False
        app.mount_busy = False
        app.mount_session = None
        app.cancel_requested = False
        app._log = lambda *args: None
        app._refresh_ps4_queue = lambda: None
        app._update_start_button_state = lambda: None
        app._qphase = lambda *args: None
        app._qstatus = lambda *args: None
        app._qprogress = lambda *args: None
        app._qlog = lambda *args: None
        app.after_idle = lambda *args: None
        return app

    @staticmethod
    def job(name, patch=""):
        return {
            "base": "C:/input/base", "patch": patch, "title": "",
            "auto_title": True, "output": "C:/output",
            "filename": name + ".ffpfsc", "auto_filename": False,
            "temp": "D:/work", "remove_snd0": False,
            "cpu": "5", "compression": "7", "block": "auto",
            "preset": "balanced", "extra_verify": False,
            "fakelib": False, "shutdown": False,
        }

    def test_fifo_mixed_update_and_base_only(self):
        app = self.make_app()
        first, second, third = (self.job("CUSA00001", "C:/update"),
                                self.job("CUSA00002"),
                                self.job("CUSA00003", "C:/patch3"))
        self.assertTrue(app._enqueue_ps4_job(first))
        self.assertTrue(app._enqueue_ps4_job(second))
        self.assertTrue(app._enqueue_ps4_job(third))
        self.assertFalse(app._enqueue_ps4_job(second))
        app.is_running = True
        app._pump_ps4_queue()
        self.assertEqual(len(app._ps4_pending_jobs), 3)
        app.is_running = False
        with patch("ps5_pfs_packager.threading.Thread"):
            app._pump_ps4_queue()
            self.assertEqual(app._ps4_active_job["filename"], "CUSA00001.ffpfsc")
            self.assertEqual(len(app._ps4_pending_jobs), 2)
            app._finish_ps4_job(True)
            app._pump_ps4_queue()
            self.assertFalse(app._ps4_active_job["patch"])
            app._finish_ps4_job(False)
            app._pump_ps4_queue()
            self.assertEqual(app._ps4_active_job["filename"], "CUSA00003.ffpfsc")

    def test_paused_queue_keeps_pending_games(self):
        app = self.make_app()
        self.assertTrue(app._enqueue_ps4_job(self.job("CUSA11111")))
        app._ps4_queue_paused = True
        with patch("ps5_pfs_packager.threading.Thread"):
            app._pump_ps4_queue()
        self.assertIsNone(app._ps4_active_job)
        self.assertEqual(len(app._ps4_pending_jobs), 1)


if __name__ == "__main__":
    unittest.main()
