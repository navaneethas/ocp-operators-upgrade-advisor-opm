#!/bin/bash
#
# OpenShift Operator Compatibility Matrix Auto-Updater
# Checks for new OCP versions and updates the compatibility matrix
#
# Usage:
#   1. Make executable: chmod +x auto-update-matrix.sh
#   2. Add to crontab: crontab -e
#   3. Add line: 0 2 * * * /Users/nsenthil/AI_TOOL/OPM/auto-update-matrix.sh >> /tmp/ocp-matrix-update.log 2>&1
#

set -e  # Exit on error

# Configuration
# On RHEL server: WORK_DIR="/root/ADVISOR"
WORK_DIR="/root/ADVISOR"
JSON_DIR="$WORK_DIR/json"
MATRIX_FILE="$WORK_DIR/compatibility_matrix.json"
PARSER_SCRIPT="$WORK_DIR/parse-opm-data.py"
GIT_REPO="$WORK_DIR"

# Refresh strategy:
# "all" = Refresh all OCP versions (thorough but takes ~5 minutes)
# "recent" = Only refresh last 5 versions (faster, ~2 minutes)
REFRESH_STRATEGY="all"  # Refresh all versions daily

# Date stamp for logs
echo "============================================================"
echo "OCP Operator Matrix Auto-Update"
echo "Started: $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================================"
echo

cd "$WORK_DIR" || exit 1

# Step 1: Get list of available OCP versions (4.12+)
echo "📡 Checking for OCP versions..."
AVAILABLE_VERSIONS=$(curl -s https://mirror.openshift.com/pub/openshift-v4/x86_64/clients/ocp/ | \
  grep -oE 'href="[0-9]+\.[0-9]+(\.[0-9]+)?/"' | \
  sed 's/href="//;s/\///' | \
  cut -d. -f1,2 | \
  sort -u -V | \
  awk -F. '($1 == 4 && $2 >= 12) || $1 >= 5')

echo "Available OCP versions: $(echo $AVAILABLE_VERSIONS | tr '\n' ' ')"
echo

# Step 2: Check which versions are already collected
EXISTING_VERSIONS=$(ls -1 "$JSON_DIR"/ocp-*.json 2>/dev/null | sed 's/.*ocp-//;s/.json//' | sort -V)

echo "Existing versions in JSON dir: $(echo $EXISTING_VERSIONS | tr '\n' ' ')"
echo

# Step 3: Determine which versions to refresh
# Operators are updated daily even without new OCP releases
if [ "$REFRESH_STRATEGY" = "all" ]; then
    echo "Refresh strategy: ALL versions"
    VERSIONS_TO_REFRESH="$AVAILABLE_VERSIONS"
else
    echo "Refresh strategy: RECENT versions only (last 5)"
    VERSIONS_TO_REFRESH=$(echo "$AVAILABLE_VERSIONS" | tail -5)
fi

# Find truly new versions for logging
NEW_VERSIONS=""
for version in $AVAILABLE_VERSIONS; do
    if ! echo "$EXISTING_VERSIONS" | grep -q "^${version}$"; then
        NEW_VERSIONS="$NEW_VERSIONS $version"
    fi
done

if [ -n "$NEW_VERSIONS" ]; then
    echo "🆕 New OCP versions detected: $NEW_VERSIONS"
fi

echo "🔄 Refreshing operator data for all versions (operators update daily)"
echo "Versions to refresh: $(echo $VERSIONS_TO_REFRESH | tr '\n' ' ')"
echo

# Step 4: Collect OPM data for all versions
for version in $VERSIONS_TO_REFRESH; do
    echo "============================================================"
    echo "📥 Collecting OPM data for OCP $version"
    echo "============================================================"

    OUTPUT_FILE="$JSON_DIR/ocp-${version}.json"

    # Check if OPM command exists
    if ! command -v opm-rhel9 &> /dev/null; then
        echo "❌ Error: opm-rhel9 command not found"
        echo "Install from: https://github.com/operator-framework/operator-registry/releases"
        exit 1
    fi

    # Run OPM render
    echo "Running: opm-rhel9 render registry.redhat.io/redhat/redhat-operator-index:v${version}"
    if opm-rhel9 render "registry.redhat.io/redhat/redhat-operator-index:v${version}" -o json > "$OUTPUT_FILE" 2>&1; then
        FILE_SIZE=$(du -h "$OUTPUT_FILE" | cut -f1)
        echo "✅ Data collected successfully ($FILE_SIZE)"
    else
        echo "⚠️  Failed to collect data for OCP $version (might not exist yet)"
        rm -f "$OUTPUT_FILE"
        continue
    fi

    echo
done

# Step 5: Re-parse all data to update matrix
echo "============================================================"
echo "🔄 Updating compatibility matrix"
echo "============================================================"

if [ ! -f "$PARSER_SCRIPT" ]; then
    echo "❌ Error: Parser script not found at $PARSER_SCRIPT"
    exit 1
fi

python3 "$PARSER_SCRIPT" --input-dir "$JSON_DIR" --output "$MATRIX_FILE"

if [ $? -eq 0 ]; then
    echo "✅ Matrix updated successfully"
else
    echo "❌ Error: Failed to update matrix"
    exit 1
fi

echo

# Step 6: Git commit and push
echo "============================================================"
echo "📤 Committing and pushing to GitHub"
echo "============================================================"

cd "$GIT_REPO"

# Check if there are changes
if ! git diff --quiet "$MATRIX_FILE" 2>/dev/null; then

    # Add only the matrix file (NOT the huge JSON files - they're 7GB!)
    git add "$MATRIX_FILE"

    # Create commit message
    if [ -n "$NEW_VERSIONS" ]; then
        COMMIT_MSG="Auto-update: Add OCP version(s)${NEW_VERSIONS}

Automatically collected OPM data and updated compatibility matrix.

Date: $(date '+%Y-%m-%d %H:%M:%S')
New OCP versions: ${NEW_VERSIONS}

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
    else
        COMMIT_MSG="Auto-update: Refresh operator catalog data

Updated compatibility matrix with latest operator versions.
(Operators are updated daily even without new OCP releases)

Date: $(date '+%Y-%m-%d %H:%M:%S')

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
    fi

    # Commit
    if git commit -m "$COMMIT_MSG"; then
        echo "✅ Changes committed"
    else
        echo "⚠️  Commit failed"
        exit 1
    fi

    # Push to remote
    if git push origin main; then
        echo "✅ Changes pushed to GitHub"
    else
        echo "⚠️  Push failed - manual intervention required"
        exit 1
    fi

else
    echo "ℹ️  No changes to commit"
fi

echo
echo "============================================================"
echo "✅ Auto-update completed successfully!"
echo "Completed: $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================================"
