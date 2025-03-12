# version.py
import subprocess

def get_git_version():
    try:
        version = subprocess.check_output(['git', 'describe', '--tags']).strip().decode('utf-8')
        return version
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

# 在打包时使用这个版本信息
try:
    # 如果是打包后的环境，版本信息会被写入到 _MEIPASS 目录下的 version.txt 文件中
    import sys
    if hasattr(sys, '_MEIPASS'):
        import os
        version_file = os.path.join(sys._MEIPASS, 'version.txt')
        if os.path.exists(version_file):
            with open(version_file, 'r') as f:
                version = f.read().strip()
                __version__ = version
        else:
            __version__ = 'unknown'
    else:
        version = get_git_version()
        if version:
            __version__ = version
        else:
            __version__ = 'unknown'
except Exception:
    __version__ = 'unknown'