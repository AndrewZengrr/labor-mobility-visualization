# 布局优化指南 - 解决节点重叠问题

## 🎯 问题诊断

你遇到的问题:
1. **节点重叠**: 深层级节点挤在一起，无法点击
2. **+/- 按钮被遮盖**: 展开指示器被其他节点覆盖
3. **标签重叠**: 文字堆叠在一起无法阅读
4. **布局拥挤**: 树形结构过于密集

## ✅ 优化方案

### 1. **三种布局模式**

#### 🌳 自适应树形布局 (Adaptive Tree)
- **适用场景**: 中等深度层级 (3-5层)
- **特点**: 
  - 动态调整节点间距
  - 碰撞检测防止重叠
  - 根据深度调整分离度
- **优势**: 保持树形结构清晰

#### ⭕ 径向布局 (Radial)
- **适用场景**: 深层级结构 (5+层)
- **特点**:
  - 从中心向外扩散
  - 空间利用率高
  - 避免水平拥挤
- **优势**: 深层级也能清晰展示

#### 📊 分层布局 (Layered)
- **适用场景**: 需要按层级分析
- **特点**:
  - 每层水平排列
  - 清晰的层级分隔
  - 类似Sankey图
- **优势**: 层级关系一目了然

---

## 🔧 关键优化点

### 1. 动态节点间距
```javascript
// 根据最大深度调整间距
const baseNodeSpacing = 120;
const depthFactor = Math.max(1, maxDepth / 3);
const nodeSpacing = baseNodeSpacing * depthFactor;
```

**效果**: 深层级自动扩大间距

### 2. 改进的分离函数
```javascript
.separation((a, b) => {
    if (a.parent === b.parent) {
        return 1.2;  // 兄弟节点
    } else {
        return 2.5;  // 不同父节点更远
    }
})
```

**效果**: 同级节点紧凑，不同分支分离

### 3. 碰撞检测
```javascript
resolveCollisions(nodes) {
    const minDistance = 40;
    // 迭代调整重叠节点位置
}
```

**效果**: 防止节点重叠

### 4. 标签优化
```javascript
// 标签放在节点下方
.attr('dy', d => {
    const r = sizeScale(comm.nodes.length);
    return r + 15;  // 节点半径 + 间隙
})

// 深层级简化标签
if (depth > 2) {
    const parts = id.split('.');
    return `${parts[parts.length - 1]} (L${level})`;
}
```

**效果**: 避免标签重叠，深层级显示简化ID

### 5. +/- 按钮位置
```javascript
.attr('x', d => {
    const comm = communities.get(d.data.id);
    return comm ? sizeScale(comm.nodes.length) + 8 : 15;
})
```

**效果**: 按钮在节点右侧，不被遮盖

### 6. 自动适配视图
```javascript
fitToView() {
    const bounds = g.node().getBBox();
    const scale = 0.9 / Math.max(
        width / fullWidth, 
        height / fullHeight
    );
    // 自动缩放和平移
}
```

**效果**: 自动调整缩放，所有节点可见

---

## 📊 布局模式对比

| 特性 | 自适应树形 | 径向布局 | 分层布局 |
|------|-----------|---------|---------|
| 最大层级 | 5层 | 8+层 | 6层 |
| 节点数量 | 中等(<200) | 大量(200+) | 中等(<150) |
| 空间利用 | ★★★☆☆ | ★★★★★ | ★★★★☆ |
| 层级清晰度 | ★★★★☆ | ★★★☆☆ | ★★★★★ |
| 交互便利性 | ★★★★★ | ★★★☆☆ | ★★★★☆ |

---

## 🚀 使用建议

### 场景1: 层级不深 (2-3层)
- **推荐**: 自适应树形
- **设置**: 默认配置即可
- **优势**: 最直观的树形结构

### 场景2: 深层级 (4-6层)
- **推荐**: 径向布局
- **设置**: 点击 "⭕ Radial" 按钮
- **优势**: 避免水平拥挤

### 场景3: 需要分析每层分布
- **推荐**: 分层布局
- **设置**: 点击 "📊 Layered" 按钮
- **优势**: 清晰看到每层的社区数量

### 场景4: 节点数量特别多
- **推荐**: 提高 `minSize` 参数
- **设置**: 调整 "Min Community Size" 到 10-20
- **优势**: 过滤小社区，减少节点数量

---

## 💡 交互技巧

### 1. 分步展开
```
不要一次 "Expand All"
↓
使用 "Expand to Level 2"
↓
观察布局
↓
需要时继续展开到 Level 3
```

### 2. 使用 "Fit to View"
- 每次展开/折叠后点击
- 切换布局模式后点击
- 自动调整到最佳视图

### 3. 组合使用缩放
- `Fit to View` 看全局
- `Zoom In` 看细节
- 拖拽移动关注区域

### 4. 切换布局找最优
```
数据加载后
↓
先看自适应树形
↓
如果拥挤，尝试径向
↓
需要层级对比，用分层
```

---

## 📐 参数调优

### 如果节点仍然重叠:

**方法1: 增加节点间距**
```javascript
// 在 visualizer.js 中调整
const baseNodeSpacing = 150;  // 从120增加到150
```

**方法2: 增加分离度**
```javascript
.separation((a, b) => {
    if (a.parent === b.parent) {
        return 1.5;  // 从1.2增加
    } else {
        return 3.0;  // 从2.5增加
    }
})
```

**方法3: 减小节点大小**
```javascript
// 在 config.js 中调整
viz: {
    minNodeSize: 6,   // 从8减小
    maxNodeSize: 30,  // 从40减小
}
```

**方法4: 增加画布高度**
```html
<!-- 在 index.html 中 -->
<div class="viz-container" style="height: 1000px;">
```

---

## 🎨 视觉优化建议

### 1. 简化深层级标签
已实现: 深度>2时只显示最后一段ID
```
完整: 1.2.3.4.5
简化: 5 (L5)
```

### 2. 调整字体大小
```javascript
.style('font-size', d => {
    const depth = getNodeDepth(d.data.id);
    return `${Math.max(9, 12 - depth)}px`;
})
```

### 3. 半透明连接线
```javascript
.attr('opacity', 0.4)  // 降低线条干扰
```

---

## 🔍 调试工具

### 查看布局信息
```javascript
// 在浏览器控制台
console.log('Layout mode:', Visualizer.layoutMode);
console.log('Visible nodes:', App.expandedNodes.size);
console.log('Max depth:', Config.maxLevels);
```

### 检查节点位置
```javascript
// 检查是否有重叠
const nodes = d3.selectAll('.node-group');
nodes.each(function(d) {
    console.log(d.data.id, d.x, d.y);
});
```

---

## 📝 最佳实践总结

1. **加载数据后**: 先用默认树形布局
2. **发现拥挤**: 切换到径向布局
3. **需要对比**: 使用分层布局
4. **逐级展开**: 不要一次展开所有
5. **使用Fit to View**: 每次操作后调整视图
6. **过滤小社区**: 提高minSize减少节点
7. **聚焦分析**: 只展开感兴趣的分支

---

## 🆕 新增功能

1. ✅ 三种布局模式切换
2. ✅ 自动适配视图按钮
3. ✅ 碰撞检测防重叠
4. ✅ 动态节点间距
5. ✅ 标签优化显示
6. ✅ 改进的节点分离
7. ✅ 更大的画布高度(850px)

---

## 🎯 预期效果

### 优化前:
- ❌ 节点挤在一起
- ❌ 无法点击+/-按钮
- ❌ 标签重叠难读
- ❌ 深层级完全拥挤

### 优化后:
- ✅ 节点间距合理
- ✅ 按钮清晰可点
- ✅ 标签分离可读
- ✅ 多种布局适应不同情况
- ✅ 自动适配最佳视图

---

**立即试用**: 使用改进的文件替换原文件即可!
