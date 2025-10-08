#!/usr/bin/env python
"""
Script to refresh VCR cassettes for youtube-comment-downloader tests

Usage:
    python tests/scripts/refresh_cassettes.py [--all] [--test TEST_NAME]

Options:
    --all           Refresh all cassettes (default)
    --test NAME     Refresh cassettes for specific test
    --check-age     Check cassette age and list stale ones
    --max-age DAYS  Maximum cassette age in days (default: 90)
"""

import os
import sys
import subprocess
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import shutil
import json


def get_cassette_age(cassette_path):
    """Get age of cassette file in days"""
    if not os.path.exists(cassette_path):
        return None
    mtime = os.path.getmtime(cassette_path)
    age = datetime.now() - datetime.fromtimestamp(mtime)
    return age.days


def find_cassettes(cassette_dir="tests/cassettes"):
    """Find all cassette files"""
    cassettes = []
    cassette_path = Path(cassette_dir)
    if cassette_path.exists():
        cassettes = list(cassette_path.glob("**/*.yaml")) + list(cassette_path.glob("**/*.yml"))
    return cassettes


def check_cassette_ages(max_age_days=90):
    """Check ages of all cassettes and report stale ones"""
    cassettes = find_cassettes()
    stale_cassettes = []

    print(f"\nChecking cassette ages (max age: {max_age_days} days)...")
    print("-" * 60)

    for cassette in cassettes:
        age = get_cassette_age(cassette)
        if age is not None:
            status = "✓ Fresh" if age <= max_age_days else "⚠ Stale"
            print(f"{status:8} | {age:3d} days | {cassette.relative_to('tests/cassettes')}")
            if age > max_age_days:
                stale_cassettes.append(cassette)

    if stale_cassettes:
        print(f"\n⚠ Found {len(stale_cassettes)} stale cassette(s)")
        print("Run with --all to refresh all cassettes")
    else:
        print("\n✓ All cassettes are fresh")

    return stale_cassettes


def backup_cassettes():
    """Create backup of existing cassettes"""
    cassette_dir = Path("tests/cassettes")
    if not cassette_dir.exists():
        return None

    backup_dir = Path("tests/cassettes.backup")
    if backup_dir.exists():
        shutil.rmtree(backup_dir)

    shutil.copytree(cassette_dir, backup_dir)
    print(f"✓ Backed up cassettes to {backup_dir}")
    return backup_dir


def refresh_all_cassettes():
    """Refresh all test cassettes"""
    print("\n🔄 Refreshing ALL cassettes...")
    print("=" * 60)

    # Backup existing cassettes
    backup_dir = backup_cassettes()

    # Remove existing cassettes
    cassette_dir = Path("tests/cassettes")
    if cassette_dir.exists():
        shutil.rmtree(cassette_dir)
        print("✓ Removed old cassettes")

    # Run tests with rewrite mode to create new cassettes
    print("\n📼 Recording new cassettes...")
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/",
        "--record-mode=rewrite",
        "-v",
        "-m", "network"  # Only run tests marked with network
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(result.stdout)

        if result.returncode != 0:
            print("\n⚠ Some tests failed during recording:")
            print(result.stderr)
            if backup_dir:
                print(f"\n💾 Restore backup with: mv {backup_dir} {cassette_dir}")
        else:
            print("\n✓ Successfully refreshed all cassettes")

            # Verify cassettes were created
            new_cassettes = find_cassettes()
            print(f"✓ Created {len(new_cassettes)} cassette files")

            # Clean up backup
            if backup_dir and backup_dir.exists():
                shutil.rmtree(backup_dir)
                print("✓ Cleaned up backup")

    except Exception as e:
        print(f"\n❌ Error during refresh: {e}")
        if backup_dir:
            print(f"💾 Restore backup with: mv {backup_dir} {cassette_dir}")
        return 1

    return 0


def refresh_specific_test(test_name):
    """Refresh cassettes for a specific test"""
    print(f"\n🔄 Refreshing cassettes for test: {test_name}")
    print("=" * 60)

    # Find the test file
    test_pattern = f"*{test_name}*" if "::" not in test_name else test_name

    # Run specific test with rewrite mode
    cmd = [
        sys.executable, "-m", "pytest",
        f"tests/{test_pattern}",
        "--record-mode=rewrite",
        "-v"
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(result.stdout)

        if result.returncode != 0:
            print("\n⚠ Test failed during recording:")
            print(result.stderr)
            return 1
        else:
            print(f"\n✓ Successfully refreshed cassettes for {test_name}")

    except Exception as e:
        print(f"\n❌ Error during refresh: {e}")
        return 1

    return 0


def verify_cassettes():
    """Verify cassettes work by running tests in strict mode"""
    print("\n🧪 Verifying cassettes...")
    print("=" * 60)

    cmd = [
        sys.executable, "-m", "pytest",
        "tests/",
        "--record-mode=none",  # Strict mode - no recording
        "--block-network",      # Block network access
        "-v",
        "-m", "network"
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            print("✓ All tests pass with recorded cassettes")
            return 0
        else:
            print("⚠ Some tests failed in strict mode:")
            print(result.stdout)
            print(result.stderr)
            return 1

    except Exception as e:
        print(f"❌ Error during verification: {e}")
        return 1


def main():
    parser = argparse.ArgumentParser(description="Refresh VCR cassettes for tests")
    parser.add_argument("--all", action="store_true", default=False,
                      help="Refresh all cassettes")
    parser.add_argument("--test", type=str,
                      help="Refresh cassettes for specific test")
    parser.add_argument("--check-age", action="store_true",
                      help="Check cassette ages")
    parser.add_argument("--max-age", type=int, default=90,
                      help="Maximum cassette age in days (default: 90)")
    parser.add_argument("--verify", action="store_true",
                      help="Verify cassettes work in strict mode")

    args = parser.parse_args()

    # Change to project root
    project_root = Path(__file__).parent.parent.parent
    os.chdir(project_root)
    print(f"📁 Working directory: {os.getcwd()}")

    if args.check_age:
        stale = check_cassette_ages(args.max_age)
        return 0 if not stale else 1

    if args.verify:
        return verify_cassettes()

    if args.test:
        return refresh_specific_test(args.test)

    if args.all:
        result = refresh_all_cassettes()
        if result == 0:
            # Optionally verify after refresh
            print("\n" + "=" * 60)
            return verify_cassettes()
        return result

    # Default: check age and suggest action
    stale = check_cassette_ages(args.max_age)
    if stale:
        print("\nTo refresh stale cassettes, run:")
        print(f"  python {__file__} --all")
    else:
        print("\nTo force refresh all cassettes, run:")
        print(f"  python {__file__} --all")

    return 0


if __name__ == "__main__":
    sys.exit(main())