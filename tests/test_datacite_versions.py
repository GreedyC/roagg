import csv

import pytest

from roagg.aggregator import write_csv
from roagg.providers.datacite import DataCiteAPI


def item(doi="10.1234/version", relations=(), version_count=0, version_of_count=0):
    return {
        "relationships": {"client": {"data": {"id": "example.client"}}},
        "attributes": {
            "doi": doi,
            "types": {"resourceTypeGeneral": "Dataset"},
            "publisher": {"name": "Example"},
            "titles": [{"title": "Example dataset"}],
            "versionCount": version_count,
            "versionOfCount": version_of_count,
            "relatedIdentifiers": list(relations),
        },
    }


def relation(kind, doi="10.1234/concept", identifier_type="DOI"):
    return {
        "relationType": kind,
        "relatedIdentifierType": identifier_type,
        "relatedIdentifier": doi,
    }


def test_version_links_to_concept_without_inferring_latest():
    record = DataCiteAPI().get_record(item(
        relations=[relation("IsVersionOf")], version_of_count=1,
    ))
    assert record.conceptDoi == "10.1234/concept"
    assert record.isLatestVersion is True
    assert record.isConceptDoi is False


def test_concept_links_to_itself():
    record = DataCiteAPI().get_record(item(
        doi="10.1234/concept", relations=[relation("HasVersion", "10.1234/version")],
        version_count=1,
    ))
    assert record.conceptDoi == record.doi
    assert record.isConceptDoi is True
    assert record.isLatestVersion is False


@pytest.mark.parametrize("relations", [
    [], [relation("IsReferencedBy")], [relation("IsVersionOf", identifier_type="URL")],
])
def test_unrelated_or_non_doi_relations_do_not_create_concept(relations):
    record = DataCiteAPI().get_record(item(relations=relations))
    assert record.conceptDoi is None


def test_explicit_previous_version_flag_is_preserved():
    record = DataCiteAPI().get_record(item(relations=[
        relation("IsVersionOf"), relation("IsPreviousVersionOf", "10.1234/newer"),
    ], version_of_count=1))
    assert record.conceptDoi == "10.1234/concept"
    assert record.isLatestVersion is False


def test_csv_exports_concept_and_empty_unversioned_value(tmp_path):
    records = [
        DataCiteAPI().get_record(item(relations=[relation("IsVersionOf")])),
        DataCiteAPI().get_record(item(doi="10.1234/unversioned")),
    ]
    target = tmp_path / "outputs.csv"
    write_csv(records, target)
    with target.open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    assert rows[0]["conceptDoi"] == "10.1234/concept"
    assert rows[1]["conceptDoi"] == ""
