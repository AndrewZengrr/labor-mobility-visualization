# 社区属性加载功能说明

## 📚 新增文件

我已经为你创建了以下文件：

### 1. `prepare_community_connections_with_attributes.py`
**主要脚本** - 从社区检测结果中提取详细属性并生成可视化数据

**核心功能**:
- ✅ 从相似度矩阵加载社区连接关系
- ✅ 从社区检测结果CSV提取详细属性
- ✅ 计算属性分布（州、都市区、NAICS产业、RICS分类等）
- ✅ 将属性整合到节点数据中
- ✅ 生成包含完整属性的JSON文件

### 2. `ATTRIBUTE_LOADING_GUIDE.md`
**详细使用指南** - 完整的使用说明和配置文档

包含:
- 📋 数据文件格式要求
- 🚀 使用方法和示例
- 📤 输出格式说明
- 🔍 数据验证方法
- 🐛 常见问题解答
- ⚙️ 高级配置选项

### 3. `example_prepare_with_attributes.py`
**示例脚本** - 交互式示例，快速上手

提供5个示例:
1. 基础用法
2. 自定义过滤阈值
3. 检查提取的属性
4. 为多个层级准备数据
5. 输入文件验证

## 🎯 与原代码的主要改进

### 原始代码
```python
# 节点只有基本信息
{
    'id': '2020_1',
    'year': 2020,
    'community': '1',
    'size': 150,
    'dominant_naics': 'unknown',
    'dominant_state': 'unknown'
}
```

### 改进后的代码
```python
# 节点包含完整的详细属性
{
    'id': '2020_1',
    'year': 2020,
    'community': '1',
    'size': 150,
    'attributes': {
        'total_workforce': 12500,
        'top3_states': [
            {'value': 'California', 'count': 100, 'percentage': 66.67},
            {'value': 'Texas', 'count': 30, 'percentage': 20.00},
            ...
        ],
        'top5_metros': [...],
        'top3_naics_2digit': [...],
        'top5_naics_4digit': [...],
        'top3_rics_k50': [...],
        'top3_rics_k200': [...],
        'top10_companies': [...]
    }
}
```

## 🚀 快速开始

### 第1步: 准备数据文件

#### 相似度矩阵 (必需)
文件位置: `./similarity_matrices_complete/similarity_matrix_level1_complete.parquet`

这个文件应该已经由你的社区演化构建代码生成。

#### 社区检测结果CSV (必需)
创建目录并放入各年份的社区检测结果:
```bash
mkdir -p community_detection_results
```

文件命名示例:
- `workforce_geo_community_2020_results.csv`
- `workforce_geo_community_2021_results.csv`
- `workforce_geo_community_2022_results.csv`
- ...

**CSV必需列**:
- `geo_rcid` - 节点ID
- `community_level1` - 社区层级

**CSV推荐列** (用于属性提取):
- `real_state` - 州
- `real_metro_area` - 都市区
- `naics_code` - NAICS代码
- `company_name` - 公司名称
- `workforce_total_people` - 劳动力人数
- `rics_k50`, `rics_k200` - RICS分类

### 第2步: 运行示例脚本

```bash
python example_prepare_with_attributes.py
```

按照提示选择示例，建议先选择示例3来检查属性提取是否正确。

### 第3步: 在代码中使用

```python
from prepare_community_connections_with_attributes import ConnectionDataPreparerWithAttributes

# 配置路径
preparer = ConnectionDataPreparerWithAttributes(
    similarity_file="./similarity_matrices_complete/similarity_matrix_level1_complete.parquet",
    community_data_dir="./community_detection_results",
    output_file="./community_connections_with_attributes.json"
)

# 运行
data = preparer.run()
```

### 第4步: 在可视化中查看

1. 打开 `explorers/community-connection-explorer.html`
2. 点击 "Load Data"
3. 选择生成的 `community_connections_with_attributes.json`
4. 点击节点查看详细属性！

## 📊 输出数据结构

生成的JSON文件包含三个主要部分:

### 1. nodes - 节点数组
每个节点包含:
- 基本信息: `id`, `year`, `community`, `size`
- 连接度: `in_degree`, `out_degree`, `total_degree`
- **详细属性**: `attributes` 对象
  - `total_workforce` - 总劳动力
  - `top3_states` - 前3个州分布
  - `top5_metros` - 前5个都市区
  - `top3_naics_2digit` - 前3个NAICS 2位代码
  - `top5_naics_4digit` - 前5个NAICS 4位代码
  - `top10_companies` - 前10个公司

### 2. links - 边数组
每个边包含:
- 连接信息: `source`, `target`
- 相似度指标: `jaccard`, `retention_forward`, `retention_backward`
- 重叠信息: `overlap_size`, `union_size`
- 属性相似度: `naics_cosine_similarity`, `state_cosine_similarity` 等

### 3. stats - 统计信息
包含:
- 总体统计: `total_nodes`, `total_links`, `attributes_loaded`
- 年份范围: `year_range`
- 各种分布统计

## 🔧 自定义配置

### 调整过滤阈值

```python
preparer.min_overlap_size = 10  # 最小重叠节点数
preparer.min_retention_forward = 0.10  # 最小前向保留率
preparer.min_retention_backward = 0.10  # 最小后向保留率
preparer.min_jaccard = 0.05  # 最小Jaccard相似度
```

### 修改属性提取

如果你的CSV使用不同的列名，编辑 `extract_community_attributes` 方法:

```python
def extract_community_attributes(self, df, community_id, level='level1'):
    # 修改列名
    if 'your_state_column' in community_df.columns:
        state_counts = community_df['your_state_column'].value_counts()
        attributes['states'] = self._format_distribution(state_counts)
```

### 添加新的属性字段

1. 在 `extract_community_attributes` 中提取新属性
2. 在 `_create_nodes_with_attributes` 中添加到输出

## 📝 使用流程图

```
相似度矩阵 (parquet)  ─┐
                      ├─→ ConnectionDataPreparerWithAttributes ─→ JSON输出
社区检测结果 (CSV)   ─┘

JSON输出 ─→ community-connection-explorer.html ─→ 可视化展示详细属性
```

## 🎓 典型工作流

### 工作流 A: 从头开始
```bash
# 1. 运行社区检测 → 生成CSV文件
# 2. 计算社区相似度 → 生成parquet文件
# 3. 提取属性并准备可视化
python example_prepare_with_attributes.py

# 4. 在浏览器中查看
# 打开 explorers/community-connection-explorer.html
```

### 工作流 B: 集成到现有流程
```python
# 在你的社区演化构建代码最后添加

from prepare_community_connections_with_attributes import ConnectionDataPreparerWithAttributes

# 社区演化构建完成后
preparer = ConnectionDataPreparerWithAttributes(
    similarity_file=similarity_output_file,
    community_data_dir=community_csv_dir,
    output_file=viz_output_file
)

viz_data = preparer.run()
print(f"✓ 可视化数据已生成: {viz_output_file}")
```

## 🐛 故障排查

### 问题1: 找不到社区数据文件
**解决方案**:
```python
# 运行验证脚本
python example_prepare_with_attributes.py
# 选择选项 0 先验证文件
```

### 问题2: 属性为空
**检查**:
1. CSV是否包含必需的列
2. 列名是否正确（区分大小写）
3. 社区ID是否匹配

### 问题3: 内存不足
**解决方案**:
1. 增加过滤阈值
2. 分批处理年份
3. 只加载必需的列

## 📚 相关文档

- **详细指南**: `ATTRIBUTE_LOADING_GUIDE.md`
- **主项目README**: `README.md`
- **社区连接探索器**: `explorers/COMMUNITY_CONNECTION_EXPLORER.md`

## 💡 提示

1. **数据质量**: 属性提取的质量取决于原始CSV数据的完整性
2. **性能优化**: 对于大规模数据，考虑提高过滤阈值
3. **可视化**: 生成的JSON可以直接用于所有现有的可视化工具
4. **调试**: 使用示例3来验证属性提取是否正确

## 🎉 开始使用

```bash
# 1. 验证文件
python example_prepare_with_attributes.py  # 选择 0

# 2. 运行基础示例
python example_prepare_with_attributes.py  # 选择 1

# 3. 在可视化中查看结果
# 打开 explorers/community-connection-explorer.html
# 加载生成的JSON文件
```

---

**祝你使用愉快！** 🚀

如有问题，请查看 `ATTRIBUTE_LOADING_GUIDE.md` 获取更多详细信息。
