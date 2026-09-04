# OpenShift Operator Compatibility Advisor

**Automated operator compatibility checker for OpenShift cluster upgrades**

---

## 🎯 Why This Matters

Before upgrading a cluster from one version to another:

- Manually checking operator compatibility takes time
- Red Hat's OCPOUIC tool requires manual web lookups

---

## 📊 What It Does

**For proactive cases**, we currently tell customers: *"Please make sure that all the installed operators are compatible with the target version. Please refer to https://access.redhat.com/labs/ocpouic/ to check the compatibility."* This is generic advice that we give to the customer.

**The solution:** This tool analyzes the cluster's must-gather data and tells you exactly which operators are ready for an upgrade and which ones need to be updated.

**Now for proactive cases**, instead of sending a generic link, you can provide a detailed, personalized analysis: *"I've analyzed the operators installed in your cluster. Here are the 5 operators that need upgrades, with specific version recommendations and channel changes."*

### Key Features:
- ✅ Checks compatibility of all installed operators against target OCP version
- ✅ Identifies which operators need upgrades
- ✅ Shows maximum supported OCP version for each current operator version
- ✅ Provides specific upgrade recommendations with version numbers
- ✅ Auto-updates daily with latest operator catalog data

---

## 🚀 How to Use (Supportshell - Geminicli)

### ⚠️ IMPORTANT NOTES:

- 📅 **Download `compatibility_matrix.json` fresh daily** - It's auto-updated every night with the latest operator data from Red Hat
- 📂 **Download files in the same directory as your must-gather** OR provide the complete path to the must-gather

---

### 📥 Method 1: Download Files in Must-Gather Directory

```bash
# Navigate to your must-gather directory
cd /home/remote/USERNAME/12345678/must-gather.local.1234567890

# Download the files
curl -O \
  https://raw.githubusercontent.com/navaneethas/ocp-operators-upgrade-advisor-opm/main/ocp-operator-compatibility-detailed.md

curl -O \
  https://raw.githubusercontent.com/navaneethas/ocp-operators-upgrade-advisor-opm/main/compatibility_matrix.json

# Run analysis (files are in same directory)
gemini check operators compatibility for OCP <target_version> .
```

---

### 📥 Method 2: Download Files Elsewhere & Use Full Path

```bash
# Download files to your working directory (do this daily for fresh data)
cd /home/remote/USERNAME

curl -O \
  https://raw.githubusercontent.com/navaneethas/ocp-operators-upgrade-advisor-opm/main/ocp-operator-compatibility-detailed.md

curl -O \
  https://raw.githubusercontent.com/navaneethas/ocp-operators-upgrade-advisor-opm/main/compatibility_matrix.json

# Run analysis with full path to must-gather
gemini check operators compatibility for OCP <target_version> \
  /home/remote/USERNAME/12345678/must-gather.local.1234567890
```

---

### 📊 Example Output

https://gss--c.vf.force.com/apex/Case_View?id=500Hn00001sNhzX&sfdc.override=1#comment_a0aHn00000aYf37IAC

---

### ⚠️ NOTES:

📋 **Output format may vary** - The analysis content remains consistent, but formatting may differ.

---

## 🤖 Automation Details

**Data Collection:**

- Runs daily at 2 AM on internal RHEL server
- Queries Red Hat operator catalogs via OPM
- Automatically detects new OCP versions (including OCP 5.0 when GA)
- Pushes updated data to GitHub automatically

**No manual maintenance required!**

---

## 🙏 Feedback Welcome

This is the first version - I'd love to hear your thoughts and suggestions!

**📝 Share your feedback:** https://docs.google.com/forms/d/e/1FAIpQLSdPpmM164p9J7kSkFB9ph7V5dBgw4McyhwCjPwMJGCLYKYH9g/viewform

Whether you've found it helpful, encountered issues, or have ideas for improvements - all feedback is appreciated!

**Questions or need help?** Feel free to reach out directly.
