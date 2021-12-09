import utils.clean_up_runs as clean_up
import unittest
import os
from pathlib import Path

class Test_lock_methods(unittest.TestCase):
    def setUp(self):
        self.dirname = Path("testdir")
 
    def tearDown(self):
        pass

    def test_lock(self):
        self.assertFalse(clean_up.locked(self.dirname))
        self.assertTrue(clean_up.lock(self.dirname))
        self.assertTrue(clean_up.locked(self.dirname))
        self.assertFalse(clean_up.lock(self.dirname))
        clean_up.unlock(self.dirname)
        self.assertFalse(clean_up.locked(self.dirname))

class Test_mark_for_cleanup(unittest.TestCase):
    def setUp(self):
        self.dirname = Path("testdir")
        self.subdir = self.dirname / 'subdir'
        self.subdir.mkdir(parents=True)
        self.mark = Path(str(self.dirname) + ".remove")


    def test_clean_up_dir(self):
        self.assertFalse(clean_up.marked_for_cleanup(self.dirname))
        self.mark.touch()
        self.assertTrue(self.dirname.exists())
        self.assertTrue(clean_up.marked_for_cleanup(self.dirname))
        clean_up.clean_up_dir(self.dirname)
        self.assertFalse(self.dirname.exists())
        self.assertFalse(clean_up.marked_for_cleanup(self.dirname))
        self.assertFalse(clean_up.locked(self.dirname))

    def tearDown(self):
        if self.subdir.exists():
            self.subdir.rmdir()
        if self.dirname.exists():
            self.dirname.rmdir()
        self.mark.touch()
        self.mark.unlink()

if __name__ == "__main__":
    unittest.main()
