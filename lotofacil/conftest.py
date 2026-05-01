import sys
import pathlib

# Put src/ on the path so tests can import lotofacil_ml without PYTHONPATH=src
sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))
