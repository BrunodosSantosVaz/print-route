"""Ajusta o sys.path para os testes importarem os módulos de src/, scripts/ e do compilador (packaging/windows/)."""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(RAIZ, "src")
SCRIPTS = os.path.join(RAIZ, "scripts")
PACKAGING_WINDOWS = os.path.join(RAIZ, "packaging", "windows")

for pasta in (SRC, SCRIPTS, PACKAGING_WINDOWS):
    if pasta not in sys.path:
        sys.path.insert(0, pasta)
