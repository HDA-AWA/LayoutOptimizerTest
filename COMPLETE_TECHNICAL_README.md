# Room Layout Optimization System - Complete Technical Documentation

## System Overview

This system validates and optimizes bedroom layouts for wheelchair accessibility compliance based on DIN 18040-2 standards. The workflow consists of four main components:

```
INPUT LAYOUT → VALIDATOR → OPTIMIZER → COST VALIDATOR → OUTPUT LAYOUT
     ↓              ↓             ↓             ↓              ↓
  room.json    violations    optimized.json  cost analysis  final.json
```

**Purpose:** Take a poorly arranged room layout and automatically rearrange furniture to comply with wheelchair accessibility standards while minimizing a multi-objective cost function.

---

# PART 1: VALIDATOR (validator.py)

## Overview
The validator checks room layouts against DIN 18040-2 (German standard for barrier-free residential construction). It identifies all violations where the layout fails to meet accessibility requirements. Returns a list of human-readable violation strings.

## DIN 18040-2 Standards Implemented
- **150cm clearance** in front of all furniture (wheelchair approach space)
- **150×150cm turning space** somewhere in room (wheelchair 360° rotation)
- **90cm door swing** clearance (unobstructed door opening arc)
- **90cm emergency path** from bed to door (evacuation route)
- **Bed side clearances:** At least one long side with 150cm clearance (wheelchair transfer)
- **Window heights:** Sill 60-110cm, handle ≤140cm (reach from wheelchair)
- **Furniture heights:** Work surfaces 75-85cm, seating 46-50cm (wheelchair compatibility)
- **Bedside reach:** ≤60cm horizontal distance, ≤15cm height difference from bed

## Core Functions

### __init__(self, layout)
Initializes validator with room dimensions, furniture list, and openings (doors/windows). Stores these as instance variables for all validation checks to access.

### validate(self)
Master orchestration function that calls all 10 validation check functions in sequence. Collects all violations into a single list and returns it. This is the only public method users call.

### _get_furniture_polygon(self, item)
Converts furniture item (x, y, width, height, rotation) into a Shapely polygon object. Handles rotation by rotating the rectangle around its center point. Polygons enable geometric operations like intersection testing.

### _check_overlaps(self)
Checks all unique furniture pairs to detect physical overlaps. Uses nested loops (O(n²) complexity) to test every combination. Returns violation string for each overlapping pair found.

### _check_clearances(self)
For each furniture item, creates a 150cm clearance zone in front based on rotation angle. Checks if any other furniture intersects this zone or if the zone extends outside room bounds. Critical for wheelchair approach space.

### _get_clearance_zone(self, item, clearance)
Helper function that creates the 150cm clearance rectangle based on furniture rotation. Rotation 0° = clearance below, 90° = left, 180° = above, 270° = right. Returns Shapely box polygon.

### _check_turning_space(self)
Searches room using 50cm grid to find at least one 150×150cm square completely free of furniture. Uses grid search (not exhaustive) for performance. If no space found anywhere, returns turning space violation.

### _check_door_swing(self)
Creates a 90cm radius circular arc at door position, clipped to room interior. Checks if any furniture intersects this arc. Door must swing freely without hitting furniture for safe passage.

### _get_door_swing_zone(self, door)
Helper that creates door swing arc polygon. Uses Shapely Point.buffer() to create circle, then clips to semicircle inside room based on which wall the door is on.

### _check_emergency_path(self)
Draws straight line from bed center to door center, buffered to 90cm width. Checks if any furniture (except bed itself) blocks this corridor. Ensures wheelchair can evacuate quickly in emergency.

### _get_door_center(self, door)
Calculates center point coordinates of door opening based on wall position and door size. Used for emergency path and other door-related calculations.

### _check_bed_clearances(self)
Determines which sides of bed are "long sides" based on rotation. Creates 150cm clearance zones for each long side. Requires at least ONE long side to have complete clearance within room bounds and unblocked by furniture.

### _check_window_clearances(self)
Creates 150cm operation zone in front of each window. Checks if furniture blocks this zone, with smart exceptions: allows low furniture under high sills, gives INFO warnings for study furniture (natural light priority), hard violations for tall immobile furniture.

### _get_window_operation_zone(self, window, clearance)
Helper that creates window clearance rectangle based on which wall window is on. Returns 150cm deep zone extending into room from window position.

### _check_window_reachability(self)
Validates window sill heights (60-110cm range) and handle heights (≤140cm). These limits ensure wheelchair users can see out window while seated and reach handles to operate window.

### _check_window_access_path(self)
Creates 90cm wide approach path to each window. Checks if large/immobile furniture blocks this path. Skips small mobile items like chairs. Ensures wheelchair can physically reach window.

### _get_window_centroid(self, window)
Calculates center point of window opening based on wall, position, and size. Used for distance calculations and approach path generation.

### _get_window_approach_zone(self, window, width)
Creates 90cm wide rectangular approach zone perpendicular to window. Returns Shapely box extending specified distance into room from window.

### _check_furniture_heights(self)
Validates z-height of furniture against DIN 18040-2 standards. Work surfaces must be 75-85cm (wheelchair clearance underneath), seating 46-50cm (transfer height), bedside tables 40-60cm (reachable from bed), storage ≤140cm (reach limit).

### _check_reach_heights(self)
Specifically validates bedside table placement. Checks horizontal distance from bed center (≤60cm reachable from lying position) and height compatibility with bed (≤15cm difference for easy reach).

### _check_door_width(self)
Validates door width meets 90cm minimum (DIN 18040-2 requirement) or 100cm recommended. Generates hard violation if <90cm, INFO message if 90-100cm.

## Output
Returns list of violation strings like: "Overlap: Bed overlaps Study Table", "Clearance violation: Wardrobe needs 150cm clearance but blocked by Sofa", "No 150×150cm turning space available", "Window sill too high: 120cm (should be ≤110cm)"

---

# PART 2: TEST-VALIDATOR (test-validator.py)

## Overview
Simple command-line test harness for validator. Takes one layout JSON file as argument, runs all validation checks, and displays categorized results.

## Functions

### test_layout(filename)
Loads JSON layout file, instantiates LayoutValidator, runs validate(), and prints results grouped by violation category (Overlaps, Clearances, Bed Clearances, Turning Space, Door, Emergency Path, Windows).

### main()
Parses command line arguments to get input filename. Calls test_layout() with provided file. Handles missing arguments by showing usage instructions.

## Usage
Run with: `python test-validator.py room-layout.json`. Output shows total violation count and categorized list of all violations found.

---

# PART 3: OPTIMIZER (optimizer.py)

## Overview
Takes a layout with violations and generates an improved layout by strategically repositioning furniture. Uses rule-based placement strategies guided by functional relationships and accessibility requirements. Attempts to maximize furniture placement while minimizing violations.

## Core Classes

### ViolationTracker
Tracks violations throughout optimization process. Records initial violations before optimization and final violations after. Provides before/after comparison showing which violations were fixed.

#### set_initial(self, layout)
Runs validator on initial layout and stores violation list. Returns initial violations for reporting.

#### finalize(self, final_layout)
Runs validator on optimized layout. Compares with initial violations to determine which were fixed. Returns dictionary with counts and categorized lists.

#### get_summary(self)
Categorizes violations into groups (Overlaps, Clearances, Bed Clearances, Turning Space, Door, Emergency Path, Windows, Heights). Returns separate categorized lists for initial, fixed, and remaining violations.

### LayoutOptimizer
Main optimization class that generates improved layouts using heuristic placement rules.

## Optimizer Functions

### __init__(self, input_layout)
Stores room dimensions, furniture list, and openings. Initializes ViolationTracker. Prepares data structures for optimization process.

### optimize(self, max_iterations=200)
Master optimization loop. Analyzes initial violations, then generates up to 200 candidate layouts using randomized placement strategies. Tracks best layout found (most furniture placed with fewest violations). Returns best layout after all iterations or when perfect layout found.

### _generate_layout(self, door, windows)
Creates single candidate layout by placing all furniture items sequentially. Uses specific placement strategies for each furniture type: bed first (away from door), bedsides next (adjacent to bed), wardrobes on walls, tables near windows, chairs with tables, sofas on walls.

### _place_bed(self, bed, door, layout)
Places bed on wall opposite from door (preferred) or tries all walls. Tests multiple positions along each wall. Returns bed with valid position or None if placement impossible.

### _place_bedside_near_bed(self, bedside, bed, layout)
Places bedside table at bed's headboard. Tries multiple positions at head end based on bed rotation: sides and corners of headboard area. Critical for maintaining functional relationship and reach requirements.

### _place_table_near_window(self, table, window, layout, door)
Positions study table near window for natural light. Tries multiple distances (50-200cm) from window. Orients table facing window. Respects door clearances and checks for overlaps.

### _place_chair_with_table(self, chair, table, layout, door)
Places chair pulled out from table based on table orientation. Calculates proper position and rotation for user to sit at table. Maintains functional pairing of table and chair.

### _place_on_wall_flexible(self, furniture, layout, door)
Generic wall placement for large furniture (wardrobes, sofas). Tries all four walls in random order, testing multiple positions along each. Returns first valid placement found.

### _place_anywhere_grid(self, furniture, layout, door)
Fallback placement strategy using 50cm grid search across entire room. Tries multiple rotations at each position. Used when specialized placement strategies fail.

### _get_wall_positions(self, item, wall, count=5)
Generates list of candidate positions along specified wall. Distributes positions evenly with proper margin from corners. Returns (x, y, rotation) tuples appropriate for that wall.

### _blocks_door(self, furniture, door)
Checks if furniture blocks 120cm door clearance zone. Creates rectangular clearance area extending from door based on wall position. Returns True if furniture intersects this critical zone.

### _analyze_unplaced(self, layout)
Compares final layout furniture count with input. Identifies which specific items couldn't be placed. Stores unplaced items and prints recommendations for user.

### get_violation_report(self)
Retrieves categorized violation summary from ViolationTracker. Returns dictionary with initial, fixed, and remaining violations organized by category, plus list of unplaced furniture.

### _check_bounds(self, item)
Simple bounds check ensuring furniture is completely within room dimensions. Prevents furniture from extending outside walls.

### _is_valid(self, item, layout, door)
Combined validation check for proposed furniture placement. Tests door blocking (except for bedsides) and overlaps with existing furniture. Returns True only if placement passes both tests.

### _get_polygon(self, item)
Converts furniture item to Shapely polygon accounting for rotation. Used for geometric overlap testing and spatial calculations.

### _count_violations(self, layout)
Instantiates LayoutValidator and runs full validation. Returns violation count for comparing candidate layouts. Used to rank optimization attempts.

## Optimization Strategy
The optimizer uses a greedy heuristic approach with randomization: (1) Places furniture in priority order (bed → bedsides → wardrobes → tables → chairs → sofas), (2) Uses specialized placement logic for each furniture type, (3) Randomizes placement within constraints for variety, (4) Generates many candidates (200 iterations) to find best solution, (5) Prioritizes: maximum furniture placed first, minimum violations second.

---

# PART 4: TEST-OPTIMIZER (test-optimizer.py)

## Overview
Test harness for running optimizer on layout files. Can process single files or batches. Provides detailed before/after analysis including violation reports and distance measurements for functional pairs (e.g., bed-bedside distance).

## Functions

### calculate_distance(item1, item2)
Calculates Euclidean distance between centers of two furniture items. Used to verify functional relationships (bedside should be ≤60cm from bed). Returns distance in centimeters.

### print_all_violations(violations_dict, title)
Pretty-prints categorized violations without truncation. Shows category headers with counts and bullet lists of all violations in each category.

### process_layout(input_file, output_folder)
Main processing function. Loads input layout, runs optimizer, analyzes output, checks critical distances (bed-bedside), retrieves violation report, and saves optimized layout to output folder. Prints comprehensive before/after comparison.

### process_single()
Single file mode. Processes one layout specified in SINGLE_INPUT configuration variable. Good for testing and debugging individual layouts.

### process_batch()
Batch mode. Finds all JSON files in BATCH_INPUT_FOLDER, processes each one through optimizer, collects results, and prints summary statistics (success count, failure count, failed files list).

### main()
Entry point that checks MODE configuration variable (single vs batch) and dispatches to appropriate processing function.

## Configuration Variables
MODE: 'single' or 'batch', SINGLE_INPUT: Path to layout file for single mode, BATCH_INPUT_FOLDER: Folder containing multiple layouts for batch mode, OUTPUT_FOLDER: Where optimized layouts are saved, MAX_ITERATIONS: Number of optimization attempts (default 200)

## Usage
Configure variables at top of script, then run: `python test-optimizer.py`. Output includes detailed violation reports (initial → fixed → remaining) and distance measurements for functional pairs.

---

# PART 5: COST VALIDATOR (cost_validator.py)

## Overview
Implements Multi-Objective Unequal-Area Facility Layout Problem (UA-FLP) cost function to quantitatively evaluate layout quality. Provides scientific validation by comparing original and optimized layouts using weighted sum of five cost components.

## Cost Function Formula
C_total(L) = w₁·C_flow + w₂·C_zone + w₃·C_env + w₄·C_clearance + w₅·C_vis. Each C component measures a different optimization objective, and w weights represent relative importance.

## CostFunctionValidator Class

### __init__(self, layout_data)
Stores room dimensions, furniture, and openings. Calls _calculate_zones() to determine functional zone centroids based on room geometry and door position.

### _calculate_zones(self)
Divides room into three functional zones (Private Zone 1 for sleeping, Private Zone 2 for working, Shared Zone for socializing). Calculates ideal centroid for each zone based on door wall. Stores which furniture types belong in each zone.

### get_centroid(self, item)
Calculates geometric center point of furniture item. Returns (x, y) tuple used for distance calculations.

### euclidean_distance(self, point1, point2)
Computes straight-line distance between two points using Pythagorean theorem. Used throughout cost calculations.

### get_furniture_polygon(self, item)
Converts furniture to Shapely polygon with rotation. Enables geometric operations for cost calculations.

## Cost Component 1: C_flow (Flow and Adjacency)

### calculate_flow_cost(self)
Implements: Σ(i,j) A_ij · d(c_i, c_j)². Sums squared distances between all furniture pairs, weighted by their affinity scores. High affinity pairs (bed-bedside, table-chair) contribute large penalties if separated. Minimizes distance between functionally related items.

### _get_affinity(self, name1, name2)
Looks up predefined affinity score for furniture pair from AFFINITY_MATRIX. Returns 0-100 value indicating how important it is for items to be close (100 = critical like bed-bedside, 0 = unrelated).

## Cost Component 2: C_zone (Zoning)

### calculate_zone_cost(self)
Implements: Σ(i∈Z₁) d(c_i, μ₁)² + Σ(j∈Z₂) d(c_j, μ₂)² + Σ(k∈Z_S) d(c_k, μ_S)². Sums squared distances from each furniture item to its designated zone centroid. Penalizes furniture placed far from intended functional areas.

### _get_item_zone(self, furniture_name)
Determines which functional zone a furniture type belongs to based on name matching. Returns 'private1', 'private2', 'shared', or None.

## Cost Component 3: C_env (Environmental)

### calculate_environmental_cost(self)
Implements: Σ(k) P_window(f_k) + Σ(m) P_light(f_m). Adds fixed penalties for tall furniture blocking windows plus distance-based penalties for work surfaces far from windows. Optimizes natural light access.

### _is_tall_furniture(self, item)
Checks if furniture z-height exceeds 140cm. Tall items (wardrobes) should not block windows.

### _needs_natural_light(self, item)
Identifies work surfaces (study tables, desks) that benefit from window proximity for task lighting.

### _blocks_window(self, item, window)
Tests if furniture polygon intersects window clearance zone. Returns True if obstruction detected.

### _get_window_zone(self, window)
Creates 50cm buffer zone around window opening. Used for obstruction testing.

### _find_nearest_window(self, item, windows)
Finds closest window to furniture item by comparing distances to all windows. Returns nearest window object.

### _get_window_centroid(self, window)
Calculates center point of window opening based on wall position and window size.

## Cost Component 4: C_clearance (Ergonomic and Access)

### calculate_clearance_cost(self)
Implements: Σ(d∈Doors) P_overlap(L, Z_swing_d) + Σ(c∈Chairs) P_overlap(L, Z_pullout_c). Applies very large penalties (100,000+) for blocking critical movement zones. Enforces hard accessibility constraints.

### _get_door_swing_zone(self, door)
Creates 90cm radius arc at door plus 50cm buffer. Represents space needed for door to swing open safely. Uses Shapely buffer and intersection operations.

### _get_chair_pullout_zone(self, chair)
Creates 80cm depth zone behind chair based on rotation. Represents space needed for person to pull out chair and sit down.

## Cost Component 5: C_vis (Aesthetics)

### calculate_aesthetics_cost(self)
Implements: Σ(k) P_view_block(f_k) + Σ(l) P_central_placement(f_l). Penalizes furniture blocking sight lines and wall furniture placed in room center. Maintains visual order and line-of-sight.

### _blocks_line_of_sight(self, point1, point2, item)
Creates line segment between two points and tests if furniture polygon intersects it. Used to check view blocking from sofa to window.

### _should_be_against_wall(self, item)
Identifies large furniture (wardrobes, closets, shelves) that conventionally belong against walls.

### _is_in_room_center(self, item)
Checks if furniture centroid is more than 100cm from all walls. Identifies centrally placed items.

## Total Cost Calculation

### calculate_total_cost(self)
Computes all five component costs, applies weights, and sums to get total weighted cost. Returns dictionary containing raw component costs, weighted costs, weights used, and total cost. This is the main output used for layout comparison.

## Comparison and Reporting

### compare_layouts(original_file, optimized_file)
Loads two layout files, calculates costs for both, compares results, and generates detailed report. Prints component-by-component comparison, weighted costs, total improvement percentage, and identifies which components improved vs degraded. Provides thesis-ready statistical summary.

---

# PART 6: BATCH COST VALIDATOR (batch_cost_validator.py)

## Overview
Statistical analysis tool for validating optimizer across multiple layout pairs. Computes aggregate statistics (mean, std dev, confidence intervals) and significance tests. Generates thesis-ready reporting text.

## Functions

### find_layout_pairs(folder_path)
Scans folder for JSON files, identifies original/optimized pairs by filename pattern (layout.json + layout-optimized.json). Returns list of (original_path, optimized_path) tuples.

### calculate_improvement(original_file, optimized_file)
Loads layout pair, runs CostFunctionValidator on both, calculates total improvement percentage and component-wise improvements. Returns (total_improvement, component_dict) or (None, None) on error.

### batch_validate(folder_path)
Main statistical analysis function. Finds all layout pairs, processes each one, collects improvement percentages, computes statistics (mean, median, std dev, percentiles), calculates 95% confidence interval, performs one-sample t-test for significance, computes success rate, and generates component-wise statistics table. Outputs thesis-ready text with sample size, effect size (Cohen's d), and formatted results.

---

# PART 7: VISUALIZE COSTS (visualize_costs.py)

## Overview
Generates publication-quality figures (300 DPI) for thesis. Creates four visualization types comparing original vs optimized layouts.

## Functions

### create_radar_chart(original_costs, optimized_costs, output_file)
Generates 5-axis radar/spider chart comparing cost components. Normalizes costs to 0-1 scale (inverted so higher = better). Plots both layouts on same axes with fill area for optimized. Saves as PNG with proper labels and legend.

### create_improvement_bar_chart(original_costs, optimized_costs, output_file)
Creates bar chart showing percentage improvement for each component. Colors bars green (improved) or red (degraded). Adds percentage labels on bars and horizontal zero line. Includes legend explaining colors.

### create_cost_breakdown(original_costs, optimized_costs, output_file)
Generates grouped bar chart comparing weighted costs component-by-component. Shows original and optimized side-by-side for each component. Adds value labels on bars and grid for readability.

### create_total_cost_comparison(original_costs, optimized_costs, output_file)
Simple comparison of total costs using two bars. Adds arrow annotation showing improvement percentage. Highlights overall optimization effectiveness.

### generate_all_visualizations(original_file, optimized_file, output_prefix)
Master function that loads layouts, calculates costs, and generates all four figure types. Prints progress messages and final summary of generated files.

---

# SYSTEM WORKFLOW

## Step 1: Initial Validation
Input layout → validator.py → List of violations. User provides poorly arranged layout. Validator identifies all DIN 18040-2 violations. Violations are categorized and displayed.

## Step 2: Optimization
Input layout → optimizer.py → Optimized layout. Optimizer analyzes door/window positions. Places furniture using heuristic rules. Generates 200 candidate layouts. Returns best layout found (max furniture, min violations).

## Step 3: Verification
Original + Optimized → test-optimizer.py → Detailed comparison. Runs validator on both layouts. Compares violation counts (initial vs remaining). Checks functional distances (bed-bedside). Categorizes improvements.

## Step 4: Cost Analysis
Original + Optimized → cost_validator.py → Scientific validation. Calculates 5 cost components for both layouts. Applies weights and computes total cost. Shows percentage improvement. Identifies which objectives improved.

## Step 5: Statistical Validation (Thesis)
Multiple pairs → batch_cost_validator.py → Statistics. Processes 30+ layout pairs. Computes mean improvement ± std dev. Calculates 95% confidence interval. Performs t-test for significance. Provides thesis-ready reporting text.

## Step 6: Visualization (Thesis)
Original + Optimized → visualize_costs.py → 4 figures. Radar chart (multi-objective comparison). Bar chart (component improvements). Cost breakdown (weighted comparison). Total cost (overall improvement).

---

# KEY TECHNICAL DETAILS

## Why Shapely Polygons?
All geometric operations use Shapely library because it provides: Robust intersection testing (overlaps, clearances), Rotation transformations, Buffer operations (door arcs, paths), Point-in-polygon tests, Computational geometry primitives.

## Why Squared Distances in Cost Function?
Distance squared (d²) penalizes large separations much more heavily than small ones. Moving items from 100cm apart to 200cm apart increases cost by 4x, not 2x. This creates strong pressure to keep functionally related items close.

## Why 200 Iterations?
Empirically determined balance between solution quality and runtime. More iterations improve results with diminishing returns. 200 iterations typically complete in 5-10 seconds and find good solutions for most layouts.

## Why Grid Search for Turning Space?
Exhaustive pixel-by-pixel search would be too slow. 50cm grid resolution finds most valid spaces while keeping runtime reasonable. May miss narrow gaps, but catches all major clear areas.

## Critical Implementation Details
Bedsides bypass door blocking check (small and mobile, shouldn't constrain placement). Window clearances have smart exceptions (low furniture under high sills is acceptable). Bed placement prioritizes opposite wall from door (maximizes privacy and minimizes traffic). Chair pullout zones are rotation-aware (direction matters for user access). Zone centroids adapt to door position (layout logic responds to room configuration).

## Standards Basis
All dimensions and requirements trace to DIN 18040-2: 150cm clearances → wheelchair turning radius, 90cm widths → wheelchair dimensions, Height limits → seated reach zones, Bed side clearances → transfer requirements.

---

# CONFIGURATION AND CUSTOMIZATION

## Validator
Edit standards constants at top of validator.py to adjust thresholds (clearances, heights, distances).

## Optimizer
Modify MAX_ITERATIONS in test-optimizer.py to balance speed vs quality. Adjust placement strategies in optimizer.py for different furniture types or priorities.

## Cost Function
Edit WEIGHTS dictionary in cost_validator.py to change component importance (must sum to 1.0). Modify AFFINITY_MATRIX to change functional relationships. Adjust PENALTY constants to change violation severity.

## Testing
Configure MODE, input paths, and output paths at top of test scripts. Set batch processing folders or single file targets as needed.

---

# OUTPUT FILES

## From Optimizer
{name}-optimized.json: Rearranged layout with same furniture, different positions/rotations

## From Cost Validator
Console output: Detailed cost comparison table, component analysis, improvement percentages

## From Batch Validator
Console output: Statistical summary with mean, std dev, confidence intervals, p-values, thesis text

## From Visualizations
cost_radar.png: 5-axis comparison chart, improvement_bars.png: Component improvement percentages, cost_breakdown.png: Weighted cost comparison, total_cost.png: Overall improvement visualization. All figures saved at 300 DPI for publication quality.
