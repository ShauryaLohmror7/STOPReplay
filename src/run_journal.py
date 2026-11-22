"""Controller-local journal. Does not replace Cem's analysis/history schema."""

import json
import os
import tempfile
from pathlib import Path
from contextlib import contextmanager
import fcntl


@contextmanager
def journal_lock(directory):
    """One local executor per journal directory, including resumed runs."""
    Path(directory).mkdir(parents=True, exist_ok=True)
    with open(Path(directory) / ".execution.lock", "a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Another local executor is using this journal directory.") from None
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def write_snapshot(path, data):
    """Atomically replace a snapshot; leave the previous one intact on failure."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".run-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
