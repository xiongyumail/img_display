# build.py
import subprocess
import os

# 获取 Git 版本信息
try:
    version = subprocess.check_output(['git', 'describe', '--tags']).strip().decode('utf-8')
except (subprocess.CalledProcessError, FileNotFoundError):
    version = 'unknown'

print(f"version: {version}")

# 将版本信息写入文件
with open('version.txt', 'w') as f:
    f.write(version)

# 执行 pyinstaller 打包命令
os.system('pyinstaller display.spec')

# 删除临时文件
if os.path.exists('version.txt'):
    os.remove('version.txt')