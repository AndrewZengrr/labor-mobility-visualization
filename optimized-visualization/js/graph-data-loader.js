// Graph Data Loader - 加载边数据以支持网络可视化
const GraphDataLoader = {
    edgesData: null,
    nodesData: null,
    
    // 从文件加载边数据
    loadEdgesFile(file, callback) {
        console.log('Loading edges file:', file.name);
        
        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const data = d3.csvParse(e.target.result);
                
                // 转换数据类型
                data.forEach(d => {
                    d.weight = parseInt(d.weight) || 1;
                    d.unique_people = parseInt(d.unique_people) || 0;
                    d.avg_salary_pre = parseFloat(d.avg_salary_pre) || 0;
                    d.avg_salary_new = parseFloat(d.avg_salary_new) || 0;
                });
                
                this.edgesData = data;
                console.log('Successfully loaded', data.length, 'edges');
                
                if (callback) callback(true);
            } catch (error) {
                console.error('Error parsing edges file:', error);
                if (callback) callback(false);
            }
        };
        
        reader.onerror = () => {
            console.error('Error reading file');
            if (callback) callback(false);
        };
        
        reader.readAsText(file);
    },
    
    // 获取社区内部的边
    getEdgesForCommunity(nodeIds) {
        if (!this.edgesData) {
            console.warn('Edges data not loaded');
            return [];
        }
        
        const nodeIdSet = new Set(nodeIds);
        
        // 筛选出源和目标都在社区内的边
        const communityEdges = this.edgesData.filter(edge => 
            nodeIdSet.has(edge.source) && nodeIdSet.has(edge.target)
        );
        
        console.log(`Found ${communityEdges.length} edges within community of ${nodeIds.length} nodes`);
        
        return communityEdges;
    },
    
    // 构建推断边(如果没有真实边数据)
    buildInferredEdges(nodes) {
        console.log('Building inferred edges from node attributes...');
        
        const edges = [];
        
        // 基于节点的相似性构建推断边
        nodes.forEach((node1, i) => {
            nodes.forEach((node2, j) => {
                if (i < j) { // 避免重复
                    let similarity = 0;
                    
                    // 相同州 +1
                    if (node1.real_state === node2.real_state) similarity += 1;
                    
                    // 相同都市区 +2
                    if (node1.real_metro_area === node2.real_metro_area) similarity += 2;
                    
                    // 相同行业 +1
                    if (node1.naics_industry === node2.naics_industry) similarity += 1;
                    
                    // 如果相似度 >= 2，创建边
                    if (similarity >= 2) {
                        edges.push({
                            source: node1.id,
                            target: node2.id,
                            weight: similarity,
                            inferred: true
                        });
                    }
                }
            });
        });
        
        console.log(`Generated ${edges.length} inferred edges`);
        return edges;
    },
    
    // 清空数据
    clear() {
        this.edgesData = null;
        this.nodesData = null;
        console.log('Graph data cleared');
    }
};