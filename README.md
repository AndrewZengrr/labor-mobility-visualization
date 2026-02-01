# Integrated Workforce Community Visualization Platform

## 🎯 概述

这是一个劳动力社区可视化平台，用于分析和可视化社区结构及其跨时间演化。包含两个核心模块：

1. **社区检测可视化** (index.html) - 展示单一年份的层级社区结构
2. **社区连接关系探索器** (community-connection-explorer.html) - 渐进式展开社区间的演化连接

---

## 📁 文件结构

```
labor-mobility-visualization/
├── index.html                                    # 主页面 - 社区检测可视化
├── prepare_community_connections_with_attributes.py  # 数据准备脚本
├── README.md                                     # 本文档
│
├── css/
│   ├── styles.css                               # 主平台样式
│   └── network-viewer.css                       # 网络视图样式
│
├── js/
│   ├── config.js                                # 社区可视化配置
│   ├── data-handler.js                          # 数据处理
│   ├── graph-data-loader.js                     # 图数据加载
│   ├── visualizer.js                            # 社区可视化核心
│   ├── composition.js                           # 组成分析
│   ├── network-viewer.js                        # 网络视图
│   └── app.js                                   # 主应用
│
└── explorers/                                    # 探索工具
    ├── community-connection-explorer.html       # 社区连接关系探索器 ⭐
    ├── COMMUNITY_CONNECTION_EXPLORER.md         # 连接探索器文档
    └── sample_community_connections.json        # 示例数据
```

---

## 🚀 使用流程

### 模块 1: 社区检测可视化

#### Step 1: 打开主页面
- 用浏览器打开 `index.html`
- 看到上传界面

#### Step 2: 上传数据
1. **必需文件**: 社区检测结果CSV
   - 文件示例: `workforce_geo_community_2023_2024_results.csv`
   - 包含: `geo_rcid`, `community_level1/2/3`, 各种属性列

2. **可选文件**: 图边数据CSV
   - 文件示例: `edges_data.csv`
   - 用于网络可视化
   - 包含: `source`, `target`, `weight`

#### Step 3: 探索社区
- **展开/折叠**: 左键点击节点
- **查看详情**: 右键点击节点
- **网络视图**: 双击叶子节点
- **切换布局**: 使用布局模式按钮
- **过滤**: 调整最小社区大小

#### Step 4: 进入社区连接探索器
- 点击右上角 **"Community Connection Explorer"** 按钮 🔗
- 自动跳转到社区连接关系探索器

---

### 模块 2: 社区连接关系探索器

这是一个**渐进式展开**的交互式工具，用于探索相邻年份间社区的连接关系。

#### 功能特性
- ✅ **渐进式展开**: 点击社区逐年展开其连接关系
- ✅ **详细属性展示**: 右键点击社区查看详细属性（州分布、产业分布等）
- ✅ **过滤与统计**: 实时统计显示节点数、边数、年份范围
- ✅ **灵活导航**: 支持缩放、拖拽、历史记录

#### Step 1: 准备数据

使用 `prepare_community_connections_with_attributes.py` 脚本从社区检测结果生成可视化数据：

```python
python prepare_community_connections_with_attributes.py
```

**所需输入文件**:
1. 相似度矩阵: `./similarity_matrices_complete/similarity_matrix_level1_complete.parquet`
2. 社区检测结果目录: `./workforce_community_results_adaptive_4d/`
   - 子目录格式: `results_2023_2024/`
   - 每个子目录包含该年度的社区检测结果CSV

**输出文件**:
- `community_connections_with_attributes.json` - 包含节点、边和详细属性的完整数据

#### Step 2: 加载数据
- 打开 `explorers/community-connection-explorer.html`
- 点击 **"加载数据"** 按钮
- 选择生成的 `community_connections_with_attributes.json` 文件

#### Step 3: 探索社区连接
- **初始视图**: 显示起始年份的所有社区
- **展开连接**: 左键点击社区，展开下一年的连接
- **查看属性**: 右键点击社区，查看详细属性分布
- **收起分支**: 再次左键点击已展开的社区可收起

#### Step 4: 查看详细属性

右键点击任何社区节点，可查看：
- 📊 **基本信息**: 年份、社区编号、规模、劳动力总数
- 🗺️ **Top 3 州分布**: 州名、数量、百分比
- 🏙️ **Top 5 都市区分布**: 都市区、数量、百分比
- 🏭 **Top 3/5 NAICS产业分布**: 2位/4位代码、数量、百分比
- 🏷️ **Top 3 RICS分类**: K50/K200分类及分布
- 🏢 **Top 10 公司**: 公司名称、数量、百分比

---

## 📊 数据格式要求

### 社区检测结果CSV

#### 必需列
```csv
geo_rcid,community_level1,community_level2,...
```

- `geo_rcid`: 节点唯一ID（地理位置编码）
- `community_level1`: 第1级社区ID
- `community_level2/3/...`: 更细粒度的社区层级（可选，支持动态检测）

#### 推荐属性列（用于详细分析）
```csv
rcid,company_name,real_state,real_metro_area,naics_code,rics_k50,rics_k200,workforce_total_people
```

- `rcid`: 原始公司ID
- `company_name`: 公司名称
- `real_state`: 州（如 California）
- `real_metro_area`: 都市区（如 San Francisco）
- `naics_code`: NAICS产业代码
- `rics_k50`, `rics_k200`, `rics_k400`: RICS分类
- `workforce_total_people`: 劳动力总人数

#### 示例行
```csv
geo_rcid,community_level1,rcid,company_name,real_state,real_metro_area,naics_code,workforce_total_people
RC123_CA_SF,1,RC123,Tech Corp,California,San Francisco,5112,500
RC456_NY_NYC,1,RC456,Finance Inc,New York,New York City,5221,800
```

---

### 相似度矩阵（Parquet格式）

由社区演化分析生成，包含：

**必需列**:
- `year1`, `year2`: 两个年份
- `community1`, `community2`: 社区ID
- `jaccard`: Jaccard相似度
- `retention_forward`, `retention_backward`: 保留率
- `overlap_size`, `union_size`: 重叠和并集大小
- `size1`, `size2`: 社区大小
- `growth_rate`: 增长率
- `year_gap`: 年份间隔

**可选列**（属性相似度）:
- `naics_cosine_similarity`, `naics_overlap_index`
- `state_cosine_similarity`, `state_overlap_index`
- `metro_cosine_similarity`, `metro_overlap_index`

---

### 输出JSON格式

`prepare_community_connections_with_attributes.py` 生成的JSON文件结构：

```json
{
  "nodes": [
    {
      "id": "2023_1",
      "year": 2023,
      "community": "1",
      "size": 150,
      "out_degree": 3,
      "in_degree": 2,
      "total_degree": 5,
      "attributes": {
        "total_workforce": 12500,
        "top3_states": [
          {"value": "California", "count": 100, "percentage": 66.67}
        ],
        "top5_metros": [...],
        "top3_naics_2digit": [...],
        "top5_naics_4digit": [...],
        "top3_rics_k50": [...],
        "top3_rics_k200": [...],
        "top10_companies": [...]
      }
    }
  ],
  "links": [
    {
      "source": "2023_1",
      "target": "2024_2",
      "jaccard": 0.45,
      "retention_forward": 0.62,
      "retention_backward": 0.38,
      "overlap_size": 85,
      "union_size": 200,
      "size1": 150,
      "size2": 135,
      "growth_rate": -0.10,
      "year_gap": 1
    }
  ],
  "stats": {
    "total_nodes": 250,
    "total_links": 450,
    "attributes_loaded": 250,
    "year_range": {"min": 2023, "max": 2027}
  }
}
```

---

## 🔧 数据准备脚本使用

### 基本用法

```python
from prepare_community_connections_with_attributes import ConnectionDataPreparerWithAttributes

# 配置路径
preparer = ConnectionDataPreparerWithAttributes(
    similarity_file="./similarity_matrices_complete/similarity_matrix_level1_complete.parquet",
    community_data_dir="./workforce_community_results_adaptive_4d",
    output_file="./community_connections_with_attributes.json"
)

# 运行
data = preparer.run()
```

### 目录结构要求

社区检测结果目录结构（支持嵌套）：

```
workforce_community_results_adaptive_4d/
├── results_2023_2024/           # 2023年度数据
│   └── community_results.csv
├── results_2024_2025/           # 2024年度数据
│   └── community_results.csv
└── results_2025_2026/           # 2025年度数据
    └── community_results.csv
```

**也支持扁平结构（向后兼容）**:
```
community_detection_results/
├── workforce_geo_community_2023_results.csv
├── workforce_geo_community_2024_results.csv
└── workforce_geo_community_2025_results.csv
```

### 调整过滤阈值

```python
# 创建准备器后，可以调整过滤阈值
preparer.min_overlap_size = 10              # 最小重叠节点数
preparer.min_retention_forward = 0.10       # 最小前向保留率
preparer.min_retention_backward = 0.10      # 最小后向保留率
preparer.min_jaccard = 0.05                 # 最小Jaccard相似度

# 运行
data = preparer.run()
```

---

## 🎨 可视化特性

### 社区检测可视化 (index.html)

- ✅ 支持动态层级深度检测
- ✅ 多种布局模式（圆形、力导向、树形）
- ✅ 按NAICS产业、州、都市区等属性着色
- ✅ 交互式展开/折叠
- ✅ 右键菜单详情面板
- ✅ 双击进入网络视图

### 社区连接探索器 (explorers/)

- ✅ 渐进式展开（逐年探索，而非一次性显示全部）
- ✅ 节点颜色编码：
  - 蓝色 = 已展开社区
  - 灰色 = 未展开社区
  - 红色 = 叶子社区（无后继）
- ✅ 边粗细：根据Jaccard相似度调整
- ✅ 详细属性面板：支持新格式（top3_states等）
- ✅ 统计信息：实时显示节点数、边数、年份范围
- ✅ 历史记录：支持导航回溯

---

## 💡 使用技巧

### 社区检测可视化
1. 先以小的最小社区大小过滤（如5），快速了解整体结构
2. 使用颜色编码按产业或地理分组识别模式
3. 右键点击节点查看详细组成
4. 双击叶子节点进入网络视图查看内部连接

### 社区连接探索器
1. 从起始年份的大社区开始探索
2. 逐年展开，观察社区演化路径
3. 使用右键菜单对比不同年份社区的属性变化
4. 关注高Jaccard相似度的连接（粗边）
5. 收起不感兴趣的分支，保持视图清晰

---

## 📖 相关文档

- **社区连接探索器详细文档**: `explorers/COMMUNITY_CONNECTION_EXPLORER.md`
- **示例数据**: `explorers/sample_community_connections.json`

---

## 🔄 工作流程图

```
┌──────────────────────────────────────┐
│  社区检测结果CSV（多年份）            │
│  + 相似度矩阵（parquet）              │
└─────────────┬────────────────────────┘
              │
              ▼
   ┌──────────────────────────────┐
   │ prepare_community_           │
   │ connections_with_            │
   │ attributes.py                │
   │                              │
   │ • 提取社区属性               │
   │ • 计算连接关系               │
   │ • 生成JSON                   │
   └──────────┬───────────────────┘
              │
              ▼
   ┌──────────────────────────────────┐
   │ community_connections_with_      │
   │ attributes.json                  │
   └──────────┬───────────────────────┘
              │
      ┌───────┴────────┐
      │                │
      ▼                ▼
┌──────────┐    ┌────────────────┐
│ index.   │    │ explorers/     │
│ html     │    │ community-     │
│          │    │ connection-    │
│社区层级  │    │ explorer.html  │
│可视化    │    │                │
│          │    │渐进式展开探索  │
└──────────┘    └────────────────┘
```

---

## 🛠️ 技术栈

**前端**:
- D3.js v7 - 数据驱动可视化
- HTML5 + CSS3
- JavaScript (ES6+)

**后端/数据**:
- Python 3 - 数据处理
- Pandas - 数据分析
- Parquet - 相似度矩阵存储
- JSON - 可视化数据格式

---

## 📝 版本说明

**当前架构**:
- ✅ 主模块：社区检测可视化 (index.html)
- ✅ 辅助模块：社区连接关系探索器 (explorers/community-connection-explorer.html)
- ✅ 数据准备：属性提取和整合脚本

**已移除的模块**:
- ❌ evolution-chain.html（已被community-connection-explorer.html取代）
- ❌ 相关的演化链JavaScript文件

---

## 🚀 快速开始

1. **准备数据**:
   ```bash
   python prepare_community_connections_with_attributes.py
   ```

2. **打开主页面**:
   - 浏览器打开 `index.html`
   - 上传社区检测结果CSV

3. **探索社区连接**:
   - 点击右上角 "Community Connection Explorer" 按钮
   - 加载生成的JSON文件
   - 开始渐进式探索！

---

**Enjoy visualizing! 🎉**
