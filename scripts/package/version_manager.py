#!/usr/bin/env python3
"""
Version Management for Thai Tokenizer Deployment Package.

This module provides version management utilities including version detection,
update procedures, and compatibility checking.
"""

import json
import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
import re
import requests
from packaging import version


class VersionManager:
    """Version management utilities."""
    
    def __init__(self, project_root: Optional[str] = None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent.parent
        self.version_file = self.project_root / "VERSION"
        self.package_info_file = self.project_root / "package_info.json"
    
    def get_current_version(self) -> str:
        """Get current version."""
        # Try version file first
        if self.version_file.exists():
            return self.version_file.read_text().strip()
        
        # Try package info file
        if self.package_info_file.exists():
            with open(self.package_info_file, 'r') as f:
                package_info = json.load(f)
                return package_info.get("version", "unknown")
        
        # Try git
        try:
            result = subprocess.run(
                ["git", "describe", "--tags", "--always"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        
        # Fallback
        return "1.0.0-dev"
    
    def set_version(self, new_version: str) -> bool:
        """Set new version."""
        try:
            # Validate version format
            version.parse(new_version)
            
            # Update version file
            self.version_file.write_text(new_version)
            
            # Update package info if it exists
            if self.package_info_file.exists():
                with open(self.package_info_file, 'r') as f:
                    package_info = json.load(f)
                
                package_info["version"] = new_version
                package_info["updated_at"] = datetime.now(timezone.utc).isoformat()
                
                with open(self.package_info_file, 'w') as f:
                    json.dump(package_info, f, indent=2)
            
            return True
            
        except Exception as e:
            print(f"Failed to set version: {e}")
            return False
    
    def bump_version(self, bump_type: str = "patch") -> str:
        """Bump version number."""
        current = self.get_current_version()
        
        try:
            # Parse current version
            v = version.parse(current)
            
            if bump_type == "major":
                new_version = f"{v.major + 1}.0.0"
            elif bump_type == "minor":
                new_version = f"{v.major}.{v.minor + 1}.0"
            elif bump_type == "patch":
                new_version = f"{v.major}.{v.minor}.{v.micro + 1}"
            else:
                raise ValueError(f"Invalid bump type: {bump_type}")
            
            if self.set_version(new_version):
                return new_version
            else:
                raise Exception("Failed to set new version")
                
        except Exception as e:
            print(f"Failed to bump version: {e}")
            return current
    
    def get_version_info(self) -> Dict[str, Any]:
        """Get comprehensive version information."""
        current_version = self.get_current_version()
        
        info = {
            "version": current_version,
            "version_file_exists": self.version_file.exists(),
            "package_info_exists": self.package_info_file.exists()
        }
        
        # Git information
        try:
            # Get git commit hash
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            if result.returncode == 0:
                info["git_commit"] = result.stdout.strip()[:8]
            
            # Get git branch
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            if result.returncode == 0:
                info["git_branch"] = result.stdout.strip()
            
            # Get git tags
            result = subprocess.run(
                ["git", "tag", "--list"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            if result.returncode == 0:
                tags = result.stdout.strip().split('\n')
                info["git_tags"] = [tag for tag in tags if tag]
            
        except:
            pass
        
        # Build information
        info["build_date"] = datetime.now(timezone.utc).isoformat()
        info["python_version"] = sys.version
        info["platform"] = sys.platform
        
        return info
    
    def check_compatibility(self, target_version: str) -> Dict[str, Any]:
        """Check compatibility with target version."""
        current = self.get_current_version()
        
        try:
            current_v = version.parse(current)
            target_v = version.parse(target_version)
            
            compatibility = {
                "current_version": current,
                "target_version": target_version,
                "compatible": True,
                "upgrade_required": False,
                "breaking_changes": False,
                "warnings": []
            }
            
            if target_v > current_v:
                compatibility["upgrade_required"] = True
                
                # Check for breaking changes (major version difference)
                if target_v.major > current_v.major:
                    compatibility["breaking_changes"] = True
                    compatibility["warnings"].append(
                        f"Major version upgrade from {current_v.major} to {target_v.major} may include breaking changes"
                    )
                
                # Check for significant changes (minor version difference)
                elif target_v.minor > current_v.minor:
                    compatibility["warnings"].append(
                        f"Minor version upgrade from {current_v.minor} to {target_v.minor} may include new features"
                    )
            
            elif target_v < current_v:
                compatibility["compatible"] = False
                compatibility["warnings"].append(
                    f"Downgrade from {current} to {target_version} is not recommended"
                )
            
            return compatibility
            
        except Exception as e:
            return {
                "current_version": current,
                "target_version": target_version,
                "compatible": False,
                "error": str(e)
            }
    
    def create_changelog_entry(self, version: str, changes: List[str]) -> str:
        """Create changelog entry."""
        timestamp = datetime.now().strftime("%Y-%m-%d")
        
        entry_lines = [
            f"## [{version}] - {timestamp}",
            ""
        ]
        
        # Categorize changes
        categories = {
            "Added": [],
            "Changed": [],
            "Fixed": [],
            "Removed": [],
            "Security": []
        }
        
        for change in changes:
            change = change.strip()
            if change.lower().startswith(("add", "new", "implement")):
                categories["Added"].append(change)
            elif change.lower().startswith(("fix", "resolve", "correct")):
                categories["Fixed"].append(change)
            elif change.lower().startswith(("change", "update", "modify")):
                categories["Changed"].append(change)
            elif change.lower().startswith(("remove", "delete", "drop")):
                categories["Removed"].append(change)
            elif change.lower().startswith(("security", "secure")):
                categories["Security"].append(change)
            else:
                categories["Changed"].append(change)
        
        # Add non-empty categories
        for category, items in categories.items():
            if items:
                entry_lines.append(f"### {category}")
                for item in items:
                    entry_lines.append(f"- {item}")
                entry_lines.append("")
        
        return "\n".join(entry_lines)
    
    def update_changelog(self, version: str, changes: List[str]) -> bool:
        """Update changelog file."""
        changelog_file = self.project_root / "CHANGELOG.md"
        
        try:
            # Create new entry
            new_entry = self.create_changelog_entry(version, changes)
            
            if changelog_file.exists():
                # Read existing changelog
                existing_content = changelog_file.read_text()
                
                # Insert new entry after the header
                lines = existing_content.split('\n')
                header_end = 0
                
                for i, line in enumerate(lines):
                    if line.startswith('## [') and header_end == 0:
                        header_end = i
                        break
                
                if header_end > 0:
                    # Insert after existing header
                    new_content = '\n'.join(lines[:header_end]) + '\n\n' + new_entry + '\n' + '\n'.join(lines[header_end:])
                else:
                    # Prepend to existing content
                    new_content = new_entry + '\n\n' + existing_content
            else:
                # Create new changelog
                header = "# Changelog\n\nAll notable changes to this project will be documented in this file.\n\n"
                new_content = header + new_entry
            
            # Write updated changelog
            changelog_file.write_text(new_content)
            return True
            
        except Exception as e:
            print(f"Failed to update changelog: {e}")
            return False
    
    def create_release_notes(self, version: str, changes: List[str]) -> str:
        """Create release notes."""
        notes_lines = [
            f"# Thai Tokenizer Deployment v{version}",
            "",
            f"Released on {datetime.now().strftime('%B %d, %Y')}",
            "",
            "## What's New",
            ""
        ]
        
        for change in changes:
            notes_lines.append(f"- {change}")
        
        notes_lines.extend([
            "",
            "## Installation",
            "",
            "Download the deployment package and run:",
            "",
            "```bash",
            "tar -xzf thai-tokenizer-deployment-{}.tar.gz".format(version),
            "cd thai-tokenizer-deployment-{}".format(version),
            "./install.sh",
            "```",
            "",
            "## Upgrade Instructions",
            "",
            "If upgrading from a previous version:",
            "",
            "1. Stop the current service",
            "2. Backup your configuration",
            "3. Install the new version",
            "4. Restore your configuration",
            "5. Start the service",
            "",
            "For detailed instructions, see the deployment guide.",
            "",
            "## Support",
            "",
            "For issues and questions, please refer to the troubleshooting guide or create an issue."
        ])
        
        return "\n".join(notes_lines)


def main():
    """Main version management function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Thai Tokenizer version management")
    parser.add_argument("command", choices=[
        "current", "set", "bump", "info", "compatibility", "changelog", "release-notes"
    ], help="Command to execute")
    
    parser.add_argument("--version", help="Version string")
    parser.add_argument("--bump-type", choices=["major", "minor", "patch"], 
                       default="patch", help="Version bump type")
    parser.add_argument("--target-version", help="Target version for compatibility check")
    parser.add_argument("--changes", nargs="+", help="List of changes for changelog")
    parser.add_argument("--project-root", help="Project root directory")
    
    args = parser.parse_args()
    
    try:
        manager = VersionManager(args.project_root)
        
        if args.command == "current":
            print(manager.get_current_version())
        
        elif args.command == "set":
            if not args.version:
                print("Error: --version is required for set command")
                return 1
            
            if manager.set_version(args.version):
                print(f"Version set to: {args.version}")
            else:
                print("Failed to set version")
                return 1
        
        elif args.command == "bump":
            new_version = manager.bump_version(args.bump_type)
            print(f"Version bumped to: {new_version}")
        
        elif args.command == "info":
            info = manager.get_version_info()
            print(json.dumps(info, indent=2))
        
        elif args.command == "compatibility":
            if not args.target_version:
                print("Error: --target-version is required for compatibility command")
                return 1
            
            compat = manager.check_compatibility(args.target_version)
            print(json.dumps(compat, indent=2))
        
        elif args.command == "changelog":
            if not args.version or not args.changes:
                print("Error: --version and --changes are required for changelog command")
                return 1
            
            if manager.update_changelog(args.version, args.changes):
                print(f"Changelog updated for version {args.version}")
            else:
                print("Failed to update changelog")
                return 1
        
        elif args.command == "release-notes":
            if not args.version or not args.changes:
                print("Error: --version and --changes are required for release-notes command")
                return 1
            
            notes = manager.create_release_notes(args.version, args.changes)
            print(notes)
        
        return 0
        
    except Exception as e:
        print(f"Version management failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())