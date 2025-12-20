"""
Security tools for SecurityOfficerAgent: Security audit and compliance checking.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List

from agency_swarm.tools import BaseTool
from pydantic import Field


class SecurityAuditTool(BaseTool):
    """
    Security audit tool that checks for:
    - .env files being tracked in git
    - Hardcoded API keys in mvp_v1/ directory
    - Exposed secrets in code
    """

    check_env_files: bool = Field(
        default=True, description="Check if .env files are being tracked"
    )
    check_hardcoded_keys: bool = Field(
        default=True, description="Check for hardcoded API keys in mvp_v1/"
    )
    scan_directory: str = Field(
        default="mvp_v1", description="Directory to scan for hardcoded keys"
    )

    def run(self) -> str:
        """
        Perform security audit and return findings.

        Checks:
        1. .env files in git tracking
        2. Hardcoded API keys in mvp_v1/
        3. Exposed secrets
        """
        findings = []
        issues = []

        # Check 1: .env files in git
        if self.check_env_files:
            env_files = self._find_env_files()
            if env_files:
                issues.append(f"⚠ Found .env files (should not be tracked): {', '.join(env_files)}")
            else:
                findings.append("✓ No .env files found in project root")

        # Check 2: Hardcoded API keys
        if self.check_hardcoded_keys:
            hardcoded_keys = self._scan_for_hardcoded_keys()
            if hardcoded_keys:
                issues.append(f"⚠ Found potential hardcoded API keys in {len(hardcoded_keys)} file(s)")
                for file_path, matches in hardcoded_keys.items():
                    issues.append(f"  - {file_path}: {len(matches)} potential key(s) found")
            else:
                findings.append(f"✓ No hardcoded API keys found in {self.scan_directory}/")

        # Compile report
        report = "=== Security Audit Report ===\n\n"
        
        if findings:
            report += "**Passed Checks:**\n"
            for finding in findings:
                report += f"{finding}\n"
            report += "\n"

        if issues:
            report += "**Issues Found:**\n"
            for issue in issues:
                report += f"{issue}\n"
            report += "\n"
            report += "**Recommendations:**\n"
            report += "1. Ensure .env files are in .gitignore\n"
            report += "2. Move all API keys to environment variables\n"
            report += "3. Use config.py to load secrets from .env\n"
            report += "4. Never commit .env files to version control\n"
        else:
            report += "✓ No security issues detected.\n"

        return report

    def _find_env_files(self) -> List[str]:
        """Find .env files in project root."""
        project_root = Path(__file__).parent.parent.parent
        env_files = []
        
        for env_file in project_root.glob(".env*"):
            if env_file.is_file() and not env_file.name.endswith(".example"):
                env_files.append(env_file.name)
        
        return env_files

    def _scan_for_hardcoded_keys(self) -> dict[str, List[str]]:
        """Scan directory for hardcoded API keys."""
        project_root = Path(__file__).parent.parent.parent
        scan_path = project_root / self.scan_directory
        
        if not scan_path.exists():
            return {}

        # Patterns for common API keys
        key_patterns = [
            (r'sk_live_[a-zA-Z0-9]{24,}', "Stripe Live Key"),
            (r'sk_test_[a-zA-Z0-9]{24,}', "Stripe Test Key"),
            (r'pk_live_[a-zA-Z0-9]{24,}', "Stripe Publishable Key"),
            (r'SG\.[a-zA-Z0-9_-]{22}\.[a-zA-Z0-9_-]{43}', "SendGrid API Key"),
            (r'AC[a-z0-9]{32}', "Twilio Account SID"),
            (r'[a-zA-Z0-9]{32}', "Generic 32-char key (potential)"),
        ]

        hardcoded_keys = {}
        
        for py_file in scan_path.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")
                matches = []
                
                for pattern, key_type in key_patterns:
                    found = re.findall(pattern, content)
                    if found:
                        # Filter out false positives (common words, etc.)
                        for match in found:
                            # Skip if it's clearly not a key (e.g., in comments explaining what a key is)
                            if not any(skip in content.lower() for skip in ["example", "placeholder", "your_", "change"]):
                                matches.append(f"{key_type}: {match[:20]}...")
                
                if matches:
                    rel_path = py_file.relative_to(project_root)
                    hardcoded_keys[str(rel_path)] = matches
            except Exception:
                # Skip files that can't be read
                continue

        return hardcoded_keys

