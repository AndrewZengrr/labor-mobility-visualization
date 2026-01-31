// Visualization core module - Optimized layout for deep hierarchies
const Visualizer = {
    svg: null,
    zoom: null,
    tooltip: null,
    width: 0,
    height: 0,
    layoutMode: 'adaptive-tree', // 'adaptive-tree', 'radial', 'layered'
    
    init() {
        const container = d3.select('#mainSvg');
        const containerNode = container.node();
        this.width = containerNode.clientWidth || 1400;
        this.height = containerNode.clientHeight || 900;
        
        this.svg = container;
        this.tooltip = d3.select('#tooltip');
        
        this.zoom = d3.zoom()
            .scaleExtent([0.1, 5])
            .on('zoom', (event) => {
                this.svg.select('.zoom-group').attr('transform', event.transform);
            });
        
        this.svg.call(this.zoom);
        this.svg.selectAll('*').remove();
        this.svg.append('g').attr('class', 'zoom-group');
    },
    
    render(data, config, expandedNodes) {
        if (!data || data.length === 0) {
            console.error('No data to render');
            return;
        }
        
        const communities = DataHandler.processCommunities(data, config.minSize);
        const visibleNodes = this.getVisibleNodes(communities, expandedNodes);
        
        // 根据布局模式选择渲染方法
        if (this.layoutMode === 'radial') {
            this.renderRadialLayout(communities, visibleNodes, expandedNodes, config, data);
        } else if (this.layoutMode === 'layered') {
            this.renderLayeredLayout(communities, visibleNodes, expandedNodes, config, data);
        } else {
            this.renderAdaptiveTree(communities, visibleNodes, expandedNodes, config, data);
        }
        
        this.updateStats(communities, visibleNodes, expandedNodes);
    },
    
    getVisibleNodes(communities, expandedNodes) {
        const visible = new Map();
        
        // Show all level 1 communities
        communities.forEach((comm, id) => {
            if (comm.level === 1) {
                visible.set(id, comm);
            }
        });
        
        // Show children of expanded nodes
        expandedNodes.forEach(nodeId => {
            if (communities.has(nodeId)) {
                const comm = communities.get(nodeId);
                comm.children.forEach(childId => {
                    if (communities.has(childId)) {
                        visible.set(childId, communities.get(childId));
                    }
                });
            }
        });
        
        return visible;
    },
    
    // ✅ 改进的自适应树形布局
    renderAdaptiveTree(communities, visibleNodes, expandedNodes, config, allData) {
        const g = this.svg.select('.zoom-group');
        g.selectAll('*').remove();
        
        // 计算最大深度
        const maxDepth = Math.max(...Array.from(visibleNodes.values()).map(n => 
            this.getNodeDepth(n.id)
        ));
        
        // 动态调整节点间距
        const baseNodeSpacing = 120;
        const depthFactor = Math.max(1, maxDepth / 3);
        const nodeSpacing = baseNodeSpacing * depthFactor;
        
        // 动态调整树的尺寸
        const effectiveWidth = Math.max(this.width - 100, visibleNodes.size * 60);
        const effectiveHeight = Math.max(this.height - 100, maxDepth * 200);
        
        const tree = d3.tree()
            .size([effectiveWidth, effectiveHeight])
            .nodeSize([nodeSpacing, 150])  // ✅ 固定节点间距
            .separation((a, b) => {
                // ✅ 根据深度和父节点调整间距
                if (a.parent === b.parent) {
                    return 1.2;  // 兄弟节点间距
                } else {
                    return 2.5;  // 不同父节点间距更大
                }
            });
        
        const root = d3.hierarchy({
            id: 'root',
            children: Array.from(visibleNodes.values()).filter(n => !n.parent || !visibleNodes.has(n.parent))
        }, d => {
            if (d.id === 'root') return d.children;
            const comm = communities.get(d.id);
            if (expandedNodes.has(d.id) && comm) {
                return Array.from(comm.children)
                    .filter(childId => visibleNodes.has(childId))
                    .map(childId => ({ id: childId }));
            }
            return null;
        });
        
        tree(root);
        
        // ✅ 碰撞检测和调整
        this.resolveCollisions(root.descendants());
        
        // 计算边界并居中
        const nodes = root.descendants().filter(d => d.data.id !== 'root');
        if (nodes.length === 0) return;
        
        const xExtent = d3.extent(nodes, d => d.x);
        const yExtent = d3.extent(nodes, d => d.y);
        
        const offsetX = (this.width - (xExtent[1] - xExtent[0])) / 2 - xExtent[0];
        const offsetY = 50;
        
        // 绘制连接线
        const links = root.links();
        g.selectAll('.link')
            .data(links)
            .enter().append('path')
            .attr('class', 'link')
            .attr('d', d3.linkVertical()
                .x(d => d.x + offsetX)
                .y(d => d.y + offsetY))
            .attr('stroke-width', d => {
                // ✅ 根据子节点数量调整线宽
                const targetComm = communities.get(d.target.data.id);
                return targetComm ? Math.min(3, 1 + targetComm.nodes.length / 50) : 1;
            })
            .attr('opacity', 0.4);
        
        this.renderNodes(g, nodes, communities, config, expandedNodes, allData, offsetX, offsetY);
    },
    
    // ✅ 径向布局（适合深层级结构）
    renderRadialLayout(communities, visibleNodes, expandedNodes, config, allData) {
        const g = this.svg.select('.zoom-group');
        g.selectAll('*').remove();
        
        const radius = Math.min(this.width, this.height) / 2 - 100;
        
        const tree = d3.tree()
            .size([2 * Math.PI, radius])
            .separation((a, b) => (a.parent === b.parent ? 1 : 2) / a.depth);
        
        const root = d3.hierarchy({
            id: 'root',
            children: Array.from(visibleNodes.values()).filter(n => !n.parent || !visibleNodes.has(n.parent))
        }, d => {
            if (d.id === 'root') return d.children;
            const comm = communities.get(d.id);
            if (expandedNodes.has(d.id) && comm) {
                return Array.from(comm.children)
                    .filter(childId => visibleNodes.has(childId))
                    .map(childId => ({ id: childId }));
            }
            return null;
        });
        
        tree(root);
        
        const nodes = root.descendants().filter(d => d.data.id !== 'root');
        
        // 转换为笛卡尔坐标
        nodes.forEach(d => {
            d.cartesian_x = d.y * Math.cos(d.x - Math.PI / 2);
            d.cartesian_y = d.y * Math.sin(d.x - Math.PI / 2);
        });
        
        const centerX = this.width / 2;
        const centerY = this.height / 2;
        
        // 绘制径向连接线
        const links = root.links();
        g.selectAll('.link')
            .data(links)
            .enter().append('path')
            .attr('class', 'link')
            .attr('d', d3.linkRadial()
                .angle(d => d.x)
                .radius(d => d.y))
            .attr('transform', `translate(${centerX},${centerY})`)
            .attr('opacity', 0.4);
        
        this.renderNodes(g, nodes, communities, config, expandedNodes, allData, 
                        centerX, centerY, true);
    },
    
    // ✅ 分层布局（类似Sugiyama）
    renderLayeredLayout(communities, visibleNodes, expandedNodes, config, allData) {
        const g = this.svg.select('.zoom-group');
        g.selectAll('*').remove();
        
        // 按层级分组
        const layers = new Map();
        visibleNodes.forEach((comm, id) => {
            const depth = this.getNodeDepth(id);
            if (!layers.has(depth)) {
                layers.set(depth, []);
            }
            layers.get(depth).push({ id, comm });
        });
        
        const maxLayerSize = Math.max(...Array.from(layers.values()).map(l => l.length));
        const layerHeight = 180;
        const nodeSpacing = Math.max(80, (this.width - 100) / maxLayerSize);
        
        const nodePositions = new Map();
        
        layers.forEach((layerNodes, depth) => {
            const y = depth * layerHeight + 50;
            const totalWidth = layerNodes.length * nodeSpacing;
            const startX = (this.width - totalWidth) / 2;
            
            layerNodes.forEach((node, i) => {
                nodePositions.set(node.id, {
                    x: startX + i * nodeSpacing + nodeSpacing / 2,
                    y: y
                });
            });
        });
        
        // 绘制连接线
        const allLinks = [];
        visibleNodes.forEach((comm, id) => {
            comm.children.forEach(childId => {
                if (visibleNodes.has(childId)) {
                    allLinks.push({ source: id, target: childId });
                }
            });
        });
        
        g.selectAll('.link')
            .data(allLinks)
            .enter().append('line')
            .attr('class', 'link')
            .attr('x1', d => nodePositions.get(d.source).x)
            .attr('y1', d => nodePositions.get(d.source).y)
            .attr('x2', d => nodePositions.get(d.target).x)
            .attr('y2', d => nodePositions.get(d.target).y)
            .attr('opacity', 0.4);
        
        // 创建节点数据结构
        const nodes = Array.from(visibleNodes.keys()).map(id => ({
            data: { id },
            x: nodePositions.get(id).x,
            y: nodePositions.get(id).y
        }));
        
        this.renderNodes(g, nodes, communities, config, expandedNodes, allData, 0, 0);
    },
    
    // ✅ 碰撞检测和解决
    resolveCollisions(nodes) {
        const minDistance = 40;  // 最小节点间距
        const iterations = 5;
        
        for (let iter = 0; iter < iterations; iter++) {
            for (let i = 0; i < nodes.length; i++) {
                for (let j = i + 1; j < nodes.length; j++) {
                    const node1 = nodes[i];
                    const node2 = nodes[j];
                    
                    // 跳过根节点
                    if (node1.data.id === 'root' || node2.data.id === 'root') continue;
                    
                    const dx = node2.x - node1.x;
                    const dy = node2.y - node1.y;
                    const distance = Math.sqrt(dx * dx + dy * dy);
                    
                    if (distance < minDistance && distance > 0) {
                        const adjust = (minDistance - distance) / 2;
                        const angle = Math.atan2(dy, dx);
                        
                        node1.x -= adjust * Math.cos(angle);
                        node2.x += adjust * Math.cos(angle);
                    }
                }
            }
        }
    },
    
    getNodeDepth(id) {
        if (!id || id === 'root' || id === '-1') return 0;
        return String(id).split('.').length;
    },
    
    // ✅ 统一的节点渲染
    renderNodes(g, nodes, communities, config, expandedNodes, allData, offsetX, offsetY, isRadial = false) {
        const colorScale = Config.getColorScale(config.colorAttr);
        
        const sizeScale = d3.scaleSqrt()
            .domain([0, d3.max(nodes, d => {
                const comm = communities.get(d.data.id);
                return comm ? comm.nodes.length : 0;
            })])
            .range([Config.viz.minNodeSize, Config.viz.maxNodeSize]);
        
        const nodeGroup = g.selectAll('.node-group')
            .data(nodes)
            .enter().append('g')
            .attr('class', 'node-group')
            .attr('transform', d => {
                if (isRadial) {
                    return `translate(${d.cartesian_x + offsetX},${d.cartesian_y + offsetY})`;
                } else {
                    return `translate(${d.x + offsetX},${d.y + offsetY})`;
                }
            });
        
        // 节点圆圈
        nodeGroup.append('circle')
            .attr('class', d => {
                const comm = communities.get(d.data.id);
                const hasChildren = comm && comm.children.size > 0;
                return `node ${hasChildren ? 'expandable' : 'leaf'}`;
            })
            .attr('r', d => {
                const comm = communities.get(d.data.id);
                return comm ? sizeScale(comm.nodes.length) : Config.viz.minNodeSize;
            })
            .attr('fill', d => {
                const comm = communities.get(d.data.id);
                if (!comm || comm.nodes.length === 0) return '#95a5a6';
                
                const values = comm.nodes.map(n => {
                    if (config.colorAttr === 'naics_industry') {
                        return n.naics_industry;
                    }
                    return n[config.colorAttr];
                }).filter(Boolean);
                
                const mostCommon = d3.mode(values) || 'Unknown';
                return colorScale(mostCommon);
            })
            .attr('stroke', d => {
                const comm = communities.get(d.data.id);
                const hasChildren = comm && comm.children.size > 0;
                return hasChildren ? '#7c9cb5' : '#95a5a6';
            })
            .attr('stroke-width', d => {
                const comm = communities.get(d.data.id);
                const hasChildren = comm && comm.children.size > 0;
                return hasChildren ? 2.5 : 2;
            })
            .style('cursor', 'pointer')
            .on('click', (event, d) => {
                event.stopPropagation();
                const comm = communities.get(d.data.id);
                if (comm && comm.children.size > 0) {
                    App.toggleNode(d.data.id);
                }
            })
            .on('contextmenu', (event, d) => {
                event.preventDefault();
                event.stopPropagation();
                Composition.showPanel(d.data.id, communities);
            })
            .on('dblclick', (event, d) => {
                event.preventDefault();
                event.stopPropagation();
                const comm = communities.get(d.data.id);
                
                if (comm && DataHandler.isLeafCommunity(d.data.id, communities)) {
                    NetworkViewer.showNetwork(d.data.id, comm, allData);
                }
            })
            .on('mouseover', (event, d) => {
                this.showTooltip(event, d.data.id, communities, config.colorAttr);
            })
            .on('mouseout', () => {
                this.hideTooltip();
            });
        
        // ✅ 改进的节点标签 - 避免重叠
        nodeGroup.append('text')
            .attr('class', 'node-label')
            .attr('dy', d => {
                const comm = communities.get(d.data.id);
                const r = comm ? sizeScale(comm.nodes.length) : Config.viz.minNodeSize;
                return r + 15;  // 标签在节点下方
            })
            .attr('text-anchor', 'middle')
            .text(d => {
                const comm = communities.get(d.data.id);
                const depth = this.getNodeDepth(d.data.id);
                // 简化深层级的标签
                if (depth > 2) {
                    const parts = d.data.id.split('.');
                    return `${parts[parts.length - 1]} (L${comm.level})`;
                }
                return comm ? `${d.data.id} (L${comm.level})` : d.data.id;
            })
            .style('font-size', d => {
                const depth = this.getNodeDepth(d.data.id);
                return `${Math.max(9, 12 - depth)}px`;
            })
            .style('pointer-events', 'none');
        
        // 展开指示器
        nodeGroup.filter(d => {
            const comm = communities.get(d.data.id);
            return comm && comm.children.size > 0;
        })
        .append('text')
        .attr('class', 'expansion-indicator')
        .attr('dy', '0.35em')
        .attr('x', d => {
            const comm = communities.get(d.data.id);
            return comm ? sizeScale(comm.nodes.length) + 8 : 15;
        })
        .attr('fill', '#7c9cb5')
        .attr('font-weight', 'bold')
        .attr('font-size', '16px')
        .text(d => expandedNodes.has(d.data.id) ? '−' : '+')
        .style('cursor', 'pointer')
        .on('click', (event, d) => {
            event.stopPropagation();
            App.toggleNode(d.data.id);
        });
    },
    
    showTooltip(event, communityId, communities, colorAttr) {
        const comm = communities.get(communityId);
        if (!comm) return;
        
        const nodes = comm.nodes;
        const attributes = ['naics_industry', 'real_state', 'real_metro_area', 'rics_k50'];
        
        const isLeaf = DataHandler.isLeafCommunity(communityId, communities);
        const depth = this.getNodeDepth(communityId);
        
        let html = `
            <h4>Community ${communityId}</h4>
            <div class="stat-item">
                <span class="stat-label">Size:</span>
                <span class="stat-value">${nodes.length} companies</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Level:</span>
                <span class="stat-value">Level ${comm.level} (Depth: ${depth})</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Type:</span>
                <span class="stat-value">${isLeaf ? 'Leaf (no children)' : `Has ${comm.children.size} children`}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Total Workforce:</span>
                <span class="stat-value">${d3.sum(nodes, d => parseInt(d.workforce_total_people) || 0).toLocaleString()}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Interaction:</span>
                <span class="stat-value">
                    ${isLeaf ? 'Double-click for network' : 'Click +/- to expand'}
                </span>
            </div>
        `;
        
        attributes.forEach(attr => {
            const composition = DataHandler.calculateComposition(nodes, attr);
            if (composition.length > 0) {
                html += `<div class="composition-section">
                    <strong>${Config.attributeLabels[attr]}:</strong>`;
                composition.slice(0, Config.composition.topN).forEach(item => {
                    html += `<div class="composition-item">
                        <span>${item.name}:</span>
                        <span>${item.count} (${item.percentage}%)</span>
                    </div>`;
                });
                html += `</div>`;
            }
        });
        
        this.tooltip.html(html);
        
        const vizContainer = document.querySelector('.viz-container');
        const vizRect = vizContainer.getBoundingClientRect();
        const tooltipNode = this.tooltip.node();
        const tooltipRect = tooltipNode.getBoundingClientRect();
        
        const offsetX = 15;
        const offsetY = 15;
        
        let left = event.clientX + offsetX;
        let top = event.clientY + offsetY;
        
        if (left + tooltipRect.width > vizRect.right) {
            left = event.clientX - tooltipRect.width - offsetX;
        }
        
        if (top + tooltipRect.height > vizRect.bottom) {
            top = event.clientY - tooltipRect.height - offsetY;
        }
        
        if (left < vizRect.left) {
            left = vizRect.left + 5;
        }
        
        if (top < vizRect.top) {
            top = vizRect.top + 5;
        }
        
        this.tooltip
            .style('left', left + 'px')
            .style('top', top + 'px')
            .style('opacity', 1);
    },
    
    hideTooltip() {
        this.tooltip.style('opacity', 0);
    },
    
    updateStats(communities, visibleNodes, expandedNodes) {
        const totalCommunities = communities.size;
        const totalCompanies = Array.from(communities.values()).reduce((sum, c) => sum + c.nodes.length, 0);
        const avgSize = totalCompanies / totalCommunities || 0;
        
        const levelCounts = {};
        communities.forEach(comm => {
            levelCounts[comm.level] = (levelCounts[comm.level] || 0) + 1;
        });
        
        let levelStats = '';
        for (let level = 1; level <= Config.maxLevels; level++) {
            if (levelCounts[level]) {
                levelStats += `<strong>Level ${level}:</strong> ${levelCounts[level]}<br>`;
            }
        }
        
        document.getElementById('statsContent').innerHTML = `
            <div style="line-height: 1.8">
                <strong>Layout:</strong> ${this.layoutMode}<br>
                <strong>Max Levels:</strong> ${Config.maxLevels}<br>
                ${levelStats}
                <strong>Total Communities:</strong> ${totalCommunities}<br>
                <strong>Visible Communities:</strong> ${visibleNodes.size}<br>
                <strong>Expanded Nodes:</strong> ${expandedNodes.size}<br>
                <strong>Total Companies:</strong> ${totalCompanies}<br>
                <strong>Average Size:</strong> ${avgSize.toFixed(1)}
            </div>
        `;
    },
    
    // 切换布局模式
    setLayoutMode(mode) {
        this.layoutMode = mode;
        console.log('Layout mode changed to:', mode);
    },
    
    zoomIn() {
        this.svg.transition().call(this.zoom.scaleBy, 1.5);
    },
    
    zoomOut() {
        this.svg.transition().call(this.zoom.scaleBy, 0.67);
    },
    
    resetZoom() {
        this.svg.transition().call(this.zoom.transform, d3.zoomIdentity);
    },
    
    // ✅ 自动适配缩放
    fitToView() {
        const g = this.svg.select('.zoom-group');
        const bounds = g.node().getBBox();
        
        const fullWidth = this.width;
        const fullHeight = this.height;
        const width = bounds.width;
        const height = bounds.height;
        
        const midX = bounds.x + width / 2;
        const midY = bounds.y + height / 2;
        
        const scale = 0.9 / Math.max(width / fullWidth, height / fullHeight);
        const translate = [fullWidth / 2 - scale * midX, fullHeight / 2 - scale * midY];
        
        this.svg.transition()
            .duration(750)
            .call(this.zoom.transform, d3.zoomIdentity
                .translate(translate[0], translate[1])
                .scale(scale));
    }
};
