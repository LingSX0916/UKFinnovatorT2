import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from backend.scanner import scan_advert
from backend.warning_list_checker import check_warning_list


def load(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def test_green():
    advert = load("data/compliant/brightline_isa_TEST.txt")
    result = scan_advert(advert)
    assert result["overall_status"] == "GREEN", (
        f"Expected GREEN, got {result['overall_status']}\n{result.get('overall_summary')}"
    )
    print("✅ GREEN — brightline_isa passed")


def test_amber():
    advert = load("data/borderline/meridian_growth_fund_TEST.txt")
    result = scan_advert(advert)
    assert result["overall_status"] == "AMBER", (
        f"Expected AMBER, got {result['overall_status']}\n{result.get('overall_summary')}"
    )
    print("✅ AMBER — meridian_growth_fund passed")


def test_red():
    advert = load("data/scam/coinvault_pro_TEST.txt")
    result = scan_advert(advert)
    hits = check_warning_list(result.get("named_firms", []), result.get("named_people", []))
    if hits:
        result["overall_status"] = "RED"
    assert result["overall_status"] == "RED", (
        f"Expected RED, got {result['overall_status']}\n{result.get('overall_summary')}"
    )
    print(f"✅ RED — coinvault_pro passed (warning list hits: {hits})")


if __name__ == "__main__":
    print("Running demo advert tests...\n")
    test_green()
    test_amber()
    test_red()
    print("\nAll tests passed. Demo adverts are behaving as expected.")
