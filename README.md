# Mapro

Mapro 是一个面向地铁图数据的 Python CLI 工具，当前聚焦于静态渲染和地图数据分析。

## 功能

- 渲染地铁图为 PNG 预览图
- 监听地图数据文件变化并自动重绘
- 在渲染前按倍数缩放站点坐标
- 计算地图站点坐标边界
- 支持目录地图包与 ZIP 地图包
- 支持地图包打包与解包

## 安装

```bash
uv sync
```

## 用法

查看帮助：

```bash
uv run python main.py --help
```

渲染预览图：

```bash
uv run python main.py render library/gz --output map_preview.png
```

渲染前缩放坐标：

```bash
uv run python main.py render library/gz --scale 1.5 --output map_preview.png
```

监听文件变化：

```bash
uv run python main.py render library/gz --watch
```

计算坐标边界：

```bash
uv run python main.py bounds library/gz
```

渲染目录地图包：

```bash
uv run python main.py render maps/gz_map/
```

仓库里已经拆好了一个完整示例包：

```bash
uv run python main.py render library/gz --output map_preview.png
```

打包目录地图包：

```bash
uv run python main.py pack maps/gz_map/ --output gz_map.zip
```

解包地图压缩包：

```bash
uv run python main.py unpack gz_map.zip --output maps/gz_map/
```

也可以通过安装后的命令入口运行：

```bash
uv run mapro --help
```

## 地图包

目录地图包推荐结构：

```text
gz_map/
  map.json
  stations/
    101.json
    102.json
  lines/
    1.json
    2.json
  connections/
    core.json
```

- `map.json` 用于存放 `id`、`meta`、`pricing` 等全局信息
- `stations/*.json` 中放 `stations`，推荐每站一个文件
- `lines/*.json` 中放 `lines`，推荐每线一个文件
- `connections/*.json` 中放 `connections`
- CLI 会在加载时自动合并这些模块
- 仓库内也提供了从 `gz.json` 拆出的完整目录包：`library/gz/`

## 开发

```bash
uvx ruff format
uvx ty check .
uv run python -m unittest discover -s tests
```
