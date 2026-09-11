import subprocess
import sys
import os

project_root = os.path.dirname(os.path.abspath(__file__))
py = os.path.join(project_root, 'venv', 'Scripts', 'python.exe')

for script in ['gsc_check.py', 'adsense_check.py']:
    print(f"\n########## {script} ##########")
    subprocess.run([py, os.path.join(project_root, script)], cwd=project_root)