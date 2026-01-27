// Main Evolution Visualization App
const EvolutionApp = {
    currentFilters: {
        lengthFilter: 'all',
        sortBy: 'length',
        layoutMode: 'timeline',
        maxChains: 50
    },
    
    /**
     * Initialize the application
     */
    init() {
        console.log('Initializing Evolution Visualization App...');
        this.setupEventListeners();
    },
    
    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // File upload
        document.getElementById('chainFileInput').addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                this.loadDataFile(file);
            }
        });
        
        // Filter controls
        document.getElementById('lengthFilter').addEventListener('change', () => {
            this.currentFilters.lengthFilter = document.getElementById('lengthFilter').value;
        });
        
        document.getElementById('sortBy').addEventListener('change', () => {
            this.currentFilters.sortBy = document.getElementById('sortBy').value;
        });
        
        document.getElementById('layoutMode').addEventListener('change', () => {
            this.currentFilters.layoutMode = document.getElementById('layoutMode').value;
        });
        
        document.getElementById('maxChains').addEventListener('change', () => {
            this.currentFilters.maxChains = parseInt(document.getElementById('maxChains').value) || 50;
        });
    },
    
    /**
     * Load data file
     */
    loadDataFile(file) {
        const statusDiv = document.getElementById('uploadStatus');
        statusDiv.textContent = 'Loading...';
        
        EvolutionDataLoader.loadChainData(file, (success) => {
            if (success) {
                statusDiv.textContent = `✓ Loaded: ${file.name} (${EvolutionDataLoader.processedChains.length} chains)`;
                
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
     * Show main visualization interface
     */
    showMainVisualization() {
        // Hide upload section
        document.getElementById('uploadSection').style.display = 'none';
        
        // Show main visualization
        document.getElementById('mainViz').style.display = 'block';
        
        // Initialize visualizer
        EvolutionVisualizer.init();
        
        // Render with initial filters
        this.applyFilters();
        
        // Update statistics
        this.updateStatistics();
        
        // Render chain list
        this.renderChainList();
        
        // Fit to view
        setTimeout(() => {
            EvolutionVisualizer.fitToView();
        }, 500);
    },
    
    /**
     * Apply current filters and re-render
     */
    applyFilters() {
        const {lengthFilter, sortBy, layoutMode, maxChains} = this.currentFilters;
        
        const filteredChains = EvolutionDataLoader.filterChains(
            lengthFilter,
            sortBy,
            maxChains
        );
        
        EvolutionVisualizer.render(filteredChains, layoutMode);
        this.renderChainList(filteredChains);
        this.updateFilteredStatistics(filteredChains);
    },
    
    /**
     * Reset filters to default
     */
    resetFilters() {
        document.getElementById('lengthFilter').value = 'all';
        document.getElementById('sortBy').value = 'length';
        document.getElementById('layoutMode').value = 'timeline';
        document.getElementById('maxChains').value = '50';
        
        this.currentFilters = {
            lengthFilter: 'all',
            sortBy: 'length',
            layoutMode: 'timeline',
            maxChains: 50
        };
        
        this.applyFilters();
    },
    
    /**
     * Update statistics panel
     */
    updateStatistics() {
        const stats = EvolutionDataLoader.statistics;
        const dist = stats.length.distribution;
        
        const html = `
            <div class="stat-row">
                <span class="stat-label">Total Chains:</span>
                <span class="stat-value">${stats.totalChains}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Year Range:</span>
                <span class="stat-value">${stats.yearRange[0]}-${stats.yearRange[1]}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Avg Length:</span>
                <span class="stat-value">${stats.length.mean.toFixed(1)} years</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Longest Chain:</span>
                <span class="stat-value">${stats.length.max} years</span>
            </div>
            <hr style="margin: 10px 0; border: none; border-top: 1px solid #ecf0f1;">
            <div class="stat-row">
                <span class="stat-label">Singleton:</span>
                <span class="stat-value">${dist.singleton}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Short (2-4):</span>
                <span class="stat-value">${dist.short}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Medium (5-9):</span>
                <span class="stat-value">${dist.medium}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Long (10-19):</span>
                <span class="stat-value">${dist.long}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Very Long (20+):</span>
                <span class="stat-value">${dist.verylong}</span>
            </div>
        `;
        
        document.getElementById('statsContent').innerHTML = html;
    },
    
    /**
     * Update statistics for filtered chains
     */
    updateFilteredStatistics(chains) {
        const stats = EvolutionDataLoader.statistics;
        const lengths = chains.map(c => c.length);
        
        const dist = {
            singleton: chains.filter(c => c.length === 1).length,
            short: chains.filter(c => c.length >= 2 && c.length <= 4).length,
            medium: chains.filter(c => c.length >= 5 && c.length <= 9).length,
            long: chains.filter(c => c.length >= 10 && c.length <= 19).length,
            verylong: chains.filter(c => c.length >= 20).length
        };
        
        const html = `
            <div class="stat-row">
                <span class="stat-label">Displayed Chains:</span>
                <span class="stat-value">${chains.length}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Year Range:</span>
                <span class="stat-value">${stats.yearRange[0]}-${stats.yearRange[1]}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Avg Length:</span>
                <span class="stat-value">${d3.mean(lengths).toFixed(1)} years</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Longest Chain:</span>
                <span class="stat-value">${d3.max(lengths)} years</span>
            </div>
            <hr style="margin: 10px 0; border: none; border-top: 1px solid #ecf0f1;">
            <div class="stat-row">
                <span class="stat-label">Singleton:</span>
                <span class="stat-value">${dist.singleton}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Short (2-4):</span>
                <span class="stat-value">${dist.short}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Medium (5-9):</span>
                <span class="stat-value">${dist.medium}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Long (10-19):</span>
                <span class="stat-value">${dist.long}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Very Long (20+):</span>
                <span class="stat-value">${dist.verylong}</span>
            </div>
        `;
        
        document.getElementById('statsContent').innerHTML = html;
    },
    
    /**
     * Render chain list in sidebar
     */
    renderChainList(chains = null) {
        if (!chains) {
            chains = EvolutionDataLoader.processedChains;
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
                this.highlightChainInList(chain.id);
                EvolutionVisualizer.highlightChain(chain.id);
            });
            
            listContent.appendChild(item);
        });
    },
    
    /**
     * Highlight chain in list
     */
    highlightChainInList(chainId) {
        document.querySelectorAll('.chain-item').forEach(item => {
            item.classList.remove('selected');
        });
        
        const item = document.querySelector(`.chain-item[data-chain-id="${chainId}"]`);
        if (item) {
            item.classList.add('selected');
            item.scrollIntoView({behavior: 'smooth', block: 'nearest'});
        }
    },
    
    /**
     * Toggle sidebar
     */
    toggleSidebar() {
        const sidebar = document.getElementById('chainListSidebar');
        sidebar.classList.toggle('active');
    },
    
    /**
     * Show community detail panel
     */
    showCommunityDetail(chainId, year) {
        EvolutionDetailPanel.showPanel(chainId, year);
    },
    
    /**
     * Close detail panel
     */
    closeDetailPanel() {
        EvolutionDetailPanel.closePanel();
    },
    
    /**
     * Zoom controls
     */
    zoomIn() {
        EvolutionVisualizer.zoomIn();
    },
    
    zoomOut() {
        EvolutionVisualizer.zoomOut();
    },
    
    resetZoom() {
        EvolutionVisualizer.resetZoom();
    },
    
    fitToView() {
        EvolutionVisualizer.fitToView();
    }
};

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing Evolution App...');
    EvolutionApp.init();
});
