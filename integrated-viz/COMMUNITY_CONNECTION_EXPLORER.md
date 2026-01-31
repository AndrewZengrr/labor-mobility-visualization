# 社区连接关系探索器

## 概述

社区连接关系探索器是一个**渐进式展开**的交互式可视化工具,用于观察相邻年份间社区的连接关系。这是社区演化链构建的**中间结果可视化**,帮助您:

- 观察有相似度的社区之间的连接关系
- 了解社区属性(规模、度数等)
- 查看连接边的属性(重叠节点数、Jaccard相似度等)
- 逐年逐步展开,避免一次性展示所有数据导致的混乱

## 核心特性

### 🎯 渐进式展开
- **初始状态**: 只显示起始年份(如2000年)的所有社区
- **点击展开**: 点击某个社区,展开下一年与它有连接的社区
- **逐年探索**: 每次点击只展开下一年,不是一次性展开所有年份
- **收起功能**: 再次点击已展开的社区可以收起其后继

### 📊 信息展示
- **社区节点**: 显示社区ID、年份、度数等信息
- **连接边**: 显示Jaccard相似度、重叠节点数、保留率等指标
- **详情面板**: 右侧面板显示点击节点或边的详细信息
- **统计信息**: 实时显示当前可见的节点数、边数、年份范围

### 🎨 可视化效果
- **节点颜色**:
  - 蓝色 = 已展开社区
  - 灰色 = 未展开社区
  - 红色 = 叶子社区(无后继)
- **边粗细**: 根据Jaccard相似度调整
- **交互提示**: 鼠标悬停显示简要信息
- **缩放拖拽**: 支持画布缩放和节点拖拽

## 使用方法

### 1. 准备数据

#### 选项A: 使用真实数据

如果您已经有相似度矩阵数据:

```bash
cd integrated-viz

# 从相似度矩阵生成可视化数据
python prepare_connection_data.py
```

这会生成 `community_connections.json` 文件。

**配置参数** (在 `prepare_connection_data.py` 中):
```python
similarity_file = "./similarity_matrices_complete/similarity_matrix_level1_complete.parquet"
output_file = "./community_connections.json"
jaccard_threshold = 0.0  # 只保留大于此阈值的连接
```

#### 选项B: 使用示例数据

快速测试可视化工具:

```bash
cd integrated-viz

# 生成示例数据
python generate_sample_data.py
```

这会生成 `sample_community_connections.json` 文件(5年,50个社区,49个连接)。

**自定义示例数据** (在 `generate_sample_data.py` 中):
```python
generator = SampleDataGenerator(
    start_year=2000,        # 起始年份
    num_years=5,            # 年份数量
    communities_per_year=10,# 每年社区数
    connection_prob=0.4     # 连接概率
)
```

### 2. 打开可视化

在浏览器中打开 `community-connection-explorer.html`

### 3. 加载数据

1. 点击左侧 "加载数据" 按钮
2. 选择生成的JSON文件:
   - 真实数据: `community_connections.json`
   - 示例数据: `sample_community_connections.json`

### 4. 开始探索

1. **初始视图**: 看到起始年份的所有社区
2. **点击展开**: 点击感兴趣的社区,展开下一年的连接
3. **查看详情**: 点击节点或边,右侧面板显示详细信息
4. **继续探索**: 逐年点击,观察演化路径
5. **收起节点**: 再次点击已展开的社区可以收起
6. **重置视图**: 点击 "重置视图" 回到初始状态
7. **收起所有**: 点击 "收起所有" 快速重置

### 5. 交互技巧

- **缩放**: 鼠标滚轮缩放画布
- **平移**: 拖拽空白区域平移画布
- **移动节点**: 拖拽节点调整位置
- **悬停提示**: 鼠标悬停在节点或边上查看简要信息
- **详情查看**: 点击节点或边在右侧面板查看完整信息

## 数据格式

### 输入数据格式 (JSON)

```json
{
  "nodes": [
    {
      "id": "2000_0",           // 节点唯一ID
      "year": 2000,             // 年份
      "community": "0",         // 社区编号
      "out_degree": 5,          // 出度
      "in_degree": 0,           // 入度
      "total_degree": 5,        // 总度数
      "size": 10                // 节点大小(用于可视化)
    }
  ],
  "links": [
    {
      "source": "2000_0",       // 源节点ID
      "target": "2001_3",       // 目标节点ID
      "jaccard": 0.234,         // Jaccard相似度
      "retention_forward": 0.45,// 前向保留率
      "retention_backward": 0.38,// 后向保留率
      "overlap_size": 67,       // 重叠节点数
      "size1": 150,             // 源社区大小
      "size2": 175,             // 目标社区大小
      "growth_rate": 0.167,     // 增长率
      "year_gap": 1             // 年份间隔
    }
  ]
}
```

## 工作流程

### 完整的社区分析流程

```
1. 社区检测
   ↓
2. 构建相似度矩阵 (similarity.py)
   ↓
3. 准备可视化数据 (prepare_connection_data.py)
   ↓
4. 交互式探索 (community-connection-explorer.html)
   ↓
5. 观察连接模式,优化演化链构建方法
   ↓
6. 构建最终的演化链 (community_matchting.py)
```

## 常见问题

### Q1: 数据太多,显示很慢怎么办?

**方案1**: 提高Jaccard阈值,只保留强连接
```python
# 在 prepare_connection_data.py 中
jaccard_threshold = 0.1  # 只保留jaccard > 0.1的连接
```

**方案2**: 只分析部分年份
```python
# 在加载数据后筛选特定年份范围
df_filtered = df[(df['year1'] >= 2000) & (df['year1'] <= 2010)]
```

### Q2: 某些年份社区数量特别多?

这是正常现象。您可以:
- 通过点击特定社区逐步展开,而不是展开所有社区
- 调整社区检测参数减少社区数量
- 在可视化中只关注重要社区(高度数节点)

### Q3: 如何识别重要的演化路径?

观察以下特征:
- **高Jaccard相似度**: 边更粗,表示强连接
- **高度数节点**: 节点更大,表示与多个社区有连接
- **连续多年的路径**: 逐年点击,观察是否有稳定的演化链

### Q4: 可以同时展开多个社区吗?

可以!点击不同的社区,可以同时展开多条演化路径,观察它们的交叉和分叉。

## 技术栈

- **D3.js v7**: 数据驱动的可视化
- **Force Simulation**: 力导向图布局
- **纯HTML/CSS/JS**: 无需服务器,浏览器直接打开

## 文件说明

```
integrated-viz/
├── community-connection-explorer.html  # 主可视化工具
├── prepare_connection_data.py         # 真实数据转换脚本
├── generate_sample_data.py           # 示例数据生成脚本
├── COMMUNITY_CONNECTION_EXPLORER.md  # 本文档
├── community_connections.json        # 真实数据(生成后)
└── sample_community_connections.json # 示例数据(生成后)
```

## 下一步

使用此工具观察社区连接模式后,您可以:

1. **优化相似度指标**: 根据观察结果调整Jaccard、保留率等指标的权重
2. **设计筛选规则**: 确定哪些连接应该被保留用于构建最终的演化链
3. **识别演化模式**: 发现社区的分裂、合并、消亡等演化模式
4. **构建演化链**: 使用 `community_matchting.py` 构建最终的演化链

## 反馈

如果您有任何问题或建议,请在项目中提出issue。

---

**祝您探索愉快!** 🚀
