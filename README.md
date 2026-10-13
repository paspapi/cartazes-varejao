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
├── .venv/
├── run_generate_windows.bat
└── run_generate.sh
```

## Requisitos

- Python 3.10+
- Ambiente virtual `.venv`
- PyMuPDF instalado dentro do `.venv`

## Ambiente `.venv`

Se o ambiente virtual ainda nao existir:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install pymupdf
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

Opcao 1:

```bash
source .venv/bin/activate
python scripts/generate.py
```

Opcao 2:

```bash
bash run_generate.sh
```

Opcao 3:

No Windows, execute `run_generate_windows.bat`.

Observacoes importantes:

- Se voce estiver no Windows com WSL, o launcher correto e o `.bat`.
- O `.bat` chama o WSL, entra no projeto, ativa `.venv` e roda `scripts/generate.py`.
- Voce pode copiar `run_generate_windows.bat` para a Area de Trabalho do Windows.
- Se mover o projeto de pasta no WSL, atualize o caminho dentro do `.bat`.

## Saida

Os arquivos sao gravados em `output/`.

Padrao dos PDFs individuais:

```text
<produto>_<tipo>_<preco>_<data>.pdf
```

Exemplo:

```text
alface_org_6-00_20260424.pdf
```

Padrao do PDF consolidado:

```text
produtos_todos_todos_20260424.pdf
```

## Observacoes

- O script nao altera o template original.
- O layout atual usa:
  - `PermanentMarker-Regular.ttf` no produto
  - `Aversa Vectors.otf` no preco, quando disponivel
  - PNGs para `tipo-organico` e `origem-producao propria`
- O consolidado junta todos os PDFs individuais gerados na mesma execucao.
- Para Windows com WSL, prefira `run_generate_windows.bat`.
