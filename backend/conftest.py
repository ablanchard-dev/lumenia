import os
import sys

# Rend le package `app` importable quand on lance pytest depuis backend/.
sys.path.insert(0, os.path.dirname(__file__))
