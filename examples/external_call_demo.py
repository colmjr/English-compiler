import os  # External module: os
import time  # External module: time

# WARNING: This program uses external calls and is NOT PORTABLE
# Required external modules: os, time

print("=== ExternalCall Demo (Tier 2, Non-Portable) ===")
print("\n1. Getting current Unix timestamp:")
timestamp = time.time()
print("   timestamp:", timestamp)
print("\n2. Getting current working directory:")
cwd = os.getcwd()
print("   cwd:", cwd)
print("\n3. Getting environment variable (USER):")
user = os.getenv("USER")
print("   USER:", user)
print("\nDone!")
