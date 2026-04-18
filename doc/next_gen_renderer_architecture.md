# Mapro 下一代渲染器架构设计

## 1. 文档目标

本文档用于细化 `doc/render_style_next_gen_plan.md` 中的架构部分，重点回答以下问题：

- 当前渲染器的真实分层是怎样的
- 下一代渲染器应在哪些位置插入新层，而不是直接重写旧层
- 圆角、共线、标签避让等核心能力应落在哪一层
- 哪些模块适合保留，哪些模块适合逐步抽离

本文档聚焦 Python 静态渲染实现，不涉及前端或交互式渲染。

## 2. 当前渲染器的真实分层

当前渲染流程以 `map_gen/renderer.py` 为总入口，可拆为以下层次：

### 2.1 顶层编排层

文件：`map_gen/renderer.py`

职责：

- 读取 `stations`、`lines`、`meta` 等基础数据
- 生成 `layout`
- 生成样式常量
- 构建线路段索引与站点 marker
- 按顺序调用 `draw_lines`、`draw_transfer_connections`、`draw_stations`、`draw_title_block`、`draw_legend`

评价：

- 这一层的职责总体合理
- 适合作为下一代渲染器继续保留的总入口
- 问题不在入口，而在入口向下传递的数据仍然比较零散

### 2.2 布局层

文件：`map_gen/layout.py`

职责：

- 计算站点边界
- 根据 `viewport` 或自动边界生成画布尺寸
- 提供 `get_pos` 坐标转换函数

评价：

- 当前边界清晰
- `Layout` dataclass 可以直接作为下一代渲染器的基础对象之一

### 2.3 路径生成层

文件：`map_gen/router.py`、`map_gen/geometry.py`

职责：

- 将站点点列转换为八方向折线路径
- 对候选路径进行评分，选择较优路线

评价：

- 这层负责“走哪条路径”，职责是合理的
- 下一代中可保留接口不变，仅在必要时升级内部算法
- 不建议把圆角或最终画笔语义塞进这层

### 2.4 段分析层

文件：`map_gen/segments.py`

职责：

- 为每条线路生成 polyline
- 切分共享路径上的原子线段
- 构建 `segment_map` 和 `segment_offsets`
- 生成 `skip_map`
- 为标签碰撞准备 `line_segments_for_collision`

评价：

- 这是当前系统最接近“中间几何层”的部分
- 方向是对的，但输出语义还不够稳定
- 当前同时混合了拓扑分析、偏移准备和标签避让数据，后续应继续细分

### 2.5 绘制层

文件：`map_gen/draw/*.py`

职责：

- 把线路、站点、连接、标题、图例画到 PIL 画布上

评价：

- `draw/title.py` 和 `draw/legend.py` 较纯
- `draw/links.py` 中等复杂度，可继续保留但后续需要样式统一
- `draw/lines.py` 与 `draw/stations.py` 负担过重，既有绘制逻辑，又有几何/布局逻辑，是后续演进重点

## 3. 当前架构的主要问题

### 3.1 `draw/lines.py` 既算几何又绘制

该模块当前同时承担：

- 线路状态分段颜色判断
- 共线时的槽位计算
- 每条线的偏移几何计算
- `tram` 等制式的线宽特判
- 端点圆帽模拟
- 最终 PIL 画线

问题：

- 以后若要支持圆角、平滑连接、不同 backend，会变得很难替换
- draw 层不应承担大量“路径成形”职责

### 3.2 `draw/stations.py` 同时是绘制器、布局器和碰撞器

该模块当前同时承担：

- 站点圆点绘制
- 标签尺寸测量与排布
- 与线路段碰撞检测
- 与其他标签框碰撞检测
- marker 与设施标签排布

问题：

- 后续任何标签系统升级都会导致此文件持续膨胀
- 标签逻辑很难独立测试

### 3.3 `styles.py` 抽象层级偏弱

当前仅返回 `dict[str, float | str]`，适合一代渲染器，但不足以表达：

- 线路 join/cap/corner radius
- marker padding / badge radius
- 标签碰撞阈值
- 图例与标题版式参数

这不是错误，但意味着下一代中至少要开始朝结构化样式对象演进。

## 4. 下一代渲染器目标架构

下一代渲染器不应从头推翻，而应在现有入口和现有布局、路由层之间插入更稳定的中间层。

目标结构如下：

1. 输入数据层
2. 布局层
3. 路由层
4. 几何计划层
5. 标签布局层
6. 绘制后端层

其中最关键的是第 4 层和第 5 层。

## 5. 关键中间层设计

### 5.1 RenderPlan 层

建议新增模块：`map_gen/render_plan.py`

作用：

- 把 renderer 入口里的零散中间数据收束成明确对象
- 为后续继续拆分几何层与标签层提供稳定承载物

推荐承载内容：

- `layout`
- `styles`
- `stations`
- `lines`
- `meta`
- `connections`
- `segment_data`
- `station_markers`
- `font_paths`
- `line_width`

第一阶段不要求一步到位，只要求开始把 renderer 的运行时上下文结构化。

### 5.2 网络几何层

建议新增模块：`map_gen/stroke_builder.py` 或后续更泛化的 `map_gen/path_postprocess.py`

作用：

- 将中心线与共享段分析结果转为真正可绘制的笔画几何
- 把 `draw/lines.py` 中的偏移、厚度、状态色等计算前移

这一层最终应产出：

- 单条线路的中心路径
- 共线路径上的 bundle 信息
- 每条线在每个 bundle 内的偏移结果
- 后续可接入的圆角化路径

### 5.3 标签布局层

建议新增模块：`map_gen/label_layout.py`

作用：

- 输入站点文本测量结果、线路碰撞几何、已有标签框
- 输出每个站点最终的 label placement

这层的引入可以显著减轻 `draw/stations.py` 的职责。

## 6. 圆角与共线的落层原则

### 6.1 共线属于几何分析问题

共线本质上回答的是：

- 哪些线路共享同一段中心路径
- 这些线路在同一 bundle 内如何稳定排列
- 它们在分叉与汇合时怎样过渡

因此共线应落在：

- `router` 之后
- `draw` 之前
- 更准确地说，落在路径分析/几何准备层

不应把共线作为 draw 层的临时偏移技巧长期保留。

### 6.2 圆角属于路径后处理问题

圆角本质上回答的是：

- 已经确定好的最终偏移路径，在视觉上如何处理拐角

因此圆角应落在：

- 中心折线生成之后
- 共线偏移路径确定之后
- 最终绘制之前

不应放在 router 层，因为 router 负责“拓扑路线”，不负责“画笔风格”。
也不应直接塞进 draw 层，否则碰撞检测和路径复用会失真。

### 6.3 正确顺序

正确顺序应为：

1. 生成中心线折线
2. 分析共享段与 bundle
3. 生成每条线的 offset path
4. 对 offset path 做圆角或其他路径后处理
5. 输出给绘制后端

## 7. 推荐保留与抽离策略

### 7.1 应优先保留的部分

- `draw_metro_map(...)` 外部函数签名
- `layout.py` 的整体结构
- `router.py` 的职责边界
- `markers.py` 这种纯派生数据模块
- 现有 CLI 和主流程

### 7.2 应优先抽离的部分

- `draw/lines.py` 中的几何与偏移计算
- `draw/stations.py` 中的标签布局与碰撞检测
- `segments.py` 中后续可拆分为更稳定语义模型的内容

## 8. 推荐数据对象草图

本节只给方向，不要求当前一次性全部落地。

### 8.1 RenderPlan

可作为第一阶段就开始引入的对象：

- `layout`
- `styles`
- `stations`
- `lines`
- `meta`
- `connections`
- `segment_data`
- `station_markers`
- `font_paths`
- `line_width`

### 8.2 后续可继续引入的对象

- `RoutedLine`
- `SharedSegment`
- `OffsetSegment`
- `StationLabelPlacement`
- `LegendLayout`
- `TitleLayout`

这些对象的目标不是增加形式主义，而是减少 draw 层对原始数据和临时缓存的依赖。

## 9. 对第一阶段代码实现的约束

第一阶段应满足以下约束：

1. 不改变 CLI 调用方式
2. 不改变 `draw_metro_map(...)` 的外部签名
3. 不要求一次性上圆角或重写共线系统
4. 允许 renderer 内部先新增 RenderPlan 过渡层
5. 每引入一层结构，都要补最少一组直接测试

## 10. 结论

下一代渲染器的优雅演进，不在于“把旧代码全部删掉重写”，而在于：

- 保留已有合理层次
- 在 `router` 与 `draw` 之间补齐中间几何层
- 在 `draw/stations.py` 前补齐标签布局层
- 让 draw 层逐步收缩为“只负责绘制，而不负责做大量决策”

这条路线的核心价值是：

- 可以小步推进
- 可以持续回归
- 可以在保持现有功能可用的前提下，逐步长成下一代渲染器
