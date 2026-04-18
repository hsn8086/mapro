# Mapro 下一代渲染器执行策略

## 1. 文档目标

本文档用于把总体规划和架构设计落到实施层，重点回答：

- 下一代渲染器应按什么顺序改
- 每一步具体改哪些模块
- 每一步最大的风险是什么
- 应该补哪些测试来避免“修一处坏一片”

## 2. 总体原则

### 2.1 小步演进

不要直接推翻现有 `draw_*` 体系，也不要一次性把圆角、共线、标签系统全部重写。

正确做法是：

1. 先插中间层
2. 再迁移职责
3. 每步都保持可运行
4. 每步都补测试

### 2.2 先结构，后风格

下一代视觉效果最终一定要依赖新的结构层，但第一阶段不是立刻让视觉发生大跳变，而是先把“结构上的地基”补齐。

### 2.3 先护栏，后重构

在当前仓库中，渲染层直接测试较少。任何新的架构层引入时，都必须同时补测试，不允许在没有护栏的情况下大规模移动逻辑。

## 3. 建议实施分期

## 3.1 第一阶段：引入 RenderPlan 中间层

目标：

- 把 renderer 当前的零散中间数据收束为明确对象
- 不改变外部调用方式
- 为后续几何层和标签层改造建立稳定承载物

建议改动：

- 新增 `map_gen/render_plan.py`
- 在 `map_gen/renderer.py` 中引入 `build_render_plan(...)`
- 让 `draw_metro_map(...)` 先构建 `RenderPlan` 再交给现有 `draw_*` 模块

本阶段不应做的事：

- 不要同时重写 `draw/lines.py`
- 不要同时引入圆角
- 不要同时改动标签布局算法

主要风险：

- 只是把旧逻辑包一层，未形成真正语义边界
- renderer 仍然可能继续把 plan 当临时 dict 使用

建议测试：

- 新增 `tests/test_render_plan.py`
- 覆盖 `build_render_plan(...)` 的基本行为
- 验证空站点、显式 `viewport`、`font_paths`、`segment_data` 与 `station_markers` 的构建结果

## 3.2 第二阶段：抽离线路笔画构建

目标：

- 把 `draw/lines.py` 中的路径偏移、厚度、分段颜色等逻辑抽离出来
- 让 `draw/lines.py` 逐步只保留最终画线动作

建议改动：

- 新增 `map_gen/stroke_builder.py`
- 定义中间笔画对象，如 `OffsetSegment`
- 把 planned/inactive/tram 等规则前移到 builder 层

主要风险：

- 线宽、颜色、偏移顺序可能悄悄变化
- 共线段渲染可能与旧图不完全一致

建议测试：

- 新增 `tests/test_draw_lines.py`
- 新增 `tests/test_stroke_builder.py`
- 覆盖单线、双线共线、`tram` 细线、planned 段等场景

## 3.3 第三阶段：抽离标签布局与碰撞检测

目标：

- 让 `draw/stations.py` 只负责站点与文本绘制
- 把标签候选搜索、碰撞检测、最终排布抽离成独立层

建议改动：

- 新增 `map_gen/label_layout.py`
- 把矩形碰撞、线路碰撞、标签互斥逻辑迁移出去

主要风险：

- 标签位置大规模漂移
- marker 与英文副标题之间的对齐失稳

建议测试：

- 新增 `tests/test_draw_stations.py`
- 新增 `tests/test_label_layout.py`
- 覆盖单站、换乘站、密集区、斜线路径附近的标签场景

## 3.4 第四阶段：引入路径后处理

目标：

- 让中心折线经过共线压缩、冗余点处理与后续圆角化
- 为下一代线条风格建立真正的几何系统

建议改动：

- 新增 `map_gen/path_postprocess.py`
- 后续视需要新增 `map_gen/corner_rounding.py`

本阶段可先做：

- 连续共线点压缩
- bundle 结构准备
- 为圆角预留数据接口

后续再打开：

- 真正的受控圆角绘制

主要风险：

- 偏移后的多线拐角几何失真
- 圆角侵入站点圆圈或标签区

建议测试：

- 几何级单元测试
- 关键局部图的像素回归测试
- 与标签碰撞逻辑的集成测试

## 3.5 第五阶段：版式与后端演进

目标：

- 让标题、图例与主图真正形成版式系统
- 为未来切换 SVG 或更强 path backend 留接口

建议改动：

- 优先调整 title/legend 参与布局
- 后续再考虑抽象 `backend`

主要风险：

- 过早抽象 backend 导致第一阶段改造复杂度失控

建议测试：

- `tests/test_draw_title.py`
- `tests/test_draw_legend.py`
- renderer 层编排测试

## 4. 重点风险矩阵

### 4.1 高风险项

1. 共线分槽规则迁移
2. 标签避让算法迁移
3. 圆角上线后碰撞几何失真
4. 标题与图例加入版式后影响现有留白

### 4.2 中风险项

1. 样式常量重组
2. `segment_data` 语义进一步细化
3. `font_paths` 和字体测量逻辑在新层中的复用

### 4.3 低风险项

1. 引入 `RenderPlan` 过渡对象
2. 为 renderer 增加更明确的中间类型
3. 为 title/legend 增加独立单元测试

## 5. 测试建设顺序

建议严格按以下顺序补测试：

1. `tests/test_render_plan.py`
2. `tests/test_draw_lines.py`
3. `tests/test_draw_stations.py`
4. `tests/test_draw_title.py`
5. `tests/test_draw_legend.py`
6. `tests/test_draw_links.py`
7. 后续再补 `tests/test_path_postprocess.py`

这样可以让每一步架构演进都有最近邻的护栏。

## 6. 每步完成后的验收标准

### 第一阶段验收

- `draw_metro_map(...)` 外部行为不变
- `RenderPlan` 已成为 renderer 内部统一中间结构
- 新增测试通过

### 第二阶段验收

- `draw/lines.py` 中的几何判断明显减少
- 线路偏移和样式生成逻辑可独立测试

### 第三阶段验收

- `draw/stations.py` 主要职责收缩为绘制
- 标签布局逻辑可独立测试

### 第四阶段验收

- 共线与圆角具备独立几何层
- 碰撞检测开始复用更真实的路径数据

### 第五阶段验收

- 标题、图例与主图形成统一版式
- 为未来 backend 抽象留下清晰接口

## 7. 对本轮开始实现的建议

本轮最适合进入编码的，是第一阶段：

1. 写清文档
2. 引入 `RenderPlan`
3. 补 `tests/test_render_plan.py`
4. 运行格式化、类型检查、单元测试

原因：

- 这一步风险最低
- 对后续所有阶段都有帮助
- 不会让视觉结果一下子不可控

## 8. 结论

下一代渲染器的最佳落地顺序，不是“先做最炫的圆角”，而是：

- 先让结构稳定
- 再让几何分层清晰
- 最后让视觉能力自然长出来

只要这条顺序保持住，后续无论是共线升级、圆角、标签系统还是版式系统，都可以在较低风险下逐步落地。
