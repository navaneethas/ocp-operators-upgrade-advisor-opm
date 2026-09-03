---
name: ocp-operator-compatibility-enhanced
description: Check OpenShift operator compatibility with detailed version analysis
---

# OpenShift Operator Compatibility Checker

Check operator compatibility for OCP upgrades with detailed version information.

## Usage

```bash
gemini check operators compatibility for OCP <version> <must-gather-path>
```

**Example:**
```bash
gemini check operators compatibility for OCP 4.20 /cases/12345678/must-gather
```

**Download files first:**
```bash
curl -O https://raw.githubusercontent.com/navaneethas/ocp-operators-upgrade-advisor-opm/main/compatibility_matrix.json
```

## Code

```python
#!/usr/bin/env python3
import json, os, sys, subprocess
from pathlib import Path
from collections import defaultdict

FAMILIES = {
    'odf': ['odf-operator', 'ocs-operator', 'rook-ceph-operator', 'mcg-operator', 
            'cephcsi-operator', 'odf-csi-addons-operator', 'odf-prometheus-operator',
            'odf-dependencies', 'ocs-client-operator', 'recipe'],
    'logging': ['cluster-logging', 'loki-operator'],
}

NAMES = {
    'amq-broker-rhel9': 'AMQ Broker',
    'cluster-logging': 'Cluster Logging',
    'loki-operator': 'Loki Operator',
    'cincinnati-operator': 'Update Service',
    'opentelemetry-product': 'OpenTelemetry',
    'cluster-observability-operator': 'Observability',
    'openshift-custom-metrics-autoscaler-operator': 'Custom Metrics',
    'kubernetes-nmstate-operator': 'NMState',
}

def load_matrix():
    if not Path("compatibility_matrix.json").exists():
        print("❌ compatibility_matrix.json not found")
        sys.exit(1)
    with open("compatibility_matrix.json") as f:
        return json.load(f)

def collect_data(mg_path):
    print(f"📂 Collecting from: {mg_path}\n")
    ops = {}
    try:
        cmd = f"omc use {mg_path} && omc get sub -A -o json"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            for item in json.loads(result.stdout).get('items', []):
                name = item['spec'].get('name', '')
                if name:
                    ops[name] = {
                        'csv': item['status'].get('currentCSV', ''),
                        'channel': item['spec'].get('channel', ''),
                        'source': item['spec'].get('source', 'redhat-operators'),
                        'version': item['status'].get('currentCSV', '').rsplit('.', 1)[-1] if '.' in item['status'].get('currentCSV', '') else ''
                    }
    except Exception as e:
        print(f"⚠️  Error: {e}")
    
    print(f"✅ Found {len(ops)} operators\n")
    return ops

def show_family(name, ops, target, matrix):
    print("=" * 100)
    print(f"🗄️  {name.upper()}")
    print("=" * 100)
    csvs = [o.get('csv', '') for n, o in ops if o.get('csv')]
    print(f"\nInstalled ({len(ops)} operators):")
    for csv in csvs[:10]:
        print(f"  • {csv}")
    if len(csvs) > 10:
        print(f"  ... and {len(csvs)-10} more")
    
    if ops:
        op_name, op_data = ops[0]
        version = op_data.get('version', '')
        if op_name in matrix and target in matrix[op_name]:
            avail = [v.rsplit('.', 1)[-1] for v in matrix[op_name][target].get('versions', [])[:10] if '.' in v]
            compat = any(version in v for v in matrix[op_name][target].get('versions', []))
            
            print(f"\nTo OCP {target}:")
            if compat:
                print(f"  Status: ✅ Compatible")
            else:
                print(f"  Status: ⚠️  Upgrade Required")
                print(f"  Current: {version}")
                print(f"  Supported: {', '.join(avail[:5])}")
                if avail:
                    print(f"  Recommendation: Upgrade to {avail[0]}")
        print()

def show_operator(op_name, op_data, target, matrix):
    name = NAMES.get(op_name, op_name)
    print("=" * 100)
    print(f"📦 {name}")
    print("=" * 100)
    print(f"\nOperator: {op_name}")
    print(f"CSV: {op_data.get('csv', 'unknown')}")
    print(f"Version: {op_data.get('version', 'unknown')}")
    
    if op_name not in matrix:
        print(f"\nTo OCP {target}: ⚠️  Not in matrix\n")
        return
    
    if target not in matrix[op_name]:
        print(f"\nTo OCP {target}: ❌ Incompatible\n")
        return
    
    data = matrix[op_name][target]
    avail = [v.rsplit('.', 1)[-1] for v in data.get('versions', [])[:10] if '.' in v]
    version = op_data.get('version', '')
    compat = any(version in v for v in data.get('versions', []))
    
    print(f"\nTo OCP {target}:")
    print(f"  Status: {'✅ Compatible' if compat else '⚠️  Upgrade Required'}")
    print(f"  Supported: {', '.join(avail[:5])}")
    
    deps = data.get('dependencies', [])
    print(f"  Dependencies: {', '.join(deps) if deps else 'None'}")
    
    skips = data.get('skipRanges', {})
    if skips:
        print(f"  Skip Range: {list(skips.values())[0]}")
    print()

def main():
    if len(sys.argv) < 3:
        print("Usage: check operators compatibility for OCP <version> <must-gather-path>")
        sys.exit(1)
    
    target = next((a for a in sys.argv if '.' in a and a.replace('.','').isdigit()), None)
    mg_path = next((a for a in sys.argv if os.path.exists(a)), None)
    
    if not target or not mg_path:
        print("❌ Missing OCP version or must-gather path")
        sys.exit(1)
    
    matrix = load_matrix()
    ops = collect_data(mg_path)
    
    # Categorize
    redhat = {n: o for n, o in ops.items() if 'redhat' in o.get('source', '').lower()}
    non_redhat = {n: o for n, o in ops.items() if n not in redhat}
    
    # Group families
    families = defaultdict(list)
    standalone = []
    
    for n, o in redhat.items():
        fam = next((f for f, members in FAMILIES.items() if n in members), None)
        if fam:
            families[fam].append((n, o))
        else:
            standalone.append((n, o))
    
    print("=" * 100)
    print(f"📊 Operator Compatibility Analysis for OCP {target}")
    print("=" * 100)
    print()
    
    # Show families
    if 'odf' in families:
        show_family('OpenShift Data Foundation', families['odf'], target, matrix)
    
    if 'logging' in families:
        show_family('Logging Stack', families['logging'], target, matrix)
    
    # Standalone operators
    for op_name, op_data in standalone:
        show_operator(op_name, op_data, target, matrix)
    
    # Non-Red Hat
    if non_redhat:
        print("\n" + "=" * 100)
        print("⚠️  Certified/Community Operators (Not Tracked)")
        print("=" * 100)
        print("\nVerify with vendors before upgrading:\n")
        for n, o in non_redhat.items():
            print(f"  • {n} ({o.get('csv', 'unknown')})")
        print()
    
    print("=" * 100)
    print("📋 More info: https://access.redhat.com/labs/ocpouic/")

if __name__ == '__main__':
    main()
```

## Features

✅ Detailed operator analysis  
✅ Operator family grouping (ODF, Logging)  
✅ Available versions display  
✅ Dependencies and skip ranges  
✅ Upgrade recommendations  
✅ Non-Red Hat operator detection  

## Data Source

Red Hat operator catalogs (OCP 4.12-4.22, 194 operators)
