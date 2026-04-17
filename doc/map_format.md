# Mapro 地铁线路图数据格式规范 (v1.0)

本文档详细定义了 Mapro 应用程序中使用的地铁线路图数据结构。该数据格式基于 TypeScript 接口定义，用于存储、导出和导入地图数据。

## 1. 核心结构 (MapData)

整个地图数据存储在一个 JSON 对象中，对应 `MapData` 接口。

除单个 JSON 文件外，Mapro 也支持“目录地图包”与 ZIP 压缩包。目录地图包会在加载时合并为同一份 `MapData`。

| 字段名 | 类型 | 描述 |
| :--- | :--- | :--- |
| `id` | `string` | 地图的唯一标识符 |
| `meta` | `Object` | 地图的元数据信息（见下文） |
| `pricing` | `Object` | (可选) 基础计价规则配置 |
| `stations` | `Record<string, Station>` | 站点集合，键为站点 ID |
| `lines` | `Record<string, Line>` | 线路集合，键为线路 ID |
| `connections` | `TransferConnection[]` | 换乘连接列表（用于定义特殊的换乘关系） |

### 1.1 元数据 (meta)

| 字段名 | 类型 | 描述 |
| :--- | :--- | :--- |
| `name` | `LocalizedString` | 地图名称（支持多语言） |
| `author` | `string` | 作者名称 |
| `version` | `string` | 数据版本号 |
| `createTime` | `string` | 创建时间 (ISO 8601 格式) |
| `updateTime` | `string` | 最后更新时间 (ISO 8601 格式) |
| `pricingScript` | `string` | (可选) 自定义计价逻辑的 JavaScript 代码字符串 |
| `viewport` | `Object` | (可选) 显式指定渲染视口边界；未提供时，程序会根据站点坐标自动计算 |

#### `meta.viewport`

当需要锁定画面范围、预留额外留白，或避免自动边界随站点编辑波动时，可指定此字段。

| 字段名 | 类型 | 描述 |
| :--- | :--- | :--- |
| `min_x` | `number` | 视口最小 X 坐标 |
| `max_x` | `number` | 视口最大 X 坐标 |
| `min_y` | `number` | 视口最小 Y 坐标 |
| `max_y` | `number` | 视口最大 Y 坐标 |

### 1.2 计价配置 (pricing)

如果未提供 `pricingScript`，系统将使用此简单配置进行计价。

| 字段名 | 类型 | 描述 |
| :--- | :--- | :--- |
| `type` | `'distance' \| 'station_count' \| 'fixed'` | 计价模式：按里程、按站数或固定票价 |
| `basePrice` | `number` | 起步价 |
| `unitPrice` | `number` | 单价（每公里或每站的价格） |

---

## 2. 站点 (Station)

定义单个物理站点及其属性。

| 字段名 | 类型 | 描述 |
| :--- | :--- | :--- |
| `id` | `string` | 站点唯一 ID |
| `name` | `LocalizedString` | 站点名称 |
| `x` | `number` | 在 SVG 画布上的 X 坐标 |
| `y` | `number` | 在 SVG 画布上的 Y 坐标 |
| `isTransfer` | `boolean` | 是否为换乘站（UI 渲染标记） |
| `lines` | `string[]` | 经过此站点的线路 ID 列表 |
| `exits` | `StationExit[]` | (可选) 出口信息列表 |
| `facilities` | `StationFacility[]` | (可选) 设施列表 |
| `status` | `'active' \| 'deferred' \| 'closed'` | (可选) 站点状态。`active`: 正常(默认)。`deferred`: 暂缓开通(列车通过, 站点灰色, 线路正常)。`closed`: 封闭(列车不通, 站点与连接线路均灰色)。对于混合状态(如换乘站仅部分线路开通)，应设为 `active`。 |
| `nearbyLandmarks` | `LocalizedString[]` | (可选) 周边地标列表 |
| `markdownDescription` | `LocalizedString` | (可选) 站点的 Markdown 格式详细描述 |

### 2.1 站点附属信息

*   **StationExit (出口):**
    *   `name`: 出口编号/名称 (如 "A", "B1")
    *   `destinations`: 该出口可到达的地点列表

*   **StationFacility (设施):**
    *   `type`: 设施类型 (`'toilet' | 'elevator' | 'shop' | 'other'`)
    *   `description`: 设施描述 (多语言)

---

## 3. 线路 (Line)

定义一条运行线路。

| 字段名 | 类型 | 描述 |
| :--- | :--- | :--- |
| `id` | `string` | 线路唯一 ID |
| `name` | `LocalizedString` | 线路名称 |
| `color` | `string` | 线路代表色 (HEX, RGB) |
| `type` | `string` | 类型：`'subway'`, `'tram'`, `'maglev'`, `'other'` |
| `width` | `number` | (可选) 线路绘制宽度 |
| `status` | `'active' \| 'under_construction' \| 'planned'` | (可选) 线路状态：`active`(默认)运营中, `under_construction`建设中, `planned`规划中 |
| `stations` | `(string \| LineStation)[]` | 有序的站点列表。可以是简单的站点 ID 字符串，也可以是包含状态的对象。 |
| `segments` | `StationEdge[]` | (可选) 相邻站点间的距离/时间数据 |

### 3.1 线路站点对象 (LineStation)

如果需要为特定线路指定站点的特殊状态（如暂缓开通、越站通过），可使用对象格式：

| 字段名 | 类型 | 描述 |
| :--- | :--- | :--- |
| `id` | `string` | 站点 ID |
| `status` | `'active' \| 'deferred' \| 'pass' \| 'planned'` | `active`: 正常停靠(默认); `deferred`: 暂缓开通(列车通过不停); `pass`: 越站(列车通过不停，且不视为未开通); `planned`: 规划/建设中(线路该段未开通，绘制为灰色) |
| `num` | `string` | (可选) 站点在线路中的编号 (如 "01", "12") |
| `service` | `'local' \| 'rapid' \| 'express'` | (可选) 停靠类型：`local` (普通/默认), `rapid` (快速), `express` (特快) |

### 3.2 线路片段 (StationEdge)

用于精确定义线路中两站之间的物理属性，用于路径规划算法。

*   `from`: 起始站点 ID
*   `to`: 终点站点 ID
*   `distance`: 距离 (公里)
*   `duration`: 行驶时间 (分钟)

### 3.2 车辆信息 (LineInfo)

*   `manufacturer`: 制造商
*   `maxSpeed`: 最高时速 (km/h)
*   `techType`: 技术类型 (如 "Third Rail")
*   `carriages`: 车厢配置列表 (`LineCarriageInfo`)，包含是否弱冷、女性专用、轮椅位等信息。

---

## 4. 换乘连接 (TransferConnection)

定义站点之间的特殊连接关系，通常用于非同站换乘或复杂的换乘通道。

| 字段名 | 类型 | 描述 |
| :--- | :--- | :--- |
| `fromStationId` | `string` | 起始站点 ID |
| `toStationId` | `string` | 目标站点 ID |
| `type` | `'virtual' \| 'physical' \| 'bus'` | 连接类型。`virtual`: 出站换乘 (虚线); `physical`: 同站换乘 (用于强调或复杂枢纽); `bus`: 接驳公交 |
| `walkingTime` | `number` | (可选) 换乘步行耗时 (分钟) |

---

## 5. 通用类型

### 5.1 多语言字符串 (LocalizedString)

用于支持国际化显示的键值对对象。

```json
{
  "zh-CN": "人民广场",
  "en-US": "People's Square"
}
```

---

## 6. 地图包格式

推荐使用目录地图包作为开发态格式，再按需打包为 ZIP 进行分发。

```text
example_map/
  map.json
  stations/
    core.json
    branch_a.json
  lines/
    metro.json
  connections/
    transfers.json
```

### 6.1 `map.json`

- 用于存放全局字段，如 `id`、`meta`、`pricing`
- 也可以包含 `stations`、`lines`、`connections`，但更推荐拆到对应子目录

### 6.2 子模块目录

- `stations/*.json`: 每个文件都可以包含一个 `stations` 对象
- `lines/*.json`: 每个文件都可以包含一个 `lines` 对象
- `connections/*.json`: 每个文件都可以包含一个 `connections` 数组

### 6.3 合并规则

- 所有模块在加载时合并为一份完整的 `MapData`
- `stations` 和 `lines` 的键必须全局唯一，重复会报错
- `connections` 会按数组顺序追加
