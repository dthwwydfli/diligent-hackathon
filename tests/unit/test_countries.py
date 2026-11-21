"""F9: full gazetteer and open sets for unmapped place-like values."""

from __future__ import annotations

from namesake.countries import (
    canonical_country,
    countries_from_values,
    parse_country_values,
)


def test_f9_five_inputs_map() -> None:
    values = [
        "Slovenia",
        "Peru",
        "PE",
        "Côte d'Ivoire",
        "Macao Special Administrative Region of China",
    ]
    mapped = countries_from_values(values)
    assert mapped == {"Slovenia", "Peru", "Cote d'Ivoire", "Macao"}


def test_tag_suffix_and_accent() -> None:
    assert canonical_country("Croatia [PEP]") == "Croatia"
    assert canonical_country("Côte d'Ivoire") == "Cote d'Ivoire"


def test_unmapped_place_opens_set() -> None:
    mapped, opened = parse_country_values(["France", "Somewhereville"])
    assert "France" in mapped
    assert opened is True


def test_not_country_does_not_open() -> None:
    mapped, opened = parse_country_values(["International", "Europe", "Croatia"])
    assert mapped == {"Croatia"}
    assert opened is False
