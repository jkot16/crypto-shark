try:
    from .gui import main as launch_gui
except ImportError:
    launch_gui = None