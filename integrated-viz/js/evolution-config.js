// Evolution Chain Visualization Configuration
const EvolutionConfig = {
    // Color schemes for different attributes
    colorSchemes: {
        chainLength: d3.scaleOrdinal()
            .domain(['singleton', 'short', 'medium', 'long', 'verylong'])
            .range(['#95a5a6', '#3498db', '#2ecc71', '#f39c12', '#e74c3c']),
        
        communityType: {
            'new_born': '#2ecc71',
            'established': '#3498db',
            'transitional': '#f39c12',
            'normal': '#95a5a6'
        },
        
        default: '#667eea'
    },
    
    // Node sizing
    nodeSizing: {
        minRadius: 8,
        maxRadius: 35,
        sizeAttribute: 'size' // or 'score'
    },
    
    // Layout parameters
    layout: {
        timeline: {
            chainSpacing: 80,  // Vertical spacing between chains
            yearWidth: 100,    // Horizontal spacing for each year
            nodeRadius: 12,
            linkCurve: 0.3     // Bezier curve control
        },
        vertical: {
            laneWidth: 150,
            yearHeight: 80,
            nodeRadius: 15
        },
        force: {
            linkDistance: 100,
            linkStrength: 0.5,
            chargeStrength: -200,
            collisionRadius: 40
        }
    },
    
    // Filters
    filters: {
        lengthCategories: {
            'all': () => true,
            'singleton': (chain) => chain.length === 1,
            'short': (chain) => chain.length >= 2 && chain.length <= 4,
            'medium': (chain) => chain.length >= 5 && chain.length <= 9,
            'long': (chain) => chain.length >= 10 && chain.length <= 19,
            'verylong': (chain) => chain.length >= 20
        }
    },
    
    // Animation
    animation: {
        duration: 750,
        easing: d3.easeCubicInOut
    },
    
    // Tooltip settings
    tooltip: {
        offset: 15,
        maxWidth: 350
    },
    
    // Helper functions
    getChainLengthCategory(length) {
        if (length === 1) return 'singleton';
        if (length <= 4) return 'short';
        if (length <= 9) return 'medium';
        if (length <= 19) return 'long';
        return 'verylong';
    },
    
    getChainColor(length) {
        const category = this.getChainLengthCategory(length);
        return this.colorSchemes.chainLength(category);
    },
    
    getNodeRadius(size, minSize, maxSize) {
        if (!size || !minSize || !maxSize || minSize === maxSize) {
            return this.nodeSizing.minRadius;
        }
        
        const scale = d3.scaleSqrt()
            .domain([minSize, maxSize])
            .range([this.nodeSizing.minRadius, this.nodeSizing.maxRadius]);
        
        return scale(size);
    },
    
    formatPercentage(value) {
        return `${value}%`;
    },
    
    formatNumber(value) {
        return value.toLocaleString();
    }
};
