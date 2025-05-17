import pathlib

bindepend_path = pathlib.Path(".venv/Lib/site-packages/PyInstaller/depend/bindepend.py")
target_line = "pe = pefile.PE(filename, fast_load=True)"

patched_block = """try:
        pe = pefile.PE(filename, fast_load=True)
    except pefile.PEFormatError:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning("Skipping non-PE file: %s", filename)
        return []"""

if not bindepend_path.exists():
    raise FileNotFoundError("Could not find bindepend.py.")

text = bindepend_path.read_text()

if "Skipping non-PE file" in text:
    print("✅ Already patched.")
else:
    if target_line not in text:
        raise RuntimeError("Target line not found in bindepend.py — aborting patch.")
    text = text.replace(target_line, patched_block)
    bindepend_path.write_text(text)
    print("🛠️ Patched PyInstaller successfully.")
