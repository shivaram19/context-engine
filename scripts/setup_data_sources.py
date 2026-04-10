#!/usr/bin/env python3
"""
Setup your data sources — configure which Google Drive folders and GitHub repos to index.

This creates a config.json that tells the system what to fetch.
"""

import json
import os
import sys
from pathlib import Path


CONFIG_FILE = Path(__file__).parent.parent / "config.data_sources.json"


def main():
    """Interactive setup wizard."""

    print("\n" + "="*70)
    print("📋 Context Engine — Data Sources Setup")
    print("="*70)
    print("""
This wizard will help you configure which documents to index.

You can specify:
  • Google Drive folder IDs (optional)
  • GitHub repositories
  • Folder names to exclude
""")

    config = {
        "organization": {
            "id": "shivaramgoud-org",
            "name": input("\nWhat's your organization name? ").strip() or "My Organization",
        },
        "google_drive": {
            "enabled": True,
            "folders": [],
        },
        "github": {
            "enabled": True,
            "repositories": [],
            "exclude_paths": [".git", "node_modules", "__pycache__", ".env"],
        },
    }

    # ============================================
    # Google Drive Setup
    # ============================================
    print("\n" + "-"*70)
    print("🔵 Google Drive Configuration")
    print("-"*70)
    print("""
To find your folder ID:
  1. Go to https://drive.google.com
  2. Right-click folder → Share
  3. Copy the ID from the URL or share link

Example folder ID: 1a2b3c4d5e6f7g8h9i0j""")

    use_gd = input("\nIndex from Google Drive? (y/n) [y]: ").strip().lower()
    if use_gd != "n":
        while True:
            folder_id = input(
                "  Folder ID (or 'done' to skip): "
            ).strip()
            if folder_id.lower() == "done" or not folder_id:
                break
            folder_name = input("    Folder name (optional): ").strip() or folder_id
            config["google_drive"]["folders"].append({
                "id": folder_id,
                "name": folder_name,
            })
            print("  ✅ Added")
    else:
        config["google_drive"]["enabled"] = False

    # ============================================
    # GitHub Setup
    # ============================================
    print("\n" + "-"*70)
    print("🟠 GitHub Configuration")
    print("-"*70)
    print("""
Repository format: owner/repo
Example: shivaram-goud/context-engine""")

    use_gh = input("\nIndex from GitHub? (y/n) [y]: ").strip().lower()
    if use_gh != "n":
        while True:
            repo = input(
                "  Repository (owner/repo, or 'done' to skip): "
            ).strip()
            if repo.lower() == "done" or not repo:
                break
            if "/" not in repo:
                print("  ❌ Invalid format. Use: owner/repo")
                continue
            config["github"]["repositories"].append(repo)
            print("  ✅ Added")
    else:
        config["github"]["enabled"] = False

    # ============================================
    # Exclusions
    # ============================================
    print("\n" + "-"*70)
    print("🚫 Exclusions (GitHub)")
    print("-"*70)
    print("\nFolders/files to skip (comma-separated):")
    print("Default: .git, node_modules, __pycache__, .env")

    exclusions = input("  Add more (or press Enter to skip): ").strip()
    if exclusions:
        custom = [x.strip() for x in exclusions.split(",")]
        config["github"]["exclude_paths"].extend(custom)

    # ============================================
    # Save config
    # ============================================
    os.makedirs(CONFIG_FILE.parent, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

    print("\n" + "="*70)
    print(f"✅ Configuration saved to: {CONFIG_FILE}")
    print("="*70)
    print(f"""
Summary:
  Organization: {config['organization']['name']}

  Google Drive:
    Enabled: {config['google_drive']['enabled']}
    Folders: {len(config['google_drive']['folders'])}
    {json.dumps(config['google_drive']['folders'], indent=6)}

  GitHub:
    Enabled: {config['github']['enabled']}
    Repositories: {len(config['github']['repositories'])}
    {json.dumps(config['github']['repositories'], indent=6)}

Next steps:
  1. Run: python scripts/test_with_real_data.py
  2. Or use: python scripts/interactive_query.py
""")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ Setup cancelled.\n")
        sys.exit(1)
