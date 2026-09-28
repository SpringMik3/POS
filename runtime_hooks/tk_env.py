import os
import sys
from pathlib import Path


def _runtime_base() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))


def _set_if_present(env_name: str, path: Path) -> None:
    if path.exists():
        os.environ[env_name] = str(path)


base = _runtime_base()
exe_dir = Path(sys.executable).resolve().parent
bundle_roots = [
    base,
    exe_dir / "_internal",
    exe_dir,
]

for bundle_root in bundle_roots:
    tcl_data = bundle_root / "_tcl_data"
    tk_data = bundle_root / "_tk_data"
    if tcl_data.exists() or tk_data.exists():
        _set_if_present("TCL_LIBRARY", tcl_data)
        _set_if_present("TK_LIBRARY", tk_data)
        break

for tcl_root in [root / "tcl" for root in bundle_roots]:
    if tcl_root.exists():
        _set_if_present("TCL_LIBRARY", tcl_root / "tcl8.6")
        _set_if_present("TK_LIBRARY", tcl_root / "tk8.6")
        break
    break
