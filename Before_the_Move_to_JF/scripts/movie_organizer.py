#!/usr/bin/env python3
"""
movie_organizer.py - Compatibility wrapper for before_the_move_to_jf.py
"""
import sys
import runpy
from pathlib import Path

target = Path(__file__).resolve().parent / "before_the_move_to_jf.py"
runpy.run_path(str(target), run_name="__main__")
