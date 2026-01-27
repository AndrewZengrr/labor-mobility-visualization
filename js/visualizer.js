// Visualization core module - Improved for dynamic hierarchy
const Visualizer = {
    svg: null,
    zoom: null,
    tooltip: null,
    width: 0,
    height: 0,
    
    init() {
        const container = d3.select('#mainSvg');
        const containerNode = container.node();
        this.width = containerNode.clientWidth || 1200;
        this.height = containerNode.clientHeight || 700;
        
        this.svg = container;
        this.tooltip = d3.select('#tooltip');
        
        this.zoom = d3.zoom()
            .scaleExtent([0.1, 3])
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
        const root = this.createHierarchy(communities, visibleNodes, expandedNodes);
        
        this.renderTree(root, communities, config, expandedNodes, data);
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
    
    createHierarchy(communities, visibleNodes, expandedNodes) {
        const tree = d3.tree()
            .size([this.width - Config.viz.treeMargin * 2, this.height - Config.viz.treeMargin * 2])
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
        return root;
    },
    
    renderTree(root, communities, config, expandedNodes, allData) {
        const g = this.svg.select('.zoom-group');
        g.selectAll('*').remove();
        
        const offsetX = Config.viz.treeMargin;
        const offsetY = Config.viz.treeMargin;
        
        // Draw links
        const links = root.links();
        g.selectAll('.link')
            .data(links)
            .enter().append('path')
            .attr('class', 'link')
            .attr('d', d3.linkVertical()
                .x(d => d.x + offsetX)
                .y(d => d.y + offsetY));
        
        const nodes = root.descendants().filter(d => d.data.id !== 'root');
        
        // Use optimized color scale
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
            .attr('transform', d => `translate(${d.x + offsetX},${d.y + offsetY})`);
        
        // Node circles
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
                
                // Get most common value for coloring
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
                
                // ✅ IMPROVED: Check if it's a leaf community (regardless of level)
                if (comm && DataHandler.isLeafCommunity(d.data.id, communities)) {
                    console.log(`Double-clicked leaf community: ${d.data.id} (level ${comm.level})`);
                    NetworkViewer.showNetwork(d.data.id, comm, allData);
                } else if (comm) {
                    console.log(`Community ${d.data.id} has children, network view only for leaf communities`);
                }
            })
            .on('mouseover', (event, d) => {
                this.showTooltip(event, d.data.id, communities, config.colorAttr);
            })
            .on('mouseout', () => {
                this.hideTooltip();
            });
        
        // Node labels
        nodeGroup.append('text')
            .attr('class', 'node-label')
            .attr('dy', '0.35em')
            .text(d => {
                // ✅ Show both ID and level info
                const comm = communities.get(d.data.id);
                return comm ? `${d.data.id} (L${comm.level})` : d.data.id;
            })
            .style('font-size', d => {
                const comm = communities.get(d.data.id);
                // Smaller font for deeper levels
                const baseSize = 11;
                return comm ? `${Math.max(8, baseSize - comm.level)}px` : `${baseSize}px`;
            });
        
        // Expansion indicator
        nodeGroup.filter(d => {
            const comm = communities.get(d.data.id);
            return comm && comm.children.size > 0;
        })
        .append('text')
        .attr('class', 'expansion-indicator')
        .attr('dy', '0.35em')
        .attr('x', d => {
            const comm = communities.get(d.data.id);
            return comm ? sizeScale(comm.nodes.length) + 5 : 15;
        })
        .attr('fill', '#7c9cb5')
        .text(d => expandedNodes.has(d.data.id) ? '−' : '+')
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
        
        // ✅ IMPROVED: Show depth and leaf status
        const isLeaf = DataHandler.isLeafCommunity(communityId, communities);
        const depth = DataHandler.getCommunityDepth(communityId);
        
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
                    ${isLeaf ? 'Double-click for network' : 'Right-click for details'}
                </span>
            </div>
        `;
        
        // Add composition distribution (top 5)
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
        
        const vizRight = vizRect.right;
        const vizBottom = vizRect.bottom;
        
        if (left + tooltipRect.width > vizRight) {
            left = event.clientX - tooltipRect.width - offsetX;
        }
        
        if (top + tooltipRect.height > vizBottom) {
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
        
        // ✅ NEW: Count communities by level
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
    
    zoomIn() {
        this.svg.transition().call(this.zoom.scaleBy, 1.5);
    },
    
    zoomOut() {
        this.svg.transition().call(this.zoom.scaleBy, 0.67);
    },
    
    resetZoom() {
        this.svg.transition().call(this.zoom.transform, d3.zoomIdentity);
    }
};