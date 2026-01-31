// 主应用模块 - 优化版,支持多种布局
const App = {
    data: null,
    expandedNodes: new Set(),
    communityFileLoaded: false,
    graphFileLoaded: false,
    config: {
        colorAttr: 'naics_industry',
        sizeAttr: 'community_size',
        minSize: 5
    },
    
    init() {
        console.log('Initializing application...');
        this.setupEventListeners();
        this.setupDragDrop();
    },
    
    setupEventListeners() {
        // Community data file upload
        document.getElementById('fileInput').addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                this.loadCommunityData(file);
            }
        });
        
        // Graph edges data file upload
        document.getElementById('graphFileInput').addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                this.loadGraphData(file);
            }
        });
        
        // Control panel
        document.getElementById('colorAttr').addEventListener('change', () => {
            this.updateConfig();
            this.render();
        });
        
        document.getElementById('sizeAttr').addEventListener('change', () => {
            this.updateConfig();
            this.render();
        });
        
        document.getElementById('minSize').addEventListener('input', () => {
            this.updateConfig();
            this.render();
        });
        
        // Window resize
        window.addEventListener('resize', () => {
            if (this.data) {
                Visualizer.init();
                this.render();
            }
        });
    },
    
    setupDragDrop() {
        const uploadZone = document.getElementById('uploadZone');
        const graphUploadZone = document.getElementById('graphUploadZone');
        
        this.setupDragDropForElement(uploadZone, (file) => {
            this.loadCommunityData(file);
        });
        
        this.setupDragDropForElement(graphUploadZone, (file) => {
            this.loadGraphData(file);
        });
    },
    
    setupDragDropForElement(element, callback) {
        element.addEventListener('dragover', (e) => {
            e.preventDefault();
            element.classList.add('dragover');
        });
        
        element.addEventListener('dragleave', () => {
            element.classList.remove('dragover');
        });
        
        element.addEventListener('drop', (e) => {
            e.preventDefault();
            element.classList.remove('dragover');
            
            const file = e.dataTransfer.files[0];
            if (file && file.name.endsWith('.csv')) {
                callback(file);
            } else {
                alert('Please upload a CSV file');
            }
        });
    },
    
    loadCommunityData(file) {
        console.log('Loading community data file:', file.name);
        
        DataHandler.loadFile(file, (data) => {
            console.log('Community data loaded:', data.length, 'rows');
            console.log('Max hierarchy levels detected:', Config.maxLevels);
            
            this.data = data;
            this.communityFileLoaded = true;
            
            // Update status with level info
            document.getElementById('communityFileStatus').textContent = 
                `✓ Loaded: ${file.name} (${data.length} records, ${Config.maxLevels} levels)`;
            
            // Enable graph data upload zone
            const graphUploadZone = document.getElementById('graphUploadZone');
            graphUploadZone.style.opacity = '1';
            graphUploadZone.style.pointerEvents = 'auto';
            
            // Show proceed button
            document.getElementById('proceedButton').style.display = 'block';
        });
    },
    
    loadGraphData(file) {
        console.log('Loading graph edges file:', file.name);
        
        GraphDataLoader.loadEdgesFile(file, (success) => {
            if (success) {
                this.graphFileLoaded = true;
                document.getElementById('graphFileStatus').textContent = 
                    `✓ Loaded: ${file.name} (${GraphDataLoader.edgesData.length} edges)`;
                console.log('Graph data loaded successfully');
            } else {
                alert('Failed to load graph edges file. Network view will use inferred connections.');
                document.getElementById('graphFileStatus').textContent = 
                    `✗ Failed to load: ${file.name}`;
            }
        });
    },
    
    proceedToVisualization() {
        if (!this.communityFileLoaded) {
            alert('Please upload community data first!');
            return;
        }
        
        // Hide upload section, show main app
        document.getElementById('uploadSection').style.display = 'none';
        document.getElementById('mainApp').style.display = 'block';
        
        // Initialize visualization and render
        Visualizer.init();
        this.render();
        
        // Auto fit to view after initial render
        setTimeout(() => {
            Visualizer.fitToView();
        }, 500);
        
        // Info message
        const layoutInfo = Config.maxLevels > 4 
            ? `\n\n💡 Tip: For deep hierarchies (${Config.maxLevels} levels), try different layout modes:\n• Adaptive Tree - Best for moderate depth\n• Radial - Good for deep hierarchies\n• Layered - Clear level separation`
            : '';
        
        if (!this.graphFileLoaded) {
            setTimeout(() => {
                alert(`📌 Network view will use inferred connections\n\nFor accurate network visualization, upload the edges_data.csv file.\n\nDetected ${Config.maxLevels} hierarchy levels.${layoutInfo}`);
            }, 600);
        } else {
            setTimeout(() => {
                alert(`✅ Data loaded successfully!\n\nDetected ${Config.maxLevels} hierarchy levels.\n\n💡 Tip: Double-click leaf communities to view network structure.${layoutInfo}`);
            }, 600);
        }
    },
    
    updateConfig() {
        this.config = {
            colorAttr: document.getElementById('colorAttr').value,
            sizeAttr: document.getElementById('sizeAttr').value,
            minSize: parseInt(document.getElementById('minSize').value)
        };
    },
    
    render() {
        if (!this.data) {
            console.error('No data available');
            return;
        }
        
        console.log('Rendering with config:', this.config);
        Visualizer.render(this.data, this.config, this.expandedNodes);
    },
    
    toggleNode(nodeId) {
        if (this.expandedNodes.has(nodeId)) {
            this.expandedNodes.delete(nodeId);
            
            // Recursively collapse child nodes
            const communities = DataHandler.processCommunities(this.data, this.config.minSize);
            const toCollapse = [nodeId];
            while (toCollapse.length > 0) {
                const current = toCollapse.pop();
                const comm = communities.get(current);
                if (comm) {
                    comm.children.forEach(childId => {
                        this.expandedNodes.delete(childId);
                        toCollapse.push(childId);
                    });
                }
            }
        } else {
            this.expandedNodes.add(nodeId);
        }
        
        this.render();
    },
    
    resetView() {
        this.expandedNodes.clear();
        Visualizer.resetZoom();
        this.render();
        
        // Auto fit after reset
        setTimeout(() => {
            Visualizer.fitToView();
        }, 100);
    },
    
    expandAll() {
        const communities = DataHandler.processCommunities(this.data, this.config.minSize);
        communities.forEach((comm, id) => {
            if (comm.children.size > 0) {
                this.expandedNodes.add(id);
            }
        });
        this.render();
        
        // Auto fit after expand all
        setTimeout(() => {
            Visualizer.fitToView();
        }, 100);
    },
    
    collapseAll() {
        this.expandedNodes.clear();
        this.render();
        
        setTimeout(() => {
            Visualizer.fitToView();
        }, 100);
    },
    
    expandToLevel(targetLevel) {
        const communities = DataHandler.processCommunities(this.data, this.config.minSize);
        this.expandedNodes.clear();
        
        communities.forEach((comm, id) => {
            if (comm.level < targetLevel && comm.children.size > 0) {
                this.expandedNodes.add(id);
            }
        });
        
        this.render();
        
        // Auto fit after level change
        setTimeout(() => {
            Visualizer.fitToView();
        }, 100);
    },
    
    zoomIn() {
        Visualizer.zoomIn();
    },
    
    zoomOut() {
        Visualizer.zoomOut();
    },
    
    resetZoom() {
        Visualizer.resetZoom();
    },
    
    // ✅ 新增: 适配视图
    fitToView() {
        Visualizer.fitToView();
    },
    
    closePanel() {
        Composition.closePanel();
    }
};

// Page load initialization
window.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing app...');
    App.init();
});
