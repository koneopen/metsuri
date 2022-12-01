import pytest
import tempfile
import os


TESTDIR = os.path.dirname(__file__)


@pytest.fixture
def log_file_name():
    with tempfile.TemporaryDirectory(dir=TESTDIR) as temp_dir:
        yield os.path.join(temp_dir, "test.log")
