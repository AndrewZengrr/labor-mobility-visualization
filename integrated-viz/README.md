# 劳动力社区演化可视化平台 (Integrated Workforce Community Visualization Platform)

## 🎯 概述

这是一个集成的劳动力社区分析和可视化平台，用于分析和展示职业流动网络中的社区结构及其跨时间演化。

**核心功能**：
1. **社区检测可视化** - 展示单一年份的层级社区结构
2. **演化链可视化** - 展示社区跨时间（2000-2024年）的演化轨迹

---

## 📁 项目结构

```
integrated-viz/
├── Python 数据处理脚本
│   ├── graph.py                    # 图数据构建（从原始职业流动数据）
│   ├── community_detection.py      # 社区检测（Leiden算法，4维属性纯净度）
│   ├── similarity.py               # 相似度矩阵计算
│   └── community_matchting.py      # 社区演化链构建（增强版，包含完整属性）
│
├── HTML 可视化页面
│   ├── index.html                  # 主页面 - 社区检测可视化
│   └── evolution-chain.html        # 演化链可视化页面
│
├── JavaScript 前端代码
│   ├── 社区检测模块
│   │   ├── app.js                  # 主应用逻辑
│   │   ├── config.js               # 配置文件
│   │   ├── data-handler.js         # 数据处理
│   │   ├── graph-data-loader.js    # 图数据加载
│   │   ├── visualizer.js           # 可视化核心
│   │   ├── composition.js          # 组成分析
│   │   └── network-viewer.js       # 网络视图
│   │
│   └── 演化链模块
│       ├── evolution-app.js        # 演化链应用
│       ├── evolution-config.js     # 演化链配置
│       ├── evolution-data-loader.js # 演化链数据加载
│       ├── evolution-visualizer.js  # 演化链可视化
│       └── evolution-detail-panel.js # 详情面板
│
├── CSS 样式文件
│   ├── styles.css                  # 主平台样式
│   ├── network-viewer.css          # 网络视图样式
│   └── evolution-styles.css        # 演化链样式
│
└── README.md                       # 本文档
```

---

## 🚀 完整数据处理和可视化流程

### 阶段 1: 图数据构建

**文件**: `graph.py`

**输入数据**:
- `individual_positions.parquet` - 个人职位历史数据
- `company_geo_distribution.parquet` - 公司地理分布数据

**处理流程**:
```python
python graph.py
```

**输出**:
- `graph_data_rolling_windows_updated/graph_{year-1}_{year}/`
  - `nodes_data.parquet` - 节点数据（公司地理位置）
  - `edges_data.parquet` - 边数据（职业转换流）
  - `graph_metadata.json` - 图元数据

**关键参数**:
- 滚动2年窗口（例如：2019-2020年）
- 节点：geo_rcid（公司+地理位置）
- 边：职业转换流（flow_count >= weight_threshold）

---

### 阶段 2: 社区检测

**文件**: `community_detection.py`

**输入**:
- 阶段1输出的图数据文件夹

**处理流程**:
```python
python community_detection.py
```

**输出**:
- `workforce_community_results_adaptive_4d/results_{year-1}_{year}/`
  - `workforce_geo_community_{year-1}_{year}_results.parquet` - 社区检测结果
  - `workforce_geo_community_{year-1}_{year}_community_metadata.parquet` - 社区元数据
  - `workforce_geo_community_{year-1}_{year}_summary.txt` - 摘要报告

**算法**:
- **Leiden算法** - 层级社区检测
- **停止条件** - 基于4维属性纯净度（NAICS 2位/4位、State、Metro Area）
- **参数**:
  - `min_size=10` - 最小社区规模
  - `purity_multiplier=5` - 纯净度阈值倍数
  - `max_depth=6` - 最大层级深度

**输出格式**:
| 列名 | 说明 |
|------|------|
| geo_rcid | 节点ID（公司地理位置） |
| community_level1/2/3... | 各层级社区标签 |
| rcid, company_name | 公司信息 |
| real_state, real_metro_area | 地理信息 |
| naics_code | 行业代码 |
| role_k1500_vector | 职位分布向量 |
| avg_seniority, avg_salary等 | 统计属性 |

---

### 阶段 3: 相似度矩阵计算

**文件**: `similarity.py`

**输入**:
- 阶段2输出的所有年份社区检测结果

**处理流程**:
```python
python similarity.py
```

**输出**:
- `similarity_matrices_complete/`
  - `similarity_matrix_level1_complete.parquet` - 完整相似度矩阵
  - `similarity_matrix_metadata_level1_complete.json` - 元数据

**相似度指标**:
1. **核心指标**（基于节点重叠）:
   - `jaccard` - Jaccard相似度系数
   - `retention_forward` - 前向保留率（year1 → year2）
   - `retention_backward` - 后向保留率（year2 ← year1）

2. **参考指标**（基于属性分布）:
   - `naics_cosine_similarity` - NAICS分布余弦相似度
   - `state_cosine_similarity` - 州分布余弦相似度
   - `metro_cosine_similarity` - 都市区分布余弦相似度

**优化**:
- 预计算所有社区的属性分布（避免重复计算）
- 支持并行计算（可选）
- 输出所有年份对的相似度（包括零值）

---

### 阶段 4: 演化链构建

**文件**: `community_matchting.py`

**输入**:
- 阶段3输出的相似度矩阵
- 阶段2输出的所有年份社区检测结果

**处理流程**:
```python
python community_matchting.py
```

**输出**:
- `evolution_chains_enhanced/`
  - `weighted_chain_details_level1.json` - **演化链详细数据**（用于可视化）
  - `basic_gap1_nodes.json` - 节点数据
  - `basic_gap1_edges.json` - 边数据
  - `basic_gap1_chains_full.parquet` - 完整链数据
  - `basic_gap1_metadata.json` - 元数据
  - `basic_gap1_d3_format.json` - D3.js格式数据

**核心改进**:
✅ **增强版演化链构建** - 包含完整的社区属性
✅ **节点组成分析** - 计算核心节点vs新节点比例
✅ **社区类型分类** - new_born / established / transitional
✅ **完整属性提取** - Top 3 States, Top 5 Metros, Top 3/5 NAICS, Top 10 Roles

**输出JSON格式** (weighted_chain_details_level1.json):
```json
[
  {
    "stable_id": "S2000_1",
    "length": 15,
    "score": 0.82,
    "communities": [
      {
        "year": 2000,
        "community_id": "1",
        "attributes": {
          "size": 250,
          "top3_states": [
            {"value": "CA", "count": 150, "percentage": 60.0},
            {"value": "NY", "count": 50, "percentage": 20.0},
            {"value": "TX", "count": 30, "percentage": 12.0}
          ],
          "top5_metros": [...],
          "top3_naics_2digit": [
            {"value": "51", "count": 100, "percentage": 40.0},
            ...
          ],
          "top5_naics_4digit": [...],
          "top10_roles": [
            {"role": "Software Engineer", "count": 80, "percentage": 32.0},
            ...
          ]
        },
        "node_composition": {
          "type": "established",
          "core_node_ratio": 0.75,
          "new_node_ratio": 0.15,
          "avg_node_weight": 0.75,
          "core_nodes": 188,
          "new_nodes": 38
        }
      },
      ...
    ]
  },
  ...
]
```

---

## 🎨 可视化使用指南

### 模块 1: 社区检测可视化

**文件**: `index.html`

**步骤**:
1. 用浏览器打开 `index.html`
2. 上传社区检测结果CSV（例如：`workforce_geo_community_2019_2020_results.csv`）
3. （可选）上传图边数据CSV（用于网络视图）
4. 探索社区结构：
   - **左键点击** - 展开/折叠社区
   - **右键点击** - 查看组成详情
   - **双击叶子节点** - 进入网络视图
5. 调整可视化：
   - 切换布局模式（自适应树/径向/分层）
   - 调整最小社区大小
   - 选择颜色和大小属性

**界面特性**:
- ✅ 自适应层级展示（支持任意深度）
- ✅ 三种布局模式
- ✅ 动态节点间距，防止重叠
- ✅ 碰撞检测
- ✅ 网络视图
- ✅ 组成分析面板

---

### 模块 2: 演化链可视化

**文件**: `evolution-chain.html`

**步骤**:
1. 用浏览器打开 `evolution-chain.html`
2. 点击 "Choose JSON File"
3. 选择 `weighted_chain_details_level1.json`
4. 等待数据加载
5. 探索演化链：
   - **点击节点** - 查看该年份社区的详细属性
   - **悬停链** - 高亮显示整条演化链
   - **点击侧边栏链** - 高亮并聚焦该链

**过滤和排序**:
- **按长度过滤**: Singleton / Short / Medium / Long / Very Long
- **排序方式**: Length / Score / Start Year / Size
- **布局模式**: Timeline / Vertical Lanes / Force-Directed
- **显示数量**: 最多显示的链数量

**详情面板内容**:
- 📊 基本信息（年份、规模、类型）
- 👥 节点组成（核心/新节点比例）
- 📍 州分布（Top 3）
- 🏙️ 都市区分布（Top 5）
- 🏭 NAICS 2位/4位行业分布
- 💼 Top 10职位角色

**界面特性**:
- ✅ 时间轴可视化
- ✅ 多种布局模式
- ✅ 链长度过滤和排序
- ✅ 详细的社区属性展示
- ✅ 交互式链列表侧边栏
- ✅ 实时统计面板
- ✅ 颜色编码（按链长度）

---

### 模块切换

**从社区检测 → 演化链**:
- 点击右上角 🔗 **"Evolution Chains"** 按钮

**从演化链 → 社区检测**:
- 点击左上角 ← **"Back to Community View"** 按钮

---

## 💡 典型工作流程

### 工作流 A: 数据处理完整流程

```bash
# 步骤1: 构建图数据（2000-2024年，每年一个图）
python graph.py

# 步骤2: 社区检测（批量处理所有年份）
python community_detection.py

# 步骤3: 计算相似度矩阵（所有年份对）
python similarity.py

# 步骤4: 构建演化链（包含完整属性）
python community_matchting.py
```

### 工作流 B: 从社区到演化分析

```
1. 打开 index.html
2. 上传某年社区检测结果（如2020年）
3. 探索该年的社区结构
4. 点击 "Evolution Chains" 按钮
5. 上传 weighted_chain_details_level1.json
6. 找到包含该年的演化链
7. 查看该社区的历史和未来演化
```

### 工作流 C: 从演化到社区分析

```
1. 打开 evolution-chain.html
2. 上传 weighted_chain_details_level1.json
3. 识别感兴趣的演化模式（如长期稳定链）
4. 记录特定年份的社区ID
5. 返回 index.html
6. 上传对应年份的社区数据
7. 深入分析该社区的详细结构
```

---

## 📊 数据文件要求

### 社区检测结果 CSV/Parquet

**必需列**:
- `geo_rcid` - 节点ID
- `community_level1`, `community_level2`, ... - 社区层级标签
- `rcid` - 原始公司ID
- `company_name` - 公司名称
- `real_state` - 州
- `real_metro_area` - 都市区
- `naics_code` - NAICS行业代码

**可选列**:
- `rics_k50`, `rics_k200`, `rics_k400` - RICS分类
- `role_k1500_vector` - 职位分布向量
- `avg_seniority`, `avg_salary` 等 - 统计属性

---

### 演化链 JSON (weighted_chain_details_level1.json)

**顶层结构**:
```json
[
  {
    "stable_id": "S2000_1",      // 链的唯一标识符
    "length": 15,                 // 链长度（年数）
    "score": 0.82,                // 链得分（0-1）
    "communities": [...]          // 社区列表
  }
]
```

**社区对象结构**:
```json
{
  "year": 2000,
  "community_id": "1",
  "attributes": {
    "size": 250,
    "top3_states": [...],         // [{"value": "CA", "count": 150, "percentage": 60.0}]
    "top5_metros": [...],
    "top3_naics_2digit": [...],
    "top5_naics_4digit": [...],
    "top10_roles": [...]          // [{"role": "Engineer", "count": 80, "percentage": 32.0}]
  },
  "node_composition": {
    "type": "established",        // new_born / established / transitional
    "core_node_ratio": 0.75,
    "new_node_ratio": 0.15,
    "avg_node_weight": 0.75,
    "core_nodes": 188,
    "new_nodes": 38
  }
}
```

---

## 🔧 技术要求

### 浏览器
- **推荐**: Chrome 90+, Firefox 88+, Edge 90+
- **JavaScript**: 必须启用
- **屏幕分辨率**: 1920x1080 或更高

### Python 环境（数据处理）
```bash
# 主要依赖
pip install pandas numpy duckdb pyarrow igraph leidenalg
```

**版本要求**:
- Python 3.8+
- pandas >= 1.3.0
- duckdb >= 0.8.0
- igraph >= 0.10.0
- leidenalg >= 0.9.0

### 文件大小建议
- **社区CSV**: < 50MB
- **边数据CSV**: < 100MB
- **演化链JSON**: < 20MB

### 性能建议
- **社区数量**: 显示 < 200 个社区效果最佳
- **演化链数量**: 显示 < 100 条链效果最佳
- **层级深度**: 6层以内效果最佳

---

## 🐛 常见问题

### Q1: 上传文件后没有反应？
**A**:
1. 打开浏览器控制台 (F12) 检查错误
2. 确认文件格式正确 (CSV/JSON)
3. 检查文件是否包含必需的列
4. 确保文件大小不超过限制

### Q2: 演化链显示空白？
**A**:
1. 检查 JSON 文件格式是否正确
2. 确认 `communities` 数组不为空
3. 确认每个社区都有 `year` 和 `community_id`
4. 查看浏览器控制台的错误信息

### Q3: 节点重叠无法点击？
**A**:
1. 使用 "Fit to View" 按钮
2. 切换到径向布局
3. 减少显示的节点数量（调整最小社区大小）
4. 使用缩放控制

### Q4: 如何找到特定社区的演化？
**A**:
1. 在社区检测页面记住社区ID（例如：community_level1 = "1.2.5"）
2. 进入演化链页面
3. 使用侧边栏浏览链
4. 点击节点查看该年份的社区ID
5. 匹配找到对应的演化链

### Q5: 演化链数据生成失败？
**A**:
1. 确认已运行完整的数据处理流程（graph.py → community_detection.py → similarity.py）
2. 检查 `community_results_dir` 路径是否正确
3. 确认相似度矩阵文件存在
4. 查看 Python 脚本的日志输出

---

## 📈 项目改进记录

### v2.0 (当前版本) - 2024年

**核心改进**:
1. ✅ **删除冗余代码**
   - 移除 `evolution-chain-progressive.html`
   - 移除 `evolution-network-explorer.html`
   - 移除 `adapted-*.js` 和 `progressive-*.js` 系列

2. ✅ **增强演化链构建**
   - 重构 `community_matchting.py` 为 `EnhancedEvolutionChainBuilder`
   - 添加完整社区属性提取
   - 添加节点组成分析
   - 添加社区类型分类

3. ✅ **修复可视化问题**
   - 确保数据格式符合前端预期
   - 添加所有必需的属性字段
   - 优化JSON输出结构

4. ✅ **改进文档**
   - 完整的数据处理流程说明
   - 详细的文件格式规范
   - 典型工作流程示例

### v1.0 - 初始版本

- 基础社区检测可视化
- 简单演化链可视化
- 多个测试HTML页面

---

## 📚 相关文档

- **社区检测算法**: 参见 `community_detection.py` 中的详细注释
- **Leiden算法**: https://www.nature.com/articles/s41598-019-41695-z
- **D3.js文档**: https://d3js.org
- **DuckDB文档**: https://duckdb.org

---

## 🎉 快速开始

```bash
# 1. 克隆或下载项目
cd integrated-viz

# 2. 准备数据（如果还未处理）
python graph.py                    # 构建图数据
python community_detection.py      # 社区检测
python similarity.py               # 计算相似度
python community_matchting.py      # 构建演化链

# 3. 打开可视化
# 双击 index.html 或用浏览器打开

# 4. 上传数据
# - 社区检测页面: 上传 workforce_geo_community_*_results.csv
# - 演化链页面: 上传 weighted_chain_details_level1.json

# 5. 开始探索！
```

---

## 💬 反馈和支持

如有问题或建议，请联系项目维护者。

**祝你分析愉快！** 🚀
