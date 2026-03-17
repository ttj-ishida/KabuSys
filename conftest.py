"""ルートレベル conftest.py — src/ を sys.path に追加する。"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))
