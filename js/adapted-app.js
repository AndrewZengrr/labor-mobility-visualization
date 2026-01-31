// Adapted App Controller for New Network Format
const AdaptedApp = {
    networkDataLoaded: false,
    attributesDataLoaded: false,
    currentFilters: {
        startYear: 'all',
        minDegree: 0,
        maxNodes: 50,
        nodeSizeBy: 'degree'
    },
    
    /**
     * Initialize application
     */
    init() {
        console.log('Initializing Adapted Evolution App...');
        this.setupEventListeners();
    },
    
    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Network data upload
        document.getElementById('networkFileInput').addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                this.loadNetworkData(file);
            }
        });
        
        // Attributes upload
        document.getElementById('attributesFileInput').addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                this.loadAttributesData(file);
            }
        });
    },
    
    /**
     * Load network data
     */
    loadNetworkData(file) {
        const statusDiv = document.getElementById('networkUploadStatus');
        statusDiv.textContent = 'Loading...';
        
        AdaptedDataLoader.loadNetworkData(file, (success) => {
            if (success) {
                this.networkDataLoaded = true;
                statusDiv.textContent = `✓ Loaded: ${file.name} (${AdaptedDataLoader.networkData.nodes.length} nodes, ${AdaptedDataLoader.networkData.links.length} links)`;
                
                // Enable attributes upload
                const attributesSection = document.getElementById('attributesUploadSection');
                attributesSection.style.opacity = '1';
                attributesSection.style.pointerEvents = 'auto';
                
                // Show visualization
                setTimeout(() => {
                    this.showMainVisualization();
                }, 500);
            } else {
                statusDiv.textContent = '✗ Failed to load file';
                statusDiv.style.color = '#e74c3c';
            }
        });
    },
    
    /**
     * Load attributes data
     */
    loadAttributesData(file) {
        const statusDiv = document.getElementById('attributesUploadStatus');
        statusDiv.textContent = 'Loading...';
        
        AdaptedDataLoader.loadAttributesData(file, (success) => {
            if (success) {
                this.attributesDataLoaded = true;
                statusDiv.textContent = `✓ Loaded: ${file.name} (${AdaptedDataLoader.attributesData.length} records)`;
                
                alert('✅ Community attributes loaded!\n\nRight-click any node to see detailed attributes.');
            } else {
                statusDiv.textContent = '✗ Failed to load file';
                statusDiv.style.color = '#e74c3c';
            }
        });
    },
    
    /**
     * Show main visualization
     */
    showMainVisualization() {
        // Hide upload
        document.getElementById('uploadSection').style.display = 'none';
        
        // Show main viz
        document.getElementById('mainViz').style.display = 'block';
        
        // Populate filters
        this.populateYearFilter();
        
        // Initialize visualizer
        AdaptedVisualizer.init();
        
        // Apply filters and render
        this.applyFilters();
        
        // Fit to view
        setTimeout(() => {
            AdaptedVisualizer.fitToView();
        }, 500);
        
        // Show instructions
        setTimeout(() => {
            this.showInstructions();
        }, 800);
    },
    
    /**
     * Show instructions
     */
    showInstructions() {
        const hasAttributes = this.attributesDataLoaded ? '\n✓ Community attributes loaded - see detailed info!' : '\n💡 Upload CSV for detailed community attributes';
        
        alert(`🎉 Progressive Evolution Network Explorer Ready!

📍 How to Use:
• Initially shows STARTING YEAR nodes (with no incoming connections)
• CLICK nodes with "+" to expand to connected nodes
• Build evolution paths by clicking through the network
• RIGHT-CLICK nodes for detailed information
• Use "Collapse All" to reset

💡 Network Structure:
• Orange border = Can expand (has outgoing connections)
• Green border = Already expanded  
• Red path = Your exploration trail
• Blue intensity = Total degree (connectivity)

🔍 Edge Types:
• Thick blue = Mutual best match
• Medium gray = Regular connection
• Thickness = Jaccard similarity

⚙️ Filters:
• Start Year: Show nodes from specific year
• Min Degree: Filter low-connectivity nodes
• Max Nodes: Limit display for performance${hasAttributes}`);
    },
    
    /**
     * Populate year filter
     */
    populateYearFilter() {
        const select = document.getElementById('startYearFilter');
        const years = AdaptedDataLoader.getAvailableYears();
        
        select.innerHTML = '<option value="all">All Years</option>';
        
        years.forEach(year => {
            const nodes = AdaptedDataLoader.getNodesByYear(year);
            const option = document.createElement('option');
            option.value = year;
            option.text = `${year} (${nodes.length} nodes)`;
            select.appendChild(option);
        });
    },
    
    /**
     * Apply filters
     */
    applyFilters() {
        // Get filter values
        const startYearValue = document.getElementById('startYearFilter').value;
        this.currentFilters.startYear = startYearValue === 'all' ? null : parseInt(startYearValue);
        this.currentFilters.minDegree = parseInt(document.getElementById('minDegree').value) || 0;
        this.currentFilters.maxNodes = parseInt(document.getElementById('maxNodes').value) || 50;
        this.currentFilters.nodeSizeBy = document.getElementById('nodeSizeBy').value;
        
        // Filter nodes
        const startNodes = AdaptedDataLoader.filterNodes(
            this.currentFilters.startYear,
            this.currentFilters.minDegree,
            this.currentFilters.maxNodes
        );
        
        // Reset state
        AdaptedVisualizer.expandedNodes.clear();
        AdaptedVisualizer.visibleNodes.clear();
        AdaptedVisualizer.activePath = [];
        
        // Set initial visible nodes
        startNodes.forEach(node => {
            AdaptedVisualizer.visibleNodes.add(node.id);
        });
        
        // Render
        AdaptedVisualizer.render(startNodes, this.currentFilters);
        
        console.log(`Applied filters: showing ${startNodes.length} starting nodes`);
    },
    
    /**
     * Show node detail panel
     */
    showNodeDetail(nodeId) {
        const node = AdaptedDataLoader.getEnrichedNode(nodeId);
        
        if (!node) {
            console.error('Node not found:', nodeId);
            return;
        }
        
        const panel = document.getElementById('communityPanel');
        const title = document.getElementById('panelTitle');
        const body = document.getElementById('panelBody');
        
        title.textContent = `Year ${node.year} - Community ${node.communityId}`;
        
        body.innerHTML = this.generateNodeDetailContent(node);
        
        panel.classList.add('active');
    },
    
    /**
     * Generate node detail content
     */
    generateNodeDetailContent(node) {
        let html = '';
        
        // Basic Info
        html += `
        <div class="info-section">
            <h4>📊 Basic Information</h4>
            <div class="info-grid">
                <div class="info-card">
                    <div class="info-card-label">Node ID</div>
                    <div class="info-card-value">${node.id}</div>
                </div>
                <div class="info-card">
                    <div class="info-card-label">Year</div>
                    <div class="info-card-value">${node.year}</div>
                </div>
                <div class="info-card">
                    <div class="info-card-label">Community</div>
                    <div class="info-card-value">${node.communityId}</div>
                </div>
                <div class="info-card">
                    <div class="info-card-label">Out-Degree</div>
                    <div class="info-card-value">${node.out_degree || 0}</div>
                </div>
                <div class="info-card">
                    <div class="info-card-label">In-Degree</div>
                    <div class="info-card-value">${node.in_degree || 0}</div>
                </div>
                <div class="info-card">
                    <div class="info-card-label">Total Degree</div>
                    <div class="info-card-value">${(node.out_degree || 0) + (node.in_degree || 0)}</div>
                </div>
            </div>
        </div>
        `;
        
        // Outgoing Connections
        const outgoingEdges = AdaptedDataLoader.getOutgoingEdges(node.id);
        if (outgoingEdges.length > 0) {
            html += `
            <div class="info-section">
                <h4>➡️ Outgoing Connections (${outgoingEdges.length})</h4>
                <ul class="attribute-list">
            `;
            
            // Sort by jaccard
            const sortedEdges = [...outgoingEdges].sort((a, b) => b.jaccard - a.jaccard);
            
            sortedEdges.slice(0, 10).forEach(edge => {
                const targetNode = AdaptedDataLoader.nodesById.get(edge.target_id);
                const targetLabel = targetNode ? `${targetNode.year}:${targetNode.communityId}` : edge.target_id;
                
                html += `
                    <li class="attribute-item">
                        <span class="attribute-name">${targetLabel}</span>
                        <span class="attribute-count">J: ${edge.jaccard.toFixed(3)}</span>
                        <span class="attribute-percentage">
                            ${edge.is_mutual_best ? '⭐' : ''}
                            ${edge.is_best_forward ? '🔝' : ''}
                        </span>
                        <div class="attribute-bar">
                            <div class="attribute-bar-fill" style="width: ${edge.jaccard * 100}%"></div>
                        </div>
                    </li>
                `;
            });
            
            html += `</ul></div>`;
        }
        
        // Enriched Attributes
        if (node.enrichedAttributes) {
            const attrs = node.enrichedAttributes;
            
            html += `
            <div class="info-section">
                <h4>🎯 Community Attributes</h4>
                <p style="color: #27ae60; font-weight: 600; margin-bottom: 15px;">
                    ✓ ${attrs.totalRecords} nodes | Total Workforce: ${attrs.totalWorkforce.toLocaleString()}
                </p>
            `;
            
            // Top States
            if (attrs.states && attrs.states.length > 0) {
                html += `
                <h4 style="font-size: 1rem; margin-top: 20px;">📍 Top States</h4>
                <ul class="attribute-list">
                    ${attrs.states.slice(0, 5).map(item => `
                        <li class="attribute-item">
                            <span class="attribute-name">${item.name}</span>
                            <span class="attribute-count">${item.count}</span>
                            <span class="attribute-percentage">${item.percentage}%</span>
                            <div class="attribute-bar">
                                <div class="attribute-bar-fill" style="width: ${item.percentage}%"></div>
                            </div>
                        </li>
                    `).join('')}
                </ul>
                `;
            }
            
            // Top Industries
            if (attrs.industries && attrs.industries.length > 0) {
                html += `
                <h4 style="font-size: 1rem; margin-top: 20px;">🏭 Top Industries</h4>
                <ul class="attribute-list">
                    ${attrs.industries.slice(0, 5).map(item => `
                        <li class="attribute-item">
                            <span class="attribute-name">${item.name}</span>
                            <span class="attribute-count">${item.count}</span>
                            <span class="attribute-percentage">${item.percentage}%</span>
                            <div class="attribute-bar">
                                <div class="attribute-bar-fill" style="width: ${item.percentage}%"></div>
                            </div>
                        </li>
                    `).join('')}
                </ul>
                `;
            }
            
            // Top Metros
            if (attrs.metros && attrs.metros.length > 0) {
                html += `
                <h4 style="font-size: 1rem; margin-top: 20px;">🏙️ Top Metro Areas</h4>
                <ul class="attribute-list">
                    ${attrs.metros.slice(0, 5).map(item => `
                        <li class="attribute-item">
                            <span class="attribute-name">${item.name}</span>
                            <span class="attribute-count">${item.count}</span>
                            <span class="attribute-percentage">${item.percentage}%</span>
                            <div class="attribute-bar">
                                <div class="attribute-bar-fill" style="width: ${item.percentage}%"></div>
                            </div>
                        </li>
                    `).join('')}
                </ul>
                `;
            }
            
            html += `</div>`;
        } else if (this.attributesDataLoaded) {
            html += `
            <div class="info-section">
                <h4>⚠️ No Matching Attributes</h4>
                <p style="color: #95a5a6;">
                    No attribute data found for this community.<br>
                    Check if the community ID matches the CSV data.
                </p>
            </div>
            `;
        }
        
        return html;
    },
    
    /**
     * Close detail panel
     */
    closeDetailPanel() {
        document.getElementById('communityPanel').classList.remove('active');
    },
    
    /**
     * Control functions
     */
    collapseAll() {
        AdaptedVisualizer.collapseAll();
    },
    
    expandAll() {
        if (confirm('Expand all reachable nodes? This may take a moment for large networks.')) {
            AdaptedVisualizer.expandAll();
        }
    },
    
    clearPath() {
        AdaptedVisualizer.clearPath();
    },
    
    toggleSidebar() {
        const sidebar = document.getElementById('chainListSidebar');
        sidebar.classList.toggle('active');
    },
    
    getCurrentNodeSizeBy() {
        return this.currentFilters.nodeSizeBy;
    },
    
    /**
     * Zoom controls
     */
    zoomIn() {
        AdaptedVisualizer.zoomIn();
    },
    
    zoomOut() {
        AdaptedVisualizer.zoomOut();
    },
    
    resetZoom() {
        AdaptedVisualizer.resetZoom();
    },
    
    fitToView() {
        AdaptedVisualizer.fitToView();
    }
};

// Initialize when DOM ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing Adapted Evolution App...');
    AdaptedApp.init();
});
