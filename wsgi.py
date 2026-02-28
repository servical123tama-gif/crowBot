import sys
import os

# Pastikan project root masuk ke Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
os.chdir(project_root)

from run_dashboard import app
