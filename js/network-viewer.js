// Network Viewer Component - 显示社区内部节点网络（第三层）- 已优化
const NetworkViewer = {
    modal: null,
    svg: null,
    zoom: null,
    simulation: null,
    width: 0,
    height: 0,
    currentCommunity: null,
    
    // 初始化模态窗口
    init() {
        // 检查是否已经初始化
        if (document.getElementById('networkModal')) {
            this.modal = document.getElementById('networkModal');
            this.svg = d3.select('#networkSvg');
            this.tooltip = d3.select('#networkTooltip');
            return;
        }
        
        // 创建模态窗口HTML
        const modalHTML = `
            <div id="networkModal" class="network-modal">
                <div class="network-modal-content">
                    <div class="network-modal-header">
                        <h3 id="networkModalTitle">Community Network</h3>
                        <div class="network-controls">
                            <button onclick="NetworkViewer.resetLayout()" class="network-btn">Reset Layout</button>
                            <button onclick="NetworkViewer.closeModal()" class="network-btn-close">×</button>
                        </div>
                    </div>
                    <div class="network-modal-body">
                        <svg id="networkSvg" width="100%" height="100%"></svg>
                        <div id="networkTooltip" class="network-tooltip"></div>
                        <div class="network-legend">
                            <h4>Legend</h4>
                            <div id="networkLegendContent"></div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // 添加到body
        const div = document.createElement('div');
        div.innerHTML = modalHTML;
        document.body.appendChild(div.firstElementChild);
        
        this.modal = document.getElementById('networkModal');
        this.svg = d3.select('#networkSvg');
        this.tooltip = d3.select('#networkTooltip');
        
        // 设置缩放
        this.zoom = d3.zoom()
            .scaleExtent([0.1, 4])
            .on('zoom', (event) => {
                this.svg.select('.network-group').attr('transform', event.transform);
            });
        
        this.svg.call(this.zoom);
        
        console.log('NetworkViewer initialized');
    },
    
    // 显示网络（传入社区数据）
    showNetwork(communityId, communityData, allData) {
        console.log('=== NetworkViewer.showNetwork called ===');
        console.log('Community ID:', communityId);
        console.log('Community nodes:', communityData.nodes.length);
        console.log('Community level:', communityData.level);
        
        if (!this.modal) {
            console.log('Initializing modal...');
            this.init();
        }
        
        this.currentCommunity = communityId;
        
        // 设置标题
        document.getElementById('networkModalTitle').textContent = 
            `Community ${communityId} - Internal Network (${communityData.nodes.length} nodes)`;
        
        // 获取容器尺寸
        const modalBody = document.querySelector('.network-modal-body');
        this.width = modalBody.clientWidth;
        this.height = modalBody.clientHeight;
        
        console.log('Container size:', this.width, 'x', this.height);
        
        // 构建网络数据
        const networkData = this.buildNetworkData(communityData);
        
        console.log('Network data:', {
            nodes: networkData.nodes.length,
            links: networkData.links.length
        });
        
        // 渲染网络
        this.renderNetwork(networkData);
        
        // 显示模态窗口
        this.modal.classList.add('active');
        console.log('Modal displayed');
    },
    
    // 构建网络数据
    buildNetworkData(communityData) {
        console.log('Building network data...');
        
        const nodes = communityData.nodes.map(node => ({
            id: node.node_id || node.geo_rcid,
            company: node.company || 'Unknown',
            naics_industry: node.naics_industry || 'Unknown',
            real_state: node.real_state || 'Unknown',
            real_metro_area: node.real_metro_area || 'Unknown',
            rics_k50: node.rics_k50 || 'Unknown',
            rics_k200: node.rics_k200 || 'Unknown',
            rics_k400: node.rics_k400 || 'Unknown',
            workforce_total_people: parseInt(node.workforce_total_people) || 0,
            workforce_role_k1500_distribution: node.workforce_role_k1500_distribution || ''
        }));
        
        const nodeIds = nodes.map(n => n.id);
        
        console.log('Node IDs:', nodeIds.slice(0, 5), '...');
        console.log('GraphDataLoader.edgesData exists?', !!GraphDataLoader.edgesData);
        
        // 尝试从加载的图数据中获取真实边
        let links = [];
        
        if (GraphDataLoader.edgesData && GraphDataLoader.edgesData.length > 0) {
            console.log('Searching for real edges...');
            links = GraphDataLoader.getEdgesForCommunity(nodeIds);
            console.log('Found', links.length, 'real edges');
        } else {
            console.log('No graph data loaded, will use inferred edges');
        }
        
        // 如果没有真实边数据或边太少，使用推断边
        if (links.length === 0) {
            console.log('No real edges found, generating inferred edges');
            links = GraphDataLoader.buildInferredEdges(nodes);
            console.log('Generated', links.length, 'inferred edges');
        } else if (links.length < nodeIds.length * 0.3) {
            console.log('Few real edges (' + links.length + '), supplementing with inferred edges');
            const inferredLinks = GraphDataLoader.buildInferredEdges(nodes);
            // 去重合并
            const existingPairs = new Set(links.map(l => `${l.source}-${l.target}`));
            inferredLinks.forEach(link => {
                const pair = `${link.source}-${link.target}`;
                if (!existingPairs.has(pair)) {
                    links.push(link);
                }
            });
            console.log('Total edges after supplementing:', links.length);
        }
        
        return { nodes, links };
    },
    
    // 渲染网络
    renderNetwork(data) {
        console.log('Rendering network...');
        
        // 清空SVG
        this.svg.selectAll('*').remove();
        
        // 创建容器组
        const g = this.svg.append('g').attr('class', 'network-group');
        
        // 创建力导向布局
        this.simulation = d3.forceSimulation(data.nodes)
            .force('link', d3.forceLink(data.links).id(d => d.id).distance(100))
            .force('charge', d3.forceManyBody().strength(-300))
            .force('center', d3.forceCenter(this.width / 2, this.height / 2))
            .force('collision', d3.forceCollide().radius(30));
        
        console.log('Force simulation created');
        
        // 绘制边
        const links = g.append('g')
            .attr('class', 'network-links')
            .selectAll('line')
            .data(data.links)
            .enter().append('line')
            .attr('class', 'network-link')
            .attr('stroke', '#cbd5e0')
            .attr('stroke-width', d => Math.min(Math.sqrt(d.weight || 1), 5))
            .attr('stroke-opacity', 0.6)
            .on('mouseover', (event, d) => this.showEdgeTooltip(event, d))
            .on('mouseout', () => this.hideTooltip());
        
        console.log('Links rendered:', data.links.length);
        
        // 绘制节点
        const colorScale = Config.getColorScale('naics_industry');
        
        const nodes = g.append('g')
            .attr('class', 'network-nodes')
            .selectAll('g')
            .data(data.nodes)
            .enter().append('g')
            .attr('class', 'network-node')
            .call(d3.drag()
                .on('start', (event, d) => this.dragStarted(event, d))
                .on('drag', (event, d) => this.dragged(event, d))
                .on('end', (event, d) => this.dragEnded(event, d)));
        
        // 节点圆圈
        nodes.append('circle')
            .attr('r', d => Math.max(5, Math.min(30, Math.sqrt(d.workforce_total_people) * 0.5 + 5)))
            .attr('fill', d => colorScale(d.naics_industry))
            .attr('stroke', '#fff')
            .attr('stroke-width', 2)
            .on('mouseover', (event, d) => this.showNodeTooltip(event, d))
            .on('mouseout', () => this.hideTooltip())
            .on('click', (event, d) => this.showNodeDetails(d));
        
        // ✅ 修改1: 移除节点标签，不再显示
        // 原来的代码已注释掉
        
        console.log('Nodes rendered:', data.nodes.length);
        
        // 更新力模拟
        this.simulation.on('tick', () => {
            links
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);
            
            nodes.attr('transform', d => `translate(${d.x},${d.y})`);
        });
        
        // 更新图例
        this.updateLegend(data.nodes);
        
        console.log('Network rendering complete');
    },
    
    // ✅ 修改3: 显示节点详情 - 在网络面板内右侧显示
    showNodeDetails(node) {
        const roleDistribution = this.parseRoleDistribution(node.workforce_role_k1500_distribution);
        
        // 检查是否已存在详情面板
        let detailPanel = document.getElementById('networkNodeDetails');
        
        if (!detailPanel) {
            // 创建详情面板
            detailPanel = document.createElement('div');
            detailPanel.id = 'networkNodeDetails';
            detailPanel.style.cssText = `
                position: absolute;
                top: 0;
                right: 0;
                width: 350px;
                height: 100%;
                background: white;
                box-shadow: -5px 0 20px rgba(0,0,0,0.3);
                overflow-y: auto;
                z-index: 10;
                display: none;
            `;
            document.querySelector('.network-modal-body').appendChild(detailPanel);
        }
        
        let html = `
            <div style="position: sticky; top: 0; background: linear-gradient(45deg, #7c9cb5, #8b9db3); color: white; padding: 15px; display: flex; justify-content: space-between; align-items: center; z-index: 11;">
                <h3 style="margin: 0; font-size: 1.1rem;">Node Details</h3>
                <button onclick="NetworkViewer.closeNodeDetails()" style="background: rgba(255,255,255,0.2); border: none; color: white; font-size: 24px; cursor: pointer; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center;">×</button>
            </div>
            <div style="padding: 20px;">
                <h3 style="margin-top: 0;">${node.id}</h3>
                <p><strong>Industry:</strong> ${node.naics_industry}</p>
                <p><strong>Location:</strong> ${node.real_metro_area}, ${node.real_state}</p>
                <p><strong>Total Workforce:</strong> ${node.workforce_total_people.toLocaleString()}</p>
                <p><strong>RICS K50:</strong> ${node.rics_k50}</p>
                <p><strong>RICS K200:</strong> ${node.rics_k200}</p>
                <p><strong>RICS K400:</strong> ${node.rics_k400}</p>
                <hr style="margin: 15px 0;">
                <h4>Role Distribution (Top 10):</h4>
        `;
        
        if (roleDistribution.length > 0) {
            html += '<div>';
            roleDistribution.forEach(role => {
                html += `
                    <div style="margin: 8px 0; padding: 8px; background: #f8f9fa; border-radius: 4px;">
                        <div style="display: flex; justify-content: space-between;">
                            <span><strong>${role.name}</strong></span>
                            <span>${role.count} (${role.percentage}%)</span>
                        </div>
                        <div style="margin-top: 4px; background: #e0e0e0; height: 6px; border-radius: 3px;">
                            <div style="width: ${role.percentage}%; background: #7c9fb0; height: 100%; border-radius: 3px;"></div>
                        </div>
                    </div>
                `;
            });
            html += '</div>';
        } else {
            html += '<p style="color: #7f8c8d;">No role data available</p>';
        }
        
        html += '</div>';
        
        detailPanel.innerHTML = html;
        detailPanel.style.display = 'block';
    },
    
    // 关闭节点详情面板
    closeNodeDetails() {
        const detailPanel = document.getElementById('networkNodeDetails');
        if (detailPanel) {
            detailPanel.style.display = 'none';
        }
    },
    
    // ✅ 修改2: 调整tooltip位置，紧贴鼠标，不超出边界
    showNodeTooltip(event, node) {
        const html = `
            <strong>${node.id}</strong><br>
            Industry: ${node.naics_industry}<br>
            Location: ${node.real_metro_area}, ${node.real_state}<br>
            Workforce: ${node.workforce_total_people.toLocaleString()}<br>
            <em style="color: #81c8e8;">Click for details</em>
        `;
        
        // 非常靠近鼠标的偏移量
        const offsetX = 10;
        const offsetY = 10;
        
        this.tooltip.html(html);
        const tooltipNode = this.tooltip.node();
        const tooltipRect = tooltipNode.getBoundingClientRect();
        
        // 计算位置
        let left = event.clientX + offsetX;
        let top = event.clientY + offsetY;
        
        // 防止右侧超出
        if (left + tooltipRect.width > window.innerWidth) {
            left = event.clientX - tooltipRect.width - offsetX;
        }
        
        // 防止下方超出
        if (top + tooltipRect.height > window.innerHeight) {
            top = event.clientY - tooltipRect.height - offsetY;
        }
        
        // 防止上方超出
        if (top < 0) {
            top = offsetY;
        }
        
        // 防止左侧超出
        if (left < 0) {
            left = offsetX;
        }
        
        this.tooltip
            .style('left', left + 'px')
            .style('top', top + 'px')
            .style('opacity', 1);
    },
    
    // 显示边tooltip - 也紧贴鼠标
    showEdgeTooltip(event, link) {
        let html = `
            <strong>Transition Edge</strong><br>
            Weight: ${link.weight} ${link.inferred ? '(inferred)' : 'people'}<br>
        `;
        
        if (link.inferred) {
            html += `<em style="color: #81c8e8;">Inferred connection</em><br>`;
        }
        
        if (link.pre_role_distribution) {
            const preRoles = this.parseRoleDistribution(link.pre_role_distribution);
            if (preRoles.length > 0) {
                html += `<br><strong>Previous Roles (Top 3):</strong><br>`;
                preRoles.slice(0, 3).forEach(role => {
                    html += `${role.name}: ${role.percentage}%<br>`;
                });
            }
        }
        
        if (link.new_role_distribution) {
            const newRoles = this.parseRoleDistribution(link.new_role_distribution);
            if (newRoles.length > 0) {
                html += `<br><strong>New Roles (Top 3):</strong><br>`;
                newRoles.slice(0, 3).forEach(role => {
                    html += `${role.name}: ${role.percentage}%<br>`;
                });
            }
        }
        
        // 紧贴鼠标
        const offsetX = 10;
        const offsetY = 10;
        
        this.tooltip.html(html);
        const tooltipNode = this.tooltip.node();
        const tooltipRect = tooltipNode.getBoundingClientRect();
        
        let left = event.clientX + offsetX;
        let top = event.clientY + offsetY;
        
        if (left + tooltipRect.width > window.innerWidth) {
            left = event.clientX - tooltipRect.width - offsetX;
        }
        
        if (top + tooltipRect.height > window.innerHeight) {
            top = event.clientY - tooltipRect.height - offsetY;
        }
        
        if (top < 0) {
            top = offsetY;
        }
        
        if (left < 0) {
            left = offsetX;
        }
        
        this.tooltip
            .style('left', left + 'px')
            .style('top', top + 'px')
            .style('opacity', 1);
    },
    
    // 隐藏tooltip
    hideTooltip() {
        this.tooltip.style('opacity', 0);
    },
    
    // 解析role分布字符串
    parseRoleDistribution(distributionStr) {
        if (!distributionStr || distributionStr === 'Unknown' || distributionStr === '') {
            return [];
        }
        
        // 格式: "role1:count1(percent1%)|role2:count2(percent2%)|..."
        const roles = distributionStr.split('|').map(item => {
            const match = item.match(/(.+):(\d+)\(([0-9.]+)%\)/);
            if (match) {
                return {
                    name: match[1].trim(),
                    count: parseInt(match[2]),
                    percentage: parseFloat(match[3])
                };
            }
            return null;
        }).filter(Boolean);
        
        return roles;
    },
    
    // 更新图例
    updateLegend(nodes) {
        const industries = [...new Set(nodes.map(n => n.naics_industry))].slice(0, 10);
        const colorScale = Config.getColorScale('naics_industry');
        
        const legendContent = document.getElementById('networkLegendContent');
        if (!legendContent) return;
        
        legendContent.innerHTML = industries.map(industry => `
            <div style="display: flex; align-items: center; margin: 5px 0;">
                <div style="width: 16px; height: 16px; background: ${colorScale(industry)}; margin-right: 8px; border-radius: 3px;"></div>
                <span style="font-size: 11px;">${industry}</span>
            </div>
        `).join('');
    },
    
    // 拖拽处理
    dragStarted(event, d) {
        if (!event.active) this.simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    },
    
    dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    },
    
    dragEnded(event, d) {
        if (!event.active) this.simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    },
    
    // 重置布局
    resetLayout() {
        if (this.simulation) {
            this.simulation.alpha(1).restart();
        }
        this.svg.transition().call(this.zoom.transform, d3.zoomIdentity);
    },
    
    // 关闭模态窗口
    closeModal() {
        if (this.simulation) {
            this.simulation.stop();
        }
        
        // 同时关闭节点详情面板
        this.closeNodeDetails();
        
        this.modal.classList.remove('active');
    }
};