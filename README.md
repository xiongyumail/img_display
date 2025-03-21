# IMG_DISPLAY
## 项目概述
`IMG_DISPLAY` 是一个基于 Flask 的 Python 项目，主要用于展示图像信息。它支持从多个 JSON 文件中加载图像元数据，并通过 Web 界面分页展示图像。用户可以对图像进行点赞操作，点赞状态会异步保存到对应 JSON 文件中。此外，用户可以通过命令行输入 `Q` 或访问 `/shutdown` 接口优雅关闭服务器。

## 功能特性
1. **多文件支持**：支持同时加载多个 JSON 文件，并通过界面切换查看不同文件的数据。
2. **图像信息展示**：从 JSON 文件中加载图像元数据，并在 Web 界面上分页展示。
3. **分类视图**：支持按分类浏览图像，每个分类有缩略图显示。
4. **收藏功能**：用户可以将喜欢的图像添加到收藏夹，并单独查看收藏的图片。
5. **未收藏功能**：新增未收藏图片的展示功能，用户可以查看所有未点赞的图片。
6. **点赞功能**：
   - 用户可以对图像进行点赞或取消点赞操作，点赞状态会异步保存到 JSON 文件中。
   - **新增**：支持**一键点赞本页所有图片**，批量操作更高效。
7. **优雅关闭**：可以通过命令行输入 `Q` 或访问 `/shutdown` 接口来关闭服务器，确保数据保存完整。
8. **随机排序**：在查看收藏或未收藏图片时，支持随机排序功能。
9. **字符串替换**：支持在加载 JSON 文件时进行字符串替换，便于处理不同环境下的路径问题。
10. **自动浏览器控制**：新增 `--no_browser` 参数，允许在启动时不自动打开浏览器。
11. **版本信息显示**：界面和命令行均会显示当前程序版本号。
12. **单元测试支持**：提供基础单元测试，验证核心功能的正确性。
13. **批量操作支持**：**新增**一键点赞所有图片功能，支持批量处理多个图像路径。

## 安装与运行
### 安装依赖
确保你已经安装了 Python 3.x 和 Flask。可以使用以下命令安装依赖：
```bash
pip install -r requirements.txt
```

### 配置参数
支持的命令行参数如下：
- `--per_page`：每页显示的项目数量，默认为 20。
- `--input_json`：输入的 JSON 文件路径（支持多个文件），默认为 `None`（启动时会弹出文件选择对话框）。
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
python display.py --input_json file1.json file2.json --per_page 100 --host 127.0.0.1 --port 8080 --debug --replace "/abc" "/def" --no_browser
```

### 访问项目
项目启动后，如果没有指定 `--no_browser` 参数，会自动打开浏览器并访问 `http://127.0.0.1:5000`。你也可以手动在浏览器中输入该地址进行访问。

## 接口说明
### 新增接口
- **`/select_json/<int:json_index>`**：切换当前显示的 JSON 文件，`json_index` 为文件列表中的索引。
- **`/like_image`**：**增强**支持批量点赞操作，接收 `paths` 参数（数组形式），返回成功/失败的路径列表。

### 原有接口
- **`/`**：显示分类视图，按分类分页展示图像分类。
- **`/all`**：显示所有图片，分页展示。
- **`/category/<path:category>`**：分类详情视图，按分类和页码展示图像。
- **`/category/_favorites`**：显示所有已收藏的图片，分页展示。
- **`/category/_unfavorites`**：显示所有未收藏的图片，分页展示。

## 构建可执行文件
### 单平台构建
使用 `PyInstaller` 构建可执行文件：
```bash
cd build
python build.py  # 自动获取版本并打包
```
构建产物位于 `build/dist/` 目录。

## CI/CD 集成
项目已配置 GitHub Actions，**仅在 `main` 分支推送或创建发布**时触发：
1. **测试阶段**：运行单元测试（`test/test_config.py`、`test/test_web.py`）。
2. **构建阶段**：生成多平台（Ubuntu、Windows、macOS）可执行文件。
3. **发布阶段**：将构建产物作为 GitHub Release 附件上传。

## 单元测试
运行测试：
```bash
python test/test_config.py
python test/test_web.py
```
**覆盖功能**：
- 配置参数解析（`test/test_config.py`）
- 分页器逻辑（`test/test_web.py`）
- Web 应用字符串替换规则（`test/test_web.py`）
- **新增测试**：
  - 批量点赞多个路径的逻辑验证（`test_like_image_multiple_paths`）
  - 未提供路径时的错误处理（`test_like_image_no_paths`）
  - 所有路径均未找到时的响应（`test_like_image_all_not_found`）
  - 总图片数传递到模板的正确性（`test_render_category_view_total_images`）
  - 分类缩略图生成逻辑（`test_get_category_thumbnail`）
  - 无效 JSON 数据的错误处理（`test_like_image_invalid_json`）
  - 并发点赞请求的线程安全验证（`test_concurrent_like_requests`）
  - 分页器处理零或负数的每页数量（`test_paginate_zero_and_negative_per_page`）
  - 多层嵌套目录的 JSON 数据加载（`test_load_image_data_with_nested_directories`）
  - 强制关闭服务器的流程（`test_shutdown_route_forced`）

## 更新说明
1. **用户界面优化**：
   - 新增**一键点赞本页所有图片**按钮（`❤ 一键点赞本页所有图片`），支持批量操作。
   - 点赞按钮样式优化，增加悬停缩放和焦点反馈效果。
   - 分类选择和 JSON 选择器布局优化，确保移动端适配。
2. **功能增强**：
   - **核心功能**：支持批量点赞操作，可同时处理多个图像路径。
   - 异步请求返回更详细的结果，包括成功和未找到的路径列表。
   - 新增总图片数显示（`({{ total_images }}P)`），方便用户了解数据规模。
3. **测试增强**：
   - 新增批量点赞相关的单元测试，覆盖正常和异常场景。
   - 增强对收藏夹分类和未收藏分类的测试。
   - 新增对分页器、JSON 数据加载、服务器关闭等核心功能的测试。
4. **代码优化**：
   - 重构 `test.py` 为 `test_config.py` 和 `test_web.py`，提升测试模块的清晰度。
   - 修复分页器在处理零或负数每页数量时的逻辑问题。
   - 增强 `like_image` 接口对无效 JSON 数据的错误处理。