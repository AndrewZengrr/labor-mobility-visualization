// Global Configuration - Improved for dynamic hierarchy levels
const Config = {
    // Color schemes - 每个类型内部使用对比明显的不同颜色
    colorSchemes: {
        // NAICS Industry - 多色系组合
        naics_industry: [
            '#7c9fb0', '#a8b899', '#c4a587', '#a892b5', '#b58e92',
            '#7ea5a0', '#b5a991', '#88b08e', '#9e8ba3', '#8faab8',
            '#c9b8a5', '#95b89a', '#b5a0c2', '#ceb296', '#6b8b9e',
            '#8f9a7e', '#a88f9b', '#7f9990', '#b89f8e', '#9b8fa8',
            '#88a3b1', '#a3b385', '#c2a895', '#9e8ba8', '#b59598'
        ],
        // State - 多色系组合
        real_state: [
            '#88b08e', '#7c9fb0', '#c4a587', '#a892b5', '#7ea5a0',
            '#b5a991', '#b58e92', '#8faab8', '#a8b899', '#9e8ba3',
            '#95b89a', '#b5a0c2', '#ceb296', '#6b8b9e', '#c9b8a5',
            '#8f9a7e', '#a88f9b', '#7f9990', '#b89f8e', '#9b8fa8',
            '#a3b385', '#c2a895', '#9e8ba8', '#b59598', '#88a3b1',
            '#a8c9ad', '#a4c7c3', '#d9c4ad', '#c7b8d4', '#9ec0bc',
            '#d4cbb8', '#d4b5b8', '#a8c5d4', '#c5d4bd', '#c4a0a5',
            '#b8d4bc', '#b5ccd8', '#e0d3bf', '#d4c5db', '#b8d4d1',
            '#e8e1d4', '#dbc5c7', '#d4e3eb', '#e0ebdb', '#e5d6d8',
            '#dae8dc', '#c0d6df', '#d9d0c1', '#ddd4e5', '#c9dedd',
            '#f0e7db', '#ede3e4', '#e1e7f0', '#dae5d3', '#e8e0ed'
        ],
        // Metro Area - 多色系组合
        real_metro_area: [
            '#c4a587', '#88b08e', '#7c9fb0', '#a892b5', '#b58e92',
            '#7ea5a0', '#ceb296', '#95b89a', '#8faab8', '#b5a0c2',
            '#b5a991', '#6b8b9e', '#a8b899', '#9e8ba3', '#c9b8a5',
            '#8f9a7e', '#a88f9b', '#7f9990', '#b89f8e', '#9b8fa8',
            '#c2a895', '#a3b385', '#88a3b1', '#9e8ba8', '#b59598',
            '#d9c4ad', '#a8c9ad', '#a4c7c3', '#c7b8d4', '#d4b5b8',
            '#9ec0bc', '#e0d3bf', '#b8d4bc', '#a8c5d4', '#d4c5db',
            '#d4cbb8', '#b5ccd8', '#c5d4bd', '#c4a0a5', '#b8d4d1',
            '#e8e1d4', '#dae8dc', '#d4e3eb', '#ddd4e5', '#dbc5c7',
            '#c0d6df', '#e0ebdb', '#c9dedd', '#e5d6d8', '#d9d0c1',
            '#f0e7db', '#dae5d3', '#e1e7f0', '#e8e0ed', '#ede3e4'
        ],
        // RICS variations
        rics_k50: [
            '#a892b5', '#88b08e', '#7c9fb0', '#c4a587', '#7ea5a0',
            '#b58e92', '#b5a0c2', '#95b89a', '#8faab8', '#ceb296',
            '#b5a991', '#9e8ba3', '#a8b899', '#6b8b9e', '#c9b8a5',
            '#8f9a7e', '#a88f9b', '#7f9990', '#b89f8e', '#9b8fa8',
            '#9e8ba8', '#a3b385', '#88a3b1', '#c2a895', '#b59598'
        ],
        rics_k200: [
            '#b58e92', '#7c9fb0', '#88b08e', '#a892b5', '#c4a587',
            '#7ea5a0', '#c4a0a5', '#8faab8', '#95b89a', '#b5a0c2',
            '#b5a991', '#dbc5c7', '#a8b899', '#9e8ba3', '#ceb296',
            '#6b8b9e', '#c9b8a5', '#8f9a7e', '#a88f9b', '#7f9990',
            '#b89f8e', '#9b8fa8', '#b59598', '#88a3b1', '#c2a895'
        ],
        rics_k400: [
            '#7ea5a0', '#88b08e', '#7c9fb0', '#c4a587', '#a892b5',
            '#b58e92', '#9ec0bc', '#95b89a', '#8faab8', '#ceb296',
            '#b5a991', '#b5a0c2', '#a8b899', '#9e8ba3', '#c9b8a5',
            '#6b8b9e', '#8f9a7e', '#a88f9b', '#7f9990', '#b89f8e',
            '#9b8fa8', '#a3b385', '#88a3b1', '#c2a895', '#9e8ba8'
        ]
    },
    
    // NAICS 2位代码到行业的映射
    naicsMapping: {
        '11': 'Agriculture, Forestry, Fishing and Hunting',
        '21': 'Mining, Quarrying, and Oil and Gas Extraction', 
        '22': 'Utilities',
        '23': 'Construction',
        '31': 'Manufacturing',
        '32': 'Manufacturing', 
        '33': 'Manufacturing',
        '42': 'Wholesale Trade',
        '44': 'Retail Trade',
        '45': 'Retail Trade',
        '48': 'Transportation and Warehousing',
        '49': 'Transportation and Warehousing',
        '51': 'Information',
        '52': 'Finance and Insurance',
        '53': 'Real Estate and Rental and Leasing',
        '54': 'Professional, Scientific, and Technical Services',
        '55': 'Management of Companies and Enterprises',
        '56': 'Administrative and Support and Waste Management',
        '61': 'Educational Services',
        '62': 'Health Care and Social Assistance',
        '71': 'Arts, Entertainment, and Recreation',
        '72': 'Accommodation and Food Services',
        '81': 'Other Services (except Public Administration)',
        '92': 'Public Administration'
    },
    
    // Visualization configuration
    viz: {
        minNodeSize: 8,
        maxNodeSize: 40,
        linkWidth: 2,
        linkOpacity: 0.5,
        treeMargin: 50
    },
    
    // Composition analysis configuration
    composition: {
        categories: [
            { key: 'naics_industry', title: 'Industry Distribution (NAICS)', colorScheme: null },
            { key: 'real_state', title: 'State Distribution', colorScheme: null },
            { key: 'real_metro_area', title: 'Metro Area Distribution', colorScheme: null },
            { key: 'rics_k50', title: 'RICS K50 Distribution', colorScheme: null },
            { key: 'rics_k200', title: 'RICS K200 Distribution', colorScheme: null }
        ],
        treemapHeight: 220,
        topN: 5
    },
    
    // Attribute labels
    attributeLabels: {
        'naics_industry': 'Industry (NAICS)',
        'real_state': 'State',
        'real_metro_area': 'Metro Area',
        'rics_k50': 'RICS K50',
        'rics_k200': 'RICS K200',
        'rics_k400': 'RICS K400'
    },
    
    // ✅ NEW: Dynamic hierarchy detection
    maxLevels: 3,  // Will be updated when data is loaded
    
    // Helper function: Convert NAICS code to industry name
    getNAICSIndustry(naicsCode) {
        if (!naicsCode || naicsCode === 'unknown' || naicsCode === 'Unknown') {
            return 'Unknown';
        }
        
        const code2digit = String(naicsCode).substring(0, 2);
        return this.naicsMapping[code2digit] || `Other Industry (${code2digit})`;
    },
    
    // Helper function: Get color scale for attribute
    getColorScale(attribute) {
        if (this.colorSchemes[attribute]) {
            return d3.scaleOrdinal(this.colorSchemes[attribute]);
        }
        return d3.scaleOrdinal(d3.schemeCategory10);
    },
    
    // ✅ NEW: Detect maximum hierarchy levels from data
    detectMaxLevels(data) {
        let maxLevel = 0;
        const sampleRow = data[0];
        
        // Count community_level columns
        for (let i = 1; i <= 20; i++) {  // Check up to 20 levels
            if (sampleRow.hasOwnProperty(`community_level${i}`)) {
                maxLevel = i;
            } else {
                break;
            }
        }
        
        this.maxLevels = maxLevel;
        console.log(`Detected maximum hierarchy levels: ${maxLevel}`);
        return maxLevel;
    }
};