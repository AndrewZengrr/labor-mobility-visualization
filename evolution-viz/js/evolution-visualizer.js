// Evolution Chain Visualizer
const EvolutionVisualizer = {
    svg: null,
    zoom: null,
    width: 0,
    height: 0,
    currentLayout: 'timeline',
    displayedChains: [],
    
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
    },
    
    /**
     * Render chains with specified layout
     */
    render(chains, layoutMode = 'timeline') {
        this.displayedChains = chains;
        this.currentLayout = layoutMode;
        
        console.log(`Rendering ${chains.length} chains in ${layoutMode} layout`);
        
        const g = this.svg.select('.main-group');
        g.selectAll('*').remove();
        
        switch (layoutMode) {
            case 'timeline':
                this.renderTimelineLayout(g, chains);
                break;
            case 'vertical':
                this.renderVerticalLayout(g, chains);
                break;
            case 'force':
                this.renderForceLayout(g, chains);
                break;
        }
        
        // Render year axis
        this.renderYearAxis();
    },
    
    /**
     * Timeline layout - horizontal time axis, chains stacked vertically
     */
    renderTimelineLayout(g, chains) {
        const config = EvolutionConfig.layout.timeline;
        const yearRange = EvolutionDataLoader.yearRange;
        const years = d3.range(yearRange[0], yearRange[1] + 1);
        
        // Calculate positions
        const xScale = d3.scaleLinear()
            .domain([yearRange[0], yearRange[1]])
            .range([100, this.width - 100]);
        
        const chainPositions = chains.map((chain, index) => ({
            chain,
            y: 50 + index * config.chainSpacing
        }));
        
        // Draw each chain
        chainPositions.forEach(({chain, y}) => {
            const chainGroup = g.append('g')
                .attr('class', 'chain-group')
                .attr('data-chain-id', chain.id);
            
            // Draw links between communities
            for (let i = 0; i < chain.communities.length - 1; i++) {
                const comm1 = chain.communities[i];
                const comm2 = chain.communities[i + 1];
                
                const x1 = xScale(comm1.year);
                const x2 = xScale(comm2.year);
                
                chainGroup.append('path')
                    .attr('class', 'chain-link')
                    .attr('d', this.createCurvedPath(x1, y, x2, y, config.linkCurve))
                    .attr('stroke', EvolutionConfig.getChainColor(chain.length))
                    .on('mouseover', () => this.highlightChain(chain.id))
                    .on('mouseout', () => this.unhighlightChain(chain.id));
            }
            
            // Draw community nodes
            chain.communities.forEach(comm => {
                const x = xScale(comm.year);
                const radius = EvolutionConfig.getNodeRadius(
                    comm.size,
                    EvolutionDataLoader.statistics.size.min,
                    EvolutionDataLoader.statistics.size.max
                );
                
                const nodeGroup = chainGroup.append('g')
                    .attr('class', 'community-node')
                    .attr('transform', `translate(${x}, ${y})`)
                    .attr('data-year', comm.year)
                    .attr('data-comm-id', comm.communityId);
                
                nodeGroup.append('circle')
                    .attr('r', radius)
                    .attr('fill', EvolutionConfig.getChainColor(chain.length))
                    .on('click', (event) => {
                        event.stopPropagation();
                        EvolutionApp.showCommunityDetail(chain.id, comm.year);
                    })
                    .on('mouseover', (event) => {
                        this.showNodeTooltip(event, chain, comm);
                        this.highlightChain(chain.id);
                    })
                    .on('mouseout', () => {
                        this.hideNodeTooltip();
                        this.unhighlightChain(chain.id);
                    });
                
                // Node label
                if (radius > 10) {
                    nodeGroup.append('text')
                        .attr('class', 'node-label')
                        .attr('dy', 4)
                        .text(comm.year);
                }
            });
            
            // Chain ID label
            const firstComm = chain.communities[0];
            if (firstComm) {
                chainGroup.append('text')
                    .attr('class', 'chain-label')
                    .attr('x', xScale(firstComm.year) - 10)
                    .attr('y', y)
                    .attr('text-anchor', 'end')
                    .text(chain.id);
            }
        });
    },
    
    /**
     * Vertical lanes layout - each chain gets a vertical lane
     */
    renderVerticalLayout(g, chains) {
        const config = EvolutionConfig.layout.vertical;
        const yearRange = EvolutionDataLoader.yearRange;
        
        const yScale = d3.scaleLinear()
            .domain([yearRange[0], yearRange[1]])
            .range([50, this.height - 100]);
        
        chains.forEach((chain, index) => {
            const x = 100 + index * config.laneWidth;
            
            const chainGroup = g.append('g')
                .attr('class', 'chain-group')
                .attr('data-chain-id', chain.id);
            
            // Draw links
            for (let i = 0; i < chain.communities.length - 1; i++) {
                const comm1 = chain.communities[i];
                const comm2 = chain.communities[i + 1];
                
                const y1 = yScale(comm1.year);
                const y2 = yScale(comm2.year);
                
                chainGroup.append('line')
                    .attr('class', 'chain-link')
                    .attr('x1', x)
                    .attr('y1', y1)
                    .attr('x2', x)
                    .attr('y2', y2)
                    .attr('stroke', EvolutionConfig.getChainColor(chain.length))
                    .on('mouseover', () => this.highlightChain(chain.id))
                    .on('mouseout', () => this.unhighlightChain(chain.id));
            }
            
            // Draw nodes
            chain.communities.forEach(comm => {
                const y = yScale(comm.year);
                const radius = config.nodeRadius;
                
                const nodeGroup = chainGroup.append('g')
                    .attr('class', 'community-node')
                    .attr('transform', `translate(${x}, ${y})`);
                
                nodeGroup.append('circle')
                    .attr('r', radius)
                    .attr('fill', EvolutionConfig.getChainColor(chain.length))
                    .on('click', () => EvolutionApp.showCommunityDetail(chain.id, comm.year))
                    .on('mouseover', (event) => {
                        this.showNodeTooltip(event, chain, comm);
                        this.highlightChain(chain.id);
                    })
                    .on('mouseout', () => {
                        this.hideNodeTooltip();
                        this.unhighlightChain(chain.id);
                    });
            });
            
            // Chain label
            chainGroup.append('text')
                .attr('class', 'chain-label')
                .attr('x', x)
                .attr('y', 30)
                .attr('text-anchor', 'middle')
                .text(chain.id);
        });
    },
    
    /**
     * Force-directed layout
     */
    renderForceLayout(g, chains) {
        const config = EvolutionConfig.layout.force;
        
        // Prepare nodes and links
        const nodes = [];
        const links = [];
        
        chains.forEach(chain => {
            chain.communities.forEach((comm, index) => {
                nodes.push({
                    id: `${chain.id}-${comm.year}`,
                    chainId: chain.id,
                    year: comm.year,
                    community: comm,
                    chainLength: chain.length
                });
                
                if (index < chain.communities.length - 1) {
                    const nextComm = chain.communities[index + 1];
                    links.push({
                        source: `${chain.id}-${comm.year}`,
                        target: `${chain.id}-${nextComm.year}`,
                        chainId: chain.id
                    });
                }
            });
        });
        
        // Create force simulation
        const simulation = d3.forceSimulation(nodes)
            .force('link', d3.forceLink(links).id(d => d.id).distance(config.linkDistance))
            .force('charge', d3.forceManyBody().strength(config.chargeStrength))
            .force('center', d3.forceCenter(this.width / 2, this.height / 2))
            .force('collision', d3.forceCollide().radius(config.collisionRadius));
        
        // Draw links
        const link = g.append('g')
            .selectAll('.chain-link')
            .data(links)
            .enter().append('line')
            .attr('class', 'chain-link')
            .attr('stroke', d => {
                const chain = EvolutionDataLoader.getChainById(d.chainId);
                return EvolutionConfig.getChainColor(chain.length);
            });
        
        // Draw nodes
        const node = g.append('g')
            .selectAll('.community-node')
            .data(nodes)
            .enter().append('g')
            .attr('class', 'community-node')
            .call(d3.drag()
                .on('start', dragstarted)
                .on('drag', dragged)
                .on('end', dragended));
        
        node.append('circle')
            .attr('r', config.collisionRadius / 2)
            .attr('fill', d => EvolutionConfig.getChainColor(d.chainLength))
            .on('click', d => {
                const chain = EvolutionDataLoader.getChainById(d.chainId);
                EvolutionApp.showCommunityDetail(d.chainId, d.year);
            })
            .on('mouseover', (event, d) => {
                const chain = EvolutionDataLoader.getChainById(d.chainId);
                this.showNodeTooltip(event, chain, d.community);
            })
            .on('mouseout', () => {
                this.hideNodeTooltip();
            });
        
        // Update positions on tick
        simulation.on('tick', () => {
            link
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);
            
            node.attr('transform', d => `translate(${d.x}, ${d.y})`);
        });
        
        function dragstarted(event) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            event.subject.fx = event.subject.x;
            event.subject.fy = event.subject.y;
        }
        
        function dragged(event) {
            event.subject.fx = event.x;
            event.subject.fy = event.y;
        }
        
        function dragended(event) {
            if (!event.active) simulation.alphaTarget(0);
            event.subject.fx = null;
            event.subject.fy = null;
        }
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
     * Highlight chain
     */
    highlightChain(chainId) {
        this.svg.selectAll('.chain-group')
            .classed('highlighted', d => false);
        
        this.svg.select(`.chain-group[data-chain-id="${chainId}"]`)
            .classed('highlighted', true)
            .raise();
        
        this.svg.selectAll(`.chain-group[data-chain-id="${chainId}"] .chain-link`)
            .classed('highlighted', true);
        
        this.svg.selectAll(`.chain-group[data-chain-id="${chainId}"] .community-node`)
            .classed('highlighted', true);
    },
    
    /**
     * Unhighlight chain
     */
    unhighlightChain(chainId) {
        this.svg.selectAll('.chain-link').classed('highlighted', false);
        this.svg.selectAll('.community-node').classed('highlighted', false);
    },
    
    /**
     * Show node tooltip
     */
    showNodeTooltip(event, chain, community) {
        const tooltip = d3.select('body').append('div')
            .attr('class', 'node-tooltip')
            .style('position', 'absolute')
            .style('background', 'rgba(44, 62, 80, 0.95)')
            .style('color', 'white')
            .style('padding', '12px 15px')
            .style('border-radius', '8px')
            .style('font-size', '12px')
            .style('pointer-events', 'none')
            .style('z-index', '10000')
            .style('box-shadow', '0 4px 12px rgba(0,0,0,0.3)');
        
        const html = `
            <strong>Chain ${chain.id}</strong><br>
            <strong>Year:</strong> ${community.year}<br>
            <strong>Community:</strong> ${community.communityId}<br>
            <strong>Size:</strong> ${community.size} companies<br>
            <strong>Type:</strong> ${community.type}<br>
            <em>Click to view details</em>
        `;
        
        tooltip.html(html)
            .style('left', (event.pageX + 15) + 'px')
            .style('top', (event.pageY - 30) + 'px')
            .style('opacity', 1);
    },
    
    /**
     * Hide node tooltip
     */
    hideNodeTooltip() {
        d3.selectAll('.node-tooltip').remove();
    },
    
    /**
     * Render year axis
     */
    renderYearAxis() {
        const yearRange = EvolutionDataLoader.yearRange;
        const years = d3.range(yearRange[0], yearRange[1] + 1);
        
        const axisDiv = d3.select('#yearAxis');
        axisDiv.selectAll('*').remove();
        
        // Show every 5th year to avoid crowding
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
     * Fit view to content
     */
    fitToView() {
        const g = this.svg.select('.main-group');
        const bounds = g.node().getBBox();
        
        const fullWidth = this.width;
        const fullHeight = this.height - 40; // Account for year axis
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
