import os
import sys
import shutil

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(ROOT_DIR, 'dist')
BUILD_DIR = os.path.join(ROOT_DIR, 'build')
SPEC_FILE = os.path.join(ROOT_DIR, 'eNSP_AutoConfig.spec')

print("=" * 50)
print("  eNSP AutoConfig v1.2 - Build Tool")
print("=" * 50)

if os.path.exists(DIST_DIR):
    print("[1/4] Cleaning dist...")
    shutil.rmtree(DIST_DIR, ignore_errors=True)
if os.path.exists(BUILD_DIR):
    print("[2/4] Cleaning build...")
    shutil.rmtree(BUILD_DIR, ignore_errors=True)
if os.path.exists(SPEC_FILE):
    os.remove(SPEC_FILE)

print("[3/4] PyInstaller packaging (onefile mode)...")

app_py = os.path.join(ROOT_DIR, 'app.py')
templates_dir = os.path.join(ROOT_DIR, 'templates')
static_dir = os.path.join(ROOT_DIR, 'static')

command = (
    'pyinstaller --noconfirm --onefile '
    '--hidden-import jinja2 '
    '--hidden-import jinja2.ext '
    '--hidden-import markupsafe '
    '--hidden-import flask '
    '--hidden-import flask.json '
    '--hidden-import win32timezone '
    '--hidden-import ai_handler '
    '--hidden-import template_manager '
    '--hidden-import history_manager '
    '--add-data "' + templates_dir + ';templates/" '
    '--add-data "' + static_dir + ';static/" '
    '--name eNSP_AutoConfig '
    '--noconsole '
    '"' + app_py + '"'
)

result = os.system(command)

if result == 0:
    exe_path = os.path.join(DIST_DIR, 'eNSP_AutoConfig.exe')
    if os.path.exists(exe_path):
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        print("")
        print("[4/4] Build SUCCESS!")
        print("  Output: " + exe_path)
        print("  Size: %.1f MB" % size_mb)
    else:
        print("")
        print("[4/4] Build FAILED: output file not found")
        sys.exit(1)
else:
    print("")
    print("Build FAILED, error code: %d" % result)
    sys.exit(1)

history_dir = os.path.join(DIST_DIR, 'history')
if not os.path.exists(history_dir):
    os.makedirs(history_dir)
    print("  Created history dir: " + history_dir)

print("")
print("Usage: Double-click eNSP_AutoConfig.exe to start")
print("=" * 50)
