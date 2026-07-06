# Put the pin-editor root on sys.path so tests can `import edits` / `import store`.
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
