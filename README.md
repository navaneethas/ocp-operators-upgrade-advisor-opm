# OpenShift Operator Compatibility Matrix

**Automated operator compatibility checker with dependency validation and upgrade path information**

Built using OPM (Operator Package Manager) data from Red Hat operator catalogs.

---

## 📂 Files in This Directory

```
/Users/nsenthil/AI_TOOL/OPM/
├── json/                                    # Raw OPM data (7GB)
│   ├── ocp-4.12.json
│   ├── ocp-4.13.json
│   ├── ...
│   └── ocp-4.22.json
├── parse-opm-data.py                        # Parser script
├── compatibility_matrix.json                # Generated matrix
├── ocp-operator-compatibility-enhanced.md   # Geminicli skill
└── README.md                                # This file
```

---

## 🚀 Quick Start

### 1. Parse OPM Data (One Time)

```bash
cd /Users/nsenthil/AI_TOOL/OPM
python3 parse-opm-data.py
```

**Output:** `compatibility_matrix.json` with all operator compatibility data

---

### 2. Use in Supportshell (Geminicli)

```bash
# Download the skill and matrix
curl -O https://raw.githubusercontent.com/navaneethas/ocp-operator-upgrade-advisor/main/ocp-operator-compatibility-enhanced.md
curl -O https://raw.githubusercontent.com/navaneethas/ocp-operator-upgrade-advisor/main/compatibility_matrix.json

# Use it
gemini check operators compatibility for OCP 4.22 /path/to/must-gather
```

---

## 📊 What the Matrix Contains

For each operator across OCP 4.12-4.22:

✅ **Available Versions** - All operator versions for each OCP version  
✅ **Max OCP Version** - Maximum supported OCP version (blocks upgrades)  
✅ **Dependencies** - Required dependent operators with version ranges  
✅ **Skip Ranges** - Upgrade path information (which versions can be skipped)  
✅ **Channels** - Available update channels  

---

## 🔄 Collecting Fresh Data

### Collect All OCP Versions

```bash
cd /Users/nsenthil/AI_TOOL/OPM/json

# Get list of OCP versions (4.12+)
VERSIONS=$(curl -s https://mirror.openshift.com/pub/openshift-v4/x86_64/clients/ocp/ | \
  grep -oE 'href="[0-9]+\.[0-9]+\.[0-9]+/"' | \
  sed 's/href="//;s/\///' | \
  cut -d. -f1,2 | \
  sort -u -V | \
  awk -F. '($1 == 4 && $2 >= 12) || $1 >= 5')

# Collect data for each version
for version in $VERSIONS; do
  echo "Querying OCP $version..."
  opm-rhel9 render registry.redhat.io/redhat/redhat-operator-index:v$version -o json > ocp-$version.json
  echo "✅ Done"
done
```

**Time:** ~30 seconds per version

---

### Parse and Update Matrix

```bash
python3 parse-opm-data.py \
  --input-dir /Users/nsenthil/AI_TOOL/OPM/json \
  --output /Users/nsenthil/AI_TOOL/OPM/compatibility_matrix.json
```

---

## 🤖 Automation (Cron Job)

### Weekly Auto-Update

```bash
# Edit crontab
crontab -e

# Add this line (runs every Thursday 2 AM)
0 2 * * 4 cd /path/to/project && ./update-matrix.sh >> /var/log/ocp-matrix.log 2>&1
```

**update-matrix.sh:**
```bash
#!/bin/bash
# Auto-detect new OCP versions and update matrix

# Detect new versions
LATEST=$(curl -s https://mirror.openshift.com/pub/openshift-v4/x86_64/clients/ocp/ | \
  grep -oE 'href="[0-9]+\.[0-9]+\.[0-9]+/"' | \
  sed 's/href="//;s/\///' | \
  cut -d. -f1,2 | \
  sort -u -V | \
  tail -1)

# Check if new version
if grep -q "\"$LATEST\":" compatibility_matrix.json; then
    echo "✅ Up to date (latest: $LATEST)"
    exit 0
fi

echo "🆕 New version detected: $LATEST"

# Collect data
opm-rhel9 render registry.redhat.io/redhat/redhat-operator-index:v$LATEST -o json > json/ocp-$LATEST.json

# Re-parse all
python3 parse-opm-data.py

# Git commit and push
git add compatibility_matrix.json
git commit -m "Auto-update: Add OCP $LATEST"
git push

echo "✅ Matrix updated with OCP $LATEST"
```

---

## 📋 Matrix Format

```json
{
  "operator-name": {
    "4.22": {
      "versions": ["v1.2.3", "v1.2.2", "v1.2.1"],
      "maxOCPVersion": "4.22",
      "dependencies": [
        "multicluster-engine (>=2.0.0)"
      ],
      "skipRanges": {
        "v1.2.3": ">=1.2.0 <1.2.3"
      },
      "channels": ["stable", "fast"]
    }
  }
}
```

---

## 🎯 Key Features

### 1. Dependency Checking
Identifies operators that require other operators:
```
advanced-cluster-management requires:
  • multicluster-engine (>=2.0.0)
```

### 2. Skip Range Information  
Shows which versions can be skipped during upgrades:
```
skipRange: >=2.11.0 <2.13.2
→ Can upgrade directly from any 2.11.x-2.13.1 to 2.13.2
```

### 3. Max OCP Version
Indicates when operators block cluster upgrades:
```
maxOCPVersion: 4.20
→ This operator blocks upgrade to 4.21+
```

---

## 📊 Data Statistics

**Coverage:**
- OCP Versions: 4.12 through 4.22 (11 versions)
- Operators: 150+ Red Hat certified operators
- Total Versions: 3,000+ operator versions
- Dependencies: Tracked for all operators
- Skip Ranges: Available for most operators

**Update Frequency:**
- Manual: On-demand
- Automated: Weekly (Thursday 2 AM)
- Detection: Automatic new version detection

---

## 🔧 Troubleshooting

### Parser Shows 0 Operators

**Issue:** JSON format not recognized

**Fix:** Make sure JSON files are from `opm render` command:
```bash
opm-rhel9 render registry.redhat.io/redhat/redhat-operator-index:v4.22 -o json > ocp-4.22.json
```

### Large File Sizes

**Normal:** OCP version files are 100MB-1.3GB each (total ~7GB)

**Tip:** Only keep versions you need (delete older versions)

### OPM Command Not Found

**Install OPM:**
```bash
curl -LO https://github.com/operator-framework/operator-registry/releases/download/v1.35.0/linux-amd64-opm
chmod +x linux-amd64-opm
sudo mv linux-amd64-opm /usr/local/bin/opm-rhel9
```

---

## 🚀 Next Steps

1. ✅ **Parse the data** - Run `python3 parse-opm-data.py`
2. ✅ **Test the skill** - Use with geminicli in supportshell
3. ✅ **Push to GitHub** - Share with your team
4. ✅ **Set up automation** - Weekly cron job for updates

---

## 📝 Credits

**Tool:** Created by Navaneetha Senthilkumar  
**Data Source:** Red Hat Operator Catalogs (registry.redhat.io)  
**Parser:** Built with Python + OPM data  
**Automation:** GitHub Actions / Cron  
**AI Assist:** Claude (Anthropic)  

---

**Last Updated:** 2026-09-03  
**Matrix Version:** 4.12-4.22  
**Total Operators:** 150+
