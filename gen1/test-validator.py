# test-enhanced-validator.py
import json
import os
from validator import LayoutValidator

# ====================
# CONFIGURATION - EDIT THIS PATH
# ====================
LAYOUT_FILE = 'Input-Layouts/room-layout.json'  # Change this to test different layouts
OUTPUT_FOLDER = 'validation_outputs'  # Where images are saved
# ====================

# Create output folder
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Load layout
print(f"\nLoading layout from: {LAYOUT_FILE}")
with open(LAYOUT_FILE) as f:
    layout = json.load(f)

# Validate
print("\nRunning validation...\n")
validator = LayoutValidator(layout)
violations = validator.validate()

# Print violations
print(f"Found {len(violations)} violations:")
for v in violations:
    print(f"  - {v}")

# Print detailed report
print("\n" + "="*70)
validator.print_terminal_report()

# Get detailed report (JSON for UI)
detailed_report = validator.get_detailed_report()
print("\nDetailed Report (JSON):")
print(json.dumps(detailed_report, indent=2))

# Save visualization
output_file = os.path.join(OUTPUT_FOLDER, 'layout_validation.png')
print(f"\nGenerating visualization...")
validator.visualize_layout(output_file)
print(f"✓ Saved to: {output_file}")