// Adapted Progressive Visualizer for Edge-Based Network Data
const AdaptedVisualizer = {
    svg: null,
    zoom: null,
    width: 0,
    height: 0,
    
    // State management
    expandedNodes: new Set(),
    visibleNodes: new Set(),
    visibleEdges: new Set(),
    activePath: [],
    
    // Display settings
    currentStartYear: null,
    currentFilters: {},
    
    /**
     * Initialize SVG and zoom
     */
    init() {
        const container = d3.select('#evolutionSvg');
        const containerNode = container.node();
        this.width = containerNode.clientWidth || 1400;
        this.height = containerNode.clientHeight || 750;
        
        this.svg = container;
        
        this.zoom = d3.zoom()
            .scaleExtent([0.1, 5])
            .on('zoom', (event) => {
                this.svg.select('.main-group').attr('transform', event.transform);
            });
        
        this.svg.call(this.zoom);
        this.svg.selectAll('*').remove();
        this.svg.append('g').attr('class', 'main-group');
        
        // Reset state
        this.expandedNodes.clear();
        this.visibleNodes.clear();
        this.visibleEdges.clear();
        this.activePath = [];
    },
    
    /**
     * Render with progressive expansion
     */
    render(startNodes, filters = {}) {
        this.currentFilters = filters;
        
        console.log(`Rendering ${startNodes.length} starting nodes`);
        
        const g = this.svg.select('.main-group');
        g.selectAll('*').remove();
        
        // Initialize visible nodes if empty
        if (this.visibleNodes.size === 0) {
            startNodes.forEach(node => {
                this.visibleNodes.add(node.id);
            });
        }
        
        // Collect all visible nodes and edges
        const { nodes, edges } = this.collectVisibleElements();
        
        console.log(`Visible: ${nodes.length} nodes, ${edges.length} edges`);
        
        // Render
        this.renderTimelineLayout(g, nodes, edges, filters);
        
        // Update statistics
        this.updateStatistics(nodes, edges);
        
        // Update breadcrumb
        this.updateBreadcrumb();
    },
    
    /**
     * Collect all visible nodes and edges
     */
    collectVisibleElements() {
        const nodes = [];
        const edges = [];
        
        // Get all visible nodes
        this.visibleNodes.forEach(nodeId => {
            const node = AdaptedDataLoader.getEnrichedNode(nodeId);
            if (node) {
                nodes.push(node);
            }
        });
        
        // Get edges between visible nodes
        this.visibleNodes.forEach(nodeId => {
            const outgoingEdges = AdaptedDataLoader.getOutgoingEdges(nodeId);
            outgoingEdges.forEach(edge => {
                if (this.visibleNodes.has(edge.target_id)) {
                    edges.push(edge);
                }
            });
        });
        
        return { nodes, edges };
    },
    
    /**
     * Render timeline layout
     */
    renderTimelineLayout(g, nodes, edges, filters) {
        const yearRange = AdaptedDataLoader.yearRange;
        
        // Group nodes by year
        const nodesByYear = new Map();
        nodes.forEach(node => {
            if (!nodesByYear.has(node.year)) {
                nodesByYear.set(node.year, []);
            }
            nodesByYear.get(node.year).push(node);
        });
        
        // Calculate layout
        const xScale = d3.scaleLinear()
            .domain([yearRange[0], yearRange[1]])
            .range([150, this.width - 150]);
        
        const verticalSpacing = 80;
        const nodePositions = new Map();
        
        // Position nodes
        nodesByYear.forEach((yearNodes, year) => {
            const x = xScale(year);
            const startY = 100;
            
            yearNodes.forEach((node, idx) => {
                nodePositions.set(node.id, {
                    x: x,
                    y: startY + idx * verticalSpacing,
                    node: node
                });
            });
        });
        
        // Draw edges
        this.renderEdges(g, edges, nodePositions);
        
        // Draw nodes
        this.renderNodes(g, nodes, nodePositions, filters);
        
        // Draw year labels
        this.renderYearLabels(g, xScale);
    },
    
    /**
     * Render edges
     */
    renderEdges(g, edges, nodePositions) {
        const linksGroup = g.append('g').attr('class', 'links-group');
        
        edges.forEach(edge => {
            const source = nodePositions.get(edge.source_id);
            const target = nodePositions.get(edge.target_id);
            
            if (!source || !target) return;
            
            const isInPath = this.isEdgeInActivePath(edge);
            const isMutualBest = edge.is_mutual_best;
            
            linksGroup.append('path')
                .attr('class', 'chain-link')
                .attr('d', this.createCurvedPath(source.x, source.y, target.x, target.y, 0.3))
                .attr('stroke', () => {
                    if (isInPath) return '#e74c3c';
                    if (isMutualBest) return '#667eea';
                    return '#cbd5e0';
                })
                .attr('stroke-width', () => {
                    if (isInPath) return 3;
                    if (isMutualBest) return 2.5;
                    return Math.max(1, edge.jaccard * 5);
                })
                .attr('opacity', () => {
                    if (isInPath) return 1;
                    if (isMutualBest) return 0.8;
                    return 0.4;
                })
                .classed('path-highlight', isInPath)
                .on('mouseover', (event) => this.showEdgeTooltip(event, edge))
                .on('mouseout', () => this.hideTooltip());
        });
    },
    
    /**
     * Render nodes
     */
    renderNodes(g, nodes, nodePositions, filters) {
        const nodesGroup = g.append('g').attr('class', 'nodes-group');
        
        // Size scale
        const nodeSizeBy = filters.nodeSizeBy || 'degree';
        const sizeScale = this.createSizeScale(nodes, nodeSizeBy);
        
        nodes.forEach(node => {
            const pos = nodePositions.get(node.id);
            if (!pos) return;
            
            const isExpanded = this.expandedNodes.has(node.id);
            const hasOutgoing = (node.out_degree || 0) > 0;
            const isExpandable = hasOutgoing && !isExpanded;
            
            const nodeGroup = nodesGroup.append('g')
                .attr('class', `community-node ${isExpandable ? 'expandable-node' : ''} ${isExpanded ? 'expanded' : ''}`)
                .attr('transform', `translate(${pos.x}, ${pos.y})`)
                .attr('data-node-id', node.id);
            
            const radius = sizeScale(node);
            
            // Circle
            nodeGroup.append('circle')
                .attr('r', radius)
                .attr('fill', this.getNodeColor(node))
                .attr('stroke', isExpandable ? '#f39c12' : (isExpanded ? '#27ae60' : 'white'))
                .attr('stroke-width', isExpandable || isExpanded ? 3 : 2)
                .style('cursor', isExpandable ? 'pointer' : 'default');
            
            // Click handler
            if (isExpandable) {
                nodeGroup.on('click', (event) => {
                    event.stopPropagation();
                    this.expandNode(node.id);
                });
                
                // Expansion indicator
                nodeGroup.append('text')
                    .attr('class', 'expand-indicator')
                    .attr('x', radius + 5)
                    .attr('dy', '0.35em')
                    .attr('fill', '#f39c12')
                    .attr('font-weight', 'bold')
                    .text('+')
                    .style('pointer-events', 'none');
            }
            
            // Right-click for details
            nodeGroup.on('contextmenu', (event) => {
                event.preventDefault();
                AdaptedApp.showNodeDetail(node.id);
            });
            
            // Hover
            nodeGroup.on('mouseover', (event) => {
                this.showNodeTooltip(event, node, isExpandable, isExpanded);
            })
            .on('mouseout', () => {
                this.hideTooltip();
            });
            
            // Label
            if (radius > 8) {
                nodeGroup.append('text')
                    .attr('class', 'node-label')
                    .attr('dy', 4)
                    .attr('font-size', '10px')
                    .text(node.communityId);
            }
        });
    },
    
    /**
     * Create size scale based on attribute
     */
    createSizeScale(nodes, sizeBy) {
        if (sizeBy === 'constant') {
            return () => 12;
        }
        
        const values = nodes.map(n => {
            if (sizeBy === 'degree') {
                return (n.out_degree || 0) + (n.in_degree || 0);
            } else if (sizeBy === 'size') {
                return n.size || 10;
            }
            return 10;
        });
        
        return d3.scaleSqrt()
            .domain([d3.min(values), d3.max(values)])
            .range([8, 30]);
    },
    
    /**
     * Get node color
     */
    getNodeColor(node) {
        const degree = (node.out_degree || 0) + (node.in_degree || 0);
        
        if (this.activePath.includes(node.id)) {
            return '#e74c3c';
        }
        
        // Color by degree
        return d3.interpolateBlues(Math.min(degree / 20, 1));
    },
    
    /**
     * Expand a node to show its targets
     */
    expandNode(nodeId) {
        console.log(`Expanding node: ${nodeId}`);
        
        // Mark as expanded
        this.expandedNodes.add(nodeId);
        
        // Add to active path
        if (!this.activePath.includes(nodeId)) {
            this.activePath.push(nodeId);
        }
        
        // Get outgoing edges
        const edges = AdaptedDataLoader.getOutgoingEdges(nodeId);
        
        // Add target nodes to visible set
        edges.forEach(edge => {
            this.visibleNodes.add(edge.target_id);
        });
        
        console.log(`Now visible: ${this.visibleNodes.size} nodes`);
        
        // Re-render
        this.render([], this.currentFilters);
    },
    
    /**
     * Collapse a node
     */
    collapseNode(nodeId) {
        console.log(`Collapsing node: ${nodeId}`);
        
        this.expandedNodes.delete(nodeId);
        
        // Remove from active path
        const pathIdx = this.activePath.indexOf(nodeId);
        if (pathIdx >= 0) {
            this.activePath.splice(pathIdx);
        }
        
        // Find and hide orphaned nodes
        this.removeOrphanedNodes();
        
        // Re-render
        this.render([], this.currentFilters);
    },
    
    /**
     * Remove nodes that are no longer reachable
     */
    removeOrphanedNodes() {
        const reachable = new Set();
        
        // BFS from all starting nodes
        const queue = [];
        this.visibleNodes.forEach(nodeId => {
            const node = AdaptedDataLoader.nodesById.get(nodeId);
            if (node && node.in_degree === 0) {
                queue.push(nodeId);
                reachable.add(nodeId);
            }
        });
        
        while (queue.length > 0) {
            const nodeId = queue.shift();
            
            if (this.expandedNodes.has(nodeId)) {
                const edges = AdaptedDataLoader.getOutgoingEdges(nodeId);
                edges.forEach(edge => {
                    if (!reachable.has(edge.target_id)) {
                        reachable.add(edge.target_id);
                        queue.push(edge.target_id);
                    }
                });
            }
        }
        
        // Remove unreachable nodes
        this.visibleNodes = reachable;
    },
    
    /**
     * Collapse all
     */
    collapseAll() {
        this.expandedNodes.clear();
        this.activePath = [];
        
        // Keep only starting nodes
        const startNodes = [];
        this.visibleNodes.forEach(nodeId => {
            const node = AdaptedDataLoader.nodesById.get(nodeId);
            if (node && node.in_degree === 0) {
                startNodes.push(nodeId);
            }
        });
        
        this.visibleNodes = new Set(startNodes);
        
        this.render([], this.currentFilters);
    },
    
    /**
     * Expand all
     */
    expandAll() {
        const maxExpansions = 1000;
        let expansions = 0;
        
        const toExpand = Array.from(this.visibleNodes);
        
        toExpand.forEach(nodeId => {
            if (expansions >= maxExpansions) return;
            
            const node = AdaptedDataLoader.nodesById.get(nodeId);
            if (node && node.out_degree > 0) {
                this.expandedNodes.add(nodeId);
                
                const edges = AdaptedDataLoader.getOutgoingEdges(nodeId);
                edges.forEach(edge => {
                    this.visibleNodes.add(edge.target_id);
                });
                
                expansions++;
            }
        });
        
        this.render([], this.currentFilters);
    },
    
    /**
     * Check if edge is in active path
     */
    isEdgeInActivePath(edge) {
        const sourceIdx = this.activePath.indexOf(edge.source_id);
        const targetIdx = this.activePath.indexOf(edge.target_id);
        
        return sourceIdx >= 0 && targetIdx === sourceIdx + 1;
    },
    
    /**
     * Create curved path
     */
    createCurvedPath(x1, y1, x2, y2, curveFactor) {
        const dx = x2 - x1;
        const dy = y2 - y1;
        const dr = Math.sqrt(dx * dx + dy * dy) * curveFactor;
        
        return `M ${x1},${y1} Q ${(x1 + x2) / 2},${y1 - dr} ${x2},${y2}`;
    },
    
    /**
     * Show tooltips
     */
    showNodeTooltip(event, node, isExpandable, isExpanded) {
        const tooltip = d3.select('body').append('div')
            .attr('class', 'tooltip')
            .style('position', 'absolute')
            .style('background', 'rgba(44, 62, 80, 0.95)')
            .style('color', 'white')
            .style('padding', '12px 15px')
            .style('border-radius', '8px')
            .style('font-size', '12px')
            .style('pointer-events', 'none')
            .style('z-index', '10000');
        
        let statusText = '';
        if (isExpandable) {
            statusText = `🔍 Click to expand (${node.out_degree} connections)`;
        } else if (isExpanded) {
            statusText = '✅ Expanded';
        } else {
            statusText = '🏁 No outgoing connections';
        }
        
        const html = `
            <strong>Year ${node.year} - Community ${node.communityId}</strong><br>
            Out-degree: ${node.out_degree || 0}<br>
            In-degree: ${node.in_degree || 0}<br>
            ${statusText}<br>
            <em style="color: #95a5a6;">Right-click for details</em>
        `;
        
        tooltip.html(html)
            .style('left', (event.pageX + 15) + 'px')
            .style('top', (event.pageY - 30) + 'px')
            .style('opacity', 1);
    },
    
    showEdgeTooltip(event, edge) {
        const tooltip = d3.select('body').append('div')
            .attr('class', 'tooltip')
            .style('position', 'absolute')
            .style('background', 'rgba(44, 62, 80, 0.95)')
            .style('color', 'white')
            .style('padding', '12px 15px')
            .style('border-radius', '8px')
            .style('font-size', '12px')
            .style('pointer-events', 'none')
            .style('z-index', '10000');
        
        const html = `
            <strong>Connection</strong><br>
            Jaccard: ${edge.jaccard.toFixed(4)}<br>
            Retention Forward: ${edge.retention_forward.toFixed(4)}<br>
            Overlap Size: ${edge.overlap_size}<br>
            ${edge.is_mutual_best ? '<em style="color: #27ae60;">⭐ Mutual Best</em>' : ''}
        `;
        
        tooltip.html(html)
            .style('left', (event.pageX + 15) + 'px')
            .style('top', (event.pageY - 30) + 'px')
            .style('opacity', 1);
    },
    
    hideTooltip() {
        d3.selectAll('.tooltip').remove();
    },
    
    /**
     * Render year labels
     */
    renderYearLabels(g, xScale) {
        const years = AdaptedDataLoader.years;
        
        years.forEach(year => {
            if (year % 5 === 0) {
                g.append('text')
                    .attr('class', 'year-label')
                    .attr('x', xScale(year))
                    .attr('y', 50)
                    .attr('text-anchor', 'middle')
                    .attr('fill', '#667eea')
                    .attr('font-weight', '700')
                    .text(year);
            }
        });
    },
    
    /**
     * Update statistics
     */
    updateStatistics(nodes, edges) {
        document.getElementById('visibleNodes').textContent = nodes.length;
        
        const html = `
            <div class="stat-row">
                <span class="stat-label">Total Edges:</span>
                <span class="stat-value">${edges.length}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Expanded:</span>
                <span class="stat-value">${this.expandedNodes.size}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Path Length:</span>
                <span class="stat-value">${this.activePath.length}</span>
            </div>
        `;
        
        document.getElementById('statsContent').innerHTML = html;
    },
    
    /**
     * Update breadcrumb
     */
    updateBreadcrumb() {
        const breadcrumb = document.getElementById('breadcrumb');
        const content = document.getElementById('breadcrumbContent');
        
        if (this.activePath.length === 0) {
            breadcrumb.classList.remove('active');
            return;
        }
        
        breadcrumb.classList.add('active');
        
        let html = '';
        this.activePath.forEach((nodeId, idx) => {
            const node = AdaptedDataLoader.nodesById.get(nodeId);
            if (node) {
                html += `<span class="breadcrumb-item ${idx === this.activePath.length - 1 ? 'active-year' : ''}">${node.year}:${node.communityId}</span>`;
                
                if (idx < this.activePath.length - 1) {
                    html += '<span class="breadcrumb-arrow">→</span>';
                }
            }
        });
        
        content.innerHTML = html;
    },
    
    clearPath() {
        this.activePath = [];
        this.updateBreadcrumb();
        this.render([], this.currentFilters);
    },
    
    /**
     * View controls
     */
    fitToView() {
        const g = this.svg.select('.main-group');
        const bounds = g.node().getBBox();
        
        const fullWidth = this.width;
        const fullHeight = this.height - 40;
        const width = bounds.width;
        const height = bounds.height;
        
        if (width === 0 || height === 0) return;
        
        const midX = bounds.x + width / 2;
        const midY = bounds.y + height / 2;
        
        const scale = 0.9 / Math.max(width / fullWidth, height / fullHeight);
        const translate = [
            fullWidth / 2 - scale * midX,
            fullHeight / 2 - scale * midY
        ];
        
        this.svg.transition()
            .duration(750)
            .call(this.zoom.transform, d3.zoomIdentity
                .translate(translate[0], translate[1])
                .scale(scale));
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
