"""
respira-rio — app.py (v2)
==========================
Lê os ficheiros NetCDF do CAMS EAC4, extrai a série temporal de Santa Cruz,
corta em pré/pós-fábrica (junho 2010), aplica 4 métodos de análise
e gera gráficos.

Métodos:
  1. Resample diário (média de 8 pontos 3-horários → 1 valor/dia)
  2. Média móvel de 30 dias (suaviza ruído diário)
  3. Percentis P95 e P99 (captura episódios extremos)
  4. Teste Mann-Whitney U (prova estatística: a diferença é real ou sorte?)

Uso:
    python app.py

Saída:
    data/santa_cruz.csv              (série diária em CSV)
    output/pm25_analysis.png
    output/pm10_analysis.png
    output/so2_analysis.png
"""

import xarray as xr
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scipy.stats import mannwhitneyu
import os

# ──────────────────────────────────────────────────────────────
# CONFIGURAÇÃO
# ──────────────────────────────────────────────────────────────

LAT = -22.9189
LON = -43.6853
CUTOFF = pd.Timestamp("2010-06-01")
OUT_DIR = "output"
os.makedirs(OUT_DIR, exist_ok=True)

# ──────────────────────────────────────────────────────────────
# 0. INSPEÇÃO RÁPIDA
# ──────────────────────────────────────────────────────────────

print("🔍 Inspeção rápida...")
ds_check = xr.open_dataset("data/pm25.nc")
var_check = [v for v in ds_check.data_vars
             if v not in ("latitude", "longitude", "valid_time")][0]
units = ds_check[var_check].attrs.get("units", "N/A")
i = abs(ds_check["latitude"] - LAT).argmin()
j = abs(ds_check["longitude"] - LON).argmin()
print(f"   Variável: {var_check}")
print(f"   Unidades: {units}")
print(f"   Grid point: lat={ds_check['latitude'][i].values:.4f}, "
      f"lon={ds_check['longitude'][j].values:.4f}")
ds_check.close()
print()

# ──────────────────────────────────────────────────────────────
# 1. LER E EXTRAIR
# ──────────────────────────────────────────────────────────────

print("📂 A ler ficheiros NetCDF...")

files = {
    "pm25": "data/pm25.nc",
    "pm10": "data/pm10.nc",
    "so2":  "data/so2.nc",
}

series = {}
for name, path in files.items():
    ds = xr.open_dataset(path)
    var = [v for v in ds.data_vars
           if v not in ("latitude", "longitude", "valid_time")][0]
    da = ds[var].sel(latitude=LAT, longitude=LON, method="nearest").squeeze()

    # Encontrar a dimensão temporal
    time_dims = [d for d in da.dims if "time" in d.lower()]
    time_dim = max(time_dims, key=lambda d: da.sizes[d])

    s = pd.Series(da.values, index=pd.to_datetime(da[time_dim].values))
    s.index.name = "time"
    series[name] = s
    ds.close()

df = pd.DataFrame(series).sort_index()
df.index = pd.to_datetime(df.index)

# Converter kg/m³ → µg/m³ (1 kg = 1e9 µg)
df = df * 1e9

print(f"✅ Dados carregados: {len(df)} pontos (3-horário)")
print(f"   Range: {df.index[0].date()} → {df.index[-1].date()}")

# ──────────────────────────────────────────────────────────────
# 2. RESAMPLE DIÁRIO
# ──────────────────────────────────────────────────────────────
#
# O EAC4 tem 8 pontos por dia (a cada 3h).
# A OMS define limites em média diária.
# Resample: tira a média dos 8 pontos → 1 valor/dia.

df_daily = df.resample("D").mean()
df_daily = df_daily.dropna()  # remover dias incompletos (ex: último dia)

print(f"\n📅 Resample diário: {len(df_daily)} dias")
df_daily.to_csv("data/santa_cruz_diario.csv")

# ──────────────────────────────────────────────────────────────
# 3. CORTAR EM PRÉ / PÓS
# ──────────────────────────────────────────────────────────────

df_daily["periodo"] = np.where(df_daily.index < CUTOFF, "pre", "pos")
df_pre = df_daily[df_daily["periodo"] == "pre"].drop(columns="periodo")
df_pos = df_daily[df_daily["periodo"] == "pos"].drop(columns="periodo")

print(f"   Pré-fábrica : {df_pre.index[0].date()} → {df_pre.index[-1].date()}  ({len(df_pre)} dias)")
print(f"   Pós-fábrica : {df_pos.index[0].date()} → {df_pos.index[-1].date()}  ({len(df_pos)} dias)")

# ──────────────────────────────────────────────────────────────
# 4. MÉDIA MÓVEL DE 30 DIAS
# ──────────────────────────────────────────────────────────────
#
# Suaviza a variabilidade diária (vento, chuva, tráfego).
# Se a fábrica adiciona um baseline constante, a rolling mean
# desloca-se após Jun/2010 e FICA lá.

df_daily["rolling30"] = df_daily["pm25"].rolling(window=30, min_periods=15).mean()

# ──────────────────────────────────────────────────────────────
# 5. MÉTRICAS COMPARATIVAS (com percentis + Mann-Whitney)
# ──────────────────────────────────────────────────────────────
#
# Para cada variável calculamos:
#   - Média pré/pós         → nível de base
#   - P95 pré/pós           → "os piores 5% dos dias" (padrão OMS/EPA)
#   - P99 pré/pós           → "os piores 1% dos dias" (extremos)
#   - Mann-Whitney U p-value → a diferença é estatisticamente significativa?
#
# Mann-Whitney U:
#   - Não assume distribuição normal (dados de poluição são assimétricos)
#   - Compara as DISTRIBUIÇÕES inteiras, não só as médias
#   - p < 0.05 → "a diferença é real, não é sorte"

print("\n" + "=" * 80)
print(f"{'Variável':<8} {'Média Pré':>10} {'Média Pós':>10} {'P95 Pré':>10} {'P95 Pós':>10} {'P99 Pré':>10} {'P99 Pós':>10} {'p-value':>10}")
print("=" * 80)

metrics = {}
for col in ["pm25", "pm10", "so2"]:
    m_pre  = df_pre[col].mean()
    m_pos  = df_pos[col].mean()
    p95_pre  = df_pre[col].quantile(0.95)
    p95_pos  = df_pos[col].quantile(0.95)
    p99_pre  = df_pre[col].quantile(0.99)
    p99_pos  = df_pos[col].quantile(0.99)

    # Mann-Whitney U (alternative="two-sided" = testa se há diferença em qualquer direção)
    stat, p_value = mannwhitneyu(df_pre[col], df_pos[col], alternative="two-sided")

    metrics[col] = {
        "mean_pre": m_pre, "mean_pos": m_pos,
        "p95_pre": p95_pre, "p95_pos": p95_pos,
        "p99_pre": p99_pre, "p99_pos": p99_pos,
        "p_value": p_value,
    }

    # Formatar p-value (se for muito pequeno, mostrar em notação científica)
    if p_value < 0.001:
        p_str = f"{p_value:.1e}"
    else:
        p_str = f"{p_value:.3f}"

    print(f"{col:<8} {m_pre:>10.2f} {m_pos:>10.2f} {p95_pre:>10.2f} {p95_pos:>10.2f} "
          f"{p99_pre:>10.2f} {p99_pos:>10.2f} {p_str:>10}")

print("=" * 80)
print("\n📌 Interpretação do p-value:")
print("   p < 0.05 → diferença estatisticamente significativa (a fábrica PROVAVELMENTE causou)")
print("   p > 0.05 → diferença NÃO significativa (pode ser ruído/sorte)")

# ──────────────────────────────────────────────────────────────
# 6. GRÁFICOS
# ──────────────────────────────────────────────────────────────
#
# Cada gráfico mostra:
#   - Série diária (pontos pequenos, alpha baixo)
#   - Média móvel de 30 dias (linha grossa) → mostra a TENDÊNCIA
#   - P95 pré (linha horizontal verde) e P95 pós (linha horizontal vermelha)
#   - Linha vertical em Jun/2010
#   - Faixas verde/vermelha (pré/pós)

plt.rcParams.update({"figure.dpi": 100, "axes.grid": True, "grid.alpha": 0.3})

labels = {"pm25": "PM2.5", "pm10": "PM10", "so2": "SO₂"}
colors = {"pm25": "#e74c3c", "pm10": "#f39c12", "so2": "#2980b9"}

for col in ["pm25", "pm10", "so2"]:
    fig, ax = plt.subplots(figsize=(14, 5))

    # 1. Série diária (pontos pequenos)
    ax.plot(df_daily.index, df_daily[col],
            color=colors[col], linewidth=0.3, alpha=0.3,
            label="Diário")

    # 2. Média móvel 30 dias (linha grossa — a TENDÊNCIA)
    ax.plot(df_daily.index, df_daily["rolling30"],
            color="black", linewidth=2, alpha=0.8,
            label="Média móvel 30d")

    # 3. Linha vertical do corte
    ax.axvline(CUTOFF, color="black", linestyle="--", linewidth=1.5,
               label="Jun/2010 (fábrica)")

    # 4. Faixas de cor
    ax.axvspan(df_daily.index[0], CUTOFF, alpha=0.06, color="green")
    ax.axvspan(CUTOFF, df_daily.index[-1], alpha=0.06, color="red")

    # 5. P95 pré e pós (linhas horizontais)
    ax.axhline(metrics[col]["p95_pre"], color="green", linestyle=":",
               linewidth=1.5, alpha=0.8,
               label=f"P95 pré ({metrics[col]['p95_pre']:.1f})")
    ax.axhline(metrics[col]["p95_pos"], color="red", linestyle=":",
               linewidth=1.5, alpha=0.8,
               label=f"P95 pós ({metrics[col]['p95_pos']:.1f})")

    # 6. Título e eixos
    sig = "✓ significativa" if metrics[col]["p_value"] < 0.05 else "✗ não significativa"
    ax.set_title(f"respira-rio — {labels[col]} em Santa Cruz, RJ  "
                 f"(Mann-Whitney p={metrics[col]['p_value']:.4f} → {sig})",
                 fontsize=11, fontweight="bold")
    ax.set_xlabel("")
    ax.set_ylabel("Concentração (µg/m³)")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.legend(loc="upper left", fontsize=8, ncol=2)

    fig.tight_layout()
    fig.savefig(f"{OUT_DIR}/{col}_analysis.png", bbox_inches="tight")
    plt.close(fig)
    print(f"📈 Gráfico guardado: output/{col}_analysis.png")

print("\n🎉 Tudo pronto!")
print("   CSV diário: data/santa_cruz_diario.csv")
print("   Gráficos:   output/*_analysis.png")   