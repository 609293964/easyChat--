from __future__ import annotations

import argparse
import shutil
import subprocess
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC_FILE = ROOT / "wechat_gui_momo.spec"
DIST_EXE = ROOT / "dist" / "wechat_gui_momo.exe"
PORTABLE_DIR = ROOT / "wechat_gui_momo_portable"
PORTABLE_ZIP = ROOT / "wechat_gui_momo_portable.zip"
README_FILE = ROOT / "打包说明.txt"


def run_pyinstaller() -> None:
    cmd = ["pyinstaller.exe", "--noconfirm", str(SPEC_FILE)]
    print("执行打包命令:", " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=ROOT)


def write_runtime_note(target_dir: Path) -> None:
    runtime_dir = target_dir / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    note_file = runtime_dir / "VC++运行库下载地址.txt"
    note_file.write_text(
        "VC++ 2015-2022 Redistributable (x64)\n"
        "下载地址: https://aka.ms/vs/17/release/vc_redist.x64.exe\n\n"
        "安装说明:\n"
        "1. 先安装 vc_redist.x64.exe\n"
        "2. 安装完成后再运行 wechat_gui_momo.exe\n",
        encoding="utf-8",
    )


def build_portable_package() -> None:
    if not DIST_EXE.exists():
        raise FileNotFoundError(f"未找到已打包的可执行文件: {DIST_EXE}")

    if PORTABLE_DIR.exists():
        shutil.rmtree(PORTABLE_DIR)
    if PORTABLE_ZIP.exists():
        PORTABLE_ZIP.unlink()

    PORTABLE_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DIST_EXE, PORTABLE_DIR / DIST_EXE.name)

    if README_FILE.exists():
        shutil.copy2(README_FILE, PORTABLE_DIR / "运行说明.txt")

    write_runtime_note(PORTABLE_DIR)

    with zipfile.ZipFile(PORTABLE_ZIP, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_path in PORTABLE_DIR.rglob("*"):
            if file_path.is_file():
                zipf.write(file_path, file_path.relative_to(PORTABLE_DIR))

    print(f"便携包已生成: {PORTABLE_ZIP.name}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="打包 wechat_gui_momo.py")
    parser.add_argument(
        "--portable",
        action="store_true",
        help="在生成 exe 后额外生成便携 zip 包",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_pyinstaller()
    if args.portable:
        build_portable_package()


if __name__ == "__main__":
    main()
