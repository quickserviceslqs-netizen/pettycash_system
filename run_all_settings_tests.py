"""
Master test runner - runs all settings tests in sequence
"""

import subprocess
import sys


def run_test(script_name, description):
    """Run a test script and return results"""
    print(f"\n{'='*80}")
    print(f"  RUNNING: {description}")
    print(f"  Script: {script_name}")
    print(f"{'='*80}\n")

    result = subprocess.run(
        [sys.executable, script_name], capture_output=False, text=True
    )

    return result.returncode == 0


def main():
    """Run all test suites"""
    print("\n" + "=" * 80)
    print("  PETTYCASH SYSTEM - COMPLETE SETTINGS VERIFICATION")
    print("  Running all test suites...")
    print("=" * 80)

    tests = [
        ("test_all_settings.py", "Comprehensive Settings Test Suite"),
        ("test_settings_integration.py", "Live Integration Test"),
    ]

    results = []
    for script, description in tests:
        try:
            passed = run_test(script, description)
            results.append((description, passed))
        except Exception as e:
            print(f"\n❌ Error running {script}: {e}")
            results.append((description, False))

    # Final Summary
    print("\n" + "=" * 80)
    print("  FINAL TEST SUMMARY")
    print("=" * 80 + "\n")

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} | {test_name}")

    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)

    print(f"\n" + "=" * 80)
    print(f"  OVERALL: {passed_count}/{total_count} test suites passed")
    print(f"=" * 80 + "\n")

    if passed_count == total_count:
        print("  🎉 ALL TESTS PASSED!")
        print("  ✅ Settings system is fully operational and integrated")
        print("  ✅ All critical settings verified")
        print("  ✅ Performance optimized with caching")
        print("  ✅ UI URLs accessible")
        print("  ✅ Django admin integrated")
        print()
        return 0
    else:
        print("  ⚠️  Some tests failed - review above output")
        print()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
