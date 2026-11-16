import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("CACHE_DIR", str(Path(__file__).resolve().parent / ".cache"))

# Testes de algoritmo usam perfis sinteticos sem recibo; testes de proveniencia habilitam a exigencia explicitamente.
os.environ["REQUIRE_VERIFIED_PROFILES"] = "false"
