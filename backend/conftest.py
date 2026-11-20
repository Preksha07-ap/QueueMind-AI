"""
Root conftest — adds the backend directory to sys.path so that
`import app.*` works without installing the package.
"""
import sys
import os

# Ensure the backend/ directory is on sys.path
sys.path.insert(0, os.path.dirname(__file__))
