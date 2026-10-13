# Cartazes Varejao

Gerador de cartazes A4 em PDF usando o template oficial da CEAGESP.

O projeto lê `data/produtos.csv`, aplica o layout definido em `scripts/generate.py` e gera:

- 1 PDF por produto em `output/`
- 1 PDF consolidado com todos os cartazes

## Estrutura

```text
cartazes-varejao/
├── assets/
│   ├── fonts/
│   │   ├── Aversa Vectors.otf
│   │   └── PermanentMarker-Regular.ttf
│   ├── hare.png
│   ├── origem-producao propria.png
│   ├── sisorg.png
│   └── tipo-organico.png
├── data/
│   └── produtos.csv
├── output/
├── scripts/
│   └── generate.py
├── template/
│   └── ceagesp_template.pdf
├── tests/
├── .venv/
├── requirements.txt
├── gerar_cartazes.bat
└── run_generate.sh
```

## Requisitos

- Python 3.10+
- Ambiente virtual `.venv`
- PyMuPDF (versao em `requirements.txt`) instalado dentro do `.venv`

## Ambiente `.venv`

Se o ambiente virtual ainda nao existir:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Se o `.venv` ja existir:

```bash
source .venv/bin/activate
```

## Assets obrigatorios

Os arquivos abaixo precisam existir:

- `template/ceagesp_template.pdf`
- `assets/hare.png`
- `assets/sisorg.png`
- `assets/tipo-organico.png`
- `assets/origem-producao propria.png`
- `assets/fonts/PermanentMarker-Regular.ttf`
- `assets/fonts/DejaVuSans.ttf` e `DejaVuSans-Bold.ttf` (incluidas no projeto; licenca em `DejaVu-LICENSE.txt`)

Opcional:

- `assets/fonts/Aversa Vectors.otf`

Se `Aversa Vectors.otf` nao existir, o preco usa fallback para `helv`.

## CSV de entrada

Arquivo: `data/produtos.csv`

Cabecalho esperado:

```csv
produto,variedade,tipo,origem,preco,cor_produto,cor_variedade,cor_tipo,cor_origem,cor_preco
```

Exemplo:

```csv
produto,variedade,tipo,origem,preco,cor_produto,cor_variedade,cor_tipo,cor_origem,cor_preco
Alface,Crespa,Orgânico,Produção própria,6.00,preto,preto,verde,preto,preto
Rúcula,,Orgânico,Produção própria,7.00,preto,,verde,preto,preto
```

## Cores aceitas

- nomes simples: `preto`, `branco`, `verde`, `azul`, `vermelho`
- hexadecimal: `#RRGGBB`

## Como executar

Linux:

```bash
bash run_generate.sh                       # todos os produtos do CSV
bash run_generate.sh --item AVOCADO=12     # so alguns produtos
```

Windows (Python nativo, sem WSL): dar dois cliques em `gerar_cartazes.bat`. Na primeira vez ele cria `.venv` e instala o PyMuPDF. Precisa do Python 3 (`winget install Python.Python.3.12`).

### Opcoes

- `--item PRODUTO[=PRECO]` (repetivel): gera so estes produtos. Aceita o nome em portugues (sem diferenciar acentos e maiusculas), `produto variedade` (ex.: `BROCOLIS NINJA`) ou o `商品名` (ex.: `アボカド`). `PRECO` substitui o preco do CSV (`12`, `12.5` ou `12,50`)
  - Se o nome casar com mais de um produto (ex.: `バナナ`) ou se o produto tiver mais de um preco no CSV sem preco informado (ex.: `ALFACE`), sai com codigo 2 e lista os candidatos
- `--list`: lista os produtos do CSV em JSON
- `--date AAAAMMDD`: data no nome dos arquivos (padrao: hoje)
- `--output-dir`, `--csv`: outra pasta de saida / outro CSV

O CSV nao e alterado: o preco de `--item` vale so para aquela geracao.

## Testes

```bash
python -m pip install -r requirements.txt pytest
python -m pytest -q
```

## Saida

Os arquivos sao gravados em `output/`.

Padrao dos PDFs individuais:

```text
<produto>[_<variedade>]_<tipo>_<preco>_<data>.pdf
```

Exemplo:

```text
alface_org_6-00_20260424.pdf
```

Padrao do PDF consolidado:

```text
__PRODUTOS_TODOS_TODOS_<data>.pdf
```

## Observacoes

- O script nao altera o template original.
- O layout atual usa:
  - `PermanentMarker-Regular.ttf` no produto
  - `Aversa Vectors.otf` no preco, quando disponivel
  - PNGs para `tipo-organico` e `origem-producao propria`
- O consolidado junta todos os PDFs individuais gerados na mesma execucao.
