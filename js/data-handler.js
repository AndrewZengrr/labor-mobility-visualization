// Data Handler - Improved for dynamic hierarchy levels
const DataHandler = {
    // Load file
    loadFile(file, callback) {
        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const data = d3.csvParse(e.target.result);
                
                // ✅ Detect hierarchy levels dynamically
                const maxLevels = Config.detectMaxLevels(data);
                
                // Check for required columns
                const requiredCols = [];
                for (let i = 1; i <= maxLevels; i++) {
                    requiredCols.push(`community_level${i}`);
                }
                
                const hasRequired = requiredCols.some(col => data[0]?.hasOwnProperty(col));
                
                if (!hasRequired) {
                    alert(`File must contain community_level columns (detected max level: ${maxLevels})`);
                    return;
                }
                
                console.log(`Data loaded: ${data.length} rows, ${maxLevels} hierarchy levels`);
                
                // Process NAICS codes to industry names
                this.processNAICSCodes(data);
                
                // ✅ Use dynamic levels for community ID assignment
                this.addCommunityIds(data, maxLevels);
                
                callback(data);
            } catch (error) {
                alert(`Parsing error: ${error.message}`);
            }
        };
        reader.readAsText(file);
    },
    
    // Process NAICS codes: extract 2-digit and map to industry
    processNAICSCodes(data) {
        data.forEach(row => {
            if (row.naics_code) {
                row.naics_industry = Config.getNAICSIndustry(row.naics_code);
            } else {
                row.naics_industry = 'Unknown';
            }
        });
    },
    
    // ✅ IMPROVED: Add community IDs with dynamic level support
    addCommunityIds(data, maxLevels) {
        data.forEach(row => {
            // Find deepest valid community level for this row
            for (let level = maxLevels; level >= 1; level--) {
                const value = row[`community_level${level}`];
                if (value && value !== '-1' && value !== '') {
                    row.community_id = value;
                    row.deepest_level = level;
                    break;
                }
            }
            
            // If no valid community found, mark as orphan
            if (!row.community_id) {
                row.community_id = '-1';
                row.deepest_level = 0;
            }
        });
    },
    
    // ✅ IMPROVED: Process communities with dynamic levels
    processCommunities(data, minSize) {
        const communities = new Map();
        const maxLevels = Config.maxLevels;
        
        data.forEach(row => {
            // Process all levels dynamically
            for (let level = 1; level <= maxLevels; level++) {
                const id = row[`community_level${level}`];
                if (id && id !== '-1' && id !== '') {
                    if (!communities.has(id)) {
                        communities.set(id, {
                            id,
                            level,
                            nodes: [],
                            children: new Set(),
                            parent: this.getParentId(id)
                        });
                    }
                    communities.get(id).nodes.push(row);
                }
            }
        });
        
        // Filter by minimum size
        const filtered = new Map();
        communities.forEach((comm, id) => {
            if (comm.nodes.length >= minSize) {
                filtered.set(id, comm);
            }
        });
        
        // Build parent-child relationships
        filtered.forEach((comm, id) => {
            if (comm.parent && filtered.has(comm.parent)) {
                filtered.get(comm.parent).children.add(id);
            }
        });
        
        return filtered;
    },
    
    // Get parent ID from community path
    getParentId(id) {
        const parts = String(id).split('.');
        return parts.length > 1 ? parts.slice(0, -1).join('.') : null;
    },
    
    // ✅ NEW: Get community depth from ID
    getCommunityDepth(id) {
        if (!id || id === '-1') return 0;
        return String(id).split('.').length;
    },
    
    // ✅ NEW: Check if community is a leaf (no children in filtered set)
    isLeafCommunity(communityId, communities) {
        const comm = communities.get(communityId);
        if (!comm) return false;
        
        // Check if any children exist in the filtered communities
        return comm.children.size === 0;
    },
    
    // Calculate composition
    calculateComposition(nodes, attribute) {
        const counts = {};
        
        nodes.forEach(node => {
            let value;
            
            // Special handling for NAICS - use processed industry name
            if (attribute === 'naics_industry') {
                value = node.naics_industry || 'Unknown';
            } else {
                value = node[attribute] || 'Unknown';
            }
            
            counts[value] = (counts[value] || 0) + 1;
        });
        
        const total = nodes.length;
        return Object.entries(counts)
            .map(([name, count]) => ({
                name,
                count,
                percentage: ((count / total) * 100).toFixed(1),
                value: count
            }))
            .sort((a, b) => b.count - a.count);
    }
};