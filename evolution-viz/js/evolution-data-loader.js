// Evolution Chain Data Loader
const EvolutionDataLoader = {
    rawData: null,
    processedChains: [],
    yearRange: [Infinity, -Infinity],
    statistics: {},
    
    /**
     * Load and parse chain data from JSON file
     */
    loadChainData(file, callback) {
        const reader = new FileReader();
        
        reader.onload = (e) => {
            try {
                const jsonData = JSON.parse(e.target.result);
                console.log('Raw data loaded:', jsonData.length, 'chains');
                
                this.rawData = jsonData;
                this.processChainData();
                this.calculateStatistics();
                
                callback(true);
            } catch (error) {
                console.error('Error parsing JSON:', error);
                alert('Error parsing chain data file. Please check the file format.');
                callback(false);
            }
        };
        
        reader.onerror = () => {
            alert('Error reading file');
            callback(false);
        };
        
        reader.readAsText(file);
    },
    
    /**
     * Process raw chain data into visualization-friendly format
     */
    processChainData() {
        console.log('Processing chain data...');
        
        this.processedChains = this.rawData.map((chain, index) => {
            const communities = chain.communities || [];
            
            // Extract years and community IDs
            const years = communities.map(c => c.year);
            const startYear = years.length > 0 ? Math.min(...years) : 0;
            const endYear = years.length > 0 ? Math.max(...years) : 0;
            
            // Update global year range
            this.yearRange[0] = Math.min(this.yearRange[0], startYear);
            this.yearRange[1] = Math.max(this.yearRange[1], endYear);
            
            // Extract sizes and scores
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
                communities: communities.map(c => ({
                    year: c.year,
                    communityId: c.community_id,
                    size: c.attributes?.size || 0,
                    attributes: c.attributes || {},
                    nodeComposition: c.node_composition || {},
                    type: c.node_composition?.type || 'normal'
                }))
            };
        });
        
        console.log(`Processed ${this.processedChains.length} chains`);
        console.log(`Year range: ${this.yearRange[0]} - ${this.yearRange[1]}`);
    },
    
    /**
     * Calculate overall statistics
     */
    calculateStatistics() {
        const lengths = this.processedChains.map(c => c.length);
        const sizes = this.processedChains.map(c => c.avgSize);
        const scores = this.processedChains.map(c => c.score);
        
        // Length distribution
        const lengthDistribution = {
            singleton: this.processedChains.filter(c => c.length === 1).length,
            short: this.processedChains.filter(c => c.length >= 2 && c.length <= 4).length,
            medium: this.processedChains.filter(c => c.length >= 5 && c.length <= 9).length,
            long: this.processedChains.filter(c => c.length >= 10 && c.length <= 19).length,
            verylong: this.processedChains.filter(c => c.length >= 20).length
        };
        
        this.statistics = {
            totalChains: this.processedChains.length,
            yearRange: [...this.yearRange],
            yearSpan: this.yearRange[1] - this.yearRange[0] + 1,
            
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
     * Filter chains based on criteria
     */
    filterChains(lengthFilter = 'all', sortBy = 'length', maxChains = 100) {
        let filtered = [...this.processedChains];
        
        // Apply length filter
        if (lengthFilter !== 'all') {
            const filterFunc = EvolutionConfig.filters.lengthCategories[lengthFilter];
            if (filterFunc) {
                filtered = filtered.filter(filterFunc);
            }
        }
        
        // Sort
        switch (sortBy) {
            case 'length':
                filtered.sort((a, b) => b.length - a.length);
                break;
            case 'score':
                filtered.sort((a, b) => b.score - a.score);
                break;
            case 'start_year':
                filtered.sort((a, b) => a.startYear - b.startYear);
                break;
            case 'size':
                filtered.sort((a, b) => b.avgSize - a.avgSize);
                break;
        }
        
        // Limit number of chains
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
     * Get community details
     */
    getCommunityDetails(chainId, year) {
        const chain = this.getChainById(chainId);
        if (!chain) return null;
        
        return chain.communities.find(c => c.year === year);
    }
};
