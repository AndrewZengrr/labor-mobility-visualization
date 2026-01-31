// Progressive Evolution Data Loader with Attributes Support
const ProgressiveDataLoader = {
    chainData: null,
    attributesData: null,
    processedChains: [],
    attributesByYear: new Map(),
    yearRange: [Infinity, -Infinity],
    statistics: {},
    
    /**
     * Load chain JSON data
     */
    loadChainData(file, callback) {
        const reader = new FileReader();
        
        reader.onload = (e) => {
            try {
                const jsonData = JSON.parse(e.target.result);
                console.log('Chain data loaded:', jsonData.length, 'chains');
                
                this.chainData = jsonData;
                this.processChainData();
                this.calculateStatistics();
                
                callback(true);
            } catch (error) {
                console.error('Error parsing chain JSON:', error);
                alert('Error parsing chain data file. Please check the file format.');
                callback(false);
            }
        };
        
        reader.onerror = () => {
            alert('Error reading chain file');
            callback(false);
        };
        
        reader.readAsText(file);
    },
    
    /**
     * Load community attributes CSV data
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
     * Process chain data into visualization format
     */
    processChainData() {
        console.log('Processing chain data...');
        
        this.processedChains = this.chainData.map((chain, index) => {
            const communities = chain.communities || [];
            
            // Sort by year
            communities.sort((a, b) => a.year - b.year);
            
            // Extract years
            const years = communities.map(c => c.year);
            const startYear = years.length > 0 ? Math.min(...years) : 0;
            const endYear = years.length > 0 ? Math.max(...years) : 0;
            
            // Update global year range
            this.yearRange[0] = Math.min(this.yearRange[0], startYear);
            this.yearRange[1] = Math.max(this.yearRange[1], endYear);
            
            // Extract sizes
            const sizes = communities.map(c => c.attributes?.size || 0);
            const avgSize = sizes.length > 0 ? d3.mean(sizes) : 0;
            const maxSize = sizes.length > 0 ? d3.max(sizes) : 0;
            
            return {
                id: chain.stable_id || `Chain${index}`,
                originalIndex: index,
                length: chain.length || communities.length,
                score: chain.score || 0,
                startYear,
                endYear,
                avgSize: Math.round(avgSize),
                maxSize,
                communities: communities.map((c, cidx) => ({
                    year: c.year,
                    communityId: c.community_id,
                    size: c.attributes?.size || 0,
                    attributes: c.attributes || {},
                    nodeComposition: c.node_composition || {},
                    type: c.node_composition?.type || 'normal',
                    // Add connection info
                    nextYear: cidx < communities.length - 1 ? communities[cidx + 1].year : null,
                    prevYear: cidx > 0 ? communities[cidx - 1].year : null,
                    isStart: cidx === 0,
                    isEnd: cidx === communities.length - 1
                }))
            };
        });
        
        console.log(`Processed ${this.processedChains.length} chains`);
        console.log(`Year range: ${this.yearRange[0]} - ${this.yearRange[1]}`);
    },
    
    /**
     * Process attributes data by year and community
     */
    processAttributesData() {
        if (!this.attributesData) return;
        
        console.log('Processing attributes data...');
        
        // Group by year (if available) or create a lookup by community ID
        this.attributesByYear = new Map();
        
        this.attributesData.forEach(row => {
            // Try to extract year from geo_rcid or other fields
            const geoId = row.geo_rcid || row.id;
            const year = this.extractYearFromId(geoId) || 'unknown';
            
            if (!this.attributesByYear.has(year)) {
                this.attributesByYear.set(year, new Map());
            }
            
            // Get community ID
            const communityId = row.community_level1 || row.community_id;
            
            if (communityId) {
                if (!this.attributesByYear.get(year).has(communityId)) {
                    this.attributesByYear.get(year).set(communityId, []);
                }
                
                this.attributesByYear.get(year).get(communityId).push(row);
            }
        });
        
        console.log(`Processed attributes for ${this.attributesByYear.size} years`);
    },
    
    /**
     * Extract year from ID (if encoded in ID)
     */
    extractYearFromId(id) {
        if (!id) return null;
        
        // Try to match patterns like "RC123_2020" or similar
        const match = id.match(/_(20\d{2})_/);
        if (match) {
            return parseInt(match[1]);
        }
        
        return null;
    },
    
    /**
     * Get enriched community data with attributes
     */
    getEnrichedCommunityData(chainId, year) {
        const chain = this.processedChains.find(c => c.id === chainId);
        if (!chain) return null;
        
        const community = chain.communities.find(c => c.year === year);
        if (!community) return null;
        
        // Merge with attributes data if available
        if (this.attributesByYear.has(year)) {
            const yearData = this.attributesByYear.get(year);
            const communityNodes = yearData.get(community.communityId) || [];
            
            if (communityNodes.length > 0) {
                // Calculate additional composition stats
                community.enrichedAttributes = {
                    totalNodes: communityNodes.length,
                    states: this.calculateDistribution(communityNodes, 'real_state'),
                    metros: this.calculateDistribution(communityNodes, 'real_metro_area'),
                    industries: this.calculateDistribution(communityNodes, 'naics_industry'),
                    rics_k50: this.calculateDistribution(communityNodes, 'rics_k50'),
                    rics_k200: this.calculateDistribution(communityNodes, 'rics_k200')
                };
            }
        }
        
        return community;
    },
    
    /**
     * Calculate distribution for an attribute
     */
    calculateDistribution(nodes, attribute) {
        const counts = {};
        
        nodes.forEach(node => {
            const value = node[attribute] || 'Unknown';
            counts[value] = (counts[value] || 0) + 1;
        });
        
        const total = nodes.length;
        return Object.entries(counts)
            .map(([name, count]) => ({
                name,
                count,
                percentage: ((count / total) * 100).toFixed(1)
            }))
            .sort((a, b) => b.count - a.count);
    },
    
    /**
     * Calculate statistics
     */
    calculateStatistics() {
        const lengths = this.processedChains.map(c => c.length);
        const sizes = this.processedChains.map(c => c.avgSize);
        const scores = this.processedChains.map(c => c.score);
        
        const lengthDistribution = {
            singleton: this.processedChains.filter(c => c.length === 1).length,
            short: this.processedChains.filter(c => c.length >= 2 && c.length <= 4).length,
            medium: this.processedChains.filter(c => c.length >= 5 && c.length <= 9).length,
            long: this.processedChains.filter(c => c.length >= 10 && c.length <= 19).length,
            verylong: this.processedChains.filter(c => c.length >= 20).length
        };
        
        // Calculate start year distribution
        const startYearDistribution = {};
        this.processedChains.forEach(chain => {
            const year = chain.startYear;
            startYearDistribution[year] = (startYearDistribution[year] || 0) + 1;
        });
        
        this.statistics = {
            totalChains: this.processedChains.length,
            yearRange: [...this.yearRange],
            yearSpan: this.yearRange[1] - this.yearRange[0] + 1,
            startYearDistribution,
            
            length: {
                min: d3.min(lengths),
                max: d3.max(lengths),
                mean: d3.mean(lengths),
                median: d3.median(lengths),
                distribution: lengthDistribution
            },
            
            size: {
                min: d3.min(sizes),
                max: d3.max(sizes),
                mean: d3.mean(sizes),
                median: d3.median(sizes)
            },
            
            score: {
                min: d3.min(scores),
                max: d3.max(scores),
                mean: d3.mean(scores),
                median: d3.median(scores)
            }
        };
        
        console.log('Statistics calculated:', this.statistics);
    },
    
    /**
     * Filter chains
     */
    filterChains(startYear = 'all', minLength = 1, maxChains = 50) {
        let filtered = [...this.processedChains];
        
        // Filter by start year
        if (startYear !== 'all') {
            const year = parseInt(startYear);
            filtered = filtered.filter(c => c.startYear === year);
        }
        
        // Filter by length
        filtered = filtered.filter(c => c.length >= minLength);
        
        // Sort by length (longest first)
        filtered.sort((a, b) => b.length - a.length);
        
        // Limit
        filtered = filtered.slice(0, maxChains);
        
        console.log(`Filtered to ${filtered.length} chains`);
        return filtered;
    },
    
    /**
     * Get chain by ID
     */
    getChainById(chainId) {
        return this.processedChains.find(c => c.id === chainId);
    },
    
    /**
     * Get available start years
     */
    getStartYears() {
        const years = [...new Set(this.processedChains.map(c => c.startYear))];
        return years.sort((a, b) => a - b);
    }
};
