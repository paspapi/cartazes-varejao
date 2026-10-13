from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import re
import sys
import unicodedata
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

try:
    import pymupdf as fitz
except ImportError as exc:  # pragma: no cover - import guard for runtime
    raise SystemExit(
        "PyMuPDF nao esta instalado. Instale a dependencia e rode novamente.\n"
        "Exemplo: python3 -m pip install PyMuPDF"
    ) from exc


ROOT_DIR = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = ROOT_DIR / "template" / "ceagesp_template.pdf"
CSV_PATH = ROOT_DIR / "data" / "produtos.csv"
OUTPUT_DIR = ROOT_DIR / "output"
HARE_LOGO_PATH = ROOT_DIR / "assets" / "hare.png"
SISORG_LOGO_PATH = ROOT_DIR / "assets" / "sisorg.png"
ORGANICO_PNG_PATH = ROOT_DIR / "assets" / "tipo-organico.png"
ORIGEM_PNG_PATH = ROOT_DIR / "assets" / "origem-producao propria.png"
FONTS_DIR = ROOT_DIR / "assets" / "fonts"
PERMANENT_MARKER_PATH = ROOT_DIR / "assets" / "fonts" / "PermanentMarker-Regular.ttf"
AVERSA_PATH = ROOT_DIR / "assets" / "fonts" / "Aversa Vectors.otf"
TANUKI_MAGIC_PATH = ROOT_DIR / "assets" / "fonts" / "TanukiMagic.ttf"
DEJAVU_BOLD_PATH = FONTS_DIR / "DejaVuSans-Bold.ttf"
DEJAVU_REGULAR_PATH = FONTS_DIR / "DejaVuSans.ttf"

REGULAR_FONT = "dejavu_regular"
BOLD_FONT = "dejavu_bold"
MARKER_FONT = "permanent_marker"
PRICE_FONT = "price_aversa"
JAPANESE_FONT = "tanuki_magic"
PRODUCT_COLOR = (0, 0, 0)
PRICE_COLOR = (0, 0, 0)
COLOR_NAME_MAP = {
    "preto": (0.066, 0.066, 0.066),
    "branco": (1.0, 1.0, 1.0),
    "verde": (0.122, 0.478, 0.227),
    "azul": (0.0, 0.24, 0.63),
    "vermelho": (0.78, 0.06, 0.06),
}
CUSTOM_FONT_FILES: dict[str, Path] = {}

@dataclass(frozen=True)
class Layout:
    # Coordenadas calibradas sobre o PDF oficial da CEAGESP.
    product_rect: fitz.Rect = fitz.Rect(236, 184, 660, 251)
    variedade_rect: fitz.Rect = fitz.Rect(262, 256, 660, 304)
    tipo_rect: fitz.Rect = fitz.Rect(184, 334, 660, 382)
    tipo_expanded_rect: fitz.Rect = fitz.Rect(184, 266, 660, 382)
    origem_rect: fitz.Rect = fitz.Rect(228, 388.8, 660, 417.8)
    price_rect: fitz.Rect = fitz.Rect(205, 430, 705, 835)
    sisorg_max_rect: fitz.Rect = fitz.Rect(85, 590, 260, 770)
    product_max_size: float = 60
    variedade_max_size: float = 32
    tipo_max_size: float = 38
    tipo_expanded_max_size: float = 68
    origem_size: float = 20
    price_integer_size: float = 334.8
    price_decimal_size: float = 132
    price_gap: float = 2
    hare_gap: float = 3
    sisorg_gap: float = 132
    decimal_drop: float = 138
    price_reserved_left: float = 238
    product_tracking: float = 1.4
    tipo_tracking: float = 2.4
    origem_hare_rect: fitz.Rect = fitz.Rect(553.3, 380, 633.3, 432)


@dataclass(frozen=True)
class BrushStyle:
    tracking: float = 0.0
    stroke_layers: int = 2
    stroke_strength: float = 1.0
    size_jitter: float = 0.03
    y_jitter: float = 1.2
    x_jitter: float = 0.4
    slope: float = 0.0
    word_rotation_hint: float = 0.0


DEFAULT_BRUSH_STYLE = BrushStyle()
PRODUCT_BRUSH_STYLE = BrushStyle(
    tracking=1.8,
    stroke_layers=3,
    stroke_strength=1.2,
    size_jitter=0.04,
    y_jitter=1.6,
    x_jitter=0.6,
    slope=0.035,
    word_rotation_hint=3.0,
)
TIPO_BRUSH_STYLE = BrushStyle(
    tracking=3.2,
    stroke_layers=4,
    stroke_strength=1.35,
    size_jitter=0.05,
    y_jitter=1.8,
    x_jitter=0.7,
    slope=0.02,
    word_rotation_hint=2.0,
)
PRICE_BRUSH_STYLE = BrushStyle(
    tracking=0.2,
    stroke_layers=4,
    stroke_strength=1.15,
    size_jitter=0.025,
    y_jitter=1.0,
    x_jitter=0.35,
    slope=0.0,
    word_rotation_hint=0.0,
)


LAYOUT = Layout()


def require_assets() -> None:
    required_paths = [
        TEMPLATE_PATH,
        CSV_PATH,
        HARE_LOGO_PATH,
        SISORG_LOGO_PATH,
        DEJAVU_BOLD_PATH,
        DEJAVU_REGULAR_PATH,
    ]
    missing = [str(path) for path in required_paths if not path.exists()]
    if missing:
        missing_list = "\n".join(f"- {item}" for item in missing)
        raise SystemExit(f"Arquivos obrigatorios ausentes:\n{missing_list}")


def parse_color(raw_value: str | None, default: tuple[float, float, float]) -> tuple[float, float, float]:
    value = (raw_value or "").strip().lower()
    if not value:
        return default

    if value in COLOR_NAME_MAP:
        return COLOR_NAME_MAP[value]

    if re.fullmatch(r"#[0-9a-f]{6}", value):
        return tuple(int(value[i:i + 2], 16) / 255.0 for i in (1, 3, 5))

    raise ValueError(
        f"Cor invalida: {raw_value!r}. Use nome simples ou hexadecimal #RRGGBB."
    )


def mix_color(
    color_a: tuple[float, float, float],
    color_b: tuple[float, float, float],
    ratio: float,
) -> tuple[float, float, float]:
    return tuple(
        (channel_a * (1.0 - ratio)) + (channel_b * ratio)
        for channel_a, channel_b in zip(color_a, color_b)
    )


def get_font(fontname: str) -> fitz.Font:
    if fontname in CUSTOM_FONT_FILES:
        return fitz.Font(fontfile=str(CUSTOM_FONT_FILES[fontname]))
    if fontname == JAPANESE_FONT:
        if TANUKI_MAGIC_PATH.exists():
            return fitz.Font(fontfile=str(TANUKI_MAGIC_PATH))
        return fitz.Font(fontname="helv")
    if fontname == PRICE_FONT:
        if AVERSA_PATH.exists():
            return fitz.Font(fontfile=str(AVERSA_PATH))
        return fitz.Font(fontname="helv")
    if fontname == MARKER_FONT:
        if PERMANENT_MARKER_PATH.exists():
            return fitz.Font(fontfile=str(PERMANENT_MARKER_PATH))
        return fitz.Font(fontname="helv")
    if fontname == BOLD_FONT:
        return fitz.Font(fontfile=str(DEJAVU_BOLD_PATH))
    if fontname == REGULAR_FONT:
        return fitz.Font(fontfile=str(DEJAVU_REGULAR_PATH))
    return fitz.Font(fontname=fontname)


def get_fontfile(fontname: str) -> str | None:
    if fontname in CUSTOM_FONT_FILES:
        return str(CUSTOM_FONT_FILES[fontname])
    if fontname == JAPANESE_FONT and TANUKI_MAGIC_PATH.exists():
        return str(TANUKI_MAGIC_PATH)
    if fontname == PRICE_FONT and AVERSA_PATH.exists():
        return str(AVERSA_PATH)
    if fontname == MARKER_FONT and PERMANENT_MARKER_PATH.exists():
        return str(PERMANENT_MARKER_PATH)
    if fontname == BOLD_FONT:
        return str(DEJAVU_BOLD_PATH)
    if fontname == REGULAR_FONT:
        return str(DEJAVU_REGULAR_PATH)
    return None


def build_text_insert_kwargs(fontname: str) -> dict[str, str]:
    resolved_fontname = resolve_page_fontname(fontname)
    kwargs: dict[str, str] = {"fontname": resolved_fontname}
    fontfile = get_fontfile(fontname)
    if fontfile and resolved_fontname != "helv":
        kwargs["fontfile"] = fontfile
    return kwargs


def register_page_fonts(page: fitz.Page) -> None:
    page.insert_font(fontname=REGULAR_FONT, fontfile=str(DEJAVU_REGULAR_PATH))
    page.insert_font(fontname=BOLD_FONT, fontfile=str(DEJAVU_BOLD_PATH))
    if PERMANENT_MARKER_PATH.exists():
        page.insert_font(fontname=MARKER_FONT, fontfile=str(PERMANENT_MARKER_PATH))
    if TANUKI_MAGIC_PATH.exists():
        page.insert_font(fontname=JAPANESE_FONT, fontfile=str(TANUKI_MAGIC_PATH))
    if AVERSA_PATH.exists():
        page.insert_font(fontname=PRICE_FONT, fontfile=str(AVERSA_PATH))
    for font_alias, font_path in CUSTOM_FONT_FILES.items():
        page.insert_font(fontname=font_alias, fontfile=str(font_path))


def deterministic_rng(seed: str) -> random.Random:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return random.Random(int(digest[:16], 16))


def fit_font_size(
    text: str,
    rect_width: float,
    fontname: str,
    max_size: float,
    min_size: float,
    tracking: float = 0.0,
) -> float:
    font = get_font(fontname)
    for size in range(int(max_size), int(min_size) - 1, -1):
        text_width = font.text_length(text, fontsize=size)
        if len(text) > 1:
            text_width += tracking * (len(text) - 1)
        if text_width <= rect_width:
            return float(size)
    return min_size


def draw_text_centered(
    page: fitz.Page,
    rect: fitz.Rect,
    text: str,
    fontname: str,
    fontsize: float,
    color: tuple[float, float, float],
    tracking: float = 0.0,
) -> None:
    font = get_font(fontname)
    text_width = font.text_length(text, fontsize=fontsize)
    if len(text) > 1:
        text_width += tracking * (len(text) - 1)
    baseline = centered_baseline(rect, fontname, fontsize)
    start_x = rect.x0 + ((rect.width - text_width) / 2.0)

    if tracking <= 0:
        page.insert_text(
            fitz.Point(start_x, baseline),
            text,
            fontsize=fontsize,
            color=color,
            **build_text_insert_kwargs(fontname),
        )
        return

    cursor_x = start_x
    for char in text:
        page.insert_text(
            fitz.Point(cursor_x, baseline),
            char,
            fontsize=fontsize,
            color=color,
            **build_text_insert_kwargs(fontname),
        )
        cursor_x += font.text_length(char, fontsize=fontsize) + tracking


def draw_brush_text_centered(
    page: fitz.Page,
    rect: fitz.Rect,
    text: str,
    fontname: str,
    fontsize: float,
    color: tuple[float, float, float],
    seed: str,
    style: BrushStyle,
) -> None:
    font = get_font(fontname)
    rng = deterministic_rng(seed)

    char_metrics: list[tuple[str, float, float, float, float]] = []
    for index, char in enumerate(text):
        size_scale = 1.0 + rng.uniform(-style.size_jitter, style.size_jitter)
        char_size = fontsize * size_scale
        char_width = font.text_length(char, fontsize=char_size)
        x_jitter = rng.uniform(-style.x_jitter, style.x_jitter)
        y_jitter = rng.uniform(-style.y_jitter, style.y_jitter)
        char_metrics.append((char, char_size, char_width, x_jitter, y_jitter))

    total_width = sum(item[2] for item in char_metrics)
    if len(char_metrics) > 1:
        total_width += style.tracking * (len(char_metrics) - 1)

    center_x = rect.x0 + (rect.width / 2.0)
    start_x = center_x - (total_width / 2.0)
    base_baseline = centered_baseline(rect, fontname, fontsize)
    shadow_color = mix_color(color, (0.02, 0.02, 0.02), 0.35)

    cursor_x = start_x
    half_width = total_width / 2.0 if total_width else 1.0

    for index, (char, char_size, char_width, x_jitter, y_jitter) in enumerate(char_metrics):
        char_center = (cursor_x - start_x) + (char_width / 2.0)
        slope_offset = ((char_center - half_width) / max(half_width, 1.0)) * (
            fontsize * style.slope
        )
        baseline = base_baseline + slope_offset + y_jitter
        x_pos = cursor_x + x_jitter

        for layer in range(style.stroke_layers - 1, 0, -1):
            offset_scale = layer / style.stroke_layers
            page.insert_text(
                fitz.Point(
                    x_pos - (offset_scale * style.stroke_strength),
                    baseline + (offset_scale * style.stroke_strength * 0.6),
                ),
                char,
                fontsize=char_size * (1.0 + (0.012 * offset_scale)),
                color=shadow_color,
                **build_text_insert_kwargs(fontname),
            )
            if index % 2 == 0:
                page.insert_text(
                    fitz.Point(
                        x_pos + (offset_scale * style.stroke_strength * 0.45),
                        baseline - (offset_scale * style.stroke_strength * 0.35),
                    ),
                    char,
                    fontsize=char_size * (1.0 + (0.008 * offset_scale)),
                    color=shadow_color,
                    **build_text_insert_kwargs(fontname),
                )

        page.insert_text(
            fitz.Point(x_pos, baseline),
            char,
            fontsize=char_size,
            color=color,
            **build_text_insert_kwargs(fontname),
        )
        cursor_x += char_width + style.tracking


def draw_brush_underline(
    page: fitz.Page,
    rect: fitz.Rect,
    text: str,
    color: tuple[float, float, float],
    seed: str,
) -> None:
    rng = deterministic_rng(f"{seed}-underline")
    width_ratio = 0.54 + rng.uniform(0.02, 0.08)
    line_width = rect.width * width_ratio
    start_x = rect.x0 + ((rect.width - line_width) / 2.0)
    baseline_y = rect.y1 - 10
    points = []
    segments = 7
    for index in range(segments + 1):
        progress = index / segments
        x_value = start_x + (line_width * progress)
        arc = math.sin(progress * math.pi) * rng.uniform(1.5, 4.0)
        y_value = baseline_y + rng.uniform(-2.5, 2.5) + arc
        points.append(fitz.Point(x_value, y_value))

    brush_color = mix_color(color, (0.02, 0.02, 0.02), 0.15)
    shape = page.new_shape()
    shape.draw_polyline(points)
    shape.finish(color=brush_color, width=4.0)

    shadow_points = [fitz.Point(point.x, point.y + 1.4) for point in points]
    shape.draw_polyline(shadow_points)
    shape.finish(color=mix_color(brush_color, (1.0, 1.0, 1.0), 0.18), width=2.0)
    shape.commit(overlay=True)


def centered_baseline(rect: fitz.Rect, fontname: str, fontsize: float) -> float:
    font = get_font(fontname)
    text_height = (font.ascender - font.descender) * fontsize
    return rect.y0 + ((rect.height - text_height) / 2.0) + (font.ascender * fontsize)


def resolve_page_fontname(fontname: str) -> str:
    if fontname in CUSTOM_FONT_FILES:
        return fontname
    if fontname == JAPANESE_FONT and not TANUKI_MAGIC_PATH.exists():
        return "helv"
    if fontname == PRICE_FONT and not AVERSA_PATH.exists():
        return "helv"
    if fontname == MARKER_FONT and not PERMANENT_MARKER_PATH.exists():
        return "helv"
    return fontname


def normalize_label(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return normalized.upper().strip()


def place_centered_image(
    page: fitz.Page,
    image_path: Path,
    rect: fitz.Rect,
    max_height_ratio: float = 0.9,
    scale_multiplier: float = 1.0,
    x_offset: float = 0.0,
    y_offset: float = 0.0,
) -> None:
    width_px, height_px = image_dimensions(image_path)
    aspect_ratio = width_px / height_px
    target_height = rect.height * max_height_ratio * scale_multiplier
    target_width = target_height * aspect_ratio

    center_x = rect.x0 + (rect.width / 2.0)
    center_y = rect.y0 + (rect.height / 2.0)
    x0 = center_x - (target_width / 2.0) + x_offset
    y0 = center_y - (target_height / 2.0) + y_offset
    image_rect = fitz.Rect(x0, y0, x0 + target_width, y0 + target_height)
    page.insert_image(image_rect, filename=str(image_path), overlay=True)


def format_price(raw_value: str) -> str:
    try:
        decimal_value = Decimal(str(raw_value).strip()).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Preco invalido: {raw_value!r}") from exc

    return f"{decimal_value:.2f}".replace(".", ",")


def sanitize_filename(product_name: str) -> str:
    normalized = unicodedata.normalize("NFC", product_name.strip())
    cleaned = re.sub(r'[\\/:*?"<>|]+', "_", normalized).strip(" .")
    if not cleaned:
        raise ValueError("Nome de produto vazio ou invalido para nome de arquivo.")
    return cleaned


def slugify_filename_part(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower().strip()
    normalized = re.sub(r"\s+", "_", normalized)
    normalized = re.sub(r"[^a-z0-9_-]+", "", normalized)
    normalized = normalized.strip("_-")
    if not normalized:
        raise ValueError("Valor invalido para nome de arquivo.")
    return normalized


def resolve_custom_font_alias(
    raw_value: str | None,
    default_alias: str,
    field_name: str,
) -> str:
    font_value = (raw_value or "").strip()
    if not font_value:
        return default_alias

    direct_path = Path(font_value)
    candidate_path = direct_path if direct_path.is_absolute() else FONTS_DIR / font_value
    if not candidate_path.exists() or not candidate_path.is_file():
        return default_alias

    alias_seed = slugify_filename_part(candidate_path.stem)
    alias = f"custom_{field_name}_{alias_seed}"
    CUSTOM_FONT_FILES[alias] = candidate_path
    return alias


def read_products(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required_headers = {
            "商品名",
            "produto",
            "variedade",
            "tipo",
            "origem",
            "preco",
            "cor_produto",
            "cor_variedade",
            "cor_tipo",
            "cor_origem",
            "cor_preco",
        }
        optional_font_headers = {
            "fonts_produto",
            "fonts_variedade",
            "fonts_tipo",
            "fonts_origem",
            "fonts_preco",
        }
        if not reader.fieldnames or not required_headers.issubset(reader.fieldnames):
            raise SystemExit(
                "CSV invalido. Cabecalhos esperados: "
                "produto,variedade,tipo,origem,preco,cor_produto,cor_variedade,"
                "cor_tipo,cor_origem,cor_preco"
            )

        rows = []
        for index, row in enumerate(reader, start=2):
            product = (row.get("produto") or "").strip()
            product_jp = (row.get("商品名") or "").strip()
            variedade = (row.get("variedade") or "").strip()
            tipo = (row.get("tipo") or "").strip()
            origem = (row.get("origem") or "").strip()
            price = (row.get("preco") or "").strip()
            if not product or not tipo or not price:
                raise SystemExit(
                    f"Linha {index} do CSV esta incompleta. "
                    "Cada linha precisa de produto, tipo e preco."
                )
            try:
                parsed_row = {
                    "_index": index - 2,
                    "produto": product,
                    "produto_jp": product_jp,
                    "variedade": variedade,
                    "tipo": tipo,
                    "origem": origem,
                    "preco": price,
                    "cor_produto": parse_color(row.get("cor_produto"), PRODUCT_COLOR),
                    "cor_variedade": parse_color(row.get("cor_variedade"), PRODUCT_COLOR),
                    "cor_tipo": parse_color(row.get("cor_tipo"), PRODUCT_COLOR),
                    "cor_origem": parse_color(row.get("cor_origem"), PRODUCT_COLOR),
                    "cor_preco": parse_color(row.get("cor_preco"), PRICE_COLOR),
                    "font_produto": resolve_custom_font_alias(
                        row.get("fonts_produto") if "fonts_produto" in reader.fieldnames else None,
                        MARKER_FONT,
                        "produto",
                    ),
                    "font_variedade": resolve_custom_font_alias(
                        row.get("fonts_variedade") if "fonts_variedade" in reader.fieldnames else None,
                        MARKER_FONT,
                        "variedade",
                    ),
                    "font_tipo": resolve_custom_font_alias(
                        row.get("fonts_tipo") if "fonts_tipo" in reader.fieldnames else None,
                        BOLD_FONT,
                        "tipo",
                    ),
                    "font_origem": resolve_custom_font_alias(
                        row.get("fonts_origem") if "fonts_origem" in reader.fieldnames else None,
                        REGULAR_FONT,
                        "origem",
                    ),
                    "font_preco": resolve_custom_font_alias(
                        row.get("fonts_preco") if "fonts_preco" in reader.fieldnames else None,
                        PRICE_FONT,
                        "preco",
                    ),
                }
            except ValueError as exc:
                raise SystemExit(f"Linha {index}: {exc}") from exc
            rows.append(parsed_row)

    if not rows:
        raise SystemExit("O CSV nao possui produtos para processar.")
    return rows


def draw_product(
    page: fitz.Page,
    product_name: str,
    color: tuple[float, float, float],
    fontname: str,
    layout: Layout,
) -> None:
    text = product_name.strip().upper()
    fontsize = fit_font_size(
        text=text,
        rect_width=layout.product_rect.width,
        fontname=fontname,
        max_size=layout.product_max_size * 1.15,
        min_size=24,
        tracking=0.6,
    )
    draw_text_centered(
        page,
        layout.product_rect,
        text,
        resolve_page_fontname(fontname),
        fontsize,
        color,
        tracking=0.6,
    )


def draw_variedade(
    page: fitz.Page,
    variedade: str,
    color: tuple[float, float, float],
    fontname: str,
    layout: Layout,
) -> None:
    if not variedade.strip():
        return

    text = variedade.strip().upper()
    fontsize = fit_font_size(
        text=text,
        rect_width=layout.variedade_rect.width,
        fontname=fontname,
        max_size=layout.product_max_size * 1.15,
        min_size=18,
    )
    draw_text_centered(
        page,
        layout.variedade_rect,
        text,
        resolve_page_fontname(fontname),
        fontsize,
        color,
        tracking=0.6,
    )


def draw_tipo(
    page: fitz.Page,
    tipo: str,
    variedade: str,
    color: tuple[float, float, float],
    fontname: str,
    layout: Layout,
) -> None:
    text = tipo.strip().upper()
    has_variedade = bool(variedade.strip())
    rect = layout.tipo_rect if has_variedade else layout.tipo_expanded_rect
    if normalize_label(text) == "ORGANICO" and ORGANICO_PNG_PATH.exists():
        place_centered_image(
            page,
            ORGANICO_PNG_PATH,
            rect,
            max_height_ratio=0.82,
            scale_multiplier=2.0,
            x_offset=14.2,
            y_offset=-14.2,
        )
        return

    max_size = (
        layout.tipo_max_size * 1.3 if has_variedade else layout.tipo_expanded_max_size
    )
    min_size = 22 if has_variedade else 34
    fontsize = fit_font_size(
        text=text,
        rect_width=rect.width,
        fontname=fontname,
        max_size=max_size * (1.12 if has_variedade else 1.22),
        min_size=min_size,
        tracking=TIPO_BRUSH_STYLE.tracking,
    )
    draw_brush_text_centered(
        page,
        rect,
        text,
        fontname,
        fontsize,
        color,
        seed=f"tipo:{text}:{has_variedade}",
        style=TIPO_BRUSH_STYLE,
    )
    draw_brush_underline(page, rect, text, color, seed=f"tipo:{text}:{has_variedade}")


def draw_origem(
    page: fitz.Page,
    origem: str,
    color: tuple[float, float, float],
    fontname: str,
    layout: Layout,
) -> None:
    if not origem.strip():
        return

    if normalize_label(origem) == "PRODUCAO PROPRIA" and ORIGEM_PNG_PATH.exists():
        place_centered_image(
            page,
            ORIGEM_PNG_PATH,
            layout.origem_rect,
            max_height_ratio=0.8,
            scale_multiplier=5.0,
        )
        return

    fontsize = fit_font_size(
        text=origem,
        rect_width=layout.origem_rect.width,
        fontname=fontname,
        max_size=layout.origem_size,
        min_size=14,
    )
    draw_text_centered(
        page,
        layout.origem_rect,
        origem,
        resolve_page_fontname(fontname),
        fontsize,
        color,
    )


def image_dimensions(image_path: Path) -> tuple[int, int]:
    pixmap = fitz.Pixmap(str(image_path))
    return pixmap.width, pixmap.height


def place_hare_logo(
    page: fitz.Page,
    _decimal_rect: fitz.Rect,
    layout: Layout,
) -> None:
    return


def place_sisorg_logo(
    page: fitz.Page,
    integer_rect: fitz.Rect,
    layout: Layout,
) -> None:
    width_px, height_px = image_dimensions(SISORG_LOGO_PATH)
    aspect_ratio = width_px / height_px

    target_height = min(integer_rect.height * 0.47, layout.sisorg_max_rect.height, 131.8)
    target_width = target_height * aspect_ratio
    x1 = integer_rect.x0 - layout.sisorg_gap
    x0 = max(layout.sisorg_max_rect.x0, x1 - target_width)

    if x0 < layout.sisorg_max_rect.x0:
        x0 = layout.sisorg_max_rect.x0
        target_width = x1 - x0
        target_height = target_width / aspect_ratio

    y0 = integer_rect.y0 + ((integer_rect.height - target_height) / 2.0)
    logo_rect = fitz.Rect(x0, y0, x0 + target_width, y0 + target_height)

    if logo_rect.intersects(
        fitz.Rect(layout.price_rect.x0, layout.price_rect.y0, layout.price_reserved_left, layout.price_rect.y1)
    ):
        shift = layout.price_reserved_left - logo_rect.x1
        logo_rect = fitz.Rect(
            logo_rect.x0 + shift,
            logo_rect.y0,
            logo_rect.x1 + shift,
            logo_rect.y1,
        )

    page.insert_image(logo_rect, filename=str(SISORG_LOGO_PATH), overlay=True)


def draw_japanese_name_vertical(
    page: fitz.Page,
    japanese_name: str,
    decimal_rect: fitz.Rect,
    color: tuple[float, float, float],
    layout: Layout,
) -> None:
    text = japanese_name.strip()
    if not text:
        return

    segments = [segment.strip() for segment in text.split("・") if segment.strip()]
    if not segments:
        segments = [text.replace("・", "").strip()]
    columns = [[char for char in segment if char.strip()] for segment in segments[:2]]
    columns = [column for column in columns if column]
    if not columns:
        return

    fontname = JAPANESE_FONT
    font = get_font(fontname)
    top_bound = layout.origem_rect.y1 + 8.0
    bottom_bound = layout.price_rect.y0 + (layout.price_rect.height / 2.0)
    available_height = bottom_bound - top_bound
    if available_height <= 20:
        available_height = max((layout.price_rect.y0 + (layout.price_rect.height / 2.0)) - top_bound, 40.0)

    fontsize = 28.0
    while fontsize > 10:
        char_height = (font.ascender - font.descender) * fontsize
        longest_column = max(len(column) for column in columns)
        total_height = char_height * longest_column
        if total_height <= available_height:
            break
        fontsize -= 1

    char_height = (font.ascender - font.descender) * fontsize
    x_center = (decimal_rect.x0 + (decimal_rect.width / 2.0)) + 113.4
    column_gap = fontsize * 0.7
    column_centers = [x_center]
    if len(columns) == 2:
        column_centers = [
            x_center + ((column_gap + fontsize) / 2.0),
            x_center - ((column_gap + fontsize) / 2.0),
        ]

    for column_index, glyphs in enumerate(columns):
        total_height = char_height * len(glyphs)
        vertical_center = top_bound + (available_height / 2.0)
        start_y = vertical_center - (total_height / 2.0)
        current_x_center = column_centers[column_index]

        for index, char in enumerate(glyphs):
            char_width = font.text_length(char, fontsize=fontsize)
            char_y0 = start_y + (index * char_height)
            baseline = char_y0 + (font.ascender * fontsize)
            page.insert_text(
                fitz.Point(current_x_center - (char_width / 2.0), baseline),
                char,
                fontsize=fontsize,
                color=color,
                **build_text_insert_kwargs(fontname),
            )


def draw_price(
    page: fitz.Page,
    price_value: str,
    japanese_name: str,
    color: tuple[float, float, float],
    fontname: str,
    show_logos: bool,
    layout: Layout,
) -> None:
    formatted_price = format_price(price_value)
    integer_part, decimal_part = formatted_price.split(",")
    decimal_text = f",{decimal_part}"

    integer_font = get_font(fontname)
    decimal_font = get_font(fontname)

    integer_width = integer_font.text_length(
        integer_part, fontsize=layout.price_integer_size
    )
    decimal_width = decimal_font.text_length(
        decimal_text, fontsize=layout.price_decimal_size
    )
    total_width = integer_width + layout.price_gap + decimal_width

    start_x = layout.price_rect.x0 + ((layout.price_rect.width - total_width) / 2.0)
    integer_rect = fitz.Rect(
        start_x,
        layout.price_rect.y0,
        start_x + integer_width,
        layout.price_rect.y1,
    )
    decimal_rect = fitz.Rect(
        integer_rect.x1 + layout.price_gap - 14.2,
        layout.price_rect.y0 + layout.decimal_drop,
        integer_rect.x1 + layout.price_gap - 14.2 + decimal_width,
        layout.price_rect.y1,
    )

    integer_baseline = centered_baseline(
        integer_rect, fontname, layout.price_integer_size
    )
    decimal_baseline = centered_baseline(
        decimal_rect, fontname, layout.price_decimal_size
    )
    page.insert_text(
        fitz.Point(integer_rect.x0, integer_baseline),
        integer_part,
        fontsize=layout.price_integer_size,
        color=color,
        **build_text_insert_kwargs(fontname),
    )
    page.insert_text(
        fitz.Point(decimal_rect.x0, decimal_baseline),
        decimal_text,
        fontsize=layout.price_decimal_size,
        color=color,
        **build_text_insert_kwargs(fontname),
    )

    draw_japanese_name_vertical(page, japanese_name, decimal_rect, color, layout)

    if show_logos:
        place_sisorg_logo(page, integer_rect, layout)
        place_hare_logo(page, decimal_rect, layout)


def should_show_organic_logos(tipo: str) -> bool:
    normalized = unicodedata.normalize("NFKD", tipo).encode("ascii", "ignore").decode("ascii")
    normalized = normalized.upper()
    return "ORGANICO" in normalized


def build_output_filename(row: dict[str, object], data: str) -> str:
    produto = slugify_filename_part(str(row["produto"]))
    if str(row["variedade"]).strip():
        produto = f"{produto}_{slugify_filename_part(str(row['variedade']))}"
    tipo_raw = str(row["tipo"]).strip()
    tipo = "org" if "ORGANICO" in normalize_label(tipo_raw) else slugify_filename_part(tipo_raw)
    preco = format_price(str(row["preco"])).replace(",", "-")
    return f"{produto}_{tipo}_{preco}_{data}.pdf"


def build_combined_output_filename(data: str) -> str:
    return f"__PRODUTOS_TODOS_TODOS_{data}.pdf"


class SelectionError(Exception):
    pass


def match_key(value: str) -> str:
    # "｜" e usado no CSV como traco de prolongamento na escrita vertical.
    value = unicodedata.normalize("NFKC", value).replace("｜", "ー").replace("|", "ー")
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = unicodedata.normalize("NFC", value)
    return re.sub(r"\s+", " ", value).strip().upper()


def row_keys(row: dict[str, object]) -> set[str]:
    produto = str(row["produto"])
    variedade = str(row["variedade"])
    keys = {match_key(produto), match_key(f"{produto} {variedade}")}
    if str(row["produto_jp"]).strip():
        keys.add(match_key(str(row["produto_jp"])))
        keys.add(match_key(str(row["produto_jp"]).replace("・", "")))
    return keys


def describe_row(row: dict[str, object]) -> str:
    name = f"{row['produto']} {row['variedade']}".strip()
    return f"{name} / {row['produto_jp']} / {format_price(str(row['preco']))}"


def parse_item_spec(spec: str) -> tuple[str, str | None]:
    name, sep, price = spec.rpartition("=")
    if not sep:
        return spec.strip(), None
    price = price.strip().replace(",", ".")
    format_price(price)
    return name.strip(), price


def select_products(
    products: list[dict[str, object]],
    item_specs: list[str],
) -> list[dict[str, object]]:
    selected = []
    for spec in item_specs:
        try:
            name, price = parse_item_spec(spec)
        except ValueError as exc:
            raise SelectionError(f"{spec!r}: {exc}") from exc
        key = match_key(name)
        matches = [row for row in products if key in row_keys(row)]
        if not matches:
            raise SelectionError(f"{name!r}: produto nao encontrado no CSV")

        # Linhas repetidas do mesmo produto (ex.: ALFACE 5 e 6) usam o mesmo layout.
        groups = {match_key(f"{row['produto']} {row['variedade']}") for row in matches}
        if len(groups) > 1:
            options = "\n".join(f"- {describe_row(row)}" for row in matches)
            raise SelectionError(f"{name!r} e ambiguo. Candidatos:\n{options}")
        if price is None:
            prices = {format_price(str(row["preco"])) for row in matches}
            if len(prices) > 1:
                options = "\n".join(f"- {describe_row(row)}" for row in matches)
                raise SelectionError(f"{name!r} tem mais de um preco no CSV. Informe o preco:\n{options}")

        row = dict(matches[0])
        if price is not None:
            row["preco"] = price
        selected.append(row)
    return selected


def read_csv_raw(csv_path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write_csv_raw(csv_path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    tmp_path = csv_path.with_suffix(".tmp")
    with tmp_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    tmp_path.replace(csv_path)


def csv_price(price: str) -> str:
    # No CSV os precos inteiros ficam sem decimais ("8"); os demais com ponto ("12.50").
    formatted = format_price(price).replace(",", ".")
    return formatted[:-3] if formatted.endswith(".00") else formatted


def save_prices(
    csv_path: Path,
    products: list[dict[str, object]],
    selected: list[dict[str, object]],
) -> list[str]:
    fieldnames, raw_rows = read_csv_raw(csv_path)
    changes = []
    for row in selected:
        group = match_key(f"{row['produto']} {row['variedade']}")
        same = [p for p in products if match_key(f"{p['produto']} {p['variedade']}") == group]
        new_price = format_price(str(row["preco"]))
        if any(format_price(str(p["preco"])) == new_price for p in same):
            continue
        if len(same) > 1:
            options = "\n".join(f"- linha {int(p['_index']) + 2}: {describe_row(p)}" for p in same)
            raise SelectionError(
                f"{describe_row(row)}: o produto tem mais de uma linha no CSV; "
                f"nao sei qual atualizar. Edite o CSV:\n{options}"
            )
        raw = raw_rows[int(same[0]["_index"])]
        changes.append(f"{describe_row(same[0])} -> {new_price}")
        raw["preco"] = csv_price(str(row["preco"]))
    if changes:
        write_csv_raw(csv_path, fieldnames, raw_rows)
    return changes


def most_common(values: list[str]) -> str:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return max(counts, key=counts.get) if counts else ""


def add_products(csv_path: Path, products: list[dict[str, object]], specs: list[str]) -> list[str]:
    fieldnames, raw_rows = read_csv_raw(csv_path)
    # Campos de estilo nao informados copiam o valor mais comum do CSV (tipo, origem, cores, fontes).
    style_fields = [f for f in fieldnames if f not in {"商品名", "produto", "variedade", "preco"}]
    defaults = {f: most_common([r.get(f) or "" for r in raw_rows]) for f in style_fields}
    existing = {match_key(f"{p['produto']} {p['variedade']}") for p in products}
    added_names = []
    for spec in specs:
        try:
            data = json.loads(spec)
        except json.JSONDecodeError as exc:
            raise SelectionError(f"--add precisa ser JSON: {spec!r}") from exc
        if not isinstance(data, dict):
            raise SelectionError(f"--add precisa ser um objeto JSON: {spec!r}")
        data = {("商品名" if k == "produto_jp" else k): str(v) for k, v in data.items()}
        unknown = set(data) - set(fieldnames)
        if unknown:
            raise SelectionError(f"--add: campos desconhecidos {sorted(unknown)}. Campos: {fieldnames}")
        produto = data.get("produto", "").strip().upper()
        if not produto or not data.get("preco", "").strip():
            raise SelectionError(f"--add precisa de produto e preco: {spec!r}")
        variedade = data.get("variedade", "").strip().upper()
        key = match_key(f"{produto} {variedade}")
        if key in existing:
            raise SelectionError(f"{produto} {variedade}".strip() + " ja existe no CSV. Use --item ... --save para mudar o preco.")
        try:
            preco = csv_price(data["preco"].replace(",", "."))
        except ValueError as exc:
            raise SelectionError(f"--add {produto}: {exc}") from exc
        raw = {f: "" for f in fieldnames}
        raw.update(defaults)
        raw.update(data)
        raw.update({"produto": produto, "variedade": variedade, "preco": preco})
        raw_rows.append(raw)
        existing.add(key)
        added_names.append(f"{produto} {variedade}".strip())
    write_csv_raw(csv_path, fieldnames, raw_rows)
    return added_names


def catalog(products: list[dict[str, object]]) -> list[dict[str, str]]:
    return [
        {
            "produto": str(row["produto"]).strip(),
            "variedade": str(row["variedade"]),
            "produto_jp": str(row["produto_jp"]),
            "preco": format_price(str(row["preco"])),
        }
        for row in products
    ]


def build_combined_pdf(input_paths: list[Path], output_path: Path) -> None:
    combined_doc = fitz.open()
    try:
        for input_path in input_paths:
            source_doc = fitz.open(input_path)
            try:
                combined_doc.insert_pdf(source_doc)
            finally:
                source_doc.close()
        # garbage=4 junta fontes e template repetidos em cada pagina (316 MB -> poucos MB).
        combined_doc.save(output_path, garbage=4, deflate=True)
    finally:
        combined_doc.close()


def build_poster(row: dict[str, object], output_path: Path) -> None:
    template_doc = fitz.open(TEMPLATE_PATH)
    output_doc = fitz.open()

    try:
        template_page = template_doc[0]
        page = output_doc.new_page(
            width=template_page.rect.width,
            height=template_page.rect.height,
        )
        page.show_pdf_page(page.rect, template_doc, 0)
        register_page_fonts(page)

        draw_product(page, str(row["produto"]), row["cor_produto"], row["font_produto"], LAYOUT)
        draw_variedade(
            page,
            str(row["variedade"]),
            row["cor_variedade"],
            row["font_variedade"],
            LAYOUT,
        )
        draw_tipo(
            page,
            str(row["tipo"]),
            str(row["variedade"]),
            row["cor_tipo"],
            row["font_tipo"],
            LAYOUT,
        )
        draw_origem(
            page,
            str(row["origem"]),
            row["cor_origem"],
            row["font_origem"],
            LAYOUT,
        )
        draw_price(
            page,
            str(row["preco"]),
            str(row["produto_jp"]),
            row["cor_preco"],
            row["font_preco"],
            should_show_organic_logos(str(row["tipo"])),
            LAYOUT,
        )

        # Mantem so os glifos usados (cerca de 7,5 MB -> 2,4 MB por cartaz; Telegram aceita ate 50 MB).
        output_doc.subset_fonts()
        output_doc.save(output_path, garbage=4, deflate=True)
    finally:
        output_doc.close()
        template_doc.close()


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gera cartazes A4 em PDF a partir de data/produtos.csv.",
    )
    parser.add_argument(
        "--item",
        action="append",
        default=[],
        metavar="PRODUTO[=PRECO]",
        help=(
            "Gera so este produto (repetivel). Aceita o nome em portugues, "
            "'produto variedade' ou o nome em japones (商品名). "
            "PRECO substitui o preco do CSV, ex.: --item AVOCADO=12 --item 'ALFACE=6,50'"
        ),
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Grava no CSV os precos informados em --item (so quando o produto tem uma linha no CSV).",
    )
    parser.add_argument(
        "--add",
        action="append",
        default=[],
        metavar="JSON",
        help=(
            "Acrescenta um produto novo ao CSV e gera o cartaz (repetivel). "
            'Ex.: --add \'{"produto": "ABACAXI", "produto_jp": "パイナップル", "preco": "12"}\'. '
            "Campos omitidos (tipo, origem, cores, fontes) copiam o valor mais comum do CSV."
        ),
    )
    parser.add_argument("--list", action="store_true", help="Lista os produtos do CSV em JSON e sai.")
    parser.add_argument("--date", default=date.today().strftime("%Y%m%d"), help="Data no nome dos arquivos (AAAAMMDD). Padrao: hoje.")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR, help="Pasta de saida. Padrao: output/")
    parser.add_argument("--csv", type=Path, default=CSV_PATH, help="CSV de entrada. Padrao: data/produtos.csv")
    args = parser.parse_args(argv)
    if not re.fullmatch(r"\d{8}", args.date):
        parser.error("--date precisa ser AAAAMMDD")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    require_assets()
    products = read_products(args.csv)

    if args.list:
        print(json.dumps(catalog(products), ensure_ascii=False, indent=1))
        return 0

    if args.save and not args.item:
        print("--save precisa de --item PRODUTO=PRECO", file=sys.stderr)
        return 2

    if args.item or args.add:
        try:
            selected = select_products(products, args.item)
            if args.save:
                for change in save_prices(args.csv, products, selected):
                    print(f"Preco atualizado no CSV: {change}")
            if args.add:
                added = add_products(args.csv, products, args.add)
                products = read_products(args.csv)
                selected += select_products(products, added)
                for name in added:
                    print(f"Produto acrescentado ao CSV: {name}")
        except SelectionError as exc:
            print(exc, file=sys.stderr)
            return 2
        products = selected

    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_paths: list[Path] = []

    for row in products:
        output_path = output_dir / build_output_filename(row, args.date)
        build_poster(row, output_path)
        if output_path not in generated_paths:
            generated_paths.append(output_path)

    combined_output_path = output_dir / build_combined_output_filename(args.date)
    build_combined_pdf(generated_paths, combined_output_path)

    print(f"{len(generated_paths) + 1} arquivo(s) gerado(s) em {output_dir}")
    for path in generated_paths:
        print(f"- {path.name}")
    print(f"Consolidado: {combined_output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
