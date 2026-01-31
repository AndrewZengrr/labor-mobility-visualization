// Adapted Data Loader for New Community Matching Format
const AdaptedDataLoader = {
    // Edge-based network data (from basic_gap1_d3_format.json)
    networkData: null,
    nodesById: new Map(),
    edgesBySource: new Map(),
    
    // Community attributes data (from CSV)
    attributesData: null,
    attributesByYearAndCommunity: new Map(),
    
    // Processed data
    yearRange: [Infinity, -Infinity],
    years: [],
    statistics: {},
    
    /**
     * Load network data (nodes + edges format)
     */
    loadNetworkData(file, callback) {
        const reader = new FileReader();
        
        reader.onload = (e) => {
            try {
                const jsonData = JSON.parse(e.target.result);
                console.log('Network data loaded:', jsonData);
                
                // Validate format
                if (!jsonData.nodes || !jsonData.links) {
                    throw new Error('Invalid format: expected {nodes: [], links: []}');
                }
                
                this.networkData = jsonData;
                this.processNetworkData();
                this.calculateStatistics();
                
                callback(true);
            } catch (error) {
                console.error('Error parsing network JSON:', error);
                alert('Error parsing network data file. Please check the file format.');
                callback(false);
            }
        };
        
        reader.onerror = () => {
            alert('Error reading network file');
            callback(false);
        };
        
        reader.readAsText(file);
    },
    
    /**
     * Process network data into usable structures
     */
    processNetworkData() {
        console.log('Processing network data...');
        
        const nodes = this.networkData.nodes;
        const links = this.networkData.links;
        
        // Build node lookup
        this.nodesById.clear();
        nodes.forEach(node => {
            // Parse node ID: "2000_1" -> {year: 2000, community: "1"}
            const [year, community] = node.id.split('_');
            node.year = parseInt(year);
            node.communityId = community;
            
            // Update year range
            this.yearRange[0] = Math.min(this.yearRange[0], node.year);
            this.yearRange[1] = Math.max(this.yearRange[1], node.year);
            
            this.nodesById.set(node.id, node);
        });
        
        // Build edge lookup by source
        this.edgesBySource.clear();
        links.forEach(link => {
            if (!this.edgesBySource.has(link.source_id)) {
                this.edgesBySource.set(link.source_id, []);
            }
            this.edgesBySource.get(link.source_id).push(link);
        });
        
        // Generate year list
        this.years = [];
        for (let y = this.yearRange[0]; y <= this.yearRange[1]; y++) {
            this.years.push(y);
        }
        
        console.log(`Processed ${nodes.length} nodes and ${links.length} links`);
        console.log(`Year range: ${this.yearRange[0]} - ${this.yearRange[1]}`);
    },
    
    /**
     * Load community attributes CSV
     */
    loadAttributesData(file, callback) {
        const reader = new FileReader();
        
        reader.onload = (e) => {
            try {
                const csvData = d3.csvParse(e.target.result);
                console.log('Attributes data loaded:', csvData.length, 'records');
                
                this.attributesData = csvData;
                this.processAttributesData();
                
                callback(true);
            } catch (error) {
                console.error('Error parsing attributes CSV:', error);
                alert('Error parsing attributes file. Please check the file format.');
                callback(false);
            }
        };
        
        reader.onerror = () => {
            alert('Error reading attributes file');
            callback(false);
        };
        
        reader.readAsText(file);
    },
    
    /**
     * Process attributes data and organize by year and community
     */
    processAttributesData() {
        if (!this.attributesData) return;
        
        console.log('Processing attributes data...');
        
        this.attributesByYearAndCommunity.clear();
        
        this.attributesData.forEach(row => {
            // Extract year from geo_rcid
            const year = this.extractYearFromGeoRcid(row.geo_rcid);
            const communityId = row.community_level1 || row.community_id;
            
            if (year && communityId) {
                const key = `${year}_${communityId}`;
                
                if (!this.attributesByYearAndCommunity.has(key)) {
                    this.attributesByYearAndCommunity.set(key, []);
                }
                
                this.attributesByYearAndCommunity.get(key).push(row);
            }
        });
        
        console.log(`Processed attributes for ${this.attributesByYearAndCommunity.size} communities`);
    },
    
    /**
     * Extract year from geo_rcid
     * Formats: RC123_2020_City or similar patterns
     */
    extractYearFromGeoRcid(geoRcid) {
        if (!geoRcid) return null;
        
        // Try to match year pattern (20XX)
        const match = geoRcid.match(/_(20\d{2})_/);
        if (match) {
            return parseInt(match[1]);
        }
        
        // Try alternative patterns
        const altMatch = geoRcid.match(/20\d{2}/);
        if (altMatch) {
            return parseInt(altMatch[0]);
        }
        
        return null;
    },
    
    /**
     * Get node with enriched attributes
     */
    getEnrichedNode(nodeId) {
        const node = this.nodesById.get(nodeId);
        if (!node) return null;
        
        // Add attributes if available
        const attributes = this.attributesByYearAndCommunity.get(nodeId);
        if (attributes && attributes.length > 0) {
            node.enrichedAttributes = this.calculateCommunityAttributes(attributes);
        }
        
        return node;
    },
    
    /**
     * Calculate community attributes from individual records
     */
    calculateCommunityAttributes(records) {
        return {
            totalRecords: records.length,
            states: this.calculateDistribution(records, 'real_state'),
            metros: this.calculateDistribution(records, 'real_metro_area'),
            industries: this.calculateDistribution(records, 'naics_industry'),
            rics_k50: this.calculateDistribution(records, 'rics_k50'),
            rics_k200: this.calculateDistribution(records, 'rics_k200'),
            totalWorkforce: d3.sum(records, r => parseInt(r.workforce_total_people) || 0)
        };
    },
    
    /**
     * Calculate distribution for an attribute
     */
    calculateDistribution(records, attribute) {
        const counts = {};
        
        records.forEach(record => {
            const value = record[attribute] || 'Unknown';
            counts[value] = (counts[value] || 0) + 1;
        });
        
        const total = records.length;
        return Object.entries(counts)
            .map(([name, count]) => ({
                name,
                count,
                percentage: ((count / total) * 100).toFixed(1)
            }))
            .sort((a, b) => b.count - a.count);
    },
    
    /**
     * Get outgoing edges for a node
     */
    getOutgoingEdges(nodeId) {
        return this.edgesBySource.get(nodeId) || [];
    },
    
    /**
     * Get nodes by year
     */
    getNodesByYear(year) {
        const nodes = [];
        this.nodesById.forEach(node => {
            if (node.year === year) {
                nodes.push(node);
            }
        });
        return nodes;
    },
    
    /**
     * Calculate statistics
     */
    calculateStatistics() {
        const nodes = Array.from(this.nodesById.values());
        const links = this.networkData.links;
        
        // Year distribution
        const yearDistribution = {};
        nodes.forEach(node => {
            yearDistribution[node.year] = (yearDistribution[node.year] || 0) + 1;
        });
        
        // Degree statistics
        const outDegrees = nodes.map(n => n.out_degree || 0);
        const inDegrees = nodes.map(n => n.in_degree || 0);
        const totalDegrees = nodes.map(n => (n.out_degree || 0) + (n.in_degree || 0));
        
        // Jaccard statistics
        const jaccards = links.map(l => l.jaccard || 0);
        
        this.statistics = {
            totalNodes: nodes.length,
            totalLinks: links.length,
            yearRange: [...this.yearRange],
            years: this.years,
            yearDistribution,
            
            degree: {
                out: {
                    mean: d3.mean(outDegrees),
                    max: d3.max(outDegrees),
                    min: d3.min(outDegrees)
                },
                in: {
                    mean: d3.mean(inDegrees),
                    max: d3.max(inDegrees),
                    min: d3.min(inDegrees)
                },
                total: {
                    mean: d3.mean(totalDegrees),
                    max: d3.max(totalDegrees),
                    min: d3.min(totalDegrees)
                }
            },
            
            jaccard: {
                mean: d3.mean(jaccards),
                median: d3.median(jaccards),
                max: d3.max(jaccards),
                min: d3.min(jaccards)
            },
            
            connectivity: {
                mutualBest: links.filter(l => l.is_mutual_best).length,
                bestForward: links.filter(l => l.is_best_forward).length,
                bestBackward: links.filter(l => l.is_best_backward).length
            }
        };
        
        console.log('Statistics calculated:', this.statistics);
    },
    
    /**
     * Get available years for filtering
     */
    getAvailableYears() {
        return this.years;
    },
    
    /**
     * Filter nodes by criteria
     */
    filterNodes(startYear = null, minDegree = 0, maxNodes = 100) {
        let filtered = Array.from(this.nodesById.values());
        
        // Filter by start year
        if (startYear !== null) {
            filtered = filtered.filter(n => n.year === startYear);
        }
        
        // Filter by degree
        if (minDegree > 0) {
            filtered = filtered.filter(n => 
                (n.out_degree || 0) + (n.in_degree || 0) >= minDegree
            );
        }
        
        // Sort by total degree (descending)
        filtered.sort((a, b) => {
            const degreeA = (a.out_degree || 0) + (a.in_degree || 0);
            const degreeB = (b.out_degree || 0) + (b.in_degree || 0);
            return degreeB - degreeA;
        });
        
        // Limit
        filtered = filtered.slice(0, maxNodes);
        
        console.log(`Filtered to ${filtered.length} nodes`);
        return filtered;
    },
    
    /**
     * Build evolution path from a starting node
     */
    buildEvolutionPath(startNodeId, maxDepth = 5) {
        const path = [];
        let currentNodeId = startNodeId;
        let depth = 0;
        
        while (currentNodeId && depth < maxDepth) {
            const node = this.nodesById.get(currentNodeId);
            if (!node) break;
            
            const edges = this.getOutgoingEdges(currentNodeId);
            if (edges.length === 0) break;
            
            // Find best outgoing edge
            const bestEdge = edges.reduce((best, edge) => {
                return (edge.jaccard > (best.jaccard || 0)) ? edge : best;
            }, edges[0]);
            
            path.push({
                node,
                edge: bestEdge
            });
            
            currentNodeId = bestEdge.target_id;
            depth++;
        }
        
        // Add final node
        if (currentNodeId) {
            const finalNode = this.nodesById.get(currentNodeId);
            if (finalNode) {
                path.push({
                    node: finalNode,
                    edge: null
                });
            }
        }
        
        return path;
    }
};
