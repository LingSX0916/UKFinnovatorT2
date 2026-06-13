"""Shared pytest config for the KYB module — forces committed fixtures so the
whole suite runs offline with no API key, no Supabase and no 21 MB sanctions file.
"""
import os
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE = FIXTURES / "uksl_sample.xml"
SAMPLE_DESIGNATION_COUNT = 30  # designations in uksl_sample.xml (see test_ingest)

# Pin the engines to fixtures BEFORE backend.kyb is imported anywhere.
os.environ["UKSL_XML_PATH"] = str(SAMPLE)
os.environ["KYB_WARM_INDEX"] = "0"
for secret in ("COMPANIES_HOUSE_API_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"):
    os.environ.pop(secret, None)


@pytest.fixture(scope="session")
def designations():
    from backend.kyb import uksl
    return uksl.load_uksl(str(SAMPLE))


@pytest.fixture(scope="session")
def index(designations):
    from backend.kyb.matching import build_index
    return build_index(designations)


@pytest.fixture(scope="session")
def by_id(designations):
    return {d.unique_id: d for d in designations}
