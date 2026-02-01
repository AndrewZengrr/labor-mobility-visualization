# 社区属性加载指南

## 📋 概述

这个脚本用于从社区检测结果中提取详细属性，并将其整合到社区演化可视化数据中。

## 🎯 主要功能

1. **从社区检测结果CSV读取属性**
   - 州分布（States）
   - 都市区分布（Metro Areas）
   - NAICS产业分布（2位和4位代码）
   - RICS分类（K50/K200/K400）
   - 公司组成
   - 劳动力统计

2. **计算属性分布**
   - Top 3 州
   - Top 5 都市区
   - Top 3/5 NAICS代码
   - Top 10 公司

3. **保存到演化数据JSON**
   - 每个节点包含完整属性信息
   - 便于可视化时展示详细信息

## 📂 数据文件准备

### 1. 相似度矩阵文件
**文件格式**: `.parquet`
**位置示例**: `./similarity_matrices_complete/similarity_matrix_level1_complete.parquet`

**必需列**:
- `year1`, `year2` - 两个年份
- `community1`, `community2` - 社区ID
- `jaccard` - Jaccard相似度
- `retention_forward`, `retention_backward` - 保留率
- `overlap_size`, `union_size` - 重叠和并集大小
- `size1`, `size2` - 社区大小
- `growth_rate` - 增长率
- `year_gap` - 年份间隔

**可选列**（属性相似度）:
- `naics_cosine_similarity`, `naics_overlap_index`
- `state_cosine_similarity`, `state_overlap_index`
- `metro_cosine_similarity`, `metro_overlap_index`

### 2. 社区检测结果CSV文件
**文件命名格式** (脚本会自动查找以下模式):
- `workforce_geo_community_YYYY_results.csv` (推荐)
- `community_YYYY_results.csv`
- `community_detection_YYYY.csv`
- `YYYY_community_results.csv`

**位置**: 所有CSV文件放在同一目录下，如 `./community_detection_results/`

**必需列**:
- `geo_rcid` - 节点ID
- `community_level1` - 社区层级1（主要层级）
- 可选: `community_level2`, `community_level3`, ... (更细粒度层级)

**推荐列** (用于属性提取):
- `real_state` - 州名称
- `real_metro_area` - 都市区名称
- `naics_code` - NAICS产业代码
- `rics_k50`, `rics_k200`, `rics_k400` - RICS分类
- `company_name` - 公司名称
- `workforce_total_people` - 劳动力人数
- `rcid` - 公司ID

**示例CSV结构**:
```csv
geo_rcid,community_level1,rcid,company_name,real_state,real_metro_area,naics_code,workforce_total_people
RC123_CA_SF,1,RC123,Tech Corp,California,San Francisco,5112,500
RC456_NY_NYC,1,RC456,Finance Inc,New York,New York City,5221,800
RC789_CA_SF,2,RC789,Data Ltd,California,San Francisco,5415,300
```

## 🚀 使用方法

### 基础用法

```python
from prepare_community_connections_with_attributes import ConnectionDataPreparerWithAttributes

# 配置文件路径
similarity_file = "./similarity_matrices_complete/similarity_matrix_level1_complete.parquet"
community_data_dir = "./community_detection_results"  # 包含各年份CSV的目录
output_file = "./community_connections_with_attributes.json"

# 创建准备器
preparer = ConnectionDataPreparerWithAttributes(
    similarity_file=similarity_file,
    community_data_dir=community_data_dir,
    output_file=output_file
)

# 运行
data = preparer.run()
```

### 调整过滤阈值

```python
# 创建准备器后，可以调整阈值
preparer.min_overlap_size = 5  # 最小重叠节点数
preparer.min_retention_forward = 0.05  # 最小前向保留率
preparer.min_retention_backward = 0.05  # 最小后向保留率
preparer.min_jaccard = 0.02  # 最小Jaccard相似度

# 运行
data = preparer.run()
```

## 📤 输出格式

### JSON结构

```json
{
  "nodes": [
    {
      "id": "2020_1",
      "year": 2020,
      "community": "1",
      "size": 150,
      "out_degree": 3,
      "in_degree": 2,
      "total_degree": 5,
      "attributes": {
        "total_workforce": 12500,
        "top3_states": [
          {"value": "California", "count": 100, "percentage": 66.67},
          {"value": "Texas", "count": 30, "percentage": 20.00},
          {"value": "New York", "count": 20, "percentage": 13.33}
        ],
        "top5_metros": [
          {"value": "San Francisco", "count": 80, "percentage": 53.33},
          {"value": "Austin", "count": 25, "percentage": 16.67},
          ...
        ],
        "top3_naics_2digit": [
          {"value": "51", "count": 90, "percentage": 60.00},
          {"value": "54", "count": 40, "percentage": 26.67},
          ...
        ],
        "top5_naics_4digit": [
          {"value": "5112", "count": 50, "percentage": 33.33},
          ...
        ],
        "top3_rics_k50": [...],
        "top3_rics_k200": [...],
        "top10_companies": [
          {"value": "Tech Corp", "count": 15, "percentage": 10.00},
          ...
        ]
      }
    }
  ],
  "links": [
    {
      "source": "2020_1",
      "target": "2021_2",
      "jaccard": 0.45,
      "retention_forward": 0.62,
      "retention_backward": 0.38,
      "overlap_size": 85,
      ...
    }
  ],
  "stats": {
    "total_nodes": 250,
    "total_links": 450,
    "attributes_loaded": 250,
    "year_range": {"min": 2020, "max": 2025},
    ...
  }
}
```

## 🔍 数据验证

运行后，脚本会输出：

1. **加载统计**
   ```
   Loading community data for year 2020 from ./community_detection_results/workforce_geo_community_2020_results.csv
     Loaded 15,234 records
   Processing 45 communities for year 2020
   ```

2. **属性摘要**
   ```
   Sample node attributes (2020_1):
     Workforce: 12,500
     Top states: 3 loaded
     Top metros: 5 loaded
     Top NAICS (2-digit): 3 loaded
     Top NAICS (4-digit): 5 loaded
   ```

3. **输出文件信息**
   ```
   ✓ Data saved successfully!
     Nodes: 250
     Links: 450
     Attributes: 250 communities
     File size: 1,234.56 KB
   ```

## 📊 在可视化中使用

生成的JSON文件可以直接用于以下可视化工具：

### 1. 社区连接探索器
```html
<!-- 打开 explorers/community-connection-explorer.html -->
<!-- 点击 "Load Data" -->
<!-- 选择生成的 community_connections_with_attributes.json -->
```

### 2. 演化链可视化
```javascript
// 在 evolution-chain.html 中加载
// 节点属性会自动显示在详情面板中
```

### 3. 网络探索器
```html
<!-- 打开 explorers/evolution-network-explorer.html -->
<!-- 加载生成的JSON文件 -->
```

## ⚙️ 高级配置

### 自定义属性提取

如果你的CSV文件使用不同的列名，可以修改代码：

```python
def extract_community_attributes(self, df, community_id, level='level1'):
    # 修改列名映射
    state_column = 'your_state_column_name'  # 替换 'real_state'
    metro_column = 'your_metro_column_name'  # 替换 'real_metro_area'

    if state_column in community_df.columns:
        state_counts = community_df[state_column].value_counts()
        attributes['states'] = self._format_distribution(state_counts)
```

### 添加自定义属性

```python
# 在 extract_community_attributes 方法中添加
attributes['custom_field'] = {}

if 'your_custom_column' in community_df.columns:
    custom_counts = community_df['your_custom_column'].value_counts()
    attributes['custom_field'] = self._format_distribution(custom_counts)

# 在 _create_nodes_with_attributes 方法中添加到输出
'attributes': {
    'total_workforce': attributes['total_workforce'],
    'top3_states': attributes['states'][:3],
    ...
    'top_custom_field': attributes['custom_field'][:5]  # 新增
}
```

## 🐛 常见问题

### Q: 找不到社区数据文件
**A**: 检查以下几点：
1. 文件是否在指定的目录中
2. 文件命名是否符合模式（包含年份）
3. 尝试在 `main()` 函数中打印目录内容验证

```python
import os
print(os.listdir(community_data_dir))
```

### Q: 某些年份没有属性
**A**:
1. 确保该年份的CSV文件存在
2. 检查CSV文件中是否包含对应的社区ID
3. 查看日志输出中的警告信息

### Q: 属性分布为空
**A**:
1. 检查CSV文件是否包含必需的列（real_state, naics_code等）
2. 验证列名是否正确（大小写敏感）
3. 检查数据是否有缺失值

### Q: 内存不足
**A**:
1. 分批处理年份
2. 只加载必需的列
3. 增加过滤阈值以减少节点数量

## 📈 性能优化建议

1. **预处理数据**
   - 清理CSV文件，删除不必要的列
   - 确保数据类型正确（避免运行时转换）

2. **使用合适的阈值**
   - 过于宽松的阈值会导致大量节点和边
   - 建议先用严格阈值测试，再逐步放宽

3. **文件大小**
   - 如果输出JSON过大（>50MB），考虑：
     - 减少Top N的数量
     - 移除不必要的属性
     - 压缩JSON文件（使用gzip）

## 📝 完整示例

```python
"""
完整的数据准备流程示例
"""
from prepare_community_connections_with_attributes import ConnectionDataPreparerWithAttributes
import logging

# 设置日志级别
logging.basicConfig(level=logging.INFO)

# 1. 配置路径
similarity_file = "./data/similarity_matrix_level1_complete.parquet"
community_data_dir = "./data/community_results"
output_file = "./output/connections_with_attrs.json"

# 2. 创建准备器
preparer = ConnectionDataPreparerWithAttributes(
    similarity_file=similarity_file,
    community_data_dir=community_data_dir,
    output_file=output_file
)

# 3. 自定义阈值（可选）
preparer.min_overlap_size = 5
preparer.min_jaccard = 0.02

# 4. 运行
try:
    data = preparer.run()

    if data:
        print(f"\n✓ Success! Generated {len(data['nodes'])} nodes")
        print(f"  Output: {output_file}")

except FileNotFoundError as e:
    print(f"❌ File not found: {e}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
```

## 🎓 下一步

1. 将生成的JSON文件用于可视化
2. 根据可视化效果调整过滤阈值
3. 添加更多自定义属性字段
4. 集成到自动化工作流中

---

**如有问题，请查看日志输出或联系开发团队** 🚀
