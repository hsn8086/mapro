# Mapro 智能体开发指南

本文档面向在当前仓库中协作的 AI 智能体。当前仓库已经移除前端内容，重点是 Python CLI 工具、地图数据处理与静态渲染。

## 回复与协作

- 默认使用简体中文回复。
- 优先做小而正确的改动，避免无关重构。
- 不要假设这是 Web 前端项目；任务中心应放在脚本、数据格式、渲染流程和命令行工具。

## 项目重点

- `map_gen/`: 地铁图渲染核心逻辑。
- `main.py`: 统一 CLI 入口，包含渲染与坐标边界分析命令。
- `library/`: 内置地图库目录，当前包含 `library/gz/` 示例地图包。

## 常用命令

- 安装依赖: `uv sync`
- 查看 CLI 帮助: `uv run python main.py --help`
- 生成预览图: `uv run python main.py render library/gz --output map_preview.png`
- 监听数据变化并自动重绘: `uv run python main.py render library/gz --watch`
- 渲染前缩放坐标: `uv run python main.py render library/gz --scale 1.5`
- 计算坐标边界: `uv run python main.py bounds library/gz`
- 类型检查: `uvx ty check .`
- 代码格式化: `uvx ruff format`
- 运行测试: `uv run python -m unittest discover -s tests`

## 代码规范

- Python 使用四格缩进。
- 新增或修改函数时补充类型标注。
- CLI 逻辑统一收口到子命令风格入口，避免脚本能力分散到多个零散文件。
- CLI 脚本尽量拆成可复用函数，避免在模块导入时直接解析参数或执行 I/O。
- 涉及路径时优先使用 `pathlib.Path`，避免写死机器相关绝对路径。
- 非必要不要引入新依赖；能用标准库解决的优先用标准库。

## 测试要求

- 所有可拆分的逻辑都应有测试覆盖。
- 与文件系统或渲染相关的逻辑可通过临时目录、桩函数或 mock 验证，不要求每次测试都真的生成完整图片。
- 交付前至少运行类型检查和测试；若某项无法运行，需要明确说明原因。

## 数据与输出文件

- 预览图、日志、缓存和虚拟环境不应纳入版本控制。
- 修改地图数据格式时，同步更新 `doc/` 下的格式文档。

## 需求文档

- 旧的前端需求草案保留在 `req.md`，但当前仓库不再以前端实现为目标。
- 如需继续演进，应优先围绕 Python 渲染、数据转换、地图格式和工具链展开。
