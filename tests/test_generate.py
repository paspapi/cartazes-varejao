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
    with pytest.raises(generate.SelectionError, match="BANANA PRATA"):
        generate.select_products(products, ["バナナ"])
    with pytest.raises(generate.SelectionError, match="HANA"):
        generate.select_products(products, ["ブロッコリー"])
    with pytest.raises(generate.SelectionError, match="CEBOLINHA"):
        generate.select_products(products, ["ねぎ"])
    with pytest.raises(generate.SelectionError, match="NINJA"):
        generate.select_products(products, ["BROCOLIS"])
    # Parte do nome com um so produto: escolhe direto
    (row,) = generate.select_products(products, ["PORO"])
    assert row["produto"] == "ALHO PORÓ"
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
    combined = tmp_path / "__PRODUTOS_TODOS_TODOS_20261013.pdf"
    with fitz.open(combined) as doc:
        assert doc.page_count == len(products)
    # Telegram aceita documentos de ate 50 MB
    assert combined.stat().st_size < 20 * 1024 * 1024


@pytest.fixture
def csv_copy(tmp_path):
    path = tmp_path / "produtos.csv"
    path.write_bytes(generate.CSV_PATH.read_bytes())
    return path


def run(csv_copy, tmp_path, *args):
    return generate.main(["--csv", str(csv_copy), "--output-dir", str(tmp_path / "out"), "--date", "20261013", *args])


def test_save_updates_single_row_only(csv_copy, tmp_path):
    original = csv_copy.read_text(encoding="utf-8")
    assert run(csv_copy, tmp_path, "--item", "AVOCADO=13,50", "--item", "ALFACE=6", "--save") == 0
    text = csv_copy.read_text(encoding="utf-8")
    assert "アボカド,AVOCADO,,ORGÂNICO,PRODUÇÃO PRÓPRIA,13.50," in text
    # ALFACE ja tinha 6 no CSV: nada muda nessas linhas
    assert len(text.splitlines()) == len(original.splitlines())
    assert [l for l in text.splitlines() if ",ALFACE," in l] == [l for l in original.splitlines() if ",ALFACE," in l]

    assert run(csv_copy, tmp_path, "--item", "AVOCADO=14", "--save") == 0
    assert "アボカド,AVOCADO,,ORGÂNICO,PRODUÇÃO PRÓPRIA,14," in csv_copy.read_text(encoding="utf-8")


def test_save_refuses_ambiguous_rows(csv_copy, tmp_path):
    before = csv_copy.read_bytes()
    assert run(csv_copy, tmp_path, "--item", "ALFACE=7", "--save") == 2
    assert csv_copy.read_bytes() == before


def test_add_new_product_with_defaults(csv_copy, tmp_path):
    rc = run(csv_copy, tmp_path, "--add", '{"produto": "abacaxi", "produto_jp": "パイナップル", "preco": "12,5"}')
    assert rc == 0
    last = csv_copy.read_text(encoding="utf-8").splitlines()[-1]
    assert last == "パイナップル,ABACAXI,,ORGÂNICO,PRODUÇÃO PRÓPRIA,12.50,preto,,verde,verde,verde,,,,,SundayLatte-E4DBW.ttf"
    assert (tmp_path / "out" / "abacaxi_org_12-50_20261013.pdf").exists()
    products = generate.read_products(csv_copy)
    assert len(generate.select_products(products, ["パイナップル"])) == 1


def test_add_rejects_existing_and_bad_input(csv_copy, tmp_path):
    before = csv_copy.read_bytes()
    assert run(csv_copy, tmp_path, "--add", '{"produto": "AVOCADO", "preco": "12"}') == 2
    assert run(csv_copy, tmp_path, "--add", '{"produto": "X"}') == 2
    assert run(csv_copy, tmp_path, "--add", '{"produto": "X", "preco": "1", "foo": "y"}') == 2
    assert run(csv_copy, tmp_path, "--add", "not json") == 2
    assert csv_copy.read_bytes() == before
