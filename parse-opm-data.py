#!/usr/bin/env python3
"""
OPM Data Parser
Parses OPM JSON output to build operator compatibility matrix

Extracts:
- Operator names and versions
- maxOCPVersion (compatibility info)
- Package dependencies
- Skip ranges (upgrade paths)
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

class OPMParser:
    def __init__(self, json_dir):
        self.json_dir = Path(json_dir)
        self.matrix = defaultdict(lambda: defaultdict(dict))

    def parse_file(self, filepath, ocp_version):
        """Parse a single OPM JSON file"""
        print(f"📊 Parsing {filepath.name} (OCP {ocp_version})...")

        packages = {}
        bundles = defaultdict(list)
        channels = defaultdict(lambda: defaultdict(list))

        # Read line by line and accumulate JSON objects
        objects = []
        current_lines = []
        brace_count = 0

        with open(filepath, 'r') as f:
            for line in f:
                current_lines.append(line)

                # Count braces
                brace_count += line.count('{') - line.count('}')

                # When brace_count returns to 0, we have a complete object
                if brace_count == 0 and current_lines:
                    json_str = ''.join(current_lines)
                    try:
                        obj = json.loads(json_str)
                        objects.append(obj)
                        if len(objects) % 1000 == 0:
                            print(f"   Processed {len(objects)} objects...")
                    except json.JSONDecodeError:
                        pass
                    current_lines = []

        print(f"   Total objects: {len(objects)}")

        # Process objects
        for obj in objects:
            try:
                schema = obj.get('schema', '')

                # Parse packages
                if schema == 'olm.package':
                    pkg_name = obj.get('name')
                    packages[pkg_name] = {
                        'defaultChannel': obj.get('defaultChannel'),
                        'icon': obj.get('icon', {}).get('base64data', '')[:50] if obj.get('icon') else ''
                    }

                # Parse channels
                elif schema == 'olm.channel':
                    pkg_name = obj.get('package')
                    channel_name = obj.get('name')
                    entries = obj.get('entries', [])

                    for entry in entries:
                        version = entry.get('name', '')
                        channels[pkg_name][channel_name].append({
                            'version': version,
                            'skipRange': entry.get('skipRange'),
                            'skips': entry.get('skips', []),
                            'replaces': entry.get('replaces')
                        })

                # Parse bundles (most important!)
                elif schema == 'olm.bundle':
                    bundle_name = obj.get('name')
                    pkg_name = obj.get('package')

                    # Extract properties
                    properties = obj.get('properties', [])

                    bundle_info = {
                        'name': bundle_name,
                        'image': obj.get('image', ''),
                        'maxOCPVersion': None,
                        'dependencies': [],
                        'skipRange': None
                    }

                    for prop in properties:
                        prop_type = prop.get('type')

                        # Max OCP version
                        if prop_type == 'olm.maxOpenShiftVersion':
                            bundle_info['maxOCPVersion'] = prop.get('value')

                        # Package dependencies
                        elif prop_type == 'olm.package.required':
                            dep_value = prop.get('value', {})
                            bundle_info['dependencies'].append({
                                'operator': dep_value.get('packageName'),
                                'versionRange': dep_value.get('versionRange')
                            })

                    bundles[pkg_name].append(bundle_info)

            except Exception as e:
                # Skip objects that cause errors
                continue

        print(f"   ✅ Found {len(packages)} operators, {len(bundles)} bundle sets")

        # Build matrix for this OCP version
        for pkg_name in packages:
            if pkg_name not in bundles:
                continue

            # Get all versions
            versions = [b['name'] for b in bundles[pkg_name]]

            # Get dependencies (from any bundle, usually consistent)
            dependencies = []
            if bundles[pkg_name]:
                # Get unique dependencies
                dep_set = set()
                for bundle in bundles[pkg_name]:
                    for dep in bundle['dependencies']:
                        dep_str = f"{dep['operator']} ({dep['versionRange']})"
                        dep_set.add(dep_str)
                dependencies = sorted(list(dep_set))

            # Get skip ranges from channels
            skip_ranges = {}
            for channel_name, channel_data in channels[pkg_name].items():
                for entry in channel_data:
                    if entry['skipRange']:
                        skip_ranges[entry['version']] = entry['skipRange']

            # Get max OCP version
            max_ocp = None
            for bundle in bundles[pkg_name]:
                if bundle['maxOCPVersion']:
                    max_ocp = bundle['maxOCPVersion']
                    break

            self.matrix[pkg_name][ocp_version] = {
                'versions': versions,
                'maxOCPVersion': max_ocp,
                'dependencies': dependencies,
                'skipRanges': skip_ranges,
                'channels': list(channels[pkg_name].keys())
            }

        return len(packages)

    def parse_all(self):
        """Parse all OCP version files"""
        print("=" * 60)
        print("OPM Data Parser - Building Compatibility Matrix")
        print("=" * 60)
        print()

        # Find all JSON files
        json_files = sorted(self.json_dir.glob('ocp-*.json'))

        if not json_files:
            print(f"❌ No OCP JSON files found in {self.json_dir}")
            return False

        print(f"Found {len(json_files)} OCP version files")
        print()

        for filepath in json_files:
            # Extract OCP version from filename: ocp-4.12.json -> 4.12
            ocp_version = filepath.stem.replace('ocp-', '')

            self.parse_file(filepath, ocp_version)
            print()

        print("=" * 60)
        print(f"✅ Parsing complete!")
        print(f"   Total operators: {len(self.matrix)}")
        print(f"   OCP versions: {len(json_files)}")
        print("=" * 60)

        return True

    def save_matrix(self, output_file):
        """Save compatibility matrix to JSON file"""
        print(f"\n💾 Saving matrix to {output_file}...")

        # Convert defaultdict to regular dict for JSON serialization
        regular_dict = {}
        for operator, versions in self.matrix.items():
            regular_dict[operator] = dict(versions)

        with open(output_file, 'w') as f:
            json.dump(regular_dict, f, indent=2)

        print(f"✅ Matrix saved!")

        # Print statistics
        print(f"\n📊 Statistics:")
        print(f"   Total operators: {len(regular_dict)}")

        # Count operators with dependencies
        with_deps = sum(1 for op_data in regular_dict.values()
                       for ver_data in op_data.values()
                       if ver_data.get('dependencies'))
        print(f"   Operators with dependencies: {with_deps}")

        # Count operators with skip ranges
        with_skip = sum(1 for op_data in regular_dict.values()
                       for ver_data in op_data.values()
                       if ver_data.get('skipRanges'))
        print(f"   Operators with skip ranges: {with_skip}")

        # Sample operators
        print(f"\n📝 Sample operators:")
        for i, (op_name, op_data) in enumerate(list(regular_dict.items())[:5]):
            ocp_versions = list(op_data.keys())
            print(f"   {i+1}. {op_name}")
            print(f"      OCP versions: {', '.join(sorted(ocp_versions))}")

            # Show dependencies if any
            for ver, data in op_data.items():
                if data.get('dependencies'):
                    print(f"      Dependencies: {', '.join(data['dependencies'])}")
                    break


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Parse OPM JSON files to build compatibility matrix')
    parser.add_argument('--input-dir', default='/Users/nsenthil/AI_TOOL/OPM/json',
                       help='Directory containing OCP JSON files')
    parser.add_argument('--output', default='/Users/nsenthil/AI_TOOL/OPM/compatibility_matrix.json',
                       help='Output matrix file')

    args = parser.parse_args()

    # Parse OPM data
    parser_obj = OPMParser(args.input_dir)

    if not parser_obj.parse_all():
        sys.exit(1)

    # Save matrix
    parser_obj.save_matrix(args.output)

    print("\n🎉 Success! Compatibility matrix ready!")
    print(f"   File: {args.output}")
    print(f"\n📋 Next steps:")
    print(f"   1. Review the matrix file")
    print(f"   2. Use it with your geminicli skill")
    print(f"   3. Push to GitHub for team access")


if __name__ == '__main__':
    main()
