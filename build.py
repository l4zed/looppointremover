import os
import shutil
import subprocess
import platform

NAME = "RemoveLoopPoints"

# очистка предыдущей сборки
for folder in ("build", "dist"):
    if os.path.exists(folder):
        shutil.rmtree(folder)

spec = NAME + ".spec"
if os.path.exists(spec):
    os.remove(spec)

cmd = [
    "pyinstaller",
    "--onefile",
    "--windowed",
    "--name", NAME,
    "app.py"
]

subprocess.run(cmd)

print()
print("=" * 40)

if platform.system() == "Windows":
    print("Done!")
    print("dist\\RemoveLoopPoints.exe")

elif platform.system() == "Darwin":
    print("Done!")
    print("dist/RemoveLoopPoints.app")

else:
    print("Done!")
    print("dist/")
