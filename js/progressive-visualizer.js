// Progressive Evolution Visualizer - Click to Expand Year by Year
const ProgressiveVisualizer = {
    svg: null,
    zoom: null,
    width: 0,
    height: 0,
    displayedChains: [],
    expandedNodes: new Set(), // Track which nodes have been expanded
    visibleNodes: new Set(),   // Track which nodes are currently visible
    activePath: [],            // Track the current exploration path
    
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
        this.activePath = [];
    },
    
    /**
     * Render chains with progressive expansion
     */
    render(chains, nodeSizeBy = 'size') {
        this.displayedChains = chains;
        
        console.log(`Rendering ${chains.length} chains in progressive mode`);
        
        const g = this.svg.select('.main-group');
        g.selectAll('*').remove();
        
        // Show only starting year initially (or maintain current state)
        if (this.expandedNodes.size === 0) {
            this.initializeStartingNodes(chains);
        }
        
        // Render timeline layout
        this.renderTimelineLayout(g, chains, nodeSizeBy);
        
        // Update statistics
        this.updateStatistics();
        
        // Update breadcrumb
        this.updateBreadcrumb();
    },
    
    /**
     * Initialize starting nodes (first year of each chain)
     */
    initializeStartingNodes(chains) {
        chains.forEach(chain => {
            if (chain.communities.length > 0) {
                const firstCommunity = chain.communities[0];
                const nodeKey = `${chain.id}-${firstCommunity.year}`;
                this.visibleNodes.add(nodeKey);
            }
        });
        
        console.log(`Initialized ${this.visibleNodes.size} starting nodes`);
    },
    
    /**
     * Render timeline layout
     */
    renderTimelineLayout(g, chains, nodeSizeBy) {
        const yearRange = ProgressiveDataLoader.yearRange;
        const years = d3.range(yearRange[0], yearRange[1] + 1);
        
        // Calculate x scale
        const xScale = d3.scaleLinear()
            .domain([yearRange[0], yearRange[1]])
            .range([150, this.width - 150]);
        
        // Calculate y positions for chains
        const chainSpacing = 100;
        const chainPositions = new Map();
        
        chains.forEach((chain, index) => {
            chainPositions.set(chain.id, {
                baseY: 100 + index * chainSpacing,
                chain: chain
            });
        });
        
        // Draw links for visible connections
        this.renderLinks(g, chains, chainPositions, xScale);
        
        // Draw nodes
        this.renderNodes(g, chains, chainPositions, xScale, nodeSizeBy);
        
        // Draw year axis
        this.renderYearAxis(years);
    },
    
    /**
     * Render links between communities
     */
    renderLinks(g, chains, chainPositions, xScale) {
        const linksGroup = g.append('g').attr('class', 'links-group');
        
        chains.forEach(chain => {
            const chainPos = chainPositions.get(chain.id);
            const y = chainPos.baseY;
            
            for (let i = 0; i < chain.communities.length - 1; i++) {
                const comm1 = chain.communities[i];
                const comm2 = chain.communities[i + 1];
                
                const node1Key = `${chain.id}-${comm1.year}`;
                const node2Key = `${chain.id}-${comm2.year}`;
                
                // Only draw link if first node is visible
                if (this.visibleNodes.has(node1Key)) {
                    const x1 = xScale(comm1.year);
                    const x2 = xScale(comm2.year);
                    
                    const isNode2Visible = this.visibleNodes.has(node2Key);
                    const isExpanded = this.expandedNodes.has(node1Key);
                    
                    linksGroup.append('path')
                        .attr('class', 'chain-link')
                        .attr('d', this.createCurvedPath(x1, y, x2, y, 0.3))
                        .attr('stroke', () => {
                            if (this.isInActivePath(node1Key, node2Key)) {
                                return '#e74c3c';
                            }
                            return isNode2Visible ? '#667eea' : '#cbd5e0';
                        })
                        .attr('stroke-width', isNode2Visible ? 2.5 : 1.5)
                        .attr('opacity', isNode2Visible ? 0.8 : 0.3)
                        .attr('stroke-dasharray', isNode2Visible ? '0' : '5,5')
                        .classed('path-highlight', this.isInActivePath(node1Key, node2Key));
                }
            }
        });
    },
    
    /**
     * Render nodes
     */
    renderNodes(g, chains, chainPositions, xScale, nodeSizeBy) {
        const nodesGroup = g.append('g').attr('class', 'nodes-group');
        
        // Calculate size scale
        const sizes = [];
        chains.forEach(chain => {
            chain.communities.forEach(comm => {
                if (nodeSizeBy === 'size') {
                    sizes.push(comm.size);
                }
            });
        });
        
        const sizeScale = nodeSizeBy === 'size' 
            ? d3.scaleSqrt().domain([0, d3.max(sizes)]).range([8, 30])
            : () => 12;
        
        // Render each community node
        chains.forEach(chain => {
            const chainPos = chainPositions.get(chain.id);
            const y = chainPos.baseY;
            
            chain.communities.forEach((comm, idx) => {
                const nodeKey = `${chain.id}-${comm.year}`;
                const isVisible = this.visibleNodes.has(nodeKey);
                const isExpanded = this.expandedNodes.has(nodeKey);
                const hasNext = !comm.isEnd;
                const isExpandable = hasNext && isVisible && !isExpanded;
                
                if (!isVisible) return; // Skip invisible nodes
                
                const x = xScale(comm.year);
                const radius = sizeScale(comm.size);
                
                const nodeGroup = nodesGroup.append('g')
                    .attr('class', `community-node ${isExpandable ? 'expandable-node' : ''} ${isExpanded ? 'expanded' : ''}`)
                    .attr('transform', `translate(${x}, ${y})`)
                    .attr('data-chain-id', chain.id)
                    .attr('data-year', comm.year)
                    .attr('data-node-key', nodeKey);
                
                // Node circle
                nodeGroup.append('circle')
                    .attr('r', radius)
                    .attr('fill', () => {
                        if (this.activePath.includes(nodeKey)) {
                            return '#e74c3c';
                        }
                        return EvolutionConfig.getChainColor(chain.length);
                    })
                    .attr('stroke', isExpandable ? '#f39c12' : (isExpanded ? '#27ae60' : 'white'))
                    .attr('stroke-width', isExpandable ? 3 : 2)
                    .style('cursor', isExpandable ? 'pointer' : 'default');
                
                // Click handler for expansion
                if (isExpandable) {
                    nodeGroup.on('click', (event) => {
                        event.stopPropagation();
                        this.expandNode(chain.id, comm.year);
                    });
                    
                    // Add expansion indicator
                    nodeGroup.append('text')
                        .attr('class', 'expand-indicator')
                        .attr('x', radius + 5)
                        .attr('dy', '0.35em')
                        .text('+')
                        .style('cursor', 'pointer');
                }
                
                // Right-click for details
                nodeGroup.on('contextmenu', (event) => {
                    event.preventDefault();
                    ProgressiveApp.showCommunityDetail(chain.id, comm.year);
                });
                
                // Hover tooltip
                nodeGroup.on('mouseover', (event) => {
                    this.showNodeTooltip(event, chain, comm, isExpandable, isExpanded);
                })
                .on('mouseout', () => {
                    this.hideTooltip();
                });
                
                // Node label
                if (radius > 10) {
                    nodeGroup.append('text')
                        .attr('class', 'node-label')
                        .attr('dy', 4)
                        .text(comm.year);
                }
            });
        });
        
        // Add chain labels on the left
        chains.forEach(chain => {
            const chainPos = chainPositions.get(chain.id);
            const y = chainPos.baseY;
            
            if (chain.communities.length > 0) {
                const firstComm = chain.communities[0];
                const x = xScale(firstComm.year);
                
                g.append('text')
                    .attr('class', 'chain-label')
                    .attr('x', x - 60)
                    .attr('y', y)
                    .attr('dy', '0.35em')
                    .attr('text-anchor', 'end')
                    .attr('fill', '#667eea')
                    .attr('font-weight', '700')
                    .attr('font-size', '11px')
                    .text(chain.id);
            }
        });
    },
    
    /**
     * Expand a node to show next year
     */
    expandNode(chainId, year) {
        const nodeKey = `${chainId}-${year}`;
        
        // Mark as expanded
        this.expandedNodes.add(nodeKey);
        
        // Add to active path
        if (!this.activePath.includes(nodeKey)) {
            this.activePath.push(nodeKey);
        }
        
        // Find next year's node
        const chain = ProgressiveDataLoader.getChainById(chainId);
        if (!chain) return;
        
        const currentIdx = chain.communities.findIndex(c => c.year === year);
        if (currentIdx >= 0 && currentIdx < chain.communities.length - 1) {
            const nextComm = chain.communities[currentIdx + 1];
            const nextNodeKey = `${chainId}-${nextComm.year}`;
            
            // Make next node visible
            this.visibleNodes.add(nextNodeKey);
            
            console.log(`Expanded ${nodeKey} → showing ${nextNodeKey}`);
        }
        
        // Re-render
        this.render(this.displayedChains, ProgressiveApp.getCurrentNodeSizeBy());
    },
    
    /**
     * Collapse a node (hide subsequent nodes)
     */
    collapseNode(chainId, year) {
        const nodeKey = `${chainId}-${year}`;
        
        // Mark as not expanded
        this.expandedNodes.delete(nodeKey);
        
        // Remove from active path
        const pathIdx = this.activePath.indexOf(nodeKey);
        if (pathIdx >= 0) {
            this.activePath.splice(pathIdx);
        }
        
        // Hide subsequent nodes
        const chain = ProgressiveDataLoader.getChainById(chainId);
        if (!chain) return;
        
        const currentIdx = chain.communities.findIndex(c => c.year === year);
        if (currentIdx >= 0) {
            for (let i = currentIdx + 1; i < chain.communities.length; i++) {
                const comm = chain.communities[i];
                const nextNodeKey = `${chainId}-${comm.year}`;
                this.visibleNodes.delete(nextNodeKey);
                this.expandedNodes.delete(nextNodeKey);
            }
        }
        
        // Re-render
        this.render(this.displayedChains, ProgressiveApp.getCurrentNodeSizeBy());
    },
    
    /**
     * Collapse all nodes
     */
    collapseAll() {
        this.expandedNodes.clear();
        this.visibleNodes.clear();
        this.activePath = [];
        
        // Re-initialize starting nodes
        this.initializeStartingNodes(this.displayedChains);
        
        // Re-render
        this.render(this.displayedChains, ProgressiveApp.getCurrentNodeSizeBy());
    },
    
    /**
     * Expand all nodes
     */
    expandAll() {
        this.displayedChains.forEach(chain => {
            chain.communities.forEach(comm => {
                const nodeKey = `${chain.id}-${comm.year}`;
                this.visibleNodes.add(nodeKey);
                if (!comm.isEnd) {
                    this.expandedNodes.add(nodeKey);
                }
            });
        });
        
        // Re-render
        this.render(this.displayedChains, ProgressiveApp.getCurrentNodeSizeBy());
    },
    
    /**
     * Check if edge is in active path
     */
    isInActivePath(node1Key, node2Key) {
        const idx1 = this.activePath.indexOf(node1Key);
        const idx2 = this.activePath.indexOf(node2Key);
        
        return idx1 >= 0 && idx2 >= 0 && Math.abs(idx2 - idx1) === 1;
    },
    
    /**
     * Create curved path for links
     */
    createCurvedPath(x1, y1, x2, y2, curveFactor) {
        const dx = x2 - x1;
        const dy = y2 - y1;
        const dr = Math.sqrt(dx * dx + dy * dy) * curveFactor;
        
        return `M ${x1},${y1} Q ${(x1 + x2) / 2},${y1 - dr} ${x2},${y2}`;
    },
    
    /**
     * Show node tooltip
     */
    showNodeTooltip(event, chain, comm, isExpandable, isExpanded) {
        const tooltip = d3.select('body').append('div')
            .attr('class', 'tooltip')
            .style('position', 'absolute')
            .style('background', 'rgba(44, 62, 80, 0.95)')
            .style('color', 'white')
            .style('padding', '12px 15px')
            .style('border-radius', '8px')
            .style('font-size', '12px')
            .style('pointer-events', 'none')
            .style('z-index', '10000')
            .style('box-shadow', '0 4px 12px rgba(0,0,0,0.3)');
        
        let statusText = '';
        if (isExpandable) {
            statusText = '🔍 Click to expand next year';
        } else if (isExpanded) {
            statusText = '✅ Expanded';
        } else if (comm.isEnd) {
            statusText = '🏁 Chain end';
        }
        
        const html = `
            <strong>${chain.id} - Year ${comm.year}</strong><br>
            Community: ${comm.communityId}<br>
            Size: ${comm.size} nodes<br>
            Type: ${comm.type}<br>
            ${statusText ? `<em style="color: #81c8e8;">${statusText}</em><br>` : ''}
            <em style="color: #95a5a6;">Right-click for details</em>
        `;
        
        tooltip.html(html)
            .style('left', (event.pageX + 15) + 'px')
            .style('top', (event.pageY - 30) + 'px')
            .style('opacity', 1);
    },
    
    /**
     * Hide tooltip
     */
    hideTooltip() {
        d3.selectAll('.tooltip').remove();
    },
    
    /**
     * Render year axis
     */
    renderYearAxis(years) {
        const axisDiv = d3.select('#yearAxis');
        axisDiv.selectAll('*').remove();
        
        const displayYears = years.filter(y => y % 5 === 0);
        
        displayYears.forEach(year => {
            axisDiv.append('div')
                .style('display', 'inline-block')
                .style('flex', '1')
                .style('text-align', 'center')
                .text(year);
        });
    },
    
    /**
     * Update statistics
     */
    updateStatistics() {
        document.getElementById('visibleNodes').textContent = this.visibleNodes.size;
        
        const expandedCount = this.expandedNodes.size;
        const totalNodes = this.displayedChains.reduce((sum, c) => sum + c.communities.length, 0);
        
        const html = `
            <div class="stat-row">
                <span class="stat-label">Total Nodes:</span>
                <span class="stat-value">${totalNodes}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Expanded:</span>
                <span class="stat-value">${expandedCount}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Chains:</span>
                <span class="stat-value">${this.displayedChains.length}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Path Length:</span>
                <span class="stat-value">${this.activePath.length}</span>
            </div>
        `;
        
        document.getElementById('statsContent').innerHTML = html;
    },
    
    /**
     * Update breadcrumb navigation
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
        this.activePath.forEach((nodeKey, idx) => {
            const [chainId, year] = nodeKey.split('-');
            
            html += `<span class="breadcrumb-item ${idx === this.activePath.length - 1 ? 'active-year' : ''}">${chainId}: ${year}</span>`;
            
            if (idx < this.activePath.length - 1) {
                html += '<span class="breadcrumb-arrow">→</span>';
            }
        });
        
        content.innerHTML = html;
    },
    
    /**
     * Clear active path
     */
    clearPath() {
        this.activePath = [];
        this.updateBreadcrumb();
        this.render(this.displayedChains, ProgressiveApp.getCurrentNodeSizeBy());
    },
    
    /**
     * Fit view to content
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
