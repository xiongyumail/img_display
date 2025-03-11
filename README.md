# IMG_DISPLAY

## 项目概述
`IMG_DISPLAY` 是一个基于 Flask 的 Python 项目，主要用于展示图像信息。它可以从指定的 JSON 文件中加载图像元数据，并通过 Web 界面分页展示图像。用户可以对图像进行点赞操作，点赞状态会异步保存到 JSON 文件中。此外，用户可以通过命令行输入 `Q` 来优雅地关闭服务器。

## 功能特性
1. **图像信息展示**：从 JSON 文件中加载图像元数据，并在 Web 界面上分页展示。
2. **分类视图**：支持按分类浏览图像，每个分类有缩略图显示。
3. **收藏功能**：用户可以将喜欢的图像添加到收藏夹，并单独查看收藏的图片。
4. **未收藏功能**：新增未收藏图片的展示功能，用户可以查看所有未点赞的图片。
5. **点赞功能**：用户可以对图像进行点赞或取消点赞操作，点赞状态会异步保存到 JSON 文件中。
6. **优雅关闭**：可以通过命令行输入 `Q` 或访问 `/shutdown` 接口来关闭服务器，确保数据保存完整。
7. **随机排序**：在查看收藏或未收藏图片时，支持随机排序功能。
8. **字符串替换**：支持在加载 JSON 文件时进行字符串替换，便于处理不同环境下的路径问题。
9. **自动浏览器控制**：新增 `--no_browser` 参数，允许在启动时不自动打开浏览器。

## 安装与运行

### 安装依赖
确保你已经安装了 Python 3.x 和 Flask。可以使用以下命令安装依赖：
```bash
pip install -r requirements.txt
```

### 配置参数
可以通过命令行参数来配置项目的运行参数，支持的参数如下：
- `--per_page`：每页显示的项目数量，默认为 20。
- `--input_json`：输入的 JSON 文件路径，默认为 `None`（启动时会弹出文件选择对话框）。
- `--host`：Flask 服务器的主机地址，默认为 `0.0.0.0`。
- `--port`：Flask 服务器的端口号，默认为 5000。
- `--debug`：启用调试模式。
- `--replace`：临时替换 JSON 文件中的字符串，例如 `--replace "/abc" "/def"`。
- `--no_browser`：启动时不自动打开浏览器。

### 运行项目
在项目根目录下，运行以下命令启动项目：
```bash
python display.py
```
或者指定自定义参数：
```bash
python display.py --per_page 100 --host 127.0.0.1 --port 8080 --debug --replace "/abc" "/def" --no_browser
```

### 访问项目
项目启动后，如果没有指定 `--no_browser` 参数，会自动打开浏览器并访问 `http://127.0.0.1:5000`。你也可以手动在浏览器中输入该地址进行访问。

## 接口说明
### 图像展示接口
- **`/`**：显示分类视图，按分类分页展示图像分类。
- **`/all`**：显示所有图片，分页展示。
- **`/category/<path:category>/page/<int:page>`** 或 **`/category/<path:category>`**：分类详情视图，按分类和页码展示图像。
- **`/category/_favorites/page/<int:page>`**：显示所有已收藏的图片，分页展示。
- **`/category/_unfavorites/page/<int:page>`**：显示所有未收藏的图片，分页展示。

### 图像文件服务接口
- **`/image/<category>/<path:filename>`**：提供图像文件服务，根据分类和文件名返回对应的图像。

### 点赞接口
- **`/like_image`**：处理图像点赞或取消点赞操作，接收 JSON 格式的请求数据，包含 `path` 和 `action` 字段。
    - `path`：图像的路径。
    - `action`：操作类型，`like` 表示点赞，`unlike` 表示取消点赞。

### 关闭服务器接口
- **`/shutdown`**：关闭服务器，确保数据保存完整。

## 数据文件格式
输入的 JSON 文件应包含图像的元数据，格式如下：
```json
{
    "version": "3",
    "date_created": "2025-03-06T02:29:31.298360+08:00",
    "date_updated": "2025-03-06T03:44:53.760607+08:00",
    "img": {
        "base_path_1": {
            "image_path_1": {
                "face_scores": [1.0, 2.0, 3.0],
                "face_landmark_scores_68": [0.5, 0.6, 0.7],
                "like": true
            },
            "sub_folder": {
                "image_path_2": {
                    "face_scores": [4.0, 5.0, 6.0],
                    "face_landmark_scores_68": [0.8, 0.9, 1.0],
                    "like": false
                }
            }
        },
        "base_path_2": {
            "image_path_3": {
                "face_scores": [7.0, 8.0, 9.0],
                "face_landmark_scores_68": [1.1, 1.2, 1.3],
                "like": true
            }
        }
    }
}
```

## 注意事项
- 确保输入的 JSON 文件路径正确，并且文件格式符合要求。
- 在关闭服务器时，建议使用命令行输入 `Q` 或访问 `/shutdown` 接口，以确保数据保存完整。
- 如果在调试模式下运行项目，修改代码后需要手动重启服务器。

## 构建可执行文件
项目支持通过 `PyInstaller` 构建可执行文件。运行以下命令进行构建：
```bash
pyinstaller display.spec
```
构建完成后，可执行文件将生成在 `dist/` 目录下。

### 多平台构建
项目支持在 Linux、Windows 和 macOS 上构建可执行文件。对于 Linux 平台，构建过程会使用 Docker 来确保兼容性。

## CI/CD 集成
项目已配置 GitHub Actions，可以在 `main` 分支的 `push` 或 `pull_request` 事件触发时，自动构建可执行文件并生成多平台的构建产物（包括 `ubuntu-latest`、`windows-latest` 和 `macos-latest`）。

### 更新说明：
1. **新增功能**：增加了未收藏图片的展示功能，用户可以通过 `/category/_unfavorites/page/<int:page>` 查看所有未点赞的图片。
2. **随机排序**：在查看收藏或未收藏图片时，支持随机排序功能。
3. **GUI 文件选择**：如果未通过命令行指定 `input_json` 文件路径，启动时会弹出 GUI 文件选择对话框，用户可以选择 JSON 文件。
4. **字符串替换**：新增 `--replace` 参数，支持在加载 JSON 文件时进行字符串替换。
5. **自动浏览器控制**：新增 `--no_browser` 参数，允许在启动时不自动打开浏览器。
6. **构建支持**：添加了通过 `PyInstaller` 构建可执行文件的说明，并支持多平台构建。
7. **CI/CD 集成**：项目已配置 GitHub Actions，支持自动构建和生成多平台的构建产物。