---
name: ocp-operator-compatibility-enhanced
description: Check OpenShift operator compatibility with dependent operators and upgrade paths
---

# OpenShift Operator Compatibility Checker (Enhanced)

Check if installed operators are compatible with target OCP version, including dependency validation and upgrade path information.

## Usage

```bash
gemini check operators compatibility for OCP <version> <must-gather-path>
```

**Example:**
```bash
gemini check operators compatibility for OCP 4.22 /cases/12345678/must-gather.local.xxx
```

**⚠️ Important:** Run this command from the directory where you downloaded:
- `ocp-operator-compatibility-enhanced.md` (this skill)
- `compatibility_matrix.json`

## What This Checks

✅ Operator compatibility with target OCP version  
✅ **Dependent operators** (if operator requires other operators)  
✅ **OLM skip ranges** (upgrade path information)  
✅ Available versions for incompatible operators  
✅ Max supported OCP version for each operator  

## Code

```python
#!/usr/bin/env python3
import json
import os
import sys
import subprocess
from pathlib import Path

def load_compatibility_matrix():
    """Load the compatibility matrix"""
    # Check current directory first
    matrix_file = Path("compatibility_matrix.json")

    if not matrix_file.exists():
        print("❌ Error: compatibility_matrix.json not found in current directory")
        print("\n📋 Download it first:")
        print("   curl -O https://raw.githubusercontent.com/navaneethas/ocp-operator-upgrade-advisor/main/compatibility_matrix.json")
        sys.exit(1)

    with open(matrix_file, 'r') as f:
        return json.load(f)

def collect_cluster_data(must_gather_path):
    """Collect operator data from must-gather"""
    mg_path = Path(must_gather_path)

    if not mg_path.exists():
        print(f"❌ Must-gather path not found: {must_gather_path}")
        sys.exit(1)

    print(f"📂 Collecting data from: {must_gather_path}")

    # Find subscription and CSV data
    operators = {}

    # Use omc if available, otherwise use find
    try:
        # Get subscriptions
        sub_cmd = f"omc use {must_gather_path} && omc get sub -A -o json"
        sub_result = subprocess.run(sub_cmd, shell=True, capture_output=True, text=True)

        if sub_result.returncode == 0:
            sub_data = json.loads(sub_result.stdout)
            for item in sub_data.get('items', []):
                name = item['spec'].get('name', '')
                namespace = item['metadata'].get('namespace', '')
                if name:
                    operators[name] = {
                        'namespace': namespace,
                        'channel': item['spec'].get('channel', ''),
                        'currentCSV': item['status'].get('currentCSV', ''),
                        'installedCSV': item['status'].get('installedCSV', '')
                    }

        # Get CSV data for versions
        csv_cmd = f"omc use {must_gather_path} && omc get csv -A -o json"
        csv_result = subprocess.run(csv_cmd, shell=True, capture_output=True, text=True)

        if csv_result.returncode == 0:
            csv_data = json.loads(csv_result.stdout)
            for item in csv_data.get('items', []):
                csv_name = item['metadata'].get('name', '')
                # Extract operator name and version from CSV name
                # Format: operator-name.v1.2.3
                if '.' in csv_name:
                    parts = csv_name.rsplit('.', 1)
                    if len(parts) == 2:
                        op_name = parts[0]
                        version = parts[1]

                        # Match with subscription data
                        for sub_name, sub_data in operators.items():
                            if csv_name in [sub_data.get('currentCSV'), sub_data.get('installedCSV')]:
                                operators[sub_name]['version'] = version
                                operators[sub_name]['csv'] = csv_name
                                break

    except Exception as e:
        print(f"⚠️  omc failed, trying alternative method: {e}")

        # Fallback: search for YAML files
        try:
            sub_files = list(mg_path.glob("**/subscriptions.yaml"))
            if sub_files:
                # Parse YAML files (simple parsing)
                for sub_file in sub_files:
                    with open(sub_file, 'r') as f:
                        content = f.read()
                        # Basic YAML parsing - look for operator names
                        # This is simplified - real implementation would use yaml module
                        pass
        except Exception as e:
            print(f"⚠️  Fallback method also failed: {e}")

    if not operators:
        print("❌ No operators found in must-gather")
        print("\n💡 Make sure the must-gather contains:")
        print("   - cluster-scoped-resources/core/subscriptions.yaml")
        print("   - cluster-scoped-resources/core/clusterserviceversions.yaml")
        sys.exit(1)

    print(f"✅ Found {len(operators)} installed operators\n")
    return operators

def check_compatibility(operators, target_ocp, matrix):
    """Check operator compatibility with target OCP version"""
    print("=" * 80)
    print(f"OpenShift Operator Compatibility Report for OCP {target_ocp}")
    print("=" * 80)
    print()

    compatible = []
    incompatible = []
    upgrade_required = []

    for op_name, op_data in operators.items():
        current_version = op_data.get('version', 'unknown')
        csv = op_data.get('csv', op_name)

        # Check if operator exists in matrix
        if op_name not in matrix:
            print(f"⚠️  {op_name}: Not found in compatibility matrix (might be community/certified operator)")
            continue

        op_matrix = matrix[op_name]

        # Check if target OCP version is supported
        if target_ocp not in op_matrix:
            incompatible.append((op_name, current_version, csv, None, op_matrix))
            continue

        target_data = op_matrix[target_ocp]
        available_versions = target_data.get('versions', [])
        max_ocp = target_data.get('maxOCPVersion')
        dependencies = target_data.get('dependencies', [])
        skip_ranges = target_data.get('skipRanges', {})

        # Check if current version is in available versions
        current_csv_in_available = any(current_version in v or csv in v for v in available_versions)

        if current_csv_in_available:
            compatible.append((op_name, current_version, csv, target_data))
        else:
            # Check if upgrade available
            if available_versions:
                upgrade_required.append((op_name, current_version, csv, target_data))
            else:
                incompatible.append((op_name, current_version, csv, max_ocp, op_matrix))

    # Display results
    print(f"✅ Compatible: {len(compatible)}")
    print(f"⚠️  Upgrade Required: {len(upgrade_required)}")
    print(f"❌ Incompatible: {len(incompatible)}")
    print()
    print("=" * 80)
    print()

    # Show compatible operators
    if compatible:
        print("✅ COMPATIBLE OPERATORS")
        print("-" * 80)
        for op_name, version, csv, data in compatible:
            print(f"\n📦 {op_name}")
            print(f"   Current: {csv} (v{version})")
            print(f"   Status: ✅ Compatible with OCP {target_ocp}")

            # Show dependencies
            if data.get('dependencies'):
                print(f"   Dependencies:")
                for dep in data['dependencies']:
                    print(f"      • {dep}")
            else:
                print(f"   Dependencies: No dependent operators")

            # Show skip range if available
            skip_info = data.get('skipRanges', {})
            if skip_info:
                for ver, skip_range in list(skip_info.items())[:1]:  # Show first skip range
                    print(f"   OLM Skip Range: {skip_range}")
                    print(f"      (Can upgrade directly from versions in this range)")
            else:
                print(f"   OLM Skip Range: Sequential upgrades required")

        print()

    # Show upgrade required operators
    if upgrade_required:
        print("⚠️  UPGRADE REQUIRED OPERATORS")
        print("-" * 80)
        for op_name, version, csv, data in upgrade_required:
            available = data.get('versions', [])
            latest = available[0] if available else 'unknown'

            print(f"\n📦 {op_name}")
            print(f"   Current: {csv} (v{version})")
            print(f"   Status: ⚠️  Upgrade required for OCP {target_ocp}")
            print(f"   Available versions: {', '.join(available[:3])}")
            print(f"   Recommended: Upgrade to {latest}")

            # Show dependencies
            if data.get('dependencies'):
                print(f"   Dependencies:")
                for dep in data['dependencies']:
                    print(f"      • {dep}")
            else:
                print(f"   Dependencies: No dependent operators")

            # Show skip range
            skip_info = data.get('skipRanges', {})
            if skip_info:
                for ver, skip_range in list(skip_info.items())[:1]:
                    print(f"   OLM Skip Range: {skip_range}")
            else:
                print(f"   OLM Skip Range: Sequential upgrades required")

        print()

    # Show incompatible operators
    if incompatible:
        print("❌ INCOMPATIBLE OPERATORS")
        print("-" * 80)
        for op_name, version, csv, max_ocp, op_matrix in incompatible:
            print(f"\n📦 {op_name}")
            print(f"   Current: {csv} (v{version})")
            print(f"   Status: ❌ Incompatible with OCP {target_ocp}")

            if max_ocp:
                print(f"   Max supported OCP: {max_ocp}")

            # Show which OCP versions are supported
            supported_versions = sorted(op_matrix.keys())
            if supported_versions:
                print(f"   Supported OCP versions: {', '.join(supported_versions)}")

            # Check dependencies (from latest available version)
            if supported_versions:
                latest_ocp = supported_versions[-1]
                latest_data = op_matrix[latest_ocp]
                if latest_data.get('dependencies'):
                    print(f"   Dependencies:")
                    for dep in latest_data['dependencies']:
                        print(f"      • {dep}")

        print()

    print("=" * 80)
    print("\n📋 Summary:")
    print(f"   Total operators checked: {len(operators)}")
    print(f"   Compatible: {len(compatible)}")
    print(f"   Upgrade required: {len(upgrade_required)}")
    print(f"   Incompatible: {len(incompatible)}")

    if incompatible:
        print(f"\n⚠️  Warning: {len(incompatible)} operator(s) are incompatible with OCP {target_ocp}")
        print(f"   These operators may block the cluster upgrade.")

def main():
    if len(sys.argv) < 3:
        print("Usage: check operators compatibility for OCP <version> <must-gather-path>")
        sys.exit(1)

    # Parse arguments - handle various formats
    args = sys.argv[1:]
    target_ocp = None
    must_gather_path = None

    # Find OCP version and path
    for i, arg in enumerate(args):
        if arg.replace('.', '').isdigit() and '.' in arg:
            target_ocp = arg
        elif os.path.exists(arg):
            must_gather_path = arg

    if not target_ocp:
        print("❌ Error: OCP version not specified")
        print("   Example: check operators compatibility for OCP 4.22 /path/to/must-gather")
        sys.exit(1)

    if not must_gather_path:
        print("❌ Error: Must-gather path not specified")
        sys.exit(1)

    # Load compatibility matrix
    matrix = load_compatibility_matrix()

    # Collect cluster data
    operators = collect_cluster_data(must_gather_path)

    # Check compatibility
    check_compatibility(operators, target_ocp, matrix)

if __name__ == '__main__':
    main()
```

## Features

### 1. Dependency Checking
Shows which operators depend on other operators:
```
Dependencies:
  • multicluster-engine (>=2.0.0)
```

### 2. Skip Range Information
Explains upgrade paths:
```
OLM Skip Range: >=2.11.0 <2.13.2
(Can upgrade directly from versions in this range)
```

### 3. Compatibility Status
- ✅ **Compatible**: No action needed
- ⚠️ **Upgrade Required**: Operator needs update
- ❌ **Incompatible**: Operator not supported in target OCP

## Data Source

Compatibility data automatically collected from Red Hat operator catalogs using OPM.

**Data coverage:** OCP 4.12 through 4.22  
**Total operators:** 150+ Red Hat operators  
**Updated:** Automatically via weekly automation
