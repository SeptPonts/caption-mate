import re
import subprocess
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.main import main as cli_main  # noqa: E402


def extract_match_count(output_lines):
    """从输出中提取匹配数量"""
    for line in output_lines:
        if "Found" in line and "matches" in line:
            # 解析 "Found 3 matches:" 这样的行
            match = re.search(r"Found (\d+) matches", line)
            if match:
                return int(match.group(1))
    return 0


def detect_ai_errors(output_lines):
    """检测AI模式特有的错误"""
    errors = []
    for line in output_lines:
        if "API" in line and "error" in line.lower():
            errors.append("API error detected")
        elif "timeout" in line.lower() and "ai" in line.lower():
            errors.append("AI timeout error")
        elif "deepseek" in line.lower() and "error" in line.lower():
            errors.append("DeepSeek API error")
        elif "json" in line.lower() and "decode" in line.lower():
            errors.append("JSON parsing error")
    return errors


def test_match_integration_ai():
    """专门测试AI模式的集成测试"""
    return test_match_integration(mode="ai")


def test_match_click_ai():
    """专门测试AI模式的Click测试"""
    return test_match_click(mode="ai")


def test_match_integration(mode="regex"):
    """通过subprocess调用真实命令 - 最真实的测试"""
    print(f"Running integration test (mode: {mode})...")

    test_path = (
        "sata11-156XXXX6325/TV Series/The Man in the High Castle/"
        "The Man in the High Castle (2015) Season 1 S01 "
        "(1080p AMZN WEB-DL x265 HEVC 10bit AAC 5-1.1 MONOLITH)"
    )

    cmd = [
        "uv",
        "run",
        "caption-mate",
        "nas",
        "match",
        test_path,
        "--dry-run",
        "--threshold=0.01",
        f"--mode={mode}",
    ]

    print(f"Executing: {' '.join(cmd)}")

    try:
        timeout = 240 if mode == "ai" else 120
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

        print(f"Return code: {result.returncode}")
        print(f"STDOUT:\n{result.stdout}")

        if result.stderr:
            print(f"STDERR:\n{result.stderr}")

        # 基本验证
        if result.returncode == 0:
            print("✓ Command executed successfully")
        else:
            print(f"✗ Command failed with return code {result.returncode}")

        # 解析输出
        lines = result.stdout.split("\n")
        match_count = extract_match_count(lines)

        if match_count > 0:
            print(f"✓ Found {match_count} matches")
        else:
            print("- No matches found (this might be expected)")

        # 检测AI模式特有错误
        ai_errors = detect_ai_errors(lines) if mode == "ai" else []

        return {
            "success": result.returncode == 0,
            "match_count": match_count,
            "output": result.stdout,
            "error": result.stderr,
            "mode": mode,
            "ai_errors": ai_errors,
        }

    except subprocess.TimeoutExpired:
        timeout_msg = "240 seconds" if mode == "ai" else "120 seconds"
        print(f"✗ Command timed out after {timeout_msg}")
        return {"success": False, "error": "Timeout"}
    except Exception as e:
        print(f"✗ Exception occurred: {e}")
        return {"success": False, "error": str(e)}


def test_match_click(mode="regex"):
    """使用Click的CliRunner - 更快，更可控"""
    print(f"Running Click test (mode: {mode})...")

    try:
        from click.testing import CliRunner

        runner = CliRunner()

        test_path = (
            "sata11-156XXXX6325/TV Series/The Man in the High Castle/"
            "The Man in the High Castle (2015) Season 1 S01 "
            "(1080p AMZN WEB-DL x265 HEVC 10bit AAC 5-1.1 MONOLITH)"
        )

        # 执行命令
        result = runner.invoke(
            cli_main,
            [
                "nas",
                "match",
                test_path,
                "--dry-run",
                "--threshold=0.01",
                f"--mode={mode}",
            ],
        )

        print(f"Exit code: {result.exit_code}")
        print(f"Output:\n{result.output}")

        if result.exception:
            print(f"Exception: {result.exception}")
            import traceback

            print(f"Traceback:\n{''.join(traceback.format_tb(result.exc_info[2]))}")

        # 解析输出
        lines = result.output.split("\n")
        match_count = extract_match_count(lines)

        if result.exit_code == 0:
            print("✓ Click test executed successfully")
        else:
            print(f"✗ Click test failed with exit code {result.exit_code}")

        if match_count > 0:
            print(f"✓ Found {match_count} matches")
        else:
            print("- No matches found (this might be expected)")

        # 检测AI模式特有错误
        ai_errors = detect_ai_errors(lines) if mode == "ai" else []

        return {
            "success": result.exit_code == 0,
            "match_count": match_count,
            "output": result.output,
            "exception": result.exception,
            "mode": mode,
            "ai_errors": ai_errors,
        }

    except ImportError as e:
        print(f"✗ Could not import required modules: {e}")
        return {"success": False, "error": "Import error"}
    except Exception as e:
        print(f"✗ Exception occurred: {e}")
        return {"success": False, "error": str(e)}


def run_comprehensive_tests():
    """运行全面的测试，包括两种模式"""
    print("=== Caption-Mate Match Command Test ===\n")

    results = {}

    # 运行Regex模式测试
    print("=== Regex Mode Tests ===")
    print("--- Integration Test (subprocess) ---")
    results["regex_integration"] = test_match_integration(mode="regex")

    print("\n--- Click Test (CliRunner) ---")
    results["regex_click"] = test_match_click(mode="regex")

    print("\n" + "=" * 60 + "\n")

    # 运行AI模式测试
    print("=== AI Mode Tests ===")
    print("--- Integration Test (subprocess) ---")
    results["ai_integration"] = test_match_integration(mode="ai")

    print("\n--- Click Test (CliRunner) ---")
    results["ai_click"] = test_match_click(mode="ai")

    print("\n" + "=" * 60 + "\n")

    # 结果对比
    print("=== Comprehensive Test Results Summary ===")
    _display_test_summary(results)

    print("\n=== Test Complete ===")
    return results


def _display_test_summary(results):
    """显示测试结果摘要"""
    print("\n--- Success Status ---")
    for test_name, result in results.items():
        success = result.get("success", False)
        status = "✓" if success else "✗"
        mode = result.get("mode", "unknown")
        print(
            f"{status} {test_name.replace('_', ' ').title()}: {success} (mode: {mode})"
        )

    print("\n--- Match Counts ---")
    for test_name, result in results.items():
        count = result.get("match_count", 0)
        mode = result.get("mode", "unknown")
        print(f"  {test_name.replace('_', ' ').title()}: {count} matches")

    print("\n--- AI Mode Error Analysis ---")
    ai_results = {k: v for k, v in results.items() if "ai" in k}
    for test_name, result in ai_results.items():
        ai_errors = result.get("ai_errors", [])
        if ai_errors:
            print(f"  {test_name}: {', '.join(ai_errors)}")
        else:
            print(f"  {test_name}: No AI-specific errors detected")

    print("\n--- Mode Comparison ---")
    regex_integration = results.get("regex_integration", {})
    ai_integration = results.get("ai_integration", {})

    regex_matches = regex_integration.get("match_count", 0)
    ai_matches = ai_integration.get("match_count", 0)

    if regex_matches == ai_matches:
        print(f"✓ Both modes found same number of matches: {regex_matches}")
    elif ai_matches > regex_matches:
        print(f"⚠ AI mode found more matches: {ai_matches} vs {regex_matches}")
    else:
        print(f"⚠ Regex mode found more matches: {regex_matches} vs {ai_matches}")


def main():
    """主函数 - 运行全面测试"""
    return run_comprehensive_tests()


if __name__ == "__main__":
    # 可以选择运行单个测试或全面测试
    # main()  # 全面测试
    # test_match_click()  # 单个regex测试
    test_match_click_ai()  # 单个AI测试
