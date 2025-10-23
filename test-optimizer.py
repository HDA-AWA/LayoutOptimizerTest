"""
Test Composite Unit Optimizer - Bed + Bedside Stuck Together
"""
import json
import sys
import math

def calculate_distance(item1, item2):
    """Calculate center-to-center distance"""
    x1 = item1['x'] + item1['width'] / 2
    y1 = item1['y'] + item1['height'] / 2
    x2 = item2['x'] + item2['width'] / 2
    y2 = item2['y'] + item2['height'] / 2
    return math.sqrt((x1 - x2)**2 + (y1 - y2)**2)

def test_composite(input_file):
    print("="*70)
    print(" TESTING COMPOSITE UNIT OPTIMIZER")
    print("="*70)
    print(f"\nInput: {input_file}\n")
    
    # Load layout
    try:
        with open(input_file, 'r') as f:
            layout = json.load(f)
    except Exception as e:
        print(f"❌ Error loading file: {e}")
        return
    
    # Show input
    furniture = layout.get('furniture', [])
    bed_count = sum(1 for f in furniture if 'bed' in f['name'].lower() and 'bedside' not in f['name'].lower())
    bedside_count = sum(1 for f in furniture if 'bedside' in f['name'].lower())
    
    print(f"📦 INPUT:")
    print(f"   Room: {layout['room']['width']}x{layout['room']['height']}cm")
    print(f"   Total furniture: {len(furniture)}")
    print(f"   - Beds: {bed_count}")
    print(f"   - Bedside tables: {bedside_count}")
    print(f"   - Other: {len(furniture) - bed_count - bedside_count}")
    
    # Run composite optimizer
    try:
        from optimizer import LayoutOptimizer
        
        print(f"\n🔧 RUNNING COMPOSITE OPTIMIZER...")
        print(f"   Strategy: Bed + Bedside as ONE UNIT\n")
        
        optimizer = LayoutOptimizer(layout)
        optimized = optimizer.optimize(max_iterations=200)
        
        if not optimized:
            print("\n❌ No solution found")
            return
        
        # Check output
        output_furniture = optimized.get('furniture', [])
        output_bed = sum(1 for f in output_furniture if 'bed' in f['name'].lower() and 'bedside' not in f['name'].lower())
        output_bedside = sum(1 for f in output_furniture if 'bedside' in f['name'].lower())
        
        print(f"\n📦 OUTPUT:")
        print(f"   Total furniture: {len(output_furniture)}")
        print(f"   - Beds: {output_bed}")
        print(f"   - Bedside tables: {output_bedside}")
        print(f"   - Other: {len(output_furniture) - output_bed - output_bedside}")
        
        # Critical check: Did bedside survive?
        if bedside_count > 0:
            if output_bedside == bedside_count:
                print(f"\n   ✅ BEDSIDE PRESERVED: {output_bedside} table(s) in output")
            else:
                print(f"\n   ❌ BEDSIDE LOST: Had {bedside_count}, now have {output_bedside}")
        
        # Check distance
        bed = next((f for f in output_furniture if 'bed' in f['name'].lower() and 'bedside' not in f['name'].lower()), None)
        bedside = next((f for f in output_furniture if 'bedside' in f['name'].lower()), None)
        
        if bed and bedside:
            distance = calculate_distance(bed, bedside)
            print(f"\n📏 DISTANCE CHECK:")
            print(f"   Bed center: ({bed['x'] + bed['width']/2:.0f}, {bed['y'] + bed['height']/2:.0f})")
            print(f"   Bedside center: ({bedside['x'] + bedside['width']/2:.0f}, {bedside['y'] + bedside['height']/2:.0f})")
            print(f"   Distance: {distance:.1f}cm")
            print(f"   Requirement: ≤60cm")
            print(f"   Status: {'✅ PASS' if distance <= 60 else '⚠️  EXCEEDS (but bedside preserved!)'}")
        
        # Run validator
        from validator import LayoutValidator
        validator = LayoutValidator(optimized)
        violations = validator.validate()
        
        print(f"\n📋 VIOLATIONS: {len(violations)}")
        
        reach_viols = [v for v in violations if 'reach' in v.lower() and 'bedside' in v.lower()]
        if reach_viols:
            print(f"   Bedside reach violations: {len(reach_viols)}")
            for v in reach_viols[:2]:
                print(f"      • {v}")
        
        # Save
        output_file = 'room-layout-composite.json'
        with open(output_file, 'w') as f:
            json.dump(optimized, f, indent=2)
        print(f"\n💾 Saved to: {output_file}")
        
        # Summary
        print("\n" + "="*70)
        print(" SUMMARY")
        print("="*70)
        print(f"Approach: Composite Unit (Bed + Bedside as ONE)")
        print(f"Bedside preserved: {'✅ YES' if output_bedside == bedside_count else '❌ NO'}")
        print(f"Total violations: {len(violations)}")
        print("="*70)
        
    except ImportError as e:
        print(f"❌ Cannot import optimizer: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_composite.py <layout-file.json>")
        sys.exit(1)
    
    test_composite(sys.argv[1])