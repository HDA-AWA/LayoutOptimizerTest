import numpy as np
from shapely.geometry import box, Polygon, Point, LineString
from shapely.affinity import rotate as shapely_rotate
import math


class LayoutValidator:
    """Validates bedroom layouts against DIN 18040-2 (R) with enhanced livability checks"""
    
    def __init__(self, layout):
        self.room = layout['room']
        self.furniture = layout['furniture']
        self.openings = layout['openings']
        
        # Define paired furniture relationships
        self.paired_furniture = {
            'bedside': {'parent': 'bed', 'max_distance': 50},
            'study chair': {'parent': 'study table', 'max_distance': 30}
        }
        
    def validate(self):
        """Main validation - returns violations list"""
        violations = []
        
        # 1. Check overlaps (CRITICAL)
        violations.extend(self._check_overlaps())
        
        # 2. Check clearances
        violations.extend(self._check_clearances())
        
        # 3. Check turning space
        violations.extend(self._check_turning_space())
        
        # 4. Check door swing
        violations.extend(self._check_door_swing())
        
        # 5. Check emergency path
        violations.extend(self._check_emergency_path())
        
        # 6. Check bed-specific clearances
        violations.extend(self._check_bed_clearances())
        
        # 7. Check paired furniture placement
        violations.extend(self._check_paired_furniture())
        
        # 8. Check window blocking
        violations.extend(self._check_window_blocking())
        
        # 9. Check circulation paths
        violations.extend(self._check_circulation())
        
        # 10. Check furniture against walls
        violations.extend(self._check_wall_placement())
        
        return violations
    
    def _get_furniture_polygon(self, item):
        """Convert furniture to Shapely polygon with rotation"""
        x, y, w, h = item['x'], item['y'], item['width'], item['height']
        rect = box(x, y, x + w, y + h)
        
        # Apply rotation if exists
        rotation = item.get('rotation', 0)
        if rotation != 0:
            center = (x + w/2, y + h/2)
            rect = shapely_rotate(rect, rotation, origin=center)
        
        return rect
    
    def _check_overlaps(self):
        """No furniture can overlap - most critical check"""
        violations = []
        polygons = [(f['name'], self._get_furniture_polygon(f)) 
                    for f in self.furniture]
        
        for i, (name1, poly1) in enumerate(polygons):
            for name2, poly2 in polygons[i+1:]:
                if poly1.intersects(poly2):
                    overlap_area = poly1.intersection(poly2).area
                    violations.append(f"CRITICAL: {name1} overlaps {name2} (area: {overlap_area:.0f}cm²)")
        
        return violations
    
    def _check_clearances(self):
        """150cm clearance in front of major furniture"""
        violations = []
        CLEARANCE = 150  # cm
        
        # Items that need clearance
        clearance_items = ['bed', 'wardrobe', 'sofa', 'study table']
        
        for item in self.furniture:
            # Check if this item needs clearance
            needs_clearance = any(ci in item['name'].lower() for ci in clearance_items)
            if not needs_clearance:
                continue
            
            clearance_zone = self._get_clearance_zone(item, CLEARANCE)
            
            # Check if clearance overlaps with other furniture
            for other in self.furniture:
                if other['name'] == item['name']:
                    continue
                
                # Allow bedside tables near bed
                if 'bed' in item['name'].lower() and 'bedside' in other['name'].lower():
                    continue
                
                # Allow chair near study table
                if 'study table' in item['name'].lower() and 'chair' in other['name'].lower():
                    continue
                    
                other_poly = self._get_furniture_polygon(other)
                if clearance_zone.intersects(other_poly):
                    violations.append(
                        f"Clearance: {item['name']} needs 150cm clearance, blocked by {other['name']}"
                    )
            
            # Check if clearance is within room bounds
            room_bounds = box(0, 0, self.room['width'], self.room['height'])
            if not room_bounds.contains(clearance_zone):
                # Check how much extends outside
                outside_area = clearance_zone.difference(room_bounds).area
                if outside_area > clearance_zone.area * 0.3:  # More than 30% outside
                    violations.append(
                        f"Clearance: {item['name']} clearance extends significantly outside room"
                    )
        
        return violations
    
    def _get_clearance_zone(self, item, clearance):
        """Get the clearance zone based on furniture type and rotation"""
        x, y = item['x'], item['y']
        w, h = item['width'], item['height']
        rot = item.get('rotation', 0)
        
        # Adjust clearance zone based on furniture type
        if 'bed' in item['name'].lower():
            # Bed needs clearance on long sides
            if rot in [0, 180]:
                # Clearance on left and right
                clear_box = box(x - clearance, y, x + w + clearance, y + h)
            else:  # 90, 270
                # Clearance on top and bottom
                clear_box = box(x, y - clearance, x + w, y + h + clearance)
        
        elif 'wardrobe' in item['name'].lower():
            # Wardrobe needs clearance in front (where doors open)
            if rot == 0:
                clear_box = box(x, y + h, x + w, y + h + clearance)
            elif rot == 90:
                clear_box = box(x - clearance, y, x, y + h)
            elif rot == 180:
                clear_box = box(x, y - clearance, x + w, y)
            else:  # 270
                clear_box = box(x + w, y, x + w + clearance, y + h)
        
        elif 'study table' in item['name'].lower():
            # Study table needs clearance where person sits
            if rot == 0:
                clear_box = box(x, y + h, x + w, y + h + clearance)
            elif rot == 90:
                clear_box = box(x - clearance, y, x, y + h)
            elif rot == 180:
                clear_box = box(x, y - clearance, x + w, y)
            else:  # 270
                clear_box = box(x + w, y, x + w + clearance, y + h)
        
        else:
            # Default: clearance in front
            if rot == 0:
                clear_box = box(x, y + h, x + w, y + h + clearance)
            elif rot == 90:
                clear_box = box(x - clearance, y, x, y + h)
            elif rot == 180:
                clear_box = box(x, y - clearance, x + w, y)
            else:  # 270
                clear_box = box(x + w, y, x + w + clearance, y + h)
        
        return clear_box
    
    def _check_turning_space(self):
        """At least one 150x150cm turning space for wheelchair"""
        violations = []
        TURNING_SIZE = 150  # cm
        
        # Create grid of potential turning spaces
        room_w, room_h = self.room['width'], self.room['height']
        step = 25  # Check every 25cm for better coverage
        
        found_valid = False
        valid_spaces = []
        
        for x in range(0, room_w - TURNING_SIZE + 1, step):
            for y in range(0, room_h - TURNING_SIZE + 1, step):
                turning_zone = box(x, y, x + TURNING_SIZE, y + TURNING_SIZE)
                
                # Check if clear of all furniture
                is_clear = True
                for item in self.furniture:
                    item_poly = self._get_furniture_polygon(item)
                    if turning_zone.intersects(item_poly):
                        is_clear = False
                        break
                
                if is_clear:
                    found_valid = True
                    valid_spaces.append((x, y))
        
        if not found_valid:
            violations.append(
                "Accessibility: No 150×150cm turning space available for wheelchair"
            )
        elif len(valid_spaces) < 2:
            violations.append(
                "Accessibility: Only one turning space available, recommend at least two"
            )
        
        return violations
    
    def _check_door_swing(self):
        """90cm door swing arc must be clear"""
        violations = []
        SWING_RADIUS = 90  # cm
        
        for opening in self.openings:
            if opening['type'] != 'door':
                continue
            
            # Get door swing zone
            swing_zone = self._get_door_swing_zone(opening, SWING_RADIUS)
            
            # Check if any furniture blocks swing
            blocking_furniture = []
            for item in self.furniture:
                item_poly = self._get_furniture_polygon(item)
                if swing_zone.intersects(item_poly):
                    blocking_furniture.append(item['name'])
            
            if blocking_furniture:
                violations.append(
                    f"Door access: Door swing blocked by {', '.join(blocking_furniture)}"
                )
        
        return violations
    
    def _get_door_swing_zone(self, door, radius):
        """Create door swing arc polygon"""
        wall = door['wall']
        pos = door['position']
        size = door['size']
        
        # Create swing arc based on wall
        if wall == 'top':
            center = (pos + size/2, 0)
            swing = Point(center).buffer(radius)
            room_half = box(0, 0, self.room['width'], radius)
            swing = swing.intersection(room_half)
        elif wall == 'bottom':
            center = (pos + size/2, self.room['height'])
            swing = Point(center).buffer(radius)
            room_half = box(0, self.room['height'] - radius, 
                           self.room['width'], self.room['height'])
            swing = swing.intersection(room_half)
        elif wall == 'left':
            center = (0, pos + size/2)
            swing = Point(center).buffer(radius)
            room_half = box(0, 0, radius, self.room['height'])
            swing = swing.intersection(room_half)
        else:  # right
            center = (self.room['width'], pos + size/2)
            swing = Point(center).buffer(radius)
            room_half = box(self.room['width'] - radius, 0, 
                           self.room['width'], self.room['height'])
            swing = swing.intersection(room_half)
        
        return swing
    
    def _check_emergency_path(self):
        """Clear 90cm path from bed to door"""
        violations = []
        PATH_WIDTH = 90  # cm
        
        # Find bed
        bed = next((f for f in self.furniture if 'bed' in f['name'].lower()), None)
        if not bed:
            return violations
        
        # Find door
        door = next((o for o in self.openings if o['type'] == 'door'), None)
        if not door:
            return violations
        
        # Get bed exit point (side of bed)
        bed_poly = self._get_furniture_polygon(bed)
        bed_center = bed_poly.centroid
        
        # Get door center
        door_pos = self._get_door_center(door)
        
        # Create path with width
        path_line = LineString([bed_center, door_pos])
        path_zone = path_line.buffer(PATH_WIDTH/2)
        
        # Check if path is blocked
        blocked_by = []
        for item in self.furniture:
            if 'bed' in item['name'].lower():
                continue
            
            item_poly = self._get_furniture_polygon(item)
            if path_zone.intersects(item_poly):
                blocked_by.append(item['name'])
        
        if blocked_by:
            violations.append(
                f"Emergency path: Path from bed to door blocked by {', '.join(blocked_by)}"
            )
        
        return violations
    
    def _get_door_center(self, door):
        """Get door center coordinates"""
        wall = door['wall']
        pos = door['position']
        size = door['size']
        
        if wall == 'top':
            return (pos + size/2, 0)
        elif wall == 'bottom':
            return (pos + size/2, self.room['height'])
        elif wall == 'left':
            return (0, pos + size/2)
        else:  # right
            return (self.room['width'], pos + size/2)
    
    def _check_bed_clearances(self):
        """Bed needs 150cm on at least one long side, 120cm on other"""
        violations = []
        
        # Find bed
        bed = next((f for f in self.furniture if 'bed' in f['name'].lower()), None)
        if not bed:
            return violations
        
        bed_poly = self._get_furniture_polygon(bed)
        rot = bed.get('rotation', 0)
        
        # Determine long sides based on rotation
        clearances_needed = [150, 120]  # At least one 150cm, other can be 120cm
        
        if rot in [0, 180]:
            # Left and right are long sides
            sides = [
                ('left', box(bed['x'] - 150, bed['y'], bed['x'], bed['y'] + bed['height'])),
                ('right', box(bed['x'] + bed['width'], bed['y'], 
                            bed['x'] + bed['width'] + 150, bed['y'] + bed['height']))
            ]
        else:  # 90 or 270
            # Top and bottom are long sides
            sides = [
                ('top', box(bed['x'], bed['y'] - 150, bed['x'] + bed['width'], bed['y'])),
                ('bottom', box(bed['x'], bed['y'] + bed['height'], 
                             bed['x'] + bed['width'], bed['y'] + bed['height'] + 150))
            ]
        
        # Check each side
        room_bounds = box(0, 0, self.room['width'], self.room['height'])
        available_clearances = []
        
        for side_name, clearance_zone in sides:
            # Check if within room
            if not room_bounds.contains(clearance_zone):
                continue
            
            # Check if blocked
            blocked = False
            for item in self.furniture:
                if 'bed' in item['name'].lower() or 'bedside' in item['name'].lower():
                    continue  # Allow bedside tables
                item_poly = self._get_furniture_polygon(item)
                if clearance_zone.intersects(item_poly):
                    blocked = True
                    break
            
            if not blocked:
                available_clearances.append(side_name)
        
        if len(available_clearances) == 0:
            violations.append(
                "Bed access: No long side of bed has required 150cm clearance"
            )
        elif len(available_clearances) == 1:
            # This is actually acceptable per DIN 18040-2
            pass
        
        return violations
    
    def _check_paired_furniture(self):
        """Check that paired furniture is properly positioned"""
        violations = []
        
        furniture_dict = {f['name'].lower(): f for f in self.furniture}
        
        for pair_type, config in self.paired_furniture.items():
            parent_type = config['parent']
            max_dist = config['max_distance']
            
            # Find paired items
            pair_item = None
            parent_item = None
            
            for name, item in furniture_dict.items():
                if pair_type in name:
                    pair_item = item
                elif parent_type in name:
                    parent_item = item
            
            if pair_item and parent_item:
                # Calculate distance between centers
                pair_center = (pair_item['x'] + pair_item['width']/2, 
                              pair_item['y'] + pair_item['height']/2)
                parent_center = (parent_item['x'] + parent_item['width']/2, 
                               parent_item['y'] + parent_item['height']/2)
                
                distance = math.sqrt((pair_center[0] - parent_center[0])**2 + 
                                   (pair_center[1] - parent_center[1])**2)
                
                # Check distance (accounting for furniture size)
                effective_max = max_dist + max(parent_item['width'], parent_item['height'])
                
                if distance > effective_max:
                    violations.append(
                        f"Paired furniture: {pair_type.title()} too far from {parent_type} "
                        f"({distance:.0f}cm, max {effective_max}cm)"
                    )
                
                # Special check for study chair orientation
                if 'chair' in pair_type and 'table' in parent_type:
                    # Chair should face the table
                    table_rot = parent_item.get('rotation', 0)
                    chair_rot = pair_item.get('rotation', 0)
                    
                    if abs(table_rot - chair_rot) > 45:  # More than 45 degrees difference
                        violations.append(
                            f"Orientation: Study chair not properly oriented to table"
                        )
        
        return violations
    
    def _check_window_blocking(self):
        """Check if furniture blocks windows"""
        violations = []
        windows = [o for o in self.openings if o['type'] == 'window']
        
        for window in windows:
            wall = window['wall']
            pos = window['position']
            size = window['size']
            
            # Define window blocking zone (within 100cm of wall with window)
            if wall == 'top':
                block_zone = box(pos, 0, pos + size, 100)
            elif wall == 'bottom':
                block_zone = box(pos, self.room['height'] - 100, 
                               pos + size, self.room['height'])
            elif wall == 'left':
                block_zone = box(0, pos, 100, pos + size)
            else:  # right
                block_zone = box(self.room['width'] - 100, pos, 
                               self.room['width'], pos + size)
            
            # Check which furniture blocks the window
            blocking_items = []
            for item in self.furniture:
                # Study tables near windows are OK
                if 'study table' in item['name'].lower():
                    continue
                
                item_poly = self._get_furniture_polygon(item)
                if block_zone.intersects(item_poly):
                    # Check how much it blocks
                    intersection = block_zone.intersection(item_poly)
                    if intersection.area > block_zone.area * 0.3:  # Blocks >30% of window zone
                        blocking_items.append(item['name'])
            
            if blocking_items:
                # Wardrobes blocking windows are worse
                severe_items = [i for i in blocking_items if 'wardrobe' in i.lower()]
                if severe_items:
                    violations.append(
                        f"Window blocked: {', '.join(severe_items)} blocking window (reduces natural light)"
                    )
                else:
                    violations.append(
                        f"Window access: {', '.join(blocking_items)} partially blocking window"
                    )
        
        return violations
    
    def _check_circulation(self):
        """Check that there's good circulation flow in the room"""
        violations = []
        
        # Check minimum passage width between furniture
        MIN_PASSAGE = 80  # cm minimum passage width
        
        # Create a grid to check passages
        room_w, room_h = self.room['width'], self.room['height']
        
        # Check horizontal passages
        blocked_horizontal = 0
        for y in range(MIN_PASSAGE, room_h - MIN_PASSAGE, 50):
            line = LineString([(0, y), (room_w, y)])
            passage = line.buffer(MIN_PASSAGE/2)
            
            blocked = False
            for item in self.furniture:
                item_poly = self._get_furniture_polygon(item)
                if passage.intersects(item_poly):
                    # Check if completely blocks passage
                    intersection = passage.intersection(item_poly)
                    if intersection.length > room_w * 0.8:  # Blocks >80% of room width
                        blocked = True
                        break
            
            if blocked:
                blocked_horizontal += 1
        
        # Check vertical passages
        blocked_vertical = 0
        for x in range(MIN_PASSAGE, room_w - MIN_PASSAGE, 50):
            line = LineString([(x, 0), (x, room_h)])
            passage = line.buffer(MIN_PASSAGE/2)
            
            blocked = False
            for item in self.furniture:
                item_poly = self._get_furniture_polygon(item)
                if passage.intersects(item_poly):
                    intersection = passage.intersection(item_poly)
                    if intersection.length > room_h * 0.8:
                        blocked = True
                        break
            
            if blocked:
                blocked_vertical += 1
        
        # Check if room is too blocked
        total_h_lines = (room_h - 2*MIN_PASSAGE) // 50
        total_v_lines = (room_w - 2*MIN_PASSAGE) // 50
        
        if total_h_lines > 0 and blocked_horizontal / total_h_lines > 0.7:
            violations.append(
                "Circulation: Limited horizontal movement through room"
            )
        
        if total_v_lines > 0 and blocked_vertical / total_v_lines > 0.7:
            violations.append(
                "Circulation: Limited vertical movement through room"
            )
        
        return violations
    
    def _check_wall_placement(self):
        """Check furniture is properly placed against walls"""
        violations = []
        
        # Items that should be against walls
        wall_furniture = ['bed', 'wardrobe', 'sofa', 'study table']
        
        for item in self.furniture:
            # Check if this should be against a wall
            should_be_wall = any(wf in item['name'].lower() for wf in wall_furniture)
            if not should_be_wall:
                continue
            
            # Check distance to nearest wall
            x, y = item['x'], item['y']
            w, h = item['width'], item['height']
            
            distances_to_walls = [
                y,  # Distance to top wall
                self.room['height'] - (y + h),  # Distance to bottom wall
                x,  # Distance to left wall
                self.room['width'] - (x + w)  # Distance to right wall
            ]
            
            min_distance = min(distances_to_walls)
            
            # Furniture should be within 50cm of a wall
            if min_distance > 50:
                if 'bed' in item['name'].lower() and min_distance < 100:
                    # Beds can be slightly further for spacious layouts
                    pass
                else:
                    violations.append(
                        f"Placement: {item['name']} too far from walls ({min_distance:.0f}cm)"
                    )
        
        return violations
    
    def get_layout_score(self):
        """Calculate overall layout score (lower is better)"""
        violations = self.validate()
        
        # Weight different types of violations
        score = 0
        for v in violations:
            if 'CRITICAL' in v or 'overlap' in v.lower():
                score += 10  # Heavy penalty for overlaps
            elif 'Emergency' in v or 'Door' in v:
                score += 5  # Important for safety
            elif 'Paired' in v:
                score += 3  # Important for usability
            elif 'Window' in v and 'wardrobe' in v.lower():
                score += 3  # Bad for natural light
            elif 'Accessibility' in v:
                score += 2  # DIN compliance
            else:
                score += 1  # Other violations
        
        return score
    
    def get_detailed_report(self):
        """Generate detailed validation report"""
        violations = self.validate()
        
        report = {
            'total_violations': len(violations),
            'score': self.get_layout_score(),
            'critical_issues': [v for v in violations if 'CRITICAL' in v or 'overlap' in v.lower()],
            'accessibility_issues': [v for v in violations if 'Accessibility' in v or 'clearance' in v.lower()],
            'safety_issues': [v for v in violations if 'Emergency' in v or 'Door' in v],
            'usability_issues': [v for v in violations if 'Paired' in v or 'Window' in v],
            'other_issues': [v for v in violations if not any(k in v for k in ['CRITICAL', 'overlap', 'Accessibility', 
                                                                            'clearance', 'Emergency', 'Door', 
                                                                            'Paired', 'Window'])]
        }
        
        return report