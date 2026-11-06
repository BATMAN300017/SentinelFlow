import os
os.environ["SENTINELFLOW_USE_SQLITE"] = "1"
os.environ["TESTING"] = "1"
import sys

# Add backend directory to sys.path
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(TEST_DIR)
sys.path.insert(0, BACKEND_DIR)
