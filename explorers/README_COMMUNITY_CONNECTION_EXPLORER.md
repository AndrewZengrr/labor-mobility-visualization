# Community Connection Explorer 使用指南

## 概述

Community Connection Explorer 是一个交互式可视化工具，用于探索和分析多层级社区演化网络。支持展示社区在时间维度和层级维度上的连接关系，以及重叠节点的属性分布。

## 数据准备流程

### 第一步：生成演化链和图数据

运行 `prepare_community_connections_with_attributes.py` 脚本来生成可视化所需的数据：

```bash
cd /home/user/labor-mobility-visualization
python prepare_community_connections_with_attributes.py
```

**重要说明：**
- 在运行脚本前，请根据您的数据路径修改 `main()` 函数中的参数：
  - `level`: 要处理的社区层级（1, 2, 或 3）
  - `similarity_file`: 相似度矩阵文件路径
  - `community_results_dir`: 社区检测结果目录
  - `output_base_dir`: 输出目录（默认: `./evolution_chains`）

### 第二步：输出文件说明

脚本会在 `evolution_chains/level{N}/` 目录下生成以下文件：

1. **evolution_chains_with_overlap_attributes.json**
   - 完整的演化链数据，包含所有重叠节点的详细属性分布
   - 用于深度分析和研究

2. **evolution_chains_simple.json**
   - 简化版演化链数据，便于快速浏览
   - 只包含主要属性（Top 3 NAICS、Top 3 States）

3. **community_connections_with_attributes.json** ⭐ **可视化所需文件**
   - 图可视化格式：`{nodes: [...], links: [...]}`
   - 这是 Community Connection Explorer 需要加载的文件
   - 包含社区节点属性和边的重叠属性

4. **chain_analysis_summary.json**
   - 统计摘要信息

### 第三步：处理多个层级

如果需要同时可视化多个层级（Level 1, 2, 3），需要分别运行脚本：

```python
# 在 prepare_community_connections_with_attributes.py 的 main() 函数中修改 level 参数

# Level 1
level = 1
analyzer = EvolutionChainAnalyzerWithOverlapAttributes(...)
analyzer.run()

# Level 2
level = 2
analyzer = EvolutionChainAnalyzerWithOverlapAttributes(...)
analyzer.run()

# Level 3
level = 3
analyzer = EvolutionChainAnalyzerWithOverlapAttributes(...)
analyzer.run()
```

## 使用可视化工具

### 打开可视化界面

在浏览器中打开：
```
file:///home/user/labor-mobility-visualization/explorers/community-connection-explorer.html
```

### 加载数据

1. 在界面左上角找到"数据加载"部分
2. 对于每个层级，点击相应的"选择文件"按钮：
   - **Level 1**: 加载 `evolution_chains/level1/community_connections_with_attributes.json`
   - **Level 2**: 加载 `evolution_chains/level2/community_connections_with_attributes.json`
   - **Level 3**: 加载 `evolution_chains/level3/community_connections_with_attributes.json`

### 交互操作

#### 社区节点交互：

- **左键点击**: 展开/收起该社区的下一年时间连接
- **右键点击**: 打开上下文菜单
  - "查看社区属性": 显示社区的详细属性（人数、行业分布、地理分布等）
  - "展开时间连接": 展开下一年的社区连接
  - "展开层级关系": 展开下一层级的子社区（基于社区编号的"."层级结构）
  - "收起社区": 收起该社区的所有展开连接
- **鼠标悬停**: 显示社区基本信息（年份、社区ID、人数）

#### 连接边交互：

- **左键点击**: 显示重叠节点的属性分布
  - NAICS 2位码分布
  - NAICS 4位码分布
  - 州（State）分布
  - 都市区（Metro Area）分布
  - 每项包含：值、计数、百分比、覆盖率、熵值
- **鼠标悬停**: 显示连接的相似度指标（Jaccard、重叠大小、保留率）

#### 视图控制：

- **起始层级**: 选择初始显示的层级（Level 1/2/3）
- **起始年份**: 选择初始显示的年份
- **年份范围筛选**: 设置可见的年份范围
- **搜索社区**: 通过社区ID快速定位和高亮显示特定社区

## 数据格式说明

### 节点数据格式
```json
{
  "id": "2000_1",
  "year": 2000,
  "community": "1",
  "attributes": {
    "total_workforce": 1500,
    "top3_states": [
      {"value": "CA", "count": 500, "percentage": 33.33}
    ],
    "top5_metros": [...],
    "top3_naics_2digit": [...],
    "top3_naics_4digit": [...],
    "avg_wage": 65000.0,
    "total_companies": 250
  }
}
```

### 边数据格式
```json
{
  "source": "2000_1",
  "target": "2001_2",
  "jaccard": 0.45,
  "retention_forward": 0.60,
  "retention_backward": 0.55,
  "overlap_size": 800,
  "overlap_attributes": {
    "naics_2digit": {
      "distribution": [
        {"value": "54", "count": 200, "percentage": 25.0}
      ],
      "coverage": 0.95,
      "entropy": 2.5,
      "unique_values": 12
    },
    "state": {...},
    "metro_area": {...}
  }
}
```

## 层级关系说明

社区的层级关系通过社区编号的"."分隔符确定：

- `"1"` 是 Level 1 社区
- `"1.1"`, `"1.2"` 是 `"1"` 的 Level 2 子社区
- `"1.1.1"`, `"1.1.2"` 是 `"1.1"` 的 Level 3 子社区

当展开层级关系时，只会显示直接的父子关系，而不是所有子社区。

## 故障排除

### 错误: "数据格式错误: Cannot read properties of undefined (reading 'length')"

**原因**: 加载的是演化链格式的JSON文件，而不是图可视化格式的文件。

**解决方案**:
1. 确保加载的是 `community_connections_with_attributes.json` 文件
2. 如果该文件不存在，重新运行 `prepare_community_connections_with_attributes.py` 生成数据
3. 不要加载 `evolution_chains_with_overlap_attributes.json` 文件（这是用于链分析的，不是可视化的）

### 第三层无法显示

**解决方案**:
1. 确保已加载 Level 3 的数据文件
2. 确保 Level 2 的社区有对应的 Level 3 子社区（通过"."分隔符判断）
3. 尝试右键点击 Level 2 社区 -> "展开层级关系"

### 边属性无法显示

**解决方案**:
1. 确保数据文件包含 `overlap_attributes` 字段
2. 左键点击连接边（不是节点）
3. 检查浮动窗口是否出现在屏幕右侧

## 备用工具：独立数据转换器

如果需要单独转换已有的演化链数据，可以使用独立转换脚本：

```bash
python convert_chains_to_graph.py
```

该脚本会读取 `evolution_chains/level{N}/evolution_chains_with_overlap_attributes.json` 并生成 `graph_data/level{N}/community_connections_with_attributes.json`。

## 技术支持

如有问题或需要更多功能，请参考以下文件：
- 数据生成脚本: `prepare_community_connections_with_attributes.py`
- 可视化代码: `explorers/community-connection-explorer.html`
- 数据转换脚本: `convert_chains_to_graph.py`
