---
name: ocp-operator-compatibility-detailed
description: Detailed OpenShift operator compatibility analysis with max supported versions
---

# OpenShift Operator Compatibility Analyzer (Detailed)

Comprehensive operator compatibility analysis for OCP upgrades.

## Usage

```bash
gemini check operators compatibility for OCP <version> <must-gather-path>
```

**Download matrix first:**
```bash
curl -O https://raw.githubusercontent.com/navaneethas/ocp-operators-upgrade-advisor-opm/main/compatibility_matrix.json
```

## Code

```python
#!/usr/bin/env python3
import json, os, sys, subprocess
from pathlib import Path

def load_matrix():
    if not Path("compatibility_matrix.json").exists():
        print("❌ compatibility_matrix.json not found"); sys.exit(1)
    with open("compatibility_matrix.json") as f:
        return json.load(f)

def get_current_ocp(mg_path):
    """Get current OCP version from must-gather"""
    try:
        cmd = f"omc use {mg_path} && omc get clusterversion version -o json"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            version = data.get('status', {}).get('desired', {}).get('version', 'unknown')
            channel = data.get('spec', {}).get('channel', 'unknown')
            return version, channel
    except:
        pass
    return 'unknown', 'unknown'

def collect_data(mg_path):
    ops = {}
    try:
        cmd = f"omc use {mg_path} && omc get sub -A -o json"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            for item in json.loads(result.stdout).get('items', []):
                name = item['spec'].get('name', '')
                if name:
                    csv = item['status'].get('currentCSV', '')
                    ops[name] = {
                        'csv': csv,
                        'channel': item['spec'].get('channel', 'unknown'),
                        'source': item['spec'].get('source', 'redhat-operators'),
                        'namespace': item['metadata'].get('namespace', ''),
                        'version': csv.rsplit('.', 1)[-1] if '.' in csv else 'unknown'
                    }
    except Exception as e:
        print(f"⚠️  Error: {e}")
    return ops

def get_max_supported_ocp(op_name, current_version, matrix):
    """Find max OCP version that supports the current operator version"""
    if op_name not in matrix:
        return 'N/A'
    
    max_ocp = None
    for ocp_ver in sorted(matrix[op_name].keys(), key=lambda v: [int(x) for x in v.split('.')], reverse=True):
        versions = matrix[op_name][ocp_ver].get('versions', [])
        if any(current_version in v for v in versions):
            max_ocp = ocp_ver
            break
    
    return max_ocp or 'N/A'

def get_compatible_versions(op_name, target_ocp, matrix):
    """Get compatible versions for target OCP"""
    if op_name not in matrix or target_ocp not in matrix[op_name]:
        return []
    
    versions = matrix[op_name][target_ocp].get('versions', [])
    # Extract clean version numbers
    clean_versions = []
    for v in versions[:20]:
        if '.' in v:
            clean_versions.append(v.rsplit('.', 1)[-1])
    return clean_versions

def main():
    if len(sys.argv) < 3:
        print("Usage: check operators compatibility for OCP <version> <must-gather-path>")
        sys.exit(1)
    
    target = next((a for a in sys.argv if '.' in a and a.replace('.','').isdigit()), None)
    mg_path = next((a for a in sys.argv if os.path.exists(a)), None)
    
    if not target or not mg_path:
        print("❌ Missing OCP version or must-gather path"); sys.exit(1)
    
    matrix = load_matrix()
    current_ocp, current_channel = get_current_ocp(mg_path)
    ops = collect_data(mg_path)
    
    # Categorize
    redhat_ops = {n: o for n, o in ops.items() if 'redhat' in o.get('source', '').lower()}
    non_redhat_ops = {n: o for n, o in ops.items() if n not in redhat_ops}
    
    # Calculate summary
    compatible = 0
    upgrade_required = 0
    
    for op_name, op_data in redhat_ops.items():
        if op_name in matrix and target in matrix[op_name]:
            version = op_data.get('version', '')
            if any(version in v for v in matrix[op_name][target].get('versions', [])):
                compatible += 1
            else:
                upgrade_required += 1
        else:
            upgrade_required += 1
    
    # Print report
    print("\n" + "=" * 100)
    print("📊 OpenShift Operator Compatibility Analysis")
    print("=" * 100)
    print()
    
    # Cluster Information
    print("Cluster Information")
    print("-" * 100)
    print(f"Current OCP Version: {current_ocp} (Channel: {current_channel})")
    print(f"Target OCP Version: {target}")
    print(f"Total Subscriptions: {len(ops)}")
    print()
    
    # Executive Summary
    print("Executive Summary")
    print("-" * 100)
    print(f"┌{'─'*30}┬{'─'*7}┬{'─'*60}┐")
    print(f"│ {'Status':<28} │ {'Count':<5} │ {'Description':<58} │")
    print(f"├{'─'*30}┼{'─'*7}┼{'─'*60}┤")
    print(f"│ {'✓ Compatible As-Is':<28} │ {compatible:^5} │ {'Operators compatible with target OCP version':<58} │")
    print(f"│ {'⚠ Upgrade Required':<28} │ {upgrade_required:^5} │ {'Operators requiring upgrade for target OCP':<58} │")
    print(f"│ {'ℹ Non-Red Hat Operators':<28} │ {len(non_redhat_ops):^5} │ {'Third-party certified/community operators':<58} │")
    print(f"└{'─'*30}┴{'─'*7}┴{'─'*60}┘")
    print()
    
    # Detailed Operator Analysis
    print("Detailed Operator Analysis")
    print("-" * 100)
    print()
    
    for op_name, op_data in sorted(redhat_ops.items()):
        csv = op_data.get('csv', 'unknown')
        version = op_data.get('version', 'unknown')
        channel = op_data.get('channel', 'unknown')
        
        # Get compatibility info
        max_ocp = get_max_supported_ocp(op_name, version, matrix)
        compatible_versions = get_compatible_versions(op_name, target, matrix)
        
        # Determine status
        if op_name in matrix and target in matrix[op_name]:
            is_compatible = any(version in v for v in matrix[op_name][target].get('versions', []))
            status = "✓ Compatible As-Is" if is_compatible else "⚠ Upgrade Required"
        else:
            status = "❌ Not Compatible"
            is_compatible = False
        
        # Print operator details
        print(f"{'='*100}")
        print(f"📦 {op_name}")
        print(f"{'='*100}")
        print()
        print(f"Current Installed Version: {version} (CSV: {csv})")
        print(f"Current Channel: {channel}")
        print(f"Status: {status}")
        print(f"Max Supported OCP for Current Version: {max_ocp}")
        
        if compatible_versions:
            # Show first 5 versions
            version_list = ', '.join(compatible_versions[:5])
            if len(compatible_versions) > 5:
                version_list += f" (... {len(compatible_versions)} total)"
            print(f"Compatible Versions in OCP {target}: {version_list}")
            
            if not is_compatible:
                recommended = compatible_versions[0] if compatible_versions else 'N/A'
                print(f"Recommendation: Upgrade to {recommended} (Recommended)")
            else:
                print(f"Recommendation: No upgrade required")
        else:
            print(f"Compatible Versions in OCP {target}: None")
            print(f"Recommendation: This operator is not supported in OCP {target}")
        
        print()
    
    # Non-Red Hat operators
    if non_redhat_ops:
        print("=" * 100)
        print("⚠️  Non-Red Hat Operators (Not Tracked)")
        print("=" * 100)
        print()
        print("These operators are not tracked in Red Hat compatibility matrices.")
        print("Please verify compatibility with vendors before upgrading.")
        print()
        
        for op_name, op_data in non_redhat_ops.items():
            csv = op_data.get('csv', 'unknown')
            version = op_data.get('version', 'unknown')
            channel = op_data.get('channel', 'unknown')
            source = op_data.get('source', 'unknown')
            
            print(f"• {op_name}")
            print(f"  CSV: {csv}")
            print(f"  Version: {version}")
            print(f"  Channel: {channel}")
            print(f"  Source: {source}")
            print(f"  Recommendation: Use oc-mirror with the respective catalog to check compatibility with OCP {target}.")
            print(f"                  To know how to use oc-mirror, please refer to: https://access.redhat.com/solutions/6994677")
            print()
    
    print("=" * 100)
    print("📋 For more information: https://access.redhat.com/labs/ocpouic/")
    print()

if __name__ == '__main__':
    main()
```

## Output Features

✅ **Cluster Information** - Current/Target OCP, Total subs  
✅ **Executive Summary Table** - Counts by status  
✅ **Per-Operator Details:**
  - Current Installed Version (CSV)
  - Current Channel
  - Status (Compatible/Upgrade Required)
  - **Max Supported OCP for Current Version**
  - Compatible Versions in target OCP
  - Specific Recommendation

## Data Source

Red Hat operator catalogs (OCP 4.12-4.22, 194 operators)
