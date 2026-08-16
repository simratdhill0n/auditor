#!/usr/bin/env python3
"""
Step-by-step verification of deployment
"""

import os
import sys

print("=" * 80)
print("🔍 DEPLOYMENT VERIFICATION CHECKLIST")
print("=" * 80)

# Step 1: Check if ai_agent.py has the fix
print("\n✅ STEP 1: Check if ai_agent.py has metadata validation")
print("-" * 80)

backend_path = os.path.abspath("services/ai_agent.py")
print(f"Checking: {backend_path}")

if os.path.exists(backend_path):
    with open(backend_path, 'r') as f:
        content = f.read()
        
    if "FINAL QUALITY CHECK" in content:
        print("✅ Found 'FINAL QUALITY CHECK' - Fix is installed!")
    else:
        print("❌ NOT FOUND - File not updated!")
        print("   Action: Copy ai_agent.py from outputs folder to services/")
        sys.exit(1)
        
    if "DATA IS METADATA" in content:
        print("✅ Found metadata rejection - Fix is installed!")
    else:
        print("❌ NOT FOUND - Old version still deployed!")
        sys.exit(1)
else:
    print(f"❌ File not found at {backend_path}")
    sys.exit(1)

# Step 2: Check if Lambda code would have been deployed
print("\n✅ STEP 2: Check SAM configuration")
print("-" * 80)

if os.path.exists("template.yaml") or os.path.exists("template.yml"):
    print("✅ Found SAM template")
else:
    print("⚠️  No SAM template found")

if os.path.exists(".aws-sam"):
    print("✅ AWS SAM build cache found - means deployment happened before")
else:
    print("⚠️  No SAM build cache")

# Step 3: Deployment instructions
print("\n✅ STEP 3: CORRECT DEPLOYMENT SEQUENCE")
print("-" * 80)

instructions = """
1. Download ai_agent.py from outputs folder to your computer

2. Copy to backend:
   cd E:\\programming\\auditor\\auditor\\backend
   cp .\\.\\ai_agent.py services\\ai_agent.py
   
   (Verify file was copied:)
   ls services\\ai_agent.py

3. Build SAM:
   sam build

4. Deploy to AWS:
   sam deploy --stack-name auditor-backend --region us-east-1 \\
     --parameter-overrides API_KEY = os.getenv("OPENROUTER_API_KEY")" \\
     --capabilities CAPABILITY_IAM --resolve-s3

   Wait for: "Successfully created/updated stack - auditor-backend"

5. Wait 10-15 seconds for Lambda to be ready

6. Test:
   python ..\test_metadata_detection.py
"""

print(instructions)

print("\n" + "=" * 80)
print("📝 CHECKLIST")
print("=" * 80)
print("""
Before testing, verify:

☐ Downloaded ai_agent.py from outputs
☐ Copied to services/ai_agent.py
☐ Ran 'sam build' 
☐ Ran 'sam deploy' (full command with parameters)
☐ Saw "Successfully created/updated stack" message
☐ Waited 15 seconds for Lambda to update
☐ Running test script AFTER all above

If you did all these and still getting metadata → 
CKAN datasets might be archived/outdated.
""")

print("\n" + "=" * 80)
print("✅ VERIFICATION COMPLETE")
print("=" * 80)
print("\nFile has the fix installed.")
print("Now follow the deployment steps above and retest.")
