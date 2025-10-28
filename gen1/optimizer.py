"""
Room Layout Optimizer - Merged Working Version
Combines: Working bedside placement + Violation tracking + Flexible placement
"""

from validator import LayoutValidator
import copy
import random
import math
from shapely.geometry import box, Point
from shapely.affinity import rotate as shapely_rotate


class ViolationTracker:
    """Tracks violations throughout optimization"""
    
    def __init__(self):
        self.initial_violations = []
        self.final_violations = []
        
    def set_initial(self, layout):
        validator = LayoutValidator(layout)
        self.initial_violations = validator.validate()
        return self.initial_violations
    
    def finalize(self, final_layout):
        validator = LayoutValidator(final_layout)
        self.final_violations = validator.validate()
        
        initial_set = set(self.initial_violations)
        final_set = set(self.final_violations)
        
        fixed = list(initial_set - final_set)
        remaining = list(final_set)
        
        return {
            'initial_count': len(self.initial_violations),
            'final_count': len(self.final_violations),
            'fixed_count': len(fixed),
            'fixed': fixed,
            'remaining': remaining,
            'improvement': len(self.initial_violations) - len(self.final_violations)
        }
    
    def get_summary(self):
        """Categorize violations for UI"""
        
        def categorize(violations):
            categories = {
                'Overlaps': [],
                'Clearances': [],
                'Bed Clearances': [],
                'Turning Space': [],
                'Door': [],
                'Emergency Path': [],
                'Windows': [],
                'Heights': [],
                'Other': []
            }
            
            for v in violations:
                v_lower = v.lower()
                if "overlap" in v_lower:
                    categories['Overlaps'].append(v)
                elif "bed" in v_lower and "clearance" in v_lower:
                    categories['Bed Clearances'].append(v)
                elif "clearance" in v_lower:
                    categories['Clearances'].append(v)
                elif "turning" in v_lower:
                    categories['Turning Space'].append(v)
                elif "door" in v_lower:
                    categories['Door'].append(v)
                elif "emergency" in v_lower or "path" in v_lower:
                    categories['Emergency Path'].append(v)
                elif "window" in v_lower or "sill" in v_lower:
                    categories['Windows'].append(v)
                elif "height" in v_lower or "reach" in v_lower:
                    categories['Heights'].append(v)
                else:
                    categories['Other'].append(v)
            
            return {k: v for k, v in categories.items() if v}
        
        return {
            'initial': categorize(self.initial_violations),
            'fixed': categorize([v for v in self.initial_violations if v not in self.final_violations]),
            'remaining': categorize(self.final_violations)
        }


class LayoutOptimizer:
    """Room layout optimizer with working bedside placement"""
    
    def __init__(self, input_layout):
        self.room = input_layout['room']
        self.furniture = input_layout['furniture']
        self.openings = input_layout['openings']
        self.tracker = ViolationTracker()
        self.unplaced_furniture = []
        
    def optimize(self, max_iterations=200):
        """Main optimization"""
        
        print(f"\n{'='*80}")
        print(f"ROOM LAYOUT OPTIMIZER")
        print(f"{'='*80}")
        print(f"Room: {self.room['width']}×{self.room['height']}cm")
        print(f"Furniture: {len(self.furniture)} items")
        
        print(f"\n📋 Analyzing initial layout...")
        self.tracker.set_initial({'room': self.room, 'furniture': self.furniture, 'openings': self.openings})
        print(f"   Initial violations: {len(self.tracker.initial_violations)}")
        
        door = next((o for o in self.openings if o['type'] == 'door'), None)
        if not door:
            door = {'wall': 'bottom', 'position': self.room['width']/2, 'size': 90}
        
        windows = [o for o in self.openings if o['type'] == 'window']
        
        print(f"\n🏗️  Generating layouts...")
        
        best_layout = None
        best_score = float('inf')
        best_placed_count = 0
        
        for attempt in range(max_iterations):
            random.seed(attempt)
            
            candidate = self._generate_layout(door, windows)
            
            if not candidate or len(candidate['furniture']) == 0:
                continue
            
            violations = self._count_violations(candidate)
            violation_count = len(violations)
            placed_count = len(candidate['furniture'])
            
            is_better = False
            if placed_count > best_placed_count:
                is_better = True
            elif placed_count == best_placed_count and violation_count < best_score:
                is_better = True
            
            if is_better:
                best_score = violation_count
                best_placed_count = placed_count
                best_layout = copy.deepcopy(candidate)
                
                if attempt % 25 == 0:
                    print(f"   Attempt {attempt}: {placed_count}/{len(self.furniture)} items, {violation_count} violations")
            
            if violation_count == 0 and placed_count == len(self.furniture):
                print(f"   ✓ Perfect layout at attempt {attempt}!")
                break
        
        if best_layout:
            summary = self.tracker.finalize(best_layout)
            
            print(f"\n{'='*80}")
            print(f"OPTIMIZATION COMPLETE")
            print(f"{'='*80}")
            print(f"✓ Furniture placed: {len(best_layout['furniture'])}/{len(self.furniture)}")
            print(f"✓ Violations: {summary['initial_count']} → {summary['final_count']}")
            print(f"✓ Fixed: {summary['fixed_count']} violations")
            print(f"✓ Improvement: {summary['improvement']}")
            
            if len(best_layout['furniture']) < len(self.furniture):
                self._analyze_unplaced(best_layout)
            
            return best_layout
        else:
            print(f"\n✗ No valid layout found")
            return None
    
    def _generate_layout(self, door, windows):
        """Generate single layout"""
        
        layout = {
            'room': self.room,
            'furniture': [],
            'openings': self.openings
        }
        
        # Identify furniture types
        bed = next((f for f in self.furniture if 'bed' in f['name'].lower() and 'bedside' not in f['name'].lower()), None)
        bedsides = [f for f in self.furniture if 'bedside' in f['name'].lower()]
        wardrobes = [f for f in self.furniture if 'wardrobe' in f['name'].lower()]
        tables = [f for f in self.furniture if 'table' in f['name'].lower() and 'bedside' not in f['name'].lower()]
        chairs = [f for f in self.furniture if 'chair' in f['name'].lower()]
        sofas = [f for f in self.furniture if 'sofa' in f['name'].lower()]
        
        # STEP 1: Place bed FIRST and add to layout
        if bed:
            placed_bed = self._place_bed(copy.deepcopy(bed), door, layout)
            if placed_bed:
                layout['furniture'].append(placed_bed)
                
                # STEP 2: Place bedsides IMMEDIATELY (bed is now in layout)
                for bedside in bedsides:
                    placed_bedside = self._place_bedside_near_bed(copy.deepcopy(bedside), placed_bed, layout)
                    if placed_bedside:
                        layout['furniture'].append(placed_bedside)
        
        # STEP 3: Place wardrobes on walls
        for wardrobe in wardrobes:
            placed = self._place_on_wall_flexible(copy.deepcopy(wardrobe), layout, door)
            if placed:
                layout['furniture'].append(placed)
        
        # STEP 4: Place tables near windows
        for table in tables:
            if windows:
                placed = self._place_table_near_window(copy.deepcopy(table), windows[0], layout, door)
            else:
                placed = self._place_anywhere_grid(copy.deepcopy(table), layout, door)
            
            if placed:
                layout['furniture'].append(placed)
                
                # STEP 5: Place chairs with tables
                for chair in chairs:
                    placed_chair = self._place_chair_with_table(copy.deepcopy(chair), placed, layout, door)
                    if placed_chair:
                        layout['furniture'].append(placed_chair)
        
        # STEP 6: Place sofas on walls
        for sofa in sofas:
            placed = self._place_on_wall_flexible(copy.deepcopy(sofa), layout, door)
            if placed:
                layout['furniture'].append(placed)
        
        return layout
    
    def _place_bed(self, bed, door, layout):
        """Place bed away from door"""
        
        door_wall = door['wall']
        margin = 30
        
        # Opposite walls from door
        opposite_walls = {
            'top': 'bottom',
            'bottom': 'top',
            'left': 'right',
            'right': 'left'
        }
        
        preferred_wall = opposite_walls.get(door_wall, 'bottom')
        
        # Try preferred wall first
        for wall in [preferred_wall, 'top', 'bottom', 'left', 'right']:
            positions = self._get_wall_positions(bed, wall, count=6)
            
            for x, y, rot in positions:
                bed['x'] = x
                bed['y'] = y
                bed['rotation'] = rot
                
                if self._check_bounds(bed) and self._is_valid(bed, layout, door):
                    return bed
        
        return None
    
    def _place_bedside_near_bed(self, bedside, bed, layout):
        """Place bedside at headboard - WORKING VERSION"""
        
        positions = []
        gap = 5
        
        rot = bed.get('rotation', 0)
        
        # Rotation 0 = headboard at top
        if rot == 0:
            positions.append((bed['x'] + bed['width'] + gap, bed['y']))
            positions.append((bed['x'] - bedside['width'] - gap, bed['y']))
            positions.append((bed['x'] + bed['width'] + gap, bed['y'] + bed['height']//3))
            positions.append((bed['x'] - bedside['width'] - gap, bed['y'] + bed['height']//3))
        elif rot == 180:
            positions.append((bed['x'] + bed['width'] + gap, bed['y'] + bed['height'] - bedside['height']))
            positions.append((bed['x'] - bedside['width'] - gap, bed['y'] + bed['height'] - bedside['height']))
            positions.append((bed['x'] + bed['width'] + gap, bed['y'] + 2*bed['height']//3))
            positions.append((bed['x'] - bedside['width'] - gap, bed['y'] + 2*bed['height']//3))
        elif rot == 90:
            positions.append((bed['x'] - bedside['width'] - gap, bed['y']))
            positions.append((bed['x'] - bedside['width'] - gap, bed['y'] + bed['height']//3))
            positions.append((bed['x'], bed['y'] - bedside['height'] - gap))
            positions.append((bed['x'], bed['y'] + bed['height'] + gap))
        else:  # 270
            positions.append((bed['x'] + bed['width'] + gap, bed['y'] + bed['height'] - bedside['height']))
            positions.append((bed['x'] + bed['width'] + gap, bed['y'] + 2*bed['height']//3))
            positions.append((bed['x'] + bed['width'] - bedside['width'], bed['y'] - bedside['height'] - gap))
            positions.append((bed['x'] + bed['width'] - bedside['width'], bed['y'] + bed['height'] + gap))
        
        # Try each position
        for x, y in positions:
            bedside['x'] = x
            bedside['y'] = y
            bedside['rotation'] = 0
            
            if self._check_bounds(bedside) and self._is_valid(bedside, layout, None):  # No door check for bedsides
                return bedside
        
        return None
    
    def _place_table_near_window(self, table, window, layout, door):
        """Place table near window"""
        
        wall = window['wall']
        pos = window['position']
        size = window.get('size', 120)
        
        if wall == 'right':
            window_y = pos + size/2
            for distance in range(50, 200, 30):
                table['x'] = self.room['width'] - table['width'] - distance
                table['y'] = window_y - table['height']/2
                table['rotation'] = 90
                
                if self._check_bounds(table) and self._is_valid(table, layout, door):
                    return table
        
        elif wall == 'left':
            window_y = pos + size/2
            for distance in range(50, 200, 30):
                table['x'] = distance
                table['y'] = window_y - table['height']/2
                table['rotation'] = 270
                
                if self._check_bounds(table) and self._is_valid(table, layout, door):
                    return table
        
        elif wall == 'top':
            window_x = pos + size/2
            for distance in range(50, 200, 30):
                table['x'] = window_x - table['width']/2
                table['y'] = distance
                table['rotation'] = 0
                
                if self._check_bounds(table) and self._is_valid(table, layout, door):
                    return table
        
        else:  # bottom
            window_x = pos + size/2
            for distance in range(50, 200, 30):
                table['x'] = window_x - table['width']/2
                table['y'] = self.room['height'] - table['height'] - distance
                table['rotation'] = 180
                
                if self._check_bounds(table) and self._is_valid(table, layout, door):
                    return table
        
        return None
    
    def _place_chair_with_table(self, chair, table, layout, door):
        """Place chair with table"""
        
        rot = table.get('rotation', 0)
        gap = 10
        
        positions = []
        
        if rot == 0:
            positions.append((table['x'] + (table['width'] - chair['width'])/2, table['y'] + table['height'] + gap, 0))
        elif rot == 180:
            positions.append((table['x'] + (table['width'] - chair['width'])/2, table['y'] - chair['height'] - gap, 180))
        elif rot == 90:
            positions.append((table['x'] - chair['width'] - gap, table['y'] + (table['height'] - chair['height'])/2, 90))
        elif rot == 270:
            positions.append((table['x'] + table['width'] + gap, table['y'] + (table['height'] - chair['height'])/2, 270))
        
        for x, y, r in positions:
            chair['x'] = x
            chair['y'] = y
            chair['rotation'] = r
            
            if self._check_bounds(chair) and self._is_valid(chair, layout, door):
                return chair
        
        return None
    
    def _place_on_wall_flexible(self, furniture, layout, door):
        """Place on wall with flexibility"""
        
        margin = 30
        walls = ['top', 'bottom', 'left', 'right']
        random.shuffle(walls)
        
        for wall in walls:
            positions = self._get_wall_positions(furniture, wall, count=8)
            
            for x, y, rot in positions:
                furniture['x'] = x
                furniture['y'] = y
                furniture['rotation'] = rot
                
                if self._check_bounds(furniture) and self._is_valid(furniture, layout, door):
                    return furniture
        
        return None
    
    def _place_anywhere_grid(self, furniture, layout, door):
        """Place anywhere using grid search"""
        
        step = 50
        for y in range(30, self.room['height'] - furniture['height'] - 30, step):
            for x in range(30, self.room['width'] - furniture['width'] - 30, step):
                furniture['x'] = x
                furniture['y'] = y
                furniture['rotation'] = random.choice([0, 90, 180, 270])
                
                if self._check_bounds(furniture) and self._is_valid(furniture, layout, door):
                    return furniture
        
        return None
    
    def _get_wall_positions(self, item, wall, count=5):
        """Get positions along a wall"""
        
        positions = []
        margin = 30
        
        if wall == 'top':
            step = max(50, (self.room['width'] - 2*margin - item['width']) // count)
            for i in range(count):
                x = margin + i * step
                if x + item['width'] <= self.room['width'] - margin:
                    positions.append((x, margin, 0))
        
        elif wall == 'bottom':
            step = max(50, (self.room['width'] - 2*margin - item['width']) // count)
            for i in range(count):
                x = margin + i * step
                if x + item['width'] <= self.room['width'] - margin:
                    positions.append((x, self.room['height'] - item['height'] - margin, 180))
        
        elif wall == 'left':
            step = max(50, (self.room['height'] - 2*margin - item['height']) // count)
            for i in range(count):
                y = margin + i * step
                if y + item['height'] <= self.room['height'] - margin:
                    positions.append((margin, y, 270))
        
        else:  # right
            step = max(50, (self.room['height'] - 2*margin - item['height']) // count)
            for i in range(count):
                y = margin + i * step
                if y + item['height'] <= self.room['height'] - margin:
                    positions.append((self.room['width'] - item['width'] - margin, y, 90))
        
        return positions
    
    def _blocks_door(self, furniture, door):
        """Check if blocks door - 120cm clearance"""
        
        if not door:
            return False
        
        wall = door['wall']
        door_pos = door['position']
        door_size = door['size']
        CLEARANCE = 120
        
        if wall == 'right':
            door_area_x = self.room['width'] - CLEARANCE
            door_area_y_start = door_pos - 30
            door_area_y_end = door_pos + door_size + 30
            
            if (furniture['x'] + furniture['width'] > door_area_x and
                furniture['y'] < door_area_y_end and
                furniture['y'] + furniture['height'] > door_area_y_start):
                return True
        
        elif wall == 'left':
            door_area_x_end = CLEARANCE
            door_area_y_start = door_pos - 30
            door_area_y_end = door_pos + door_size + 30
            
            if (furniture['x'] < door_area_x_end and
                furniture['y'] < door_area_y_end and
                furniture['y'] + furniture['height'] > door_area_y_start):
                return True
        
        elif wall == 'top':
            door_area_y_end = CLEARANCE
            door_area_x_start = door_pos - 30
            door_area_x_end = door_pos + door_size + 30
            
            if (furniture['y'] < door_area_y_end and
                furniture['x'] < door_area_x_end and
                furniture['x'] + furniture['width'] > door_area_x_start):
                return True
        
        else:  # bottom
            door_area_y = self.room['height'] - CLEARANCE
            door_area_x_start = door_pos - 30
            door_area_x_end = door_pos + door_size + 30
            
            if (furniture['y'] + furniture['height'] > door_area_y and
                furniture['x'] < door_area_x_end and
                furniture['x'] + furniture['width'] > door_area_x_start):
                return True
        
        return False
    
    def _analyze_unplaced(self, layout):
        """Analyze unplaced furniture"""
        
        placed_items = layout['furniture']
        input_ids = [f"{f['name']}_{i}_{f['width']}_{f['height']}" for i, f in enumerate(self.furniture)]
        placed_ids = []
        
        for placed in placed_items:
            for i, original in enumerate(self.furniture):
                item_id = f"{original['name']}_{i}_{original['width']}_{original['height']}"
                if (placed['name'] == original['name'] and 
                    placed['width'] == original['width'] and 
                    placed['height'] == original['height'] and
                    item_id not in placed_ids):
                    placed_ids.append(item_id)
                    break
        
        unplaced_ids = [id for id in input_ids if id not in placed_ids]
        self.unplaced_furniture = []
        
        for unplaced_id in unplaced_ids:
            idx = int(unplaced_id.split('_')[1])
            self.unplaced_furniture.append(self.furniture[idx])
        
        if self.unplaced_furniture:
            print(f"\n{'='*80}")
            print(f"⚠️  FURNITURE PLACEMENT SUGGESTIONS")
            print(f"{'='*80}")
            print(f"\nCouldn't place {len(self.unplaced_furniture)} item(s):")
            
            for item in self.unplaced_furniture:
                print(f"  ❌ {item['name']} ({item['width']}×{item['height']}cm)")
    
    def get_violation_report(self):
        """Get violation report for UI"""
        summary = self.tracker.get_summary()
        
        return {
            'initial': summary['initial'],
            'fixed': summary['fixed'],
            'remaining': summary['remaining'],
            'unplaced_furniture': self.unplaced_furniture
        }
    
    def _check_bounds(self, item):
        """Check if within room bounds"""
        return (item['x'] >= 0 and item['y'] >= 0 and
                item['x'] + item['width'] <= self.room['width'] and
                item['y'] + item['height'] <= self.room['height'])
    
    def _is_valid(self, item, layout, door):
        """Check if valid placement"""
        
        # Check door blocking (skip for bedsides)
        if door and 'bedside' not in item['name'].lower():
            if self._blocks_door(item, door):
                return False
        
        # Check overlaps
        item_poly = self._get_polygon(item)
        
        for other in layout['furniture']:
            other_poly = self._get_polygon(other)
            if item_poly.intersects(other_poly):
                return False
        
        return True
    
    def _get_polygon(self, item):
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
        """Count violations"""
        validator = LayoutValidator(layout)
        return validator.validate()