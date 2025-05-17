from src.gui.app import StorageAssistant
import ctypes
import sys
import os

if __name__ == "__main__":
    try:
        app = StorageAssistant()
        app.run()
    except Exception as e:
        import traceback
        with open("error_log.txt", "w") as f:
            f.write(traceback.format_exc())
        raise

