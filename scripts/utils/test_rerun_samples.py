import rerun_samples as rr
from pathlib import Path


class TestObject:
    def test_lock(self):
        folder = rr.markedfolder("test/test_lock")
        folder.mkdir()
        assert folder.locked() == False
        assert folder.lock() == True
        assert folder.lock() == False
        assert folder.locked() == True
        folder.unlock()
        assert folder.locked() == False
        folder.rmdir()

    def test_cleanup(self):
        folder = rr.markedfolder("test/test_cleanup")
        folder.mkdir()
        folder.mark_for_cleanup()
        assert folder.marked_for_cleanup() == True
        folder.cleanup()
        assert folder.marked_for_cleanup() == False
        assert folder.exists() == False

    def create_testenv(self, path):
        testpath = rr.markedfolder(path)
        testpath.mkdir()
        for dir in testpath.iterdir():
            dir.rmdir()
        delete_dir = testpath / Path("delete")
        keep_dir = testpath / Path("keep")
        delete_dir.mkdir()
        keep_dir.mkdir()
        return testpath, keep_dir, delete_dir

    def remove_testenv(self, path):
        path.rmdir()

    def test_rerun(self):
        folder, keep_dir, delete_dir = self.create_testenv("test/test_rerun")
        with open(folder.rerun_mark,'w') as fh:
            fh.write("delete")
        assert folder.marked_for_rerun() == True
        folder.rerun()
        assert folder.marked_for_rerun() == False
        assert delete_dir.exists() == False
        assert keep_dir.exists() == True
        keep_dir.rmdir()
        self.remove_testenv(folder)

    def test_rerun_w_permissions(self):
        folder, keep_dir, delete_dir = self.create_testenv("test/test_rerun_w_permissions")
        with open(folder.rerun_mark,'w') as fh:
            fh.write("delete")
        folder.chmod(0o555)
        assert folder.marked_for_rerun() == True
        folder.rerun()
        assert delete_dir.exists() == True
        assert keep_dir.exists() == True
        folder.chmod(0o755)
        keep_dir.rmdir()
        delete_dir.rmdir()
        self.remove_testenv(folder)

