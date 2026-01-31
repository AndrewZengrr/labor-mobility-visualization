// Progressive Evolution Chain App Controller
const ProgressiveApp = {
    chainDataLoaded: false,
    attributesDataLoaded: false,
    currentFilters: {
        startYear: 'all',
        minLength: 1,
        maxChains: 20,
        nodeSizeBy: 'size'
    },
    
    /**
     * Initialize application
     */
    init() {
        console.log('Initializing Progressive Evolution App...');
        this.setupEventListeners();
    },
    
    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Chain data file upload
        document.getElementById('chainFileInput').addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                this.loadChainData(file);
            }
        });
        
        // Attributes file upload
        document.getElementById('attributesFileInput').addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                this.loadAttributesData(file);
            }
        });
    },
    
    /**
     * Load chain data
     */
    loadChainData(file) {
        const statusDiv = document.getElementById('chainUploadStatus');
        statusDiv.textContent = 'Loading...';
        
        ProgressiveDataLoader.loadChainData(file, (success) => {
            if (success) {
                this.chainDataLoaded = true;
                statusDiv.textContent = `✓ Loaded: ${file.name} (${ProgressiveDataLoader.processedChains.length} chains)`;
                
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
        
        ProgressiveDataLoader.loadAttributesData(file, (success) => {
            if (success) {
                this.attributesDataLoaded = true;
                statusDiv.textContent = `✓ Loaded: ${file.name}`;
                
                alert('✅ Community attributes loaded!\n\nRight-click any node to see enriched details with composition data.');
            } else {
                statusDiv.textContent = '✗ Failed to load file';
                statusDiv.style.color = '#e74c3c';
            }
        });
    },
    
    /**
     * Show main visualization interface
     */
    showMainVisualization() {
        // Hide upload section
        document.getElementById('uploadSection').style.display = 'none';
        
        // Show main visualization
        document.getElementById('mainViz').style.display = 'block';
        
        // Populate start year filter
        this.populateStartYearFilter();
        
        // Initialize visualizer
        ProgressiveVisualizer.init();
        
        // Apply initial filters and render
        this.applyFilters();
        
        // Render chain list
        this.renderChainList();
        
        // Fit to view
        setTimeout(() => {
            ProgressiveVisualizer.fitToView();
        }, 500);
        
        // Show instructions
        setTimeout(() => {
            alert(`🎉 Progressive Evolution Explorer Ready!

📍 How to Use:
• Initially shows only STARTING YEAR communities
• CLICK any node with "+" to expand to next year
• Build evolution paths by clicking through years
• RIGHT-CLICK nodes for detailed information
• Use "Collapse All" to reset and start over

💡 Tips:
• Orange border = Can expand
• Green border = Already expanded
• Red path = Your exploration trail
${this.attributesDataLoaded ? '\n✓ Community attributes loaded - see detailed compositions!' : '\n💡 Upload CSV for detailed attributes'}`);
        }, 800);
    },
    
    /**
     * Populate start year filter dropdown
     */
    populateStartYearFilter() {
        const select = document.getElementById('startYearFilter');
        const years = ProgressiveDataLoader.getStartYears();
        
        // Clear existing options (except "All")
        select.innerHTML = '<option value="all">All Start Years</option>';
        
        // Add year options
        years.forEach(year => {
            const count = ProgressiveDataLoader.statistics.startYearDistribution[year] || 0;
            const option = document.createElement('option');
            option.value = year;
            option.text = `${year} (${count} chains)`;
            select.appendChild(option);
        });
    },
    
    /**
     * Apply current filters and render
     */
    applyFilters() {
        // Get filter values
        this.currentFilters.startYear = document.getElementById('startYearFilter').value;
        this.currentFilters.minLength = parseInt(document.getElementById('minLength').value) || 1;
        this.currentFilters.maxChains = parseInt(document.getElementById('maxChains').value) || 20;
        this.currentFilters.nodeSizeBy = document.getElementById('nodeSizeBy').value;
        
        // Filter chains
        const filteredChains = ProgressiveDataLoader.filterChains(
            this.currentFilters.startYear,
            this.currentFilters.minLength,
            this.currentFilters.maxChains
        );
        
        // Render
        ProgressiveVisualizer.render(filteredChains, this.currentFilters.nodeSizeBy);
        
        // Update chain list
        this.renderChainList(filteredChains);
    },
    
    /**
     * Render chain list in sidebar
     */
    renderChainList(chains = null) {
        if (!chains) {
            chains = ProgressiveDataLoader.processedChains.slice(0, 50);
        }
        
        const listContent = document.getElementById('chainListContent');
        listContent.innerHTML = '';
        
        chains.forEach(chain => {
            const item = document.createElement('div');
            item.className = 'chain-item';
            item.dataset.chainId = chain.id;
            
            item.innerHTML = `
                <div class="chain-item-header">
                    <span class="chain-item-id">${chain.id}</span>
                    <span class="chain-item-length">${chain.length} years</span>
                </div>
                <div class="chain-item-info">
                    ${chain.startYear} - ${chain.endYear}<br>
                    Avg Size: ${chain.avgSize} | Score: ${chain.score.toFixed(3)}
                </div>
            `;
            
            item.addEventListener('click', () => {
                this.focusOnChain(chain.id);
            });
            
            listContent.appendChild(item);
        });
    },
    
    /**
     * Focus on a specific chain
     */
    focusOnChain(chainId) {
        // Highlight in list
        document.querySelectorAll('.chain-item').forEach(item => {
            item.classList.remove('selected');
        });
        
        const item = document.querySelector(`.chain-item[data-chain-id="${chainId}"]`);
        if (item) {
            item.classList.add('selected');
            item.scrollIntoView({behavior: 'smooth', block: 'nearest'});
        }
        
        // Highlight in visualization
        // (Could add zoom to chain here)
    },
    
    /**
     * Show community detail panel
     */
    showCommunityDetail(chainId, year) {
        const community = ProgressiveDataLoader.getEnrichedCommunityData(chainId, year);
        const chain = ProgressiveDataLoader.getChainById(chainId);
        
        if (!community || !chain) {
            console.error('Community not found');
            return;
        }
        
        const panel = document.getElementById('communityPanel');
        const title = document.getElementById('panelTitle');
        const body = document.getElementById('panelBody');
        
        title.textContent = `${chainId} - Year ${year} - Community ${community.communityId}`;
        
        body.innerHTML = this.generatePanelContent(chain, community);
        
        panel.classList.add('active');
    },
    
    /**
     * Generate detail panel content
     */
    generatePanelContent(chain, community) {
        const attrs = community.attributes;
        const composition = community.nodeComposition;
        const enriched = community.enrichedAttributes;
        
        let html = '';
        
        // Basic Info
        html += `
        <div class="info-section">
            <h4>📊 Basic Information</h4>
            <div class="info-grid">
                <div class="info-card">
                    <div class="info-card-label">Chain ID</div>
                    <div class="info-card-value">${chain.id}</div>
                </div>
                <div class="info-card">
                    <div class="info-card-label">Year</div>
                    <div class="info-card-value">${community.year}</div>
                </div>
                <div class="info-card">
                    <div class="info-card-label">Community ID</div>
                    <div class="info-card-value">${community.communityId}</div>
                </div>
                <div class="info-card">
                    <div class="info-card-label">Size</div>
                    <div class="info-card-value">${attrs.size || community.size || 0}</div>
                </div>
                <div class="info-card">
                    <div class="info-card-label">Type</div>
                    <div class="info-card-value">
                        <span class="type-badge ${composition.type}">${composition.type || 'normal'}</span>
                    </div>
                </div>
                <div class="info-card">
                    <div class="info-card-label">Position</div>
                    <div class="info-card-value">
                        ${community.isStart ? '🚀 Start' : (community.isEnd ? '🏁 End' : '🔄 Middle')}
                    </div>
                </div>
            </div>
        </div>
        `;
        
        // Node Composition
        if (composition && Object.keys(composition).length > 0) {
            html += `
            <div class="info-section">
                <h4>👥 Node Composition</h4>
                <div class="info-grid">
                    ${composition.core_node_ratio !== undefined ? `
                    <div class="info-card">
                        <div class="info-card-label">Core Nodes</div>
                        <div class="info-card-value">${(composition.core_node_ratio * 100).toFixed(1)}%</div>
                    </div>
                    ` : ''}
                    ${composition.new_node_ratio !== undefined ? `
                    <div class="info-card">
                        <div class="info-card-label">New Nodes</div>
                        <div class="info-card-value">${(composition.new_node_ratio * 100).toFixed(1)}%</div>
                    </div>
                    ` : ''}
                    ${composition.avg_node_weight !== undefined ? `
                    <div class="info-card">
                        <div class="info-card-label">Avg Weight</div>
                        <div class="info-card-value">${composition.avg_node_weight.toFixed(3)}</div>
                    </div>
                    ` : ''}
                </div>
            </div>
            `;
        }
        
        // Enriched Attributes (from CSV)
        if (enriched) {
            html += `
            <div class="info-section">
                <h4>🎯 Detailed Attributes (from CSV)</h4>
                <p style="color: #27ae60; font-weight: 600; margin-bottom: 15px;">
                    ✓ ${enriched.totalNodes} nodes with detailed attributes
                </p>
            `;
            
            // States
            if (enriched.states && enriched.states.length > 0) {
                html += `
                <h4 style="font-size: 1rem; margin-top: 20px;">📍 Top States</h4>
                <ul class="attribute-list">
                    ${enriched.states.slice(0, 5).map(item => `
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
            
            // Industries
            if (enriched.industries && enriched.industries.length > 0) {
                html += `
                <h4 style="font-size: 1rem; margin-top: 20px;">🏭 Top Industries</h4>
                <ul class="attribute-list">
                    ${enriched.industries.slice(0, 5).map(item => `
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
        }
        
        // Original Attributes from Chain JSON
        if (attrs.top3_states && attrs.top3_states.length > 0) {
            html += `
            <div class="info-section">
                <h4>📍 State Distribution (from Chain Data)</h4>
                <ul class="attribute-list">
                    ${attrs.top3_states.map(item => `
                        <li class="attribute-item">
                            <span class="attribute-name">${item.value}</span>
                            <span class="attribute-count">${item.count}</span>
                            <span class="attribute-percentage">${item.percentage}%</span>
                        </li>
                    `).join('')}
                </ul>
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
     * Collapse all nodes
     */
    collapseAll() {
        ProgressiveVisualizer.collapseAll();
    },
    
    /**
     * Expand all nodes
     */
    expandAll() {
        if (confirm('Expand all nodes? This will show the complete evolution paths for all chains.')) {
            ProgressiveVisualizer.expandAll();
        }
    },
    
    /**
     * Clear active path
     */
    clearPath() {
        ProgressiveVisualizer.clearPath();
    },
    
    /**
     * Toggle sidebar
     */
    toggleSidebar() {
        const sidebar = document.getElementById('chainListSidebar');
        sidebar.classList.toggle('active');
    },
    
    /**
     * Get current node size setting
     */
    getCurrentNodeSizeBy() {
        return this.currentFilters.nodeSizeBy;
    },
    
    /**
     * Zoom controls
     */
    zoomIn() {
        ProgressiveVisualizer.zoomIn();
    },
    
    zoomOut() {
        ProgressiveVisualizer.zoomOut();
    },
    
    resetZoom() {
        ProgressiveVisualizer.resetZoom();
    },
    
    fitToView() {
        ProgressiveVisualizer.fitToView();
    }
};

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing Progressive Evolution App...');
    ProgressiveApp.init();
});
