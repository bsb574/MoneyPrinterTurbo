"""PyInstaller runtime hook: 修复 importlib.metadata.version() 在打包后的 StopIteration"""
import importlib.metadata as _imd

_original_version = _imd.version

def _safe_version(package_name):
    try:
        return _original_version(package_name)
    except Exception:
        return "0.0.0"

_imd.version = _safe_version

# 同时修复 moviepy 的 __version__
try:
    import moviepy
    if not hasattr(moviepy, "__version__"):
        moviepy.__version__ = "2.2.1"
except Exception:
    pass
