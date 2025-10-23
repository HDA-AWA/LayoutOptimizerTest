"""
Test Optimizer - Modified for V3 with Full Violation Display
Usage: python test-optimizer.py
"""
import json
import os
import math
from pathlib import Path

# ============================================================================
# CONFIGURATION - CHANGE THESE SETTINGS
# ============================================================================

# MODE: 'single' or 'batch'
MODE = 'batch'

# For SINGLE mode: specify the input file path
SINGLE_INPUT = 'Input-Layouts/room-layout (1).json'

# For BATCH mode: specify the input folder
BATCH_INPUT_FOLDER = 'Input-Layouts'

# Output folder for all processed layouts
OUTPUT_FOLDER = 'Output-Layouts'

# Optimizer settings
MAX_ITERATIONS = 200

# ============================================================================


def calculate_distance(item1, item2):
    """Calculate center-to-center distance"""
    x1 = item1['x'] + item1['width'] / 2
    y1 = item1['y'] + item1['height'] / 2
    x2 = item2['x'] + item2['width'] / 2
    y2 = item2['y'] + item2['height'] / 2
    return math.sqrt((x1 - x2)**2 + (y1 - y2)**2)


def print_all_violations(violations_dict, title):
    """Print ALL violations without truncation"""
    
    if not violations_dict:
        print(f"   None!")
        return
    
    for category, violations in violations_dict.items():
        if violations:
            print(f"\n  {category} ({len(violations)}):")
            for v in violations:  # Print ALL, not just first 3
                print(f"    • {v}")


def process_layout(input_file, output_folder):
    """Process a single layout file"""
    
    print("="*80)
    print(f" PROCESSING: {input_file}")
    print("="*80)
    
    # Load layout
    try:
        with open(input_file, 'r') as f:
            layout = json.load(f)
    except Exception as e:
        print(f"❌ Error loading file: {e}")
        return False
    
    # Show input
    furniture = layout.get('furniture', [])
    bed_count = sum(1 for f in furniture if 'bed' in f['name'].lower() and 'bedside' not in f['name'].lower())
    bedside_count = sum(1 for f in furniture if 'bedside' in f['name'].lower())
    
    print(f"\n📦 INPUT:")
    print(f"   Room: {layout['room']['width']}x{layout['room']['height']}cm")
    print(f"   Total furniture: {len(furniture)}")
    print(f"   - Beds: {bed_count}")
    print(f"   - Bedside tables: {bedside_count}")
    print(f"   - Other: {len(furniture) - bed_count - bedside_count}")
    
    # Run optimizer V3
    try:
        from optimizer import LayoutOptimizer
        
        print(f"\n🔧 RUNNING OPTIMIZER V3...")
        
        optimizer = LayoutOptimizer(layout)
        optimized = optimizer.optimize(max_iterations=MAX_ITERATIONS)
        
        if not optimized:
            print("\n❌ No solution found")
            return False
        
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
                print(f"   ✅ BEDSIDE PRESERVED: {output_bedside} table(s)")
            else:
                print(f"   ⚠️  BEDSIDE COUNT: Had {bedside_count}, now have {output_bedside}")
        
        # Check distance
        bed = next((f for f in output_furniture if 'bed' in f['name'].lower() and 'bedside' not in f['name'].lower()), None)
        bedside = next((f for f in output_furniture if 'bedside' in f['name'].lower()), None)
        
        if bed and bedside:
            distance = calculate_distance(bed, bedside)
            print(f"\n📏 DISTANCE: {distance:.1f}cm ({'✅ ≤60cm' if distance <= 60 else '⚠️  >60cm'})")
        
        # Get violation report
        report = optimizer.get_violation_report()
        
        print(f"\n" + "="*80)
        print(f"📋 DETAILED VIOLATION REPORT")
        print(f"="*80)
        
        print(f"\n🔴 INITIAL VIOLATIONS:")
        print_all_violations(report['initial'], "INITIAL")
        
        print(f"\n" + "="*80)
        print(f"\n✅ FIXED VIOLATIONS:")
        print_all_violations(report['fixed'], "FIXED")
        
        print(f"\n" + "="*80)
        print(f"\n⚠️  REMAINING VIOLATIONS:")
        print_all_violations(report['remaining'], "REMAINING")
        
        if report['unplaced_furniture']:
            print(f"\n" + "="*80)
            print(f"\n❌ UNPLACED FURNITURE:")
            for item in report['unplaced_furniture']:
                print(f"  • {item['name']} ({item['width']}×{item['height']}cm)")
        
        # Save output
        os.makedirs(output_folder, exist_ok=True)
        
        # Generate output filename
        input_path = Path(input_file)
        output_filename = f"{input_path.stem}-optimized.json"
        output_path = os.path.join(output_folder, output_filename)
        
        with open(output_path, 'w') as f:
            json.dump(optimized, f, indent=2)
        
        print(f"\n💾 Saved to: {output_path}")
        
        # Summary
        initial_count = sum(len(v) for v in report['initial'].values())
        remaining_count = sum(len(v) for v in report['remaining'].values())
        
        print(f"\n✅ SUCCESS")
        print(f"   Violations: {initial_count} → {remaining_count}")
        print(f"   Improvement: {initial_count - remaining_count} violations fixed")
        print("="*80 + "\n")
        
        return True
        
    except ImportError as e:
        print(f"❌ Cannot import optimizer_v3: {e}")
        print(f"   Make sure optimizer_v3.py is in the same folder")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def process_single():
    """Process single file mode"""
    print("\n🎯 MODE: SINGLE FILE")
    print(f"Input: {SINGLE_INPUT}")
    print(f"Output folder: {OUTPUT_FOLDER}\n")
    
    if not os.path.exists(SINGLE_INPUT):
        print(f"❌ Error: File not found: {SINGLE_INPUT}")
        print("\nTo fix:")
        print(f"  1. Create the file: {SINGLE_INPUT}")
        print(f"  2. Or change SINGLE_INPUT in this script")
        return
    
    success = process_layout(SINGLE_INPUT, OUTPUT_FOLDER)
    
    if success:
        print("🎉 DONE!")
    else:
        print("❌ FAILED!")


def process_batch():
    """Process all JSON files in folder"""
    print("\n🎯 MODE: BATCH PROCESSING")
    print(f"Input folder: {BATCH_INPUT_FOLDER}")
    print(f"Output folder: {OUTPUT_FOLDER}\n")
    
    if not os.path.exists(BATCH_INPUT_FOLDER):
        print(f"❌ Error: Folder not found: {BATCH_INPUT_FOLDER}")
        print("\nTo fix:")
        print(f"  1. Create the folder: {BATCH_INPUT_FOLDER}")
        print(f"  2. Or change BATCH_INPUT_FOLDER in this script")
        return
    
    # Find all JSON files
    json_files = list(Path(BATCH_INPUT_FOLDER).glob('*.json'))
    
    if not json_files:
        print(f"❌ No JSON files found in: {BATCH_INPUT_FOLDER}")
        return
    
    print(f"📁 Found {len(json_files)} layout file(s)\n")
    
    results = []
    
    for i, json_file in enumerate(json_files, 1):
        print(f"\n[{i}/{len(json_files)}] Processing: {json_file.name}")
        success = process_layout(str(json_file), OUTPUT_FOLDER)
        results.append((json_file.name, success))
    
    # Final summary
    print("\n" + "="*80)
    print(" BATCH PROCESSING COMPLETE")
    print("="*80)
    
    successful = sum(1 for _, success in results if success)
    failed = len(results) - successful
    
    print(f"\n📊 SUMMARY:")
    print(f"   Total files: {len(results)}")
    print(f"   ✅ Successful: {successful}")
    print(f"   ❌ Failed: {failed}")
    
    if failed > 0:
        print(f"\n❌ Failed files:")
        for filename, success in results:
            if not success:
                print(f"   • {filename}")
    
    print(f"\n📂 All outputs saved to: {OUTPUT_FOLDER}")
    print("="*80)


def main():
    """Main entry point"""
    print("\n" + "="*80)
    print(" OPTIMIZER V3 - BATCH PROCESSOR")
    print("="*80)
    
    if MODE == 'single':
        process_single()
    elif MODE == 'batch':
        process_batch()
    else:
        print(f"❌ Invalid MODE: {MODE}")
        print("   Valid options: 'single' or 'batch'")
        print("   Change MODE in the configuration section")


if __name__ == "__main__":
    main()