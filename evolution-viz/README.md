# Community Evolution Chain Visualization - User Guide

## 📋 Overview

This interactive visualization tool displays community evolution chains across time, allowing you to explore how workforce communities transform, split, merge, and evolve over 25 years (2000-2024).

---

## 🚀 Quick Start

### Step 1: Upload Data
1. Open `index.html` in your web browser
2. Click "Choose File" button
3. Upload your `weighted_chain_details_level1.json` file
4. Wait for data to load (should take a few seconds)

### Step 2: Explore Chains
Once loaded, you'll see:
- **Timeline visualization** showing all evolution chains
- **Statistics panel** with chain distribution
- **Control panel** for filtering and layout options
- **Chain list sidebar** (click 📋 button to show/hide)

---

## 🎨 Features

### 1. Three Layout Modes

#### 🕐 Timeline Layout (Default)
- **Best for**: Understanding temporal progression
- **Display**: Horizontal time axis, chains stacked vertically
- **Features**: Clear year-by-year visualization, easy to follow chain evolution

#### 📊 Vertical Lanes Layout  
- **Best for**: Comparing multiple chains side-by-side
- **Display**: Each chain in its own vertical lane
- **Features**: Easy comparison of chain patterns

#### 🔀 Force-Directed Layout
- **Best for**: Exploring complex network structures
- **Display**: Physics-based simulation
- **Features**: Draggable nodes, natural clustering

---

### 2. Filtering Options

#### By Chain Length
- **All Chains**: Display everything
- **Singleton (1 year)**: Chains that only appear once
- **Short (2-4 years)**: Brief evolution patterns
- **Medium (5-9 years)**: Moderate persistence
- **Long (10-19 years)**: Long-term stable communities
- **Very Long (20+ years)**: Ultra-stable communities

#### Sort By
- **Length**: Longest chains first
- **Similarity Score**: Most similar communities first
- **Start Year**: Chronological order
- **Community Size**: Largest communities first

#### Max Chains to Display
- Adjustable from 10 to 500 chains
- **Recommended**: 50-100 for best performance

---

### 3. Interactive Elements

#### Nodes (Circles)
- **Size**: Represents community size (number of companies)
- **Color**: Represents chain length category
- **Click**: Open detailed information panel
- **Hover**: Show quick tooltip

#### Links (Connecting Lines)
- **Curved paths**: Show temporal flow
- **Color**: Matches chain color
- **Hover**: Highlight entire chain

---

### 4. Community Detail Panel

Click any node to see:

#### 📊 Basic Information
- Chain ID
- Year
- Community ID  
- Community Size
- Chain Length
- Community Type (new_born, established, transitional, normal)

#### 👥 Node Composition
- Core Nodes Ratio
- New Nodes Ratio
- Average Node Weight
- Core/New Nodes Count

#### 📍 State Distribution (Top 3)
- Each state with count and percentage
- Visual progress bars

#### 🏙️ Metro Area Distribution (Top 5)
- Major metropolitan areas
- Company counts and percentages

#### 🏭 Industry Distribution
- **NAICS 2-digit**: Broad industry categories (Top 3)
- **NAICS 4-digit**: Specific industries (Top 5)

#### 💼 Top Roles (Top 10)
- Most common job roles in the community
- Count and percentage for each role

---

## 🎯 Navigation & Controls

### Zoom Controls (Top Right)
- **+** : Zoom in
- **−** : Zoom out
- **⊙** : Reset zoom

### Main Buttons
- **Apply Filters**: Update visualization with current filter settings
- **Reset**: Return to default settings
- **🎯 Fit to View**: Auto-adjust zoom to show all chains

### Chain List Sidebar
- **📋 Button**: Toggle sidebar on/off
- **Click chain**: Highlight in main visualization
- **Scroll**: Browse all chains

---

## 💡 Usage Tips

### For Best Performance
1. Start with **50 chains** max
2. Use **Timeline layout** for initial exploration
3. Filter by length category before increasing max chains
4. Use **Fit to View** after changing filters

### Understanding Color Coding
- **Gray**: Singleton chains (1 year)
- **Blue**: Short chains (2-4 years)
- **Green**: Medium chains (5-9 years)
- **Orange**: Long chains (10-19 years)
- **Red**: Very long chains (20+ years)

### Exploring Patterns
1. **Find stable communities**: Filter by "Long" or "Very Long"
2. **Track transformations**: Click nodes to see attribute changes
3. **Compare similar chains**: Use Vertical Lanes layout
4. **Identify transitions**: Look for node composition changes

---

## 📊 Understanding the Data

### Community Types
- **new_born**: >70% new nodes, recently formed
- **established**: >60% core nodes, stable and mature
- **transitional**: <30% core nodes, undergoing change
- **normal**: Mixed composition, regular evolution

### Node Weights
- **High weight (>0.7)**: Core, long-standing members
- **Low weight (<0.3)**: New, recently joined members
- Represents temporal stability of nodes

### Similarity Score
- Range: 0 to 1
- **High score**: Communities share many common nodes
- **Low score**: Significant change between years

---

## 🔍 Example Workflows

### Workflow 1: Find Longest-Running Communities
1. Set "Filter by Length" to "Very Long (20+ years)"
2. Sort by "Length"
3. Click nodes to explore their composition
4. Look for consistent industry/location patterns

### Workflow 2: Analyze Industry Transitions
1. Select any chain
2. Click first year node → note NAICS codes
3. Click last year node → compare NAICS codes
4. Identify industry shifts

### Workflow 3: Geographic Mobility Analysis
1. Filter to "Long" chains
2. For each chain, compare:
   - Start state vs. end state
   - Start metro vs. end metro
3. Identify geographic clustering patterns

### Workflow 4: Community Growth Patterns
1. Sort by "Size"
2. Click large community nodes
3. Check node composition (core vs. new ratio)
4. Identify growth strategies (organic vs. merger)

---

## 🐛 Troubleshooting

### "File upload failed"
- **Check**: File must be JSON format
- **Check**: File name should be `weighted_chain_details_level1.json`
- **Try**: Re-generate the file from your Python script

### "Visualization is too crowded"
- **Reduce**: Max chains to 20-30
- **Use**: Length filter to focus on specific categories
- **Try**: Fit to View button

### "Page is slow/unresponsive"
- **Reduce**: Number of displayed chains
- **Avoid**: Displaying 200+ chains at once
- **Try**: Filter to specific year range

### "Can't see chain labels"
- **Zoom in**: Use + button
- **Hover**: Over chains to see tooltips
- **Use**: Chain list sidebar

---

## 📁 File Structure

```
evolution-viz/
├── index.html                          # Main HTML file
├── css/
│   └── evolution-styles.css           # All styles
└── js/
    ├── evolution-config.js            # Configuration
    ├── evolution-data-loader.js       # Data processing
    ├── evolution-visualizer.js        # Visualization logic
    ├── evolution-detail-panel.js      # Detail panel
    └── evolution-app.js               # Main application
```

---

## 🎓 Advanced Features

### Custom Filtering (Developer)
Edit `evolution-config.js` to add custom filter categories:

```javascript
filters: {
    lengthCategories: {
        'custom': (chain) => chain.avgSize > 100 && chain.length > 10
    }
}
```

### Color Customization
Modify color schemes in `evolution-config.js`:

```javascript
colorSchemes: {
    chainLength: d3.scaleOrdinal()
        .domain(['singleton', 'short', 'medium', 'long', 'verylong'])
        .range(['#color1', '#color2', '#color3', '#color4', '#color5'])
}
```

---

## 📞 Support

For issues or questions:
1. Check this documentation
2. Review browser console for errors (F12)
3. Verify JSON file format matches expected structure

---

## 📝 Data Format Requirements

Your JSON file should have this structure:

```json
[
  {
    "stable_id": "S0",
    "length": 10,
    "score": 0.75,
    "communities": [
      {
        "year": 2000,
        "community_id": "1",
        "attributes": {
          "size": 150,
          "top3_states": [...],
          "top5_metros": [...],
          "top3_naics_2digit": [...],
          "top5_naics_4digit": [...],
          "top10_roles": [...]
        },
        "node_composition": {
          "type": "established",
          "core_node_ratio": 0.8,
          "new_node_ratio": 0.1,
          ...
        }
      },
      ...
    ]
  },
  ...
]
```

---

**Enjoy exploring your community evolution chains!** 🎉
