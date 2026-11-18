# respira-rio

Análise do impacto da poluição industrial na qualidade do ar em Santa Cruz,
Zona Oeste, Rio de Janeiro (coordenadas: -22.9189, -43.6853).

## O que este projeto faz

Compara a qualidade do ar em dois períodos:

| Período | Datas | O que representa |
|---------|-------|-----------------|
| **Pré-fábrica** | Jan 2008 → Mai 2010 | Linha de base (antes da instalação industrial) |
| **Pós-fábrica** | Jun 2010 → 2025 | Período de exposição à poluição industrial |

O marco de corte é **2010-06-01** (exclusivo: tudo antes dessa data é "pré").

Variáveis analisadas: **PM2.5**, **PM10** e **SO₂** (dióxido de enxofre).

* **PM2.5**: Partículas finas em suspensão (com diâmetro inferior a 2,5 micrômetros) que conseguem ultrapassar as defesas pulmonares e entrar diretamente na corrente sanguínea.

* **PM10**: Partículas inaláveis (com diâmetro inferior a 10 micrômetros) que ficam retidas nas vias aéreas superiores, causando irritação e problemas respiratórios.  
​
* **SO₂**(Dióxido de Enxofre): Um gás poluente e irritante, altamente associado a emissões de processos industriais pesados e queima de carvão ou derivados.

---

## O que os dados mostram (resultado atual)

| Variável | Média Pré | Média Pós | P95 Pré | P95 Pós | p-value | Conclusão |
|----------|-----------|-----------|---------|---------|---------|-----------|
| PM2.5 | 22.69 | 23.02 | 52.19 | 52.85 | 0.768 | **Sem mudança significativa** |
| PM10 | 32.57 | 33.16 | 72.82 | 74.23 | 0.576 | **Sem mudança significativa** |
| SO₂ | 8.46 | 7.85 | 18.47 | 16.79 | **0.003** | **Melhora significativa** |

**Conclusão honesta:** Com o CAMS EAC4, **não é possível detectar** um impacto
significativo da fábrica. O SO2 até melhorou (p=0.003). PM2.5 e PM10
permaneceram estáveis.

---

## Por que o CAMS EAC4 NÃO funciona para este projeto

### O problema: resolução espacial

#### O que são as coordenadas

Toda a localização na Terra é definida por **2 números**:

- **Latitude** (N/S): distância angular ao Equador. 0° = Equador.
  Sul → negativo.
- **Longitude** (L/O): distância angular ao Meridiano de Greenwich. 0° = Londres.
  Oeste → negativo.

### Dois formatos de escrita

| Formato | Exemplo | Onde aparece |
|---------|---------|-------------|
| **DMS** (Graus, Minutos, Segundos) | 22°55′13″S, 43°41′06″W | Wikipedia, GPS, cartas náuticas |
| **Decimal** | -22.92028, -43.68500 | Python, xarray, APIs |

O nosso projeto usa **decimal** (é o formato que o `xarray` e a API do ADS esperam).

### Como converter DMS → Decimal

A fórmula é simples:

```
Decimal = Graus + Minutos/60 + Segundos/3600
```

Se for **Sul** (latitude) ou **Oeste** (longitude) → **negativo**.

#### Exemplo: Santa Cruz

**Latitude: 22°55′13″S**

```
22 + 55/60 + 13/3600
= 22 + 0.91667 + 0.00361
= 22.92028
→ Sul → -22.92028
```

**Longitude: 43°41′06″W**

```
43 + 41/60 + 6/3600
= 43 + 0.68333 + 0.00167
= 43.68500
→ Oeste → -43.68500
```

### Por que o grid point do CAMS está a ~50 km?

As nossas coordenadas são exatas: `-22.9189, -43.6853` (Santa Cruz).
Mas o CAMS EAC4 tem resolução de **0.75°** — cada "célula" do grid
representa ~50 km × 50 km. O grid point mais próximo é
`lat=-23.25, lon=-43.50`, que é a célula que **contém** Santa Cruz,
mas cujo centro está a ~50 km. É como se a tua casa estivesse num
quadradão de 50 km e o "termómetro" estivesse no centro do quadradão.

O CAMS EAC4 é um **modelo global** de transporte atmosférico com resolução
de **0.75° (~50 km)**. Isto significa:

1. **O grid point mais próximo** de Santa Cruz (-22.9189, -43.6853) é
   `lat=-23.25, lon=-43.50` — a **~50 km** do local real.
2. **Uma fábrica pontual** (uma chaminé, um forno) é **invisível** a essa
   escala. O modelo calcula a **média de toda a célula de 50×50 km**.
3. **Sem ponto de controle**, não é possível isolar o efeito da fábrica
   do efeito regional (clima, tráfego, outras indústrias).

### Analogia

Imagina que você quer medir a temperatura de uma casa com um termómetro que
mede a média de **todo o quarteirão**. Se a tua casa aquecer, o termómetro
mal vai registar a diferença, porque a média de 100 casas dilui o sinal.

O CAMS EAC4 é esse termómetro de quarteirão. Para uma fábrica, precisamos
de um termómetro de **casa**.

### O que o CAMS EAC4 é bom para

- Tendências **regionais** (ex: "a poluição no Sudeste do Brasil subiu 10%
  em 10 anos")
- Comparação entre **regiões** (ex: "o Rio tem mais PM10 que São Paulo")
- **Não** é bom para: impacto de **uma** fonte pontual a **1 km** de distância

---

## O que vamos fazer a seguir: Sentinel-5P (TROPOMI)

### Por que Sentinel-5P?

| Característica | CAMS EAC4 | Sentinel-5P (TROPOMI) |
|----------------|-----------|----------------------|
| **Tipo** | Modelo (simulação) | **Satélite** (medição real) |
| **Resolução** | 0.75° (~50 km) | **~5.5 km** |
| **Cobre o Brasil?** | Sim | Sim |
| **Variáveis** | PM2.5, PM10, SO₂, NO₂, O₃, etc. | **SO₂, NO₂**, CO, O₃, AOD (aerosóis) |
| **Frequência** | 3-horário (modelado) | **1 passagem/dia** (~10:30 local) |
| **Custo** | Grátis | **Grátis** (ESA Copernicus) |
| **Captura pluma industrial?** | Não | **Sim** (resolução 5.5 km) |

O Sentinel-5P é um **satélite da ESA** (Agência Espacial Europeia) que mede
a composição do ar **de facto** (não simula). Com resolução de ~5.5 km,
uma pluma industrial de 2-3 km **é visível** nos dados.

### O que muda no código

| Componente | CAMS EAC4 (atual) | Sentinel-5P (próximo) |
|------------|-------------------|----------------------|
| **Fonte de dados** | ADS (ECMWF) | **Copernicus Data Space** (ESA) |
| **Formato** | NetCDF (`.nc`) | NetCDF (`.nc`) — **mesmo formato** |
| **Biblioteca de leitura** | `xarray` + `netCDF4` | **Idem** — não muda |
| **Seleção por coordenada** | `.sel(lat, lon, method="nearest")` | **Idem** — mas agora o grid point cai **em Santa Cruz** |
| **Conversão de unidades** | kg/m³ → µg/m³ (×1e9) | **Diferente** — TROPOMI dá colunas (mol/m²) para SO₂/NO₂; AOD para aerosóis |
| **Resample** | 8 pts/dia → 1 dia | **1 pt/dia** (já é diário) |
| **Métodos de análise** | Resample, rolling 30d, P95, Mann-Whitney | **Idem** — os 4 métodos continuam válidos |
| **Ponto de controlo** | Não era possível (grid 50 km) | **Possível** — ex: Barra da Tijuca (-23.0, -43.55) a 5 km |

### O que NÃO muda

- A estrutura do projeto (2 ficheiros: download + análise)
- Os 4 métodos de análise (resample, rolling, percentis, Mann-Whitney)
- A lógica de corte em 2010-06-01
- O formato dos gráficos
- O `xarray` como biblioteca de leitura

### O que muda (resumo)

1. **`download_data.py`** → novo endpoint (Copernicus Data Space da ESA),
   novos parâmetros (produto TROPOMI, variáveis `SO2_column_number_density`,
   `NO2_column_number_density`, `AOD`)
2. **`app.py`** → nova conversão de unidades (mol/m² → µg/m³ precisa de
   pressão e temperatura), novo grid point (agora em Santa Cruz),
   **adicionar ponto de controlo**
3. **Conclusão** → com resolução 5.5 km + ponto de controlo, finalmente
   conseguimos **isolar** o efeito da fábrica

---

## Estrutura do projeto

```
respira-rio/
├── .gitignore              ← ignora .venv, data/, output/
├── README.md               ← este ficheiro
├── download_data.py        ← DESCARREGA os .nc (corre 1 vez)
├── app.py                  ← LÊ, CORTE, CALCULA, PLOTA (corre em <10s)
├── data/                   ← (gerado) ficheiros .nc e .csv
└── output/                 ← (gerado) PNGs
```

---

## Como rodar (do zero)

### Pré-requisitos

- Windows 10/11 ou Linux/Mac
- Python 3.10+
- Conta no [Atmosphere Data Store](https://ads.atmosphere.copernicus.eu) (grátis)

### 1. Instalar `uv` (gestor de pacotes)

```bash
# Windows
irm https://astral.sh/uv/install.ps1 | iex

# Linux/Mac
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Criar ambiente e instalar dependências

```bash
uv venv
uv pip install xarray pandas numpy matplotlib netCDF4 cdsapi scipy
```

### 3. Configurar credenciais ADS

Criar `~/.cdsapirc` (Windows: `C:\Users\<user>\.cdsapirc`):

```
url: https://ads.atmosphere.copernicus.eu/api
key: <a_tua_api_key>
```

Aceitar licença:
https://ads.atmosphere.copernicus.eu/datasets/cams-global-reanalysis-eac4?tab=download#manage-licences

### 4. Descarregar dados (~2h)

```bash
python download_data.py
```

### 5. Correr análise (<10s)

```bash
python app.py
```

### 6. Ver resultados

- Tabela no terminal (médias, P95, P99, p-value)
- `data/santa_cruz_diario.csv` — série temporal diária
- `output/pm25_analysis.png`
- `output/pm10_analysis.png`
- `output/so2_analysis.png`

---

## Métodos de análise (explicação)

| # | Método | O que faz | Por que |
|---|--------|-----------|---------|
| 1 | **Resample diário** | Tira a média dos 8 pontos 3-horários → 1 valor/dia | A OMS define limites em média diária. Reduz 52.000 pts → 6.500. |
| 2 | **Média móvel 30 dias** | Média deslizante de 30 dias | Suaviza variabilidade diária. Se a fábrica adiciona um baseline constante, a rolling mean desloca-se e fica. |
| 3 | **Percentis P95/P99** | "Nos piores 5% (1%) dos dias, o valor foi X" | O "máximo" é 1 ponto (pode ser artefato). P95 é o padrão OMS/EPA. Captura se os dias maus estão a ficar piores. |
| 4 | **Mann-Whitney U** | Teste estatístico não-paramétrico | Responde: "a diferença entre pré e pós é **real** ou é **sorte**?" p < 0.05 = significativa. Não assume normalidade (dados de poluição são assimétricos). |

---

## Limitações conhecidas

1. **Resolução 0.75°** — o grid point está a ~50 km de Santa Cruz.
   Uma fonte pontual não é visível.
2. **Sem ponto de controlo** — não é possível isolar a fábrica do
   background regional.
3. **Modelo, não medição** — o CAMS EAC4 simula o ar baseado em emissões
   reportadas. Se a fábrica não reportou corretamente, o modelo não inclui.
4. **SO₂ a 1000 hPa** — é uma variável multi-level; usamos o nível mais
   baixo (superfície), mas não é exatamente "no chão" (é a ~100 m).

---

## Próximos passos

- [ ] Migrar para **Sentinel-5P TROPOMI** (resolução 5.5 km, medição real)
- [ ] Adicionar **ponto de controlo** (ex: Barra da Tijuca)
- [ ] Converter colunas (mol/m²) para concentração (µg/m³)
- [ ] Re-analisar com os 4 métodos
- [ ] Gerar relatório final com conclusões

---

## Licença e Propriedade Intelectual

**Todos os direitos reservados © 2026 Luan Oliveira Moreira da Silva.**

Este estudo, códigos, documentação e resultados apresentados neste repositório são de propriedade intelectual exclusiva do autor. O acesso público destina-se estritamente a fins de portfólio, sendo proibida a sua reprodução ou utilização sem autorização prévia.

*Dados utilizados:* © Copernicus Atmosphere Monitoring Service (ECMWF).
