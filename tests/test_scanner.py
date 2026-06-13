import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from backend.scanner import scan_advert
from backend.warning_list_checker import find_warning_list_matches


def load(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def verdict(result: dict) -> str:
    # v2.0 rulebook uses overall_verdict; tolerate the legacy overall_status key.
    return result.get("overall_verdict") or result.get("overall_status")


def test_green():
    advert = load("data/compliant/brightline_isa_TEST.txt")
    result = scan_advert(advert)
    assert verdict(result) == "GREEN", (
        f"Expected GREEN, got {verdict(result)}\n{result.get('summary')}"
    )
    print("✅ GREEN — brightline_isa passed")


def test_amber():
    advert = load("data/borderline/meridian_growth_fund_TEST.txt")
    result = scan_advert(advert)
    assert verdict(result) == "AMBER", (
        f"Expected AMBER, got {verdict(result)}\n{result.get('summary')}"
    )
    print("✅ AMBER — meridian_growth_fund passed")


def test_red():
    advert = load("data/scam/coinvault_pro_TEST.txt")
    result = scan_advert(advert)
    hits = find_warning_list_matches(advert)
    v = "RED" if hits else verdict(result)
    assert v == "RED", (
        f"Expected RED, got {v}\n{result.get('summary')}"
    )
    print(f"✅ RED — coinvault_pro passed (warning list hits: {hits})")


if __name__ == "__main__":
    print("Running demo advert tests...\n")
    test_green()
    test_amber()
    test_red()
    print("\nAll tests passed. Demo adverts are behaving as expected.")
