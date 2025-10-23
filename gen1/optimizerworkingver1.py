from validator import LayoutValidator
import copy
import random
from shapely.geometry import box, Point
from shapely.affinity import rotate as shapely_rotate
import math

class LayoutOptimizer:
    """Optimizes bedroom layouts - COMPOSITE UNIT APPROACH (Bed + Bedside as ONE)"""
    
    def __init__(self, input_layout):
        self.original = input_layout
        self.room = input_layout['room']
        self.furniture = input_layout['furniture']
        self.openings = input_layout['openings']
        self.grid_step = 10
        
    def optimize(self, max_iterations=2000):
        """Main optimization with composite unit strategy"""
        
        print(f"Optimizing room layout with {len(self.furniture)} items...")
        print(f"Room: {self.room['width']}x{self.room['height']}cm\n")
        
        best_layout = None
        best_score = float('inf')
        
        # Try 200 deterministic attempts
        print("Attempting deterministic placement...")
        for attempt in range(200):
            try:
                candidate = self._generate_deterministic_layout()
                
                if candidate is None:
                    continue
                
                if self._has_overlap(candidate):
                    continue
                
                violations = self._count_violations(candidate)
                score = len(violations)
                
                if score < best_score:
                    best_score = score
                    best_layout = copy.deepcopy(candidate)
                    print(f"  Attempt {attempt}: {score} violations")
                
                if score == 0:
                    print(f"Perfect layout found!")
                    return best_layout
                    
            except Exception as e:
                continue
        
        if best_layout:
            print(f"\nFinal: {best_score} violations")
        else:
            print("\nNo valid layout found")
        
        return best_layout

    def _generate_deterministic_layout(self):
        """Generate layout with composite bed+bedside unit"""
        layout = {
            'room': self.room,
            'furniture': [],
            'openings': self.openings
        }
        
        # STEP 1: Identify bed and bedside tables
        bed = next((f for f in self.furniture if 'bed' in f['name'].lower() and 'bedside' not in f['name'].lower()), None)
        bedside_tables = [f for f in self.furniture if 'bedside' in f['name'].lower()]
        other_furniture = [f for f in self.furniture if f != bed and f not in bedside_tables]
        
        # Debug
        has_bedside = len(bedside_tables) > 0
        
        # STEP 2: Create composite BedUnit if bed + bedside exist
        if bed and bedside_tables:
            bed_unit = self._create_bed_unit(bed, bedside_tables)
            
            # Try to place BedUnit first
            placed_unit = self._place_bed_unit(bed_unit, layout)
            if placed_unit:
                # STEP 3: Decompose BedUnit back into bed + bedside
                decomposed = self._decompose_bed_unit(placed_unit)
                # Verify decomposed items don't overlap
                temp_layout = copy.deepcopy(layout)
                all_valid = True
                for item in decomposed:
                    if not self._is_placement_valid(item, temp_layout):
                        all_valid = False
                        break
                    temp_layout['furniture'].append(item)
                
                if all_valid:
                    for item in decomposed:
                        layout['furniture'].append(item)
                else:
                    # FALLBACK: Place bed and bedside separately
                    placed_bed = self._place_bed_smart(copy.deepcopy(bed), layout)
                    if placed_bed and self._is_placement_valid(placed_bed, layout):
                        layout['furniture'].append(placed_bed)
                        
                        # Try to place bedside near bed
                        for bedside in bedside_tables:
                            placed_bedside = self._place_bedside_near_bed(
                                copy.deepcopy(bedside), placed_bed, layout
                            )
                            if placed_bedside and self._is_placement_valid(placed_bedside, layout):
                                layout['furniture'].append(placed_bedside)
                    else:
                        return None
            else:
                # FALLBACK: BedUnit couldn't be placed, try separately
                placed_bed = self._place_bed_smart(copy.deepcopy(bed), layout)
                if placed_bed and self._is_placement_valid(placed_bed, layout):
                    layout['furniture'].append(placed_bed)
                    
                    # Try to place bedside near bed
                    for bedside in bedside_tables:
                        placed_bedside = self._place_bedside_near_bed(
                            copy.deepcopy(bedside), placed_bed, layout
                        )
                        if placed_bedside and self._is_placement_valid(placed_bedside, layout):
                            layout['furniture'].append(placed_bedside)
                        # If bedside can't be placed near bed, try anywhere
                        elif self._find_valid_spot(copy.deepcopy(bedside), layout):
                            layout['furniture'].append(self._find_valid_spot(copy.deepcopy(bedside), layout))
                else:
                    return None
        elif bed:
            # Just bed, no bedside
            placed_bed = self._place_bed_smart(copy.deepcopy(bed), layout)
            if placed_bed and self._is_placement_valid(placed_bed, layout):
                layout['furniture'].append(placed_bed)
            else:
                return None
        
        # STEP 4: Place other furniture
        sorted_furniture = self._sort_by_priority(other_furniture)
        
        for item in sorted_furniture:
            new_item = copy.deepcopy(item)
            name_lower = item['name'].lower()
            
            if 'study table' in name_lower:
                new_item = self._place_table_near_window(new_item, layout)
            elif 'wardrobe' in name_lower:
                new_item = self._place_wardrobe_smart(new_item, layout)
            elif 'sofa' in name_lower:
                new_item = self._place_sofa_smart(new_item, layout)
            elif 'chair' in name_lower:
                new_item = self._place_chair_in_front(new_item, layout)
            else:
                new_item = self._find_valid_spot(new_item, layout)
            
            if new_item and self._is_placement_valid(new_item, layout):
                layout['furniture'].append(new_item)
            # Skip this item if it can't be placed, continue with others
        
        # Return layout even if some items couldn't be placed (as long as we have bed)
        if len(layout['furniture']) > 0:
            return layout
        
        return None
    
    def _create_bed_unit(self, bed, bedside_tables):
        """Create composite BedUnit (bed + bedside as single unit)"""
        # Use first bedside table and place it on right side
        bedside = bedside_tables[0]
        
        bed_unit = {
            'name': 'BedUnit',
            'type': 'composite',
            'bed': copy.deepcopy(bed),
            'bedside': copy.deepcopy(bedside),
            # Composite dimensions: bed width + bedside width
            'width': bed['width'] + bedside['width'],
            'height': max(bed['height'], bedside['height']),
            'x': 0,
            'y': 0,
            'rotation': 0,
            'zHeight': bed.get('zHeight', 55)
        }
        
        return bed_unit
    
    def _place_bed_unit(self, bed_unit, layout):
        """Place the composite BedUnit as a single piece"""
        door = next((o for o in self.openings if o['type'] == 'door'), None)
        windows = [o for o in self.openings if o['type'] == 'window']
        
        window_walls = set(w['wall'] for w in windows)
        
        # Determine walls to try
        if door:
            door_wall = door['wall']
            opposite_walls = {
                'top': 'bottom', 'bottom': 'top',
                'left': 'right', 'right': 'left'
            }
            preferred_wall = opposite_walls[door_wall]
            perpendicular = ['left', 'right'] if door_wall in ['top', 'bottom'] else ['top', 'bottom']
            walls_to_try = [preferred_wall] + [w for w in perpendicular if w not in window_walls]
        else:
            walls_to_try = ['bottom', 'top', 'left', 'right']
        
        # Try placing BedUnit on different walls
        for wall in walls_to_try:
            positions = self._get_wall_positions_grid(bed_unit, wall, count=8)
            
            for x, y, rot in positions:
                bed_unit['x'] = x
                bed_unit['y'] = y
                bed_unit['rotation'] = rot
                
                if self._is_placement_valid(bed_unit, layout):
                    return bed_unit
        
        # Fallback: try any position
        return self._find_valid_spot(bed_unit, layout)
    
    def _decompose_bed_unit(self, bed_unit):
        """Decompose BedUnit back into individual bed + bedside items"""
        bed = bed_unit['bed']
        bedside = bed_unit['bedside']
        
        rot = bed_unit.get('rotation', 0)
        
        # Position bed at BedUnit position
        bed['x'] = bed_unit['x']
        bed['y'] = bed_unit['y']
        bed['rotation'] = rot
        
        # Position bedside relative to bed based on rotation
        if rot == 0:
            # Bedside on right side of bed, aligned to headboard (bottom)
            bedside['x'] = bed['x'] + bed['width']
            bedside['y'] = bed['y'] + bed['height'] - bedside['height']
        elif rot == 180:
            # Rotated 180: bedside on left, aligned to headboard (top)
            bedside['x'] = bed['x'] - bedside['width']
            bedside['y'] = bed['y']
        elif rot == 90:
            # Rotated 90: bedside below bed
            bedside['x'] = bed['x']
            bedside['y'] = bed['y'] + bed['height']
        else:  # 270
            # Rotated 270: bedside above bed
            bedside['x'] = bed['x'] + bed['width'] - bedside['width']
            bedside['y'] = bed['y'] - bedside['height']
        
        bedside['rotation'] = 0
        
        return [bed, bedside]
    
    def _place_bedside_near_bed(self, bedside, bed, layout):
        """Place bedside table near bed (fallback when composite fails)"""
        # Try positions around the bed
        positions = []
        gap = 5
        
        rot = bed.get('rotation', 0)
        
        if rot == 0:
            # Right side at headboard (bottom)
            positions.append((bed['x'] + bed['width'] + gap, bed['y'] + bed['height'] - bedside['height']))
            # Left side at headboard
            positions.append((bed['x'] - bedside['width'] - gap, bed['y'] + bed['height'] - bedside['height']))
            # Right side at middle
            positions.append((bed['x'] + bed['width'] + gap, bed['y'] + bed['height']//2 - bedside['height']//2))
            # Left side at middle
            positions.append((bed['x'] - bedside['width'] - gap, bed['y'] + bed['height']//2 - bedside['height']//2))
        elif rot == 180:
            positions.append((bed['x'] + bed['width'] + gap, bed['y']))
            positions.append((bed['x'] - bedside['width'] - gap, bed['y']))
            positions.append((bed['x'] + bed['width'] + gap, bed['y'] + bed['height']//2 - bedside['height']//2))
            positions.append((bed['x'] - bedside['width'] - gap, bed['y'] + bed['height']//2 - bedside['height']//2))
        elif rot == 90:
            positions.append((bed['x'], bed['y'] - bedside['height'] - gap))
            positions.append((bed['x'], bed['y'] + bed['height'] + gap))
            positions.append((bed['x'] + bed['width']//2 - bedside['width']//2, bed['y'] - bedside['height'] - gap))
            positions.append((bed['x'] + bed['width']//2 - bedside['width']//2, bed['y'] + bed['height'] + gap))
        else:  # 270
            positions.append((bed['x'] + bed['width'] - bedside['width'], bed['y'] - bedside['height'] - gap))
            positions.append((bed['x'] + bed['width'] - bedside['width'], bed['y'] + bed['height'] + gap))
            positions.append((bed['x'] + bed['width']//2 - bedside['width']//2, bed['y'] - bedside['height'] - gap))
            positions.append((bed['x'] + bed['width']//2 - bedside['width']//2, bed['y'] + bed['height'] + gap))
        
        # Try each position
        for x, y in positions:
            bedside['x'] = x
            bedside['y'] = y
            bedside['rotation'] = 0
            
            if self._check_item_bounds(bedside) and self._is_placement_valid(bedside, layout):
                return bedside
        
        return None
    
    def _place_bed_smart(self, bed, layout):
        """Place bed without bedside (fallback)"""
        door = next((o for o in self.openings if o['type'] == 'door'), None)
        windows = [o for o in self.openings if o['type'] == 'window']
        
        window_walls = set(w['wall'] for w in windows)
        
        if door:
            door_wall = door['wall']
            opposite_walls = {
                'top': 'bottom', 'bottom': 'top',
                'left': 'right', 'right': 'left'
            }
            preferred_wall = opposite_walls[door_wall]
            perpendicular = ['left', 'right'] if door_wall in ['top', 'bottom'] else ['top', 'bottom']
            walls_to_try = [preferred_wall] + [w for w in perpendicular if w not in window_walls]
        else:
            walls_to_try = ['bottom', 'top', 'left', 'right']
        
        for wall in walls_to_try:
            positions = self._get_wall_positions_grid(bed, wall, count=5)
            
            for x, y, rot in positions:
                bed['x'] = x
                bed['y'] = y
                bed['rotation'] = rot
                
                if self._is_placement_valid(bed, layout):
                    return bed
        
        return self._find_valid_spot(bed, layout)
    
    def _place_table_near_window(self, table, layout):
        """Place study table facing window with fallback positions"""
        windows = [o for o in self.openings if o['type'] == 'window']
        
        if not windows:
            return self._place_along_wall_multi(table, layout)
        
        for window in windows:
            wall = window['wall']
            pos = window['position']
            size = window['size']
            
            positions = []
            margin = 30
            
            if wall == 'top':
                positions = [
                    (pos - table['width']//2, margin, 0),
                    (pos - table['width'] - 20, margin, 0),
                    (pos + size + 20, margin, 0),
                ]
            elif wall == 'bottom':
                positions = [
                    (pos - table['width']//2, self.room['height'] - table['height'] - margin, 180),
                    (pos - table['width'] - 20, self.room['height'] - table['height'] - margin, 180),
                    (pos + size + 20, self.room['height'] - table['height'] - margin, 180),
                ]
            elif wall == 'left':
                positions = [
                    (margin, pos - table['height']//2, 270),
                    (margin, pos - table['height'] - 20, 270),
                    (margin, pos + size + 20, 270),
                ]
            else:  # right
                positions = [
                    (self.room['width'] - table['width'] - margin, pos - table['height']//2, 90),
                    (self.room['width'] - table['width'] - margin, pos - table['height'] - 20, 90),
                    (self.room['width'] - table['width'] - margin, pos + size + 20, 90),
                ]
            
            for x, y, rot in positions:
                table['x'] = max(20, min(x, self.room['width'] - table['width'] - 20))
                table['y'] = max(20, min(y, self.room['height'] - table['height'] - 20))
                table['rotation'] = rot
                
                if self._is_placement_valid(table, layout):
                    return table
        
        return self._place_along_wall_multi(table, layout)
    
    def _place_chair_in_front(self, chair, layout):
        """Place chair IN FRONT of table with fallback positions"""
        table = next((f for f in layout['furniture'] 
                     if 'study table' in f['name'].lower()), None)
        
        if not table:
            return self._find_valid_spot(chair, layout)
        
        rot = table.get('rotation', 0)
        gap = 10
        
        positions = []
        
        if rot == 0:
            positions = [
                (table['x'] + table['width']//2 - chair['width']//2, 
                 table['y'] + table['height'] + gap, 0),
                (table['x'] - chair['width'] - gap, table['y'], 0),
                (table['x'] + table['width'] + gap, table['y'], 0),
            ]
        elif rot == 180:
            positions = [
                (table['x'] + table['width']//2 - chair['width']//2, 
                 table['y'] - chair['height'] - gap, 180),
                (table['x'] - chair['width'] - gap, table['y'], 180),
                (table['x'] + table['width'] + gap, table['y'], 180),
            ]
        elif rot == 90:
            positions = [
                (table['x'] - chair['width'] - gap, 
                 table['y'] + table['height']//2 - chair['height']//2, 90),
                (table['x'], table['y'] - chair['height'] - gap, 90),
                (table['x'], table['y'] + table['height'] + gap, 90),
            ]
        else:  # 270
            positions = [
                (table['x'] + table['width'] + gap, 
                 table['y'] + table['height']//2 - chair['height']//2, 270),
                (table['x'], table['y'] - chair['height'] - gap, 270),
                (table['x'], table['y'] + table['height'] + gap, 270),
            ]
        
        for x, y, chair_rot in positions:
            chair['x'] = x
            chair['y'] = y
            chair['rotation'] = chair_rot
            
            if self._check_item_bounds(chair) and self._is_placement_valid(chair, layout):
                return chair
        
        return self._find_valid_spot(chair, layout)
    
    def _place_wardrobe_smart(self, wardrobe, layout):
        """Place wardrobe away from windows"""
        windows = [o for o in self.openings if o['type'] == 'window']
        door = next((o for o in self.openings if o['type'] == 'door'), None)
        
        window_walls = set(w['wall'] for w in windows)
        door_wall = door['wall'] if door else None
        
        walls = ['top', 'bottom', 'left', 'right']
        available_walls = [w for w in walls if w != door_wall and w not in window_walls]
        
        if not available_walls:
            available_walls = [w for w in walls if w != door_wall]
        if not available_walls:
            available_walls = walls
        
        for wall in available_walls:
            positions = self._get_wall_positions_grid(wardrobe, wall, count=8)
            
            for x, y, rot in positions:
                wardrobe['x'] = x
                wardrobe['y'] = y
                wardrobe['rotation'] = rot
                
                if any(self._blocks_window(wardrobe, w) for w in windows):
                    continue
                
                if self._is_placement_valid(wardrobe, layout):
                    return wardrobe
        
        return self._find_valid_spot(wardrobe, layout)
    
    def _place_sofa_smart(self, sofa, layout):
        """Place sofa with multiple attempts"""
        walls = ['top', 'bottom', 'left', 'right']
        
        for wall in walls:
            positions = self._get_wall_positions_grid(sofa, wall, count=6)
            
            for x, y, rot in positions:
                sofa['x'] = x
                sofa['y'] = y
                sofa['rotation'] = rot
                
                if self._is_placement_valid(sofa, layout):
                    return sofa
        
        return self._find_valid_spot(sofa, layout)
    
    def _get_wall_positions_grid(self, item, wall, count=5):
        """Generate grid of positions along a wall"""
        positions = []
        margin = 20
        
        if wall == 'top':
            y = margin
            step = max(50, (self.room['width'] - 2*margin - item['width']) // count)
            for i in range(count):
                x = margin + i * step
                if x + item['width'] <= self.room['width'] - margin:
                    positions.append((x, y, 0))
                    
        elif wall == 'bottom':
            y = self.room['height'] - item['height'] - margin
            step = max(50, (self.room['width'] - 2*margin - item['width']) // count)
            for i in range(count):
                x = margin + i * step
                if x + item['width'] <= self.room['width'] - margin:
                    positions.append((x, y, 180))
                    
        elif wall == 'left':
            x = margin
            step = max(50, (self.room['height'] - 2*margin - item['height']) // count)
            for i in range(count):
                y = margin + i * step
                if y + item['height'] <= self.room['height'] - margin:
                    positions.append((x, y, 270))
                    
        else:  # right
            x = self.room['width'] - item['width'] - margin
            step = max(50, (self.room['height'] - 2*margin - item['height']) // count)
            for i in range(count):
                y = margin + i * step
                if y + item['height'] <= self.room['height'] - margin:
                    positions.append((x, y, 90))
        
        return positions
    
    def _place_along_wall_multi(self, item, layout):
        """Place along any wall with multiple attempts"""
        walls = ['top', 'bottom', 'left', 'right']
        
        for wall in walls:
            positions = self._get_wall_positions_grid(item, wall, count=8)
            
            for x, y, rot in positions:
                item['x'] = x
                item['y'] = y
                item['rotation'] = rot
                
                if self._is_placement_valid(item, layout):
                    return item
        
        return self._find_valid_spot(item, layout)
    
    def _find_valid_spot(self, item, layout):
        """Find any valid position with systematic search"""
        step = 50
        for y in range(20, max(21, self.room['height'] - item['height'] - 20), step):
            for x in range(20, max(21, self.room['width'] - item['width'] - 20), step):
                item['x'] = x
                item['y'] = y
                item['rotation'] = 0
                
                if self._is_placement_valid(item, layout):
                    return item
        
        step = 30
        for y in range(20, max(21, self.room['height'] - item['height'] - 20), step):
            for x in range(20, max(21, self.room['width'] - item['width'] - 20), step):
                item['x'] = x
                item['y'] = y
                item['rotation'] = 0
                
                if self._is_placement_valid(item, layout):
                    return item
        
        # Try fine grid as last resort
        step = 20
        for y in range(20, max(21, self.room['height'] - item['height'] - 20), step):
            for x in range(20, max(21, self.room['width'] - item['width'] - 20), step):
                item['x'] = x
                item['y'] = y
                item['rotation'] = 0
                
                if self._is_placement_valid(item, layout):
                    return item
        
        return None  # No valid position found
    
    def _sort_by_priority(self, furniture_list):
        """Sort furniture by placement priority"""
        priority_order = {
            'study table': 1,
            'wardrobe': 2,
            'sofa': 3,
            'study chair': 4
        }
        
        def get_priority(item):
            name_lower = item['name'].lower()
            for key, priority in priority_order.items():
                if key in name_lower:
                    return priority
            return 5
        
        return sorted(furniture_list, key=get_priority)
    
    def _blocks_window(self, furniture, window):
        """Check if furniture blocks window"""
        wall = window['wall']
        pos = window['position']
        size = window['size']
        threshold = 80
        
        if wall == 'top' and furniture['y'] < threshold:
            if furniture['x'] < pos + size and furniture['x'] + furniture['width'] > pos:
                return True
        elif wall == 'bottom' and furniture['y'] > self.room['height'] - furniture['height'] - threshold:
            if furniture['x'] < pos + size and furniture['x'] + furniture['width'] > pos:
                return True
        elif wall == 'left' and furniture['x'] < threshold:
            if furniture['y'] < pos + size and furniture['y'] + furniture['height'] > pos:
                return True
        elif wall == 'right' and furniture['x'] > self.room['width'] - furniture['width'] - threshold:
            if furniture['y'] < pos + size and furniture['y'] + furniture['height'] > pos:
                return True
        
        return False
    
    def _check_item_bounds(self, item):
        """Check if item is within room bounds"""
        return (item['x'] >= 0 and item['y'] >= 0 and 
                item['x'] + item['width'] <= self.room['width'] and 
                item['y'] + item['height'] <= self.room['height'])
    
    def _is_placement_valid(self, item, layout):
        """Check if placement is valid (no overlaps)"""
        if not self._check_item_bounds(item):
            return False
        
        item_poly = self._get_furniture_polygon(item)
        
        for other in layout['furniture']:
            other_poly = self._get_furniture_polygon(other)
            if item_poly.intersects(other_poly):
                return False
        
        return True
    
    def _has_overlap(self, layout):
        """Check for any overlaps in layout"""
        for i, item1 in enumerate(layout['furniture']):
            poly1 = self._get_furniture_polygon(item1)
            for item2 in layout['furniture'][i+1:]:
                poly2 = self._get_furniture_polygon(item2)
                if poly1.intersects(poly2):
                    return True
        return False
    
    def _get_furniture_polygon(self, item):
        """Get furniture polygon"""
        x, y = item['x'], item['y']
        w, h = item['width'], item['height']
        rect = box(x, y, x + w, y + h)
        
        rotation = item.get('rotation', 0)
        if rotation != 0:
            center = (x + w/2, y + h/2)
            rect = shapely_rotate(rect, rotation, origin=center)
        
        return rect
    
    def _count_violations(self, layout):
        """Count violations using validator"""
        validator = LayoutValidator(layout)
        return validator.validate()