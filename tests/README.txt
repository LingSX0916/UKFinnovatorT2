Test scripts to confirm the scanner returns the right verdict on the three demo adverts.

Files:
  test_scanner.py — runs all three demo adverts through the scanner and asserts:
                    brightline_isa        → GREEN
                    meridian_growth_fund  → AMBER
                    coinvault_pro         → RED

To run:
  python tests/test_scanner.py

Requires .env at the project root with ANTHROPIC_API_KEY set.

Run this before freezing the build on day two. If any assertion fails, the demo
adverts are not behaving as expected — check the rules prompt or the advert text.
