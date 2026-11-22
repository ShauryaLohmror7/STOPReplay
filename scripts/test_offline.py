"""Run offline tests with no credentials/network and all generated files in /tmp.

Usage: .venv/bin/python -B scripts/test_offline.py
Database integration is deliberately skipped. It resets schema and needs an
explicit disposable database; never point those tests at the shared project.
"""
import os
from pathlib import Path
import socket
import sys
import tempfile

root = Path(__file__).resolve().parents[1]
os.chdir(root)
sys.path.insert(0, str(root))
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.dont_write_bytecode = True
for key in ('DATABASE_URL', 'LLM_API_KEY', 'OPENROUTER_API_KEY', 'FORCE_REAL_LLM',
            'REVEL8_TEAM_KEY', 'TARGET_API_KEY', 'LLM_MODEL', 'LLM_PROVIDER', 'TARGET_API_URL'):
    os.environ.pop(key, None)


def no_network(*args, **kwargs):
    raise RuntimeError('Network is disabled by the offline test runner.')


socket.socket.connect = no_network
socket.socket.connect_ex = no_network
import src.controller
import pytest
with tempfile.TemporaryDirectory(prefix='stopreplay-tests-') as directory:
    src.controller.LOGS_DIR = directory
    raise SystemExit(pytest.main(['-q', '-p', 'no:cacheprovider', '--basetemp', directory + '/pytest', 'tests']))
