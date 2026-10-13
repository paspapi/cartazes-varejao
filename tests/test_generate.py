import sys
from pathlib import Path

import pymupdf as fitz
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import generate  # noqa: E402


@pytest.fixture(scope="module")
def products():
    return generate.read_products(generate.CSV_PATH)


def test_match_by_portuguese_japanese_and_accents(products):
    for name in ["AVOCADO", "avocado", "アボカド", "rucula", "ルッコラ", "ローズマリー", "パクチーコリアンダー"]:
        assert len(generate.select_products(products, [name])) == 1, name


def test_price_override(products):
    (row,) = generate.select_products(products, ["AVOCADO=13,50"])
    assert generate.format_price(row["preco"]) == "13,50"


def test_ambiguous_name_lists_candidates(products):
    with pytest.raises(generate.SelectionError, match="BANANA NANICA"):
        generate.select_products(products, ["バナナ"])
    with pytest.raises(generate.SelectionError, match="NINJA"):
        generate.select_products(products, ["BROCOLIS"])
    assert len(generate.select_products(products, ["BROCOLIS NINJA"])) == 1


def test_duplicate_rows_need_price(products):
    with pytest.raises(generate.SelectionError, match="preco"):
        generate.select_products(products, ["ALFACE"])
    assert len(generate.select_products(products, ["ALFACE=6"])) == 1


def test_unknown_and_bad_price(products):
    with pytest.raises(generate.SelectionError, match="nao encontrado"):
        generate.select_products(products, ["ABACAXI"])
    with pytest.raises(generate.SelectionError):
        generate.select_products(products, ["AVOCADO=doze"])


def test_generate_selected(tmp_path):
    rc = generate.main(["--item", "アボカド=12", "--item", "BROCOLIS HANA", "--date", "20261013", "--output-dir", str(tmp_path)])
    assert rc == 0
    names = sorted(p.name for p in tmp_path.iterdir())
    assert names == [
        "__PRODUTOS_TODOS_TODOS_20261013.pdf",
        "avocado_org_12-00_20261013.pdf",
        "brocolis_hana_org_10-00_20261013.pdf",
    ]
    with fitz.open(tmp_path / "__PRODUTOS_TODOS_TODOS_20261013.pdf") as doc:
        assert doc.page_count == 2
        assert "12" in doc[0].get_text()


def test_generate_all_has_one_page_per_row(tmp_path, products):
    assert generate.main(["--output-dir", str(tmp_path), "--date", "20261013"]) == 0
    with fitz.open(tmp_path / "__PRODUTOS_TODOS_TODOS_20261013.pdf") as doc:
        assert doc.page_count == len(products)
