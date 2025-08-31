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


def test_match_integration():
    """通过subprocess调用真实命令 - 最真实的测试"""
    print("Running integration test...")

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
    ]

    print(f"Executing: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

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

        return {
            "success": result.returncode == 0,
            "match_count": match_count,
            "output": result.stdout,
            "error": result.stderr,
        }

    except subprocess.TimeoutExpired:
        print("✗ Command timed out after 120 seconds")
        return {"success": False, "error": "Timeout"}
    except Exception as e:
        print(f"✗ Exception occurred: {e}")
        return {"success": False, "error": str(e)}


def test_match_click():
    """使用Click的CliRunner - 更快，更可控"""
    print("Running Click test...")

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
            cli_main, ["nas", "match", test_path, "--dry-run", "--threshold=0.01"]
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

        return {
            "success": result.exit_code == 0,
            "match_count": match_count,
            "output": result.output,
            "exception": result.exception,
        }

    except ImportError as e:
        print(f"✗ Could not import required modules: {e}")
        return {"success": False, "error": "Import error"}
    except Exception as e:
        print(f"✗ Exception occurred: {e}")
        return {"success": False, "error": str(e)}


def main():
    """运行两种测试并对比结果"""
    print("=== Caption-Mate Match Command Test ===\n")

    # 运行集成测试
    print("=== Integration Test (subprocess) ===")
    integration_result = test_match_integration()

    print("\n" + "=" * 50 + "\n")

    # 运行Click测试
    print("=== Click Test (CliRunner) ===")
    click_result = test_match_click()

    print("\n" + "=" * 50 + "\n")

    # 结果对比
    print("=== Test Results Summary ===")

    print(f"Integration test success: {integration_result.get('success', False)}")
    print(f"Click test success: {click_result.get('success', False)}")

    integration_matches = integration_result.get("match_count", 0)
    click_matches = click_result.get("match_count", 0)

    print(f"Integration test matches: {integration_matches}")
    print(f"Click test matches: {click_matches}")

    # 一致性检查
    if integration_result.get("success") and click_result.get("success"):
        if integration_matches == click_matches:
            print("✓ Both tests produced consistent results")
        else:
            print("⚠ Tests produced different match counts")
    else:
        print("- Cannot compare results due to test failures")

    print("\n=== Test Complete ===")


if __name__ == "__main__":
    # main()
    test_match_click()
