// Composition panel module - with optimized colors
const Composition = {
    showPanel(communityId, communities) {
        const comm = communities.get(communityId);
        if (!comm) return;
        
        const panel = document.getElementById('compositionPanel');
        const title = document.getElementById('panelTitle');
        const content = document.getElementById('panelContent');
        
        title.textContent = `Community ${communityId} Composition Analysis`;
        
        let html = `
            <div class="community-info">
                <strong>Community ${communityId}</strong>
                <span>Size: ${comm.nodes.length} companies</span>
                <span>Total Workforce: ${d3.sum(comm.nodes, d => parseInt(d.workforce_total_people) || 0).toLocaleString()}</span>
                <span>Level: Level ${comm.level}</span>
            </div>
        `;
        
        // Create treemap for each category
        Config.composition.categories.forEach((category, idx) => {
            const composition = DataHandler.calculateComposition(comm.nodes, category.key);
            html += this.createTreemapSection(composition, category, communityId, idx);
        });
        
        content.innerHTML = html;
        
        // Render all treemaps
        Config.composition.categories.forEach((category, idx) => {
            const composition = DataHandler.calculateComposition(comm.nodes, category.key);
            this.renderTreemap(composition, category, `treemap-${communityId}-${idx}`);
        });
        
        panel.classList.add('active');
    },
    
    createTreemapSection(composition, category, communityId, idx) {
        const totalItems = composition.reduce((sum, item) => sum + item.count, 0);
        const uniqueValues = composition.length;
        const topCategory = composition[0] || { name: 'N/A', percentage: 0 };
        
        return `
            <div class="composition-section">
                <h4>${category.title}</h4>
                <div class="treemap-container" id="treemap-${communityId}-${idx}"></div>
                <div class="composition-stats">
                    <div class="stat-row">
                        <span>Total:</span>
                        <span><strong>${totalItems}</strong></span>
                    </div>
                    <div class="stat-row">
                        <span>Categories:</span>
                        <span><strong>${uniqueValues}</strong></span>
                    </div>
                    <div class="stat-row">
                        <span>Top Category:</span>
                        <span><strong>${topCategory.name} (${topCategory.percentage}%)</strong></span>
                    </div>
                </div>
            </div>
        `;
    },
    
    renderTreemap(data, category, containerId) {
        const container = document.getElementById(containerId);
        if (!container || data.length === 0) return;
        
        const width = container.clientWidth;
        const height = Config.composition.treemapHeight;
        
        container.innerHTML = '';
        
        // Use optimized color scale
        const colorScale = Config.getColorScale(category.key);
        
        const treemap = d3.treemap()
            .size([width, height])
            .padding(2)
            .round(true);
        
        const root = d3.hierarchy({ children: data })
            .sum(d => d.value)
            .sort((a, b) => b.value - a.value);
        
        treemap(root);
        
        const tooltip = document.createElement('div');
        tooltip.className = 'treemap-tooltip';
        container.appendChild(tooltip);
        
        // Render rectangles
        root.leaves().forEach(node => {
            const rect = document.createElement('div');
            rect.className = 'treemap-rect';
            rect.style.left = node.x0 + 'px';
            rect.style.top = node.y0 + 'px';
            rect.style.width = (node.x1 - node.x0) + 'px';
            rect.style.height = (node.y1 - node.y0) + 'px';
            rect.style.backgroundColor = colorScale(node.data.name);
            
            const area = (node.x1 - node.x0) * (node.y1 - node.y0);
            if (area > 2500) {
                rect.innerHTML = `${node.data.name}<br>${node.data.percentage}%`;
            } else if (area > 1200) {
                rect.innerHTML = `${node.data.percentage}%`;
            } else if (area > 500) {
                rect.innerHTML = node.data.count;
            }
            
            rect.addEventListener('mouseenter', (e) => {
                tooltip.innerHTML = `
                    <strong>${node.data.name}</strong><br>
                    Count: ${node.data.count}<br>
                    Percentage: ${node.data.percentage}%
                `;
                const rect = container.getBoundingClientRect();
                tooltip.style.left = (e.clientX - rect.left + 10) + 'px';
                tooltip.style.top = (e.clientY - rect.top - 10) + 'px';
                tooltip.style.opacity = '1';
            });
            
            rect.addEventListener('mouseleave', () => {
                tooltip.style.opacity = '0';
            });
            
            rect.addEventListener('mousemove', (e) => {
                const rect = container.getBoundingClientRect();
                tooltip.style.left = (e.clientX - rect.left + 10) + 'px';
                tooltip.style.top = (e.clientY - rect.top - 10) + 'px';
            });
            
            container.appendChild(rect);
        });
    },
    
    closePanel() {
        document.getElementById('compositionPanel').classList.remove('active');
    }
};