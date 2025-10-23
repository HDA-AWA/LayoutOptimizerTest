"""
Simple Validator Test - Just run it on your layout files
Usage: python simple_test.py your-layout.json
"""

import json
import sys

# Import validator
try:
    from validator import LayoutValidator
except ImportError:
    print("❌ Error: Cannot import validator")
    print("Make sure validator.py is in the same directory")
    print("Install shapely: pip install shapely")
    sys.exit(1)


def test_layout(filename):
    """Test a layout file and print violations"""
    
    print("="*70)
    print(f" TESTING: {filename}")
    print("="*70)
    
    # Load layout
    try:
        with open(filename, 'r') as f:
            layout = json.load(f)
        print(f"✅ Loaded layout: {filename}")
    except FileNotFoundError:
        print(f"❌ File not found: {filename}")
        return
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON in: {filename}")
        return
    
    # Show layout info
    print(f"\n📐 Room: {layout['room']['width']}x{layout['room']['height']} cm")
    print(f"🪑 Furniture: {len(layout.get('furniture', []))} items")
    print(f"🚪 Openings: {len(layout.get('openings', []))} items")
    
    # Validate
    print("\n🔍 Running validation...")
    validator = LayoutValidator(layout)
    violations = validator.validate()
    
    # Results
    print("\n" + "="*70)
    print(f" RESULTS: {len(violations)} VIOLATIONS")
    print("="*70)
    
    if not violations:
        print("\n🎉 Perfect! No violations found.")
        return
    
    # Group violations by type
    groups = {
        "Overlaps": [],
        "Clearances": [],
        "Bed Clearances": [],
        "Turning Space": [],
        "Door": [],
        "Emergency Path": [],
        "Windows": []
    }
    
    for v in violations:
        if "overlap" in v.lower():
            groups["Overlaps"].append(v)
        elif "bed" in v.lower() and "clearance" in v.lower():
            groups["Bed Clearances"].append(v)
        elif "clearance" in v.lower():
            groups["Clearances"].append(v)
        elif "turning" in v.lower():
            groups["Turning Space"].append(v)
        elif "door" in v.lower():
            groups["Door"].append(v)
        elif "emergency" in v.lower() or "path" in v.lower():
            groups["Emergency Path"].append(v)
        elif "window" in v.lower() or "sill" in v.lower() or "INFO:" in v:
            groups["Windows"].append(v)
    
    # Print grouped violations
    for category, viols in groups.items():
        if viols:
            print(f"\n{category}: {len(viols)}")
            for v in viols:
                if v.startswith("INFO:"):
                    print(f"   ℹ️  {v}")
                else:
                    print(f"   • {v}")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    # Check arguments
    if len(sys.argv) < 2:
        print("Usage: python simple_test.py <layout-file.json>")
        print("\nExample:")
        print("  python simple_test.py room-layout.json")
        sys.exit(1)
    
    # Test the file
    test_layout(sys.argv[1])