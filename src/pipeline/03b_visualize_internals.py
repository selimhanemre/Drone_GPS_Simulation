"""Compatibility entry point: evaluation saves all diagnostic figures headlessly."""
import runpy
from pathlib import Path

if __name__ == '__main__':
    runpy.run_path(str(Path(__file__).with_name('03_evaluate_defenses.py')),run_name='__main__')
