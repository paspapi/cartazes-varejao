# Sessao Atual

Este projeto gera cartazes A4 em PDF a partir do template CEAGESP usando `scripts/generate.py`.

## Arquivos principais

- `scripts/generate.py`: pipeline principal
- `template/ceagesp_template.pdf`: template base
- `data/produtos.csv`: entrada
- `output/`: PDFs gerados
- `run_generate.sh`: executa usando `.venv`
- `run_generate_windows.bat`: launcher para Windows via WSL
- `README.md`: instrucoes de uso

## Ambiente

- O projeto espera `.venv/` na raiz.
- Dependencia principal: `PyMuPDF` (`fitz`)
- Execucao recomendada:
  - `bash run_generate.sh`
  - ou `source .venv/bin/activate && python scripts/generate.py`
  - ou execute `run_generate_windows.bat` no Windows

## Assets usados no layout

- `assets/sisorg.png`
- `assets/tipo-organico.png`
- `assets/origem-producao propria.png`
- `assets/fonts/PermanentMarker-Regular.ttf`
- `assets/fonts/Aversa Vectors.otf`

Observacao:
- `hare.png` continua no projeto, mas o logo do sol foi desativado no layout atual.

## CSV esperado

Cabecalho:

```csv
produto,variedade,tipo,origem,preco,cor_produto,cor_variedade,cor_tipo,cor_origem,cor_preco
```

Cores aceitas:

- nomes: `preto`, `branco`, `verde`, `azul`, `vermelho`
- hexadecimal: `#RRGGBB`

## Regras implementadas

- `produto`: texto com `Permanent Marker`
- `variedade`: mesma fonte do produto
- `tipo`: se o texto normalizado for `ORGANICO`, usa PNG `assets/tipo-organico.png`
- `origem`: se o texto normalizado for `PRODUCAO PROPRIA`, usa PNG `assets/origem-producao propria.png`
- `preco`: usa `Aversa Vectors.otf`; fallback `helv`
- `sisorg`: aparece apenas quando `tipo` contem `ORGANICO`
- `hare`: desativado

## Nome dos arquivos

Individuais:

```text
<produto>_<tipo>_<preco>_<data>.pdf
```

Regras:

- `produto`: minusculo, sem acento
- `tipo`: `org` se contiver `orgânico`
- `preco`: `6,00 -> 6-00`
- `data`: fixada no codigo como `20260424`

Consolidado:

```text
produtos_todos_todos_20260424.pdf
```

## Estado atual do layout

O layout foi ajustado manualmente varias vezes. Os numeros atuais em `Layout` sao intencionais e nao devem ser trocados sem comparar PDF gerado:

- `product_rect = fitz.Rect(236, 184, 660, 251)`
- `variedade_rect = fitz.Rect(262, 256, 660, 304)`
- `tipo_rect = fitz.Rect(184, 334, 660, 382)`
- `tipo_expanded_rect = fitz.Rect(184, 266, 660, 382)`
- `origem_rect = fitz.Rect(228, 388.8, 660, 417.8)`
- `price_rect = fitz.Rect(205, 430, 705, 835)`
- `sisorg_max_rect = fitz.Rect(85, 590, 260, 770)`

Escalas atuais relevantes:

- `product_max_size = 60`
- `price_integer_size = 334.8`
- `price_decimal_size = 132`
- `price_gap = 2`
- decimal deslocado `14.2 pt` para a esquerda
- `sisorg` reduzido e alinhado verticalmente ao preco

## Funcoes principais

- `read_products()`: valida CSV e converte cores
- `draw_product()`
- `draw_variedade()`
- `draw_tipo()`
- `draw_origem()`
- `draw_price()`
- `place_sisorg_logo()`
- `build_output_filename()`
- `build_combined_pdf()`

## Cuidados ao continuar

- Nao mexer no template CEAGESP.
- Fazer apenas sobreposicao.
- `.sh` sozinho nao e bom launcher para o Desktop do Windows.
- O launcher de Windows atual e `run_generate_windows.bat`.
- O `.bat` usa caminho absoluto WSL:
  - `/home/anando/projects/cartazes-varejao`
- Se o projeto for movido de pasta, atualizar o caminho dentro do `.bat`.
- Se for ajustar layout, mudar poucos valores por vez e comparar PDF.
- Se os PNGs nao forem usados, verificar:
  - nomes exatos dos arquivos em `assets/`
  - normalizacao via `normalize_label()`
- Se a fonte do preco falhar, checar `assets/fonts/Aversa Vectors.otf`.
- Se precisar reativar o sol, hoje a funcao `place_hare_logo()` retorna imediatamente.
