# Integrated Workforce Community Visualization Platform

## 🎯 概述

这是一个集成的劳动力社区可视化平台，包含两个核心模块：

1. **社区检测可视化** (主页面) - 展示单一年份的层级社区结构
2. **演化链可视化** (Evolution Chains) - 展示社区跨时间演化轨迹

---

## 📁 文件结构

```
labor-mobility-visualization/
├── index.html                        # 主页面 - 社区检测可视化
├── evolution-chain.html              # 演化链可视化页面
├── README.md                         # 本文档
├── css/
│   ├── styles.css                   # 主平台样式
│   ├── network-viewer.css           # 网络视图样式
│   └── evolution-styles.css         # 演化链样式
├── js/
│   ├── config.js                    # 社区可视化配置
│   ├── data-handler.js              # 数据处理
│   ├── graph-data-loader.js         # 图数据加载
│   ├── visualizer.js                # 社区可视化核心
│   ├── composition.js               # 组成分析
│   ├── network-viewer.js            # 网络视图
│   ├── app.js                       # 主应用
│   ├── evolution-config.js          # 演化链配置
│   ├── evolution-data-loader.js     # 演化链数据加载
│   ├── evolution-visualizer.js      # 演化链可视化核心
│   ├── evolution-detail-panel.js    # 演化链详情面板
│   ├── evolution-app.js             # 演化链应用
│   ├── progressive-*.js             # 渐进式探索工具
│   └── adapted-*.js                 # 网络探索工具
└── explorers/                        # 辅助探索工具
    ├── community-connection-explorer.html    # 社区连接关系探索器
    ├── evolution-chain-progressive.html      # 渐进式演化链可视化
    ├── evolution-network-explorer.html       # 演化网络探索器
    ├── COMMUNITY_CONNECTION_EXPLORER.md      # 连接探索器文档
    └── sample_community_connections.json     # 示例数据
```

---

## 🚀 使用流程

### 模块 1: 社区检测可视化

#### Step 1: 打开主页面
- 用浏览器打开 `index.html`
- 看到上传界面

#### Step 2: 上传数据
1. **必需文件**: 社区检测结果CSV
   - 文件示例: `workforce_geo_community_2019_2020_results.csv`
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

#### Step 4: 进入演化链模块
- 点击右上角 **"Evolution Chains"** 按钮 🔗
- 自动跳转到演化链页面

---

### 模块 2: 演化链可视化

#### Step 1: 上传演化链数据
- 在演化链页面点击 **"Choose JSON File"**
- 选择你的 `weighted_chain_details_level1.json` 文件
- 等待数据加载

#### Step 2: 探索演化
- **查看链**: 时间轴上显示所有演化链
- **过滤链**: 按长度、得分、年份过滤
- **切换布局**: Timeline / Vertical Lanes / Force-Directed
- **点击节点**: 查看该年份社区的详细属性

#### Step 3: 分析社区属性
点击任何节点查看：
- 📊 基本信息 (年份、规模、类型)
- 👥 节点组成 (核心/新节点比例)
- 📍 州分布 (Top 3)
- 🏙️ 都市区分布 (Top 5)
- 🏭 NAICS 2位/4位行业分布
- 💼 Top 10职位角色

#### Step 4: 返回主页面
- 点击左上角 **"Back to Community View"** 按钮 ←

---

## 💡 典型工作流程

### 工作流 A: 从社区到演化
```
1. 主页面上传某年社区检测结果 (如2020年)
2. 探索该年的社区结构
3. 点击"Evolution Chains"按钮
4. 上传演化链数据
5. 找到包含该年的演化链
6. 查看该社区的历史和未来演化
```

### 工作流 B: 从演化到社区
```
1. 直接打开evolution-chain.html
2. 上传演化链数据
3. 识别感兴趣的演化模式
4. 记录特定年份的社区ID
5. 返回主页面
6. 上传对应年份的社区数据
7. 深入分析该社区的详细结构
```

---

## 📊 数据文件要求

### 社区检测结果 CSV
**列要求**:
- `geo_rcid`: 节点ID (必需)
- `community_level1`, `community_level2`, ... : 社区层级 (必需)
- `rcid`: 原始公司ID
- `company_name`: 公司名称
- `real_state`: 州
- `real_metro_area`: 都市区
- `naics_code`: NAICS行业代码
- `rics_k50`, `rics_k200`, `rics_k400`: RICS分类
- 其他属性...

**示例行**:
```csv
geo_rcid,community_level1,community_level2,rcid,company_name,real_state,naics_code
RC123_CA_SanFrancisco,1,1.5,RC123,Tech Corp,California,5112
```

### 演化链 JSON
**结构要求**:
```json
[
  {
    "stable_id": "S0",
    "length": 10,
    "score": 0.75,
    "communities": [
      {
        "year": 2000,
        "community_id": "1",
        "attributes": {
          "size": 150,
          "top3_states": [{"value": "CA", "count": 100, "percentage": 66.7}],
          "top5_metros": [...],
          "top3_naics_2digit": [...],
          "top5_naics_4digit": [...],
          "top10_roles": [...]
        },
        "node_composition": {
          "type": "established",
          "core_node_ratio": 0.8,
          "new_node_ratio": 0.1,
          "avg_node_weight": 0.75
        }
      }
    ]
  }
]
```

---

## 🎨 界面特性

### 主页面特性
- ✅ 自适应层级展示 (支持任意深度)
- ✅ 三种布局模式 (树形/径向/分层)
- ✅ 动态节点间距，防止重叠
- ✅ 碰撞检测
- ✅ 网络视图 (双击叶子节点)
- ✅ 组成分析面板
- ✅ 自动适配视图

### 演化链页面特性
- ✅ 时间轴可视化
- ✅ 多种布局模式
- ✅ 链长度过滤和排序
- ✅ 详细的社区属性展示
- ✅ 交互式链列表侧边栏
- ✅ 实时统计面板
- ✅ 颜色编码 (按链长度)

---

## 🔗 模块切换

### 从主页面 → 演化链
- **按钮位置**: 右上角
- **按钮图标**: 🔗 Evolution Chains
- **操作**: 单击即可跳转

### 从演化链 → 主页面
- **按钮位置**: 左上角
- **按钮图标**: ← Back to Community View
- **操作**: 单击即可返回

---

## 🎯 使用建议

### 对于单年分析
1. 使用主页面的社区检测可视化
2. 深入探索层级结构
3. 使用网络视图查看连接

### 对于时间演化分析
1. 使用演化链页面
2. 过滤出长期稳定的链
3. 追踪属性变化

### 对于综合分析
1. 在演化链中识别关键转折点
2. 返回主页面查看转折年份的详细结构
3. 结合两个视角理解演化机制

---

## 💻 技术要求

### 浏览器
- **推荐**: Chrome 90+, Firefox 88+, Edge 90+
- **JavaScript**: 必须启用
- **屏幕**: 1920x1080 或更高

### 文件大小
- **社区CSV**: 通常 < 50MB
- **边数据CSV**: 通常 < 100MB  
- **演化链JSON**: 通常 < 20MB

### 性能建议
- **社区数量**: 显示 < 200 个社区效果最佳
- **演化链数量**: 显示 < 100 条链效果最佳
- **层级深度**: 6层以内效果最佳

---

## 🐛 常见问题

### Q: 上传文件后没有反应？
**A**: 
1. 检查浏览器控制台 (F12) 是否有错误
2. 确认文件格式正确 (CSV/JSON)
3. 检查文件是否包含必需的列

### Q: 节点重叠无法点击？
**A**: 
1. 使用 "Fit to View" 按钮
2. 切换到径向布局
3. 减少显示的节点数量

### Q: 演化链加载很慢？
**A**: 
1. 减少 "Max Chains to Display" 数量
2. 使用长度过滤器
3. 确保JSON文件 < 50MB

### Q: 如何找到特定社区的演化？
**A**: 
1. 在主页面记住社区ID
2. 进入演化链页面
3. 使用侧边栏搜索对应的链
4. 查看包含该社区的年份节点

---

## 📖 相关文档

- **社区连接探索器**: 参考 `explorers/COMMUNITY_CONNECTION_EXPLORER.md`
- **D3.js文档**: https://d3js.org

---

## 🛠️ 辅助探索工具

除了两个核心模块，本平台还提供三个辅助探索工具（位于 `explorers/` 文件夹）：

### 1. 社区连接关系探索器
- **文件**: `explorers/community-connection-explorer.html`
- **功能**: 渐进式展开相邻年份社区的连接关系
- **用途**: 观察社区演化链构建的中间结果

### 2. 渐进式演化链可视化
- **文件**: `explorers/evolution-chain-progressive.html`
- **功能**: 逐步展开演化链，避免一次性显示过多数据
- **用途**: 适合大规模演化链数据的探索

### 3. 演化网络探索器
- **文件**: `explorers/evolution-network-explorer.html`
- **功能**: 网络视图下的演化关系探索
- **用途**: 适合复杂网络结构的可视化分析

详细使用说明请参考 `explorers/COMMUNITY_CONNECTION_EXPLORER.md`

---

## 🎉 快速开始

```bash
# 1. 克隆或下载项目
git clone <repository-url>
cd labor-mobility-visualization

# 2. 打开主页面
# 直接在浏览器中打开 index.html
# 或使用本地服务器：
# python -m http.server 8000
# 然后访问 http://localhost:8000

# 3. 上传社区检测结果
# 点击"Choose Community CSV File"

# 4. 探索演化
# 点击"Evolution Chains"按钮
# 上传 weighted_chain_details_level1.json
```

---

## 📋 项目优化说明

本项目已进行清理和优化：
- ✅ 移除了重复的文件夹和zip压缩包
- ✅ 移除了混杂的Python脚本文件
- ✅ 将辅助工具整理到 `explorers/` 文件夹
- ✅ 优化了文件结构，使核心功能更清晰
- ✅ 保留了所有功能，无功能损失

**祝你分析愉快!** 🚀
