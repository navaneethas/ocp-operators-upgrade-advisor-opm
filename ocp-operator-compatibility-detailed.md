---
name: ocp-operator-compatibility-detailed
description: Detailed OpenShift operator compatibility analysis with max supported versions
---

# OpenShift Operator Compatibility Analyzer (Detailed)

Comprehensive operator compatibility analysis for OCP upgrades.

## Usage

**Mode 1: Must-gather analysis**
```bash
gemini check operators compatibility for OCP <version> <must-gather-path>
```

**Mode 2: Single operator lookup (for customer queries)**
```bash
gemini check operator <name> version <version> for OCP <version>
```

**Examples:**
```bash
# Must-gather analysis
gemini check operators compatibility for OCP 4.22 /path/to/must-gather

# Single operator queries
gemini check operator amq-broker version 7.12.7 for OCP 4.21
gemini check operator tempo-product version 0.22.0-1 for OCP 4.22
gemini check operator amq-streams version 3.2.1-11 for OCP 4.21 4.22
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

def check_single_operator(matrix, args):
    """Check single operator compatibility - for customer queries"""
    import re
    
    # Parse: operator <name> version <version> for OCP <version>
    args_str = ' '.join(args)
    op_match = re.search(r'operator\s+([a-zA-Z0-9\-_]+)', args_str, re.I)
    ver_match = re.search(r'version\s+([a-zA-Z0-9\.\-_]+)', args_str, re.I)
    ocp_matches = re.findall(r'(\d+\.\d+)', args_str)
    
    if not op_match or not ver_match:
        print("Usage: check operator <name> version <version> for OCP <version>")
        return
    
    op_query = op_match.group(1).lower()
    current_ver = ver_match.group(1)
    targets = ocp_matches if ocp_matches else ['4.22']
    
    # Find operator (partial match)
    matches = [k for k in matrix.keys() if op_query.replace('-','') in k.lower().replace('-','')]
    
    if not matches:
        print(f"❌ '{op_query}' not found. Try: amq-broker, tempo-product, amq-streams, etc.")
        return
    
    op_name = matches[0]
    if len(matches) > 1:
        print(f"Multiple matches, using: {op_name}\n")
    
    print(f"Operator: {op_name} | Current: {current_ver}\n")
    
    for target in targets:
        if target not in matrix[op_name]:
            print(f"OCP {target}: ❌ Not available")
            continue
        
        versions = matrix[op_name][target].get('versions', [])
        is_compat = any(current_ver in v for v in versions)
        
        if is_compat:
            print(f"OCP {target}: ✅ SUPPORTED")
        else:
            clean = [v.rsplit('.v',1)[-1] if '.v' in v else v.rsplit('.',1)[-1] for v in versions[:15]]
            print(f"OCP {target}: ❌ NOT SUPPORTED")
            print(f"  Available: {clean[0]} (latest) ← {clean[-1]} (oldest)")
            print(f"  Versions: {', '.join(clean[:8])}")
            print(f"  Recommendation: Upgrade to {clean[0]}")
        print()

def main():
    args = sys.argv[1:]
    
    # Detect mode: single operator lookup vs must-gather analysis
    if 'operator' in ' '.join(args).lower() and 'version' in ' '.join(args).lower():
        # Single operator mode
        matrix = load_matrix()
        check_single_operator(matrix, args)
        return
    
    # Must-gather mode
    if len(args) < 3:
        print("Usage:")
        print("  Must-gather: check operators compatibility for OCP <version> <must-gather-path>")
        print("  Single op:   check operator <name> version <version> for OCP <version>")
        sys.exit(1)
    
    target = next((a for a in args if '.' in a and a.replace('.','').isdigit()), None)
    mg_path = next((a for a in args if os.path.exists(a)), None)
    
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
    
    # Print compact report
    print(f"\n=== OCP Upgrade Analysis: {current_ocp} → {target} ===")
    print(f"Subscriptions: {len(ops)} | Compatible: {compatible} | Upgrade Needed: {upgrade_required} | Non-RH: {len(non_redhat_ops)}\n")
    
    for op_name, op_data in sorted(redhat_ops.items()):
        version = op_data.get('version', 'unknown')
        channel = op_data.get('channel', 'unknown')
        
        max_ocp = get_max_supported_ocp(op_name, version, matrix)
        compatible_versions = get_compatible_versions(op_name, target, matrix)
        
        if op_name in matrix and target in matrix[op_name]:
            is_compatible = any(version in v for v in matrix[op_name][target].get('versions', []))
            status = "✓" if is_compatible else "⚠"
        else:
            status = "❌"
            is_compatible = False
        
        print(f"{status} {op_name} | v{version} (ch:{channel}) | MaxOCP:{max_ocp}")
        
        if compatible_versions and not is_compatible:
            min_v = compatible_versions[-1]
            max_v = compatible_versions[0]
            print(f"  → Upgrade needed: {min_v} to {max_v} ({len(compatible_versions)} versions) | Latest: {max_v}")
        elif compatible_versions:
            print(f"  → OK (compatible)")
        else:
            print(f"  → Not supported in OCP {target}")
    
    # Non-Red Hat operators
    if non_redhat_ops:
        print(f"\n⚠ Non-RH Operators ({len(non_redhat_ops)}): Use oc-mirror to verify - https://access.redhat.com/solutions/6994677")
        for op_name, op_data in non_redhat_ops.items():
            print(f"  • {op_name} v{op_data.get('version', '?')} (ch:{op_data.get('channel', '?')})")
    
    print(f"\nℹ More info: https://access.redhat.com/labs/ocpouic/")
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
