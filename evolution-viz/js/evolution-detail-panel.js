// Community Detail Panel
const EvolutionDetailPanel = {
    /**
     * Show community detail panel
     */
    showPanel(chainId, year) {
        const community = EvolutionDataLoader.getCommunityDetails(chainId, year);
        const chain = EvolutionDataLoader.getChainById(chainId);
        
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
     * Close detail panel
     */
    closePanel() {
        document.getElementById('communityPanel').classList.remove('active');
    },
    
    /**
     * Generate panel HTML content
     */
    generatePanelContent(chain, community) {
        const attrs = community.attributes;
        const composition = community.nodeComposition;
        
        let html = '';
        
        // Basic Info Section
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
                    <div class="info-card-label">Community Size</div>
                    <div class="info-card-value">${attrs.size || 0}</div>
                </div>
                <div class="info-card">
                    <div class="info-card-label">Chain Length</div>
                    <div class="info-card-value">${chain.length} years</div>
                </div>
                <div class="info-card">
                    <div class="info-card-label">Community Type</div>
                    <div class="info-card-value">
                        <span class="type-badge ${composition.type}">${composition.type || 'normal'}</span>
                    </div>
                </div>
            </div>
        </div>
        `;
        
        // Node Composition Section
        if (composition && Object.keys(composition).length > 0) {
            html += `
            <div class="info-section">
                <h4>👥 Node Composition</h4>
                <div class="info-grid">
                    ${composition.core_node_ratio !== undefined ? `
                    <div class="info-card">
                        <div class="info-card-label">Core Nodes Ratio</div>
                        <div class="info-card-value">${(composition.core_node_ratio * 100).toFixed(1)}%</div>
                    </div>
                    ` : ''}
                    ${composition.new_node_ratio !== undefined ? `
                    <div class="info-card">
                        <div class="info-card-label">New Nodes Ratio</div>
                        <div class="info-card-value">${(composition.new_node_ratio * 100).toFixed(1)}%</div>
                    </div>
                    ` : ''}
                    ${composition.avg_node_weight !== undefined ? `
                    <div class="info-card">
                        <div class="info-card-label">Avg Node Weight</div>
                        <div class="info-card-value">${composition.avg_node_weight.toFixed(3)}</div>
                    </div>
                    ` : ''}
                    ${composition.core_nodes !== undefined ? `
                    <div class="info-card">
                        <div class="info-card-label">Core Nodes Count</div>
                        <div class="info-card-value">${composition.core_nodes}</div>
                    </div>
                    ` : ''}
                    ${composition.new_nodes !== undefined ? `
                    <div class="info-card">
                        <div class="info-card-label">New Nodes Count</div>
                        <div class="info-card-value">${composition.new_nodes}</div>
                    </div>
                    ` : ''}
                </div>
            </div>
            `;
        }
        
        // State Distribution
        if (attrs.top3_states && attrs.top3_states.length > 0) {
            html += `
            <div class="info-section">
                <h4>📍 State Distribution (Top 3)</h4>
                <ul class="attribute-list">
                    ${attrs.top3_states.map(item => `
                        <li class="attribute-item">
                            <span class="attribute-name">${item.value}</span>
                            <span class="attribute-count">${item.count} companies</span>
                            <span class="attribute-percentage">${item.percentage}%</span>
                            <div class="attribute-bar">
                                <div class="attribute-bar-fill" style="width: ${item.percentage}%"></div>
                            </div>
                        </li>
                    `).join('')}
                </ul>
            </div>
            `;
        }
        
        // Metro Area Distribution
        if (attrs.top5_metros && attrs.top5_metros.length > 0) {
            html += `
            <div class="info-section">
                <h4>🏙️ Metro Area Distribution (Top 5)</h4>
                <ul class="attribute-list">
                    ${attrs.top5_metros.map(item => `
                        <li class="attribute-item">
                            <span class="attribute-name">${item.value}</span>
                            <span class="attribute-count">${item.count} companies</span>
                            <span class="attribute-percentage">${item.percentage}%</span>
                            <div class="attribute-bar">
                                <div class="attribute-bar-fill" style="width: ${item.percentage}%"></div>
                            </div>
                        </li>
                    `).join('')}
                </ul>
            </div>
            `;
        }
        
        // NAICS 2-digit Distribution
        if (attrs.top3_naics_2digit && attrs.top3_naics_2digit.length > 0) {
            html += `
            <div class="info-section">
                <h4>🏭 Industry Distribution - NAICS 2-digit (Top 3)</h4>
                <ul class="attribute-list">
                    ${attrs.top3_naics_2digit.map(item => `
                        <li class="attribute-item">
                            <span class="attribute-name">NAICS ${item.value}</span>
                            <span class="attribute-count">${item.count} companies</span>
                            <span class="attribute-percentage">${item.percentage}%</span>
                            <div class="attribute-bar">
                                <div class="attribute-bar-fill" style="width: ${item.percentage}%"></div>
                            </div>
                        </li>
                    `).join('')}
                </ul>
            </div>
            `;
        }
        
        // NAICS 4-digit Distribution
        if (attrs.top5_naics_4digit && attrs.top5_naics_4digit.length > 0) {
            html += `
            <div class="info-section">
                <h4>🏢 Industry Distribution - NAICS 4-digit (Top 5)</h4>
                <ul class="attribute-list">
                    ${attrs.top5_naics_4digit.map(item => `
                        <li class="attribute-item">
                            <span class="attribute-name">NAICS ${item.value}</span>
                            <span class="attribute-count">${item.count} companies</span>
                            <span class="attribute-percentage">${item.percentage}%</span>
                            <div class="attribute-bar">
                                <div class="attribute-bar-fill" style="width: ${item.percentage}%"></div>
                            </div>
                        </li>
                    `).join('')}
                </ul>
            </div>
            `;
        }
        
        // Role Distribution
        if (attrs.top10_roles && attrs.top10_roles.length > 0) {
            html += `
            <div class="info-section">
                <h4>💼 Top Roles (Top 10)</h4>
                <ul class="attribute-list">
                    ${attrs.top10_roles.slice(0, 10).map(item => `
                        <li class="attribute-item">
                            <span class="attribute-name">${item.role}</span>
                            <span class="attribute-count">${item.count} occurrences</span>
                            <span class="attribute-percentage">${item.percentage}%</span>
                            <div class="attribute-bar">
                                <div class="attribute-bar-fill" style="width: ${item.percentage}%"></div>
                            </div>
                        </li>
                    `).join('')}
                </ul>
            </div>
            `;
        }
        
        return html;
    }
};
