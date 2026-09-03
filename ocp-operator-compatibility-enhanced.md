---
name: ocp-operator-compatibility-enhanced
description: Check OpenShift operator compatibility with detailed version analysis, dependencies, and upgrade paths
---

# OpenShift Operator Compatibility Checker (Enhanced)

Check if installed operators are compatible with target OCP version with detailed version information, dependency validation, and upgrade path guidance.

## Usage

```bash
gemini check operators compatibility for OCP <version> <must-gather-path>
```

**Example:**
```bash
gemini check operators compatibility for OCP 4.20 /cases/12345678/must-gather.local.xxx
```

**⚠️ Important:** Run this command from the directory where you downloaded:
- `ocp-operator-compatibility-enhanced.md` (this skill)
- `compatibility_matrix.json`

## What This Provides

✅ **Detailed operator analysis** with CSV names and versions  
✅ **Available versions** for each operator in target OCP  
✅ **Operator grouping** by product family (ODF, Logging, etc.)  
✅ **Dependent operators** (if operator requires other operators)  
✅ **OLM skip ranges** (upgrade path information)  
✅ **Specific recommendations** for each operator  
✅ **Non-Red Hat operator detection** (Certified/Community)  

## Code

```python
#!/usr/bin/env python3
import json
import os
import sys
import subprocess
from pathlib import Path
from collections import defaultdict

# Operator family groupings
OPERATOR_FAMILIES = {
    'odf': ['odf-operator', 'ocs-operator', 'rook-ceph-operator', 'mcg-operator', 
            'cephcsi-operator', 'odf-csi-addons-operator', 'odf-prometheus-operator',
            'odf-dependencies', 'ocs-client-operator', 'recipe'],
    'logging': ['cluster-logging', 'loki-operator', 'elasticsearch-operator'],
    'nmstate': ['kubernetes-nmstate-operator'],
    'observability': ['cluster-observability-operator', 'opentelemetry-product'],
}

def load_compatibility_matrix():
    """Load the compatibility matrix"""
    matrix_file = Path("compatibility_matrix.json")
    if not matrix_file.exists():
        print("❌ Error: compatibility_matrix.json not found in current directory")
        print("\n📋 Download it first:")
        print("   curl -O https://raw.githubusercontent.com/navaneethas/ocp-operators-upgrade-advisor-opm/main/compatibility_matrix.json")
        sys.exit(1)
    
    with open(matrix_file, 'r') as f:
        return json.load(f)

def collect_cluster_data(must_gather_path):
    """Collect operator data from must-gather"""
    mg_path = Path(must_gather_path)
    if not mg_path.exists():
        print(f"❌ Must-gather path not found: {must_gather_path}")
        sys.exit(1)
    
    print(f"📂 Collecting data from: {must_gather_path}\n")
    
    operators = {}
    
    # Try using omc
    try:
        sub_cmd = f"omc use {must_gather_path} && omc get sub -A -o json"
        sub_result = subprocess.run(sub_cmd, shell=True, capture_output=True, text=True, timeout=30)
        
        if sub_result.returncode == 0:
            sub_data = json.loads(sub_result.stdout)
            for item in sub_data.get('items', []):
                name = item['spec'].get('name', '')
                namespace = item['metadata'].get('namespace', '')
                source = item['spec'].get('source', 'redhat-operators')
                
                if name:
                    operators[name] = {
                        'namespace': namespace,
                        'channel': item['spec'].get('channel', ''),
                        'currentCSV': item['status'].get('currentCSV', ''),
                        'installedCSV': item['status'].get('installedCSV', ''),
                        'source': source,
                        'version': ''
                    }
        
        # Get CSV data
        csv_cmd = f"omc use {must_gather_path} && omc get csv -A -o json"
        csv_result = subprocess.run(csv_cmd, shell=True, capture_output=True, text=True, timeout=30)
        
        if csv_result.returncode == 0:
            csv_data = json.loads(csv_result.stdout)
            for item in csv_data.get('items', []):
                csv_name = item['metadata'].get('name', '')
                if '.' in csv_name:
                    parts = csv_name.rsplit('.', 1)
                    if len(parts) == 2:
                        version = parts[1]
                        for sub_name, sub_data in operators.items():
                            if csv_name in [sub_data.get('currentCSV'), sub_data.get('installedCSV')]:
                                operators[sub_name]['version'] = version
                                operators[sub_name]['csv'] = csv_name
                                break
    
    except Exception as e:
        print(f"⚠️  Error collecting data: {e}")
    
    if not operators:
        print("❌ No operators found in must-gather")
        sys.exit(1)
    
    print(f"✅ Found {len(operators)} installed operators\n")
    return operators

def get_operator_family(op_name):
    """Get operator family name"""
    for family, members in OPERATOR_FAMILIES.items():
        if op_name in members:
            return family
    return None

def format_version_list(versions):
    """Format version list for display"""
    if not versions:
        return "None"
    # Show first 5 versions
    if len(versions) > 5:
        return f"{', '.join(versions[:5])}, ... ({len(versions)} total)"
    return ', '.join(versions)

def check_compatibility(operators, target_ocp, matrix):
    """Check operator compatibility with detailed analysis"""
    
    print("=" * 100)
    print(f"📊 Detailed Operator Compatibility Analysis for OCP {target_ocp}")
    print("=" * 100)
    print()
    
    # Categorize operators
    redhat_ops = {}
    non_redhat_ops = {}
    
    for op_name, op_data in operators.items():
        source = op_data.get('source', 'redhat-operators')
        if 'redhat' in source.lower() or source == 'redhat-operators':
            redhat_ops[op_name] = op_data
        else:
            non_redhat_ops[op_name] = op_data
    
    # Group by families
    families = defaultdict(list)
    standalone = []
    
    for op_name, op_data in redhat_ops.items():
        family = get_operator_family(op_name)
        if family:
            families[family].append((op_name, op_data))
        else:
            standalone.append((op_name, op_data))
    
    # Process operator families
    if 'odf' in families:
        print_odf_analysis(families['odf'], target_ocp, matrix)
        print()
    
    if 'logging' in families:
        print_logging_analysis(families['logging'], target_ocp, matrix)
        print()
    
    # Process standalone operators
    for op_name, op_data in standalone:
        print_operator_detail(op_name, op_data, target_ocp, matrix)
        print()
    
    # Process other families
    for family, ops in families.items():
        if family not in ['odf', 'logging']:
            for op_name, op_data in ops:
                print_operator_detail(op_name, op_data, target_ocp, matrix)
                print()
    
    # Non-Red Hat operators
    if non_redhat_ops:
        print("\n" + "=" * 100)
        print("⚠️  Skipped (Certified/Community Operators)")
        print("=" * 100)
        print("\nThese operators are not tracked by Red Hat's compatibility matrix:")
        print("Verify compatibility with vendors before upgrading.\n")
        
        for op_name, op_data in non_redhat_ops.items():
            csv = op_data.get('csv', op_name)
            version = op_data.get('version', 'unknown')
            namespace = op_data.get('namespace', '')
            source = op_data.get('source', '')
            print(f"  • {op_name}")
            print(f"    CSV: {csv}")
            print(f"    Version: {version}")
            print(f"    Source: {source}")
            print(f"    Namespace: {namespace}")
            print()
    
    print("=" * 100)
    print("\n📋 For more information: https://access.redhat.com/labs/ocpouic/")
    print()

def print_odf_analysis(odf_ops, target_ocp, matrix):
    """Print ODF operator family analysis"""
    print("="  * 100)
    print("🗄️  OpenShift Data Foundation (ODF) - Storage Suite")
    print("=" * 100)
    print()
    
    # Get all ODF CSVs
    csvs = []
    sample_version = None
    for op_name, op_data in odf_ops:
        csv = op_data.get('csv', '')
        version = op_data.get('version', '')
        if csv:
            csvs.append(f"  • {csv}")
        if version and not sample_version:
            sample_version = version
    
    print(f"Installed Operators ({len(odf_ops)} components):")
    for csv in csvs:
        print(csv)
    print()
    
    # Check compatibility using first ODF operator as representative
    if odf_ops:
        op_name, op_data = odf_ops[0]
        
        if op_name in matrix and target_ocp in matrix[op_name]:
            target_data = matrix[op_name][target_ocp]
            available = target_data.get('versions', [])
            
            # Extract version numbers from CSVs
            available_versions = []
            for v in available[:10]:  # First 10
                if '.' in v:
                    parts = v.rsplit('.', 1)
                    if len(parts) == 2:
                        available_versions.append(parts[1])
            
            current_version = op_data.get('version', '')
            current_in_available = any(current_version in v for v in available)
            
            print(f"To OCP {target_ocp}:")
            if current_in_available:
                print(f"  Status: ✅ Compatible")
                print(f"  Current version ({current_version}) is supported")
            else:
                print(f"  Status: ⚠️  Upgrade Required")
                print(f"  Current version: {current_version}")
                print(f"  Supported versions: {format_version_list(available_versions)}")
                if available_versions:
                    print(f"  Recommendation: Upgrade ODF to {available_versions[0]} before upgrading cluster")
        else:
            print(f"To OCP {target_ocp}:")
            print(f"  Status: ❌ Not Found")
            print(f"  This version is not in the compatibility matrix")
    print()

def print_logging_analysis(logging_ops, target_ocp, matrix):
    """Print logging operator family analysis"""
    print("=" * 100)
    print("📝 Logging Stack")
    print("=" * 100)
    print()
    
    for op_name, op_data in logging_ops:
        print_operator_detail(op_name, op_data, target_ocp, matrix, indent=False)

def print_operator_detail(op_name, op_data, target_ocp, matrix, indent=True):
    """Print detailed operator analysis"""
    prefix = "  " if indent else ""
    
    # Display name mapping
    display_names = {
        'amq-broker-rhel9': 'AMQ Broker (RHEL 9)',
        'cluster-logging': 'Cluster Logging',
        'loki-operator': 'Loki Operator',
        'cincinnati-operator': 'OpenShift Update Service',
        'opentelemetry-product': 'OpenTelemetry Operator',
        'cluster-observability-operator': 'Cluster Observability Operator',
        'openshift-custom-metrics-autoscaler-operator': 'Custom Metrics Autoscaler',
        'kubernetes-nmstate-operator': 'Kubernetes NMState Operator',
    }
    
    display_name = display_names.get(op_name, op_name)
    
    print(f"{prefix}{'=' * 100}")
    print(f"{prefix}📦 {display_name}")
    print(f"{prefix}{'=' * 100}")
    print()
    
    csv = op_data.get('csv', op_name)
    version = op_data.get('version', 'unknown')
    channel = op_data.get('channel', '')
    
    print(f"{prefix}Operator: {op_name}")
    print(f"{prefix}Current CSV: {csv}")
    print(f"{prefix}Current Version: {version}")
    if channel:
        print(f"{prefix}Channel: {channel}")
    print()
    
    # Check in matrix
    if op_name not in matrix:
        print(f"{prefix}To OCP {target_ocp}:")
        print(f"{prefix}  Status: ⚠️  Not in compatibility matrix")
        print(f"{prefix}  This might be a certified/community operator")
        return
    
    op_matrix = matrix[op_name]
    
    if target_ocp not in op_matrix:
        print(f"{prefix}To OCP {target_ocp}:")
        print(f"{prefix}  Status: ❌ Incompatible")
        
        # Show which versions ARE supported
        supported_versions = sorted(op_matrix.keys())
        if supported_versions:
            print(f"{prefix}  Supported OCP versions: {', '.join(supported_versions)}")
        return
    
    target_data = op_matrix[target_ocp]
    available = target_data.get('versions', [])
    max_ocp = target_data.get('maxOCPVersion')
    dependencies = target_data.get('dependencies', [])
    skip_ranges = target_data.get('skipRanges', {})
    
    # Extract clean version numbers
    available_versions = []
    for v in available[:15]:
        if '.' in v:
            parts = v.rsplit('.', 1)
            if len(parts) == 2:
                available_versions.append(parts[1])
    
    # Check if current version is compatible
    current_in_available = any(version in v for v in available)
    
    print(f"{prefix}To OCP {target_ocp}:")
    if current_in_available:
        print(f"{prefix}  Status: ✅ Compatible")
        print(f"{prefix}  Supported versions: {format_version_list(available_versions)}")
    else:
        print(f"{prefix}  Status: ⚠️  Upgrade Required")
        print(f"{prefix}  Current version ({version}) not found in supported versions")
        print(f"{prefix}  Supported versions: {format_version_list(available_versions)}")
        if available_versions:
            print(f"{prefix}  Recommendation: Upgrade to {available_versions[0]}")
    
    if max_ocp:
        print(f"{prefix}  Max OCP Version: {max_ocp}")
    
    # Dependencies
    if dependencies:
        print(f"{prefix}  Dependencies:")
        for dep in dependencies:
            print(f"{prefix}    • {dep}")
    else:
        print(f"{prefix}  Dependencies: None")
    
    # Skip range
    if skip_ranges:
        sample_range = list(skip_ranges.values())[0] if skip_ranges else None
        if sample_range:
            print(f"{prefix}  OLM Skip Range: {sample_range}")
            print(f"{prefix}    (Can upgrade directly within this range)")
    else:
        print(f"{prefix}  OLM Skip Range: Sequential upgrades required")
    
    print()

def main():
    if len(sys.argv) < 3:
        print("Usage: check operators compatibility for OCP <version> <must-gather-path>")
        sys.exit(1)
    
    args = sys.argv[1:]
    target_ocp = None
    must_gather_path = None
    
    for i, arg in enumerate(args):
        if arg.replace('.', '').isdigit() and '.' in arg:
            target_ocp = arg
        elif os.path.exists(arg):
            must_gather_path = arg
    
    if not target_ocp:
        print("❌ Error: OCP version not specified")
        sys.exit(1)
    
    if not must_gather_path:
        print("❌ Error: Must-gather path not specified")
        sys.exit(1)
    
    matrix = load_compatibility_matrix()
    operators = collect_cluster_data(must_gather_path)
    check_compatibility(operators, target_ocp, matrix)

if __name__ == '__main__':
    main()
```

## Output Format

The skill now provides:

### For Operator Families (e.g., ODF)
```
🗄️  OpenShift Data Foundation (ODF) - Storage Suite
Installed Operators (10 components):
  • odf-operator.v4.18.24-rhodf
  • ocs-operator.v4.18.24-rhodf
  ...

To OCP 4.20:
  Status: ⚠️  Upgrade Required
  Current version: 4.18.24-rhodf
  Supported versions: 4.18.25, 4.19.20, 4.20.15
  Recommendation: Upgrade ODF to 4.20.15 before upgrading cluster
```

### For Individual Operators
```
📦 AMQ Broker (RHEL 9)
Operator: amq-broker-rhel9
Current CSV: amq-broker-operator.v7.14.0-opr-1
Current Version: 7.14.0

To OCP 4.20:
  Status: ✅ Compatible
  Supported versions: 7.13.5, 7.14.0
  Dependencies: None
  OLM Skip Range: >=7.13.0 <7.14.0
```

## Data Source

Compatibility data from Red Hat operator catalogs (OCP 4.12-4.22, 194 operators)  
Auto-updated via OPM tool
