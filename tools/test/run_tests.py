#!/usr/bin/env python3
"""
Test runner script for qrie-infra.
Runs unit tests with coverage reporting.
"""
import subprocess
import sys
import os


def run_tests():
    """Run all unit tests with coverage"""
    
    # Change to qrie-infra directory where tests are located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))  # Go up two levels from tools/test/
    infra_dir = os.path.join(project_root, "qrie-infra")
    
    if not os.path.exists(infra_dir):
        print(f"❌ qrie-infra directory not found at {infra_dir}")
        sys.exit(1)
        
    os.chdir(infra_dir)
    print(f"📁 Working directory: {os.getcwd()}")
    
    # Install test requirements
    print("Installing test requirements...")
    subprocess.run([
        sys.executable, "-m", "pip", "install", "-r", "requirements-test.txt"
    ], check=True)
    
    # Run tests with coverage
    print("\nRunning unit tests with coverage...")
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/unit/",
        "-v",
        "--cov=lambda/data_access",
        "--cov-report=html:htmlcov",
        "--cov-report=term-missing",
        "--cov-fail-under=76.9"
    ]
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print("\n✅ All tests passed!")
        print("📊 Coverage report generated in htmlcov/index.html")
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    run_tests()
