from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
import io
import base64

app = FastAPI()

def hex_rgb(color: str):
    """Converte string de cor para formato aceito pelo matplotlib"""
    if isinstance(color, tuple):
        return color
    if color.startswith("rgb"):
        parts = color.replace("rgb", "").replace("(", "").replace(")", "").split(",")
        return tuple(int(p.strip()) / 255 for p in parts)
    if color.startswith("#"):
        color = color.lstrip("#")
        if len(color) == 3:
            color = "".join([c * 2 for c in color])
        return "#" + color
    return color

@app.post("/grafico")
async def gerar_grafico(request: Request):
    req = await request.json()

    insumos = req.get("insumos", [])
    settings = req.get("personalizacao", {})

    largura = int(settings.get("largura", 1200))
    altura = int(settings.get("altura", 400))
    cor_barra = hex_rgb(settings.get("cor_barra", "#25ad60"))
    legenda = settings.get("legenda", True)
    x = int(settings.get("x", 0))
    y = int(settings.get("y", 0))
    background_b64 = settings.get("background_b64", None)

    labels = [item["titulo"] for item in insumos]
    valores = [item.get("valor_verde", 0.0) for item in insumos]
    indices = range(len(labels))

    # ==== GRAFICO PNG TRANSPARENTE =====
    dpi = 100
    fig, ax = plt.subplots(figsize=(largura/dpi, altura/dpi), dpi=dpi)

    bar_width = 0.8

    # Eixo Y - sempre 4 divisões iguais
    max_y = max(valores) if any(valores) else 1
    num_yticks = 4
    yticks = np.linspace(0, max_y, num_yticks)
    ax.set_ylim([0, max_y * 1.05])
    ax.set_yticks(yticks)
    ylabels = [f"R$ {y/1e6:.1f} Mi" if y != 0 else "R$ 0,0 Mi" for y in yticks]
    ax.set_yticklabels(ylabels, fontsize=13, color="#fff")
    ax.tick_params(axis="y", colors="#fff")

    # Eixo X
    ax.set_xticks(range(len(labels)))
    if legenda:
        ax.set_xticklabels(labels, rotation=0, ha="center", fontsize=12, color="#fff")
    else:
        ax.set_xticklabels([""] * len(labels))

    # Barras
    ax.bar(indices, valores, bar_width, color=cor_barra, label="Valores", zorder=2)

    # ==== SÓ A BASE DA CAIXA DO GRÁFICO VISÍVEL ====
    ax.spines["top"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_visible(True)
    ax.spines["bottom"].set_color("#fff")
    ax.spines["bottom"].set_linewidth(1.0)

    # Grid horizontal
    ax.grid(which="major", axis="y", linestyle="--", alpha=0.4, color="white", zorder=0)

    # Valor em cima da barra
    for idx, total in enumerate(valores):
        if total > 0:
            valor_fmt = f"R$ {total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            ax.text(idx, total + max_y * 0.016,
                    valor_fmt,
                    ha="center", va="bottom",
                    fontweight="bold", fontsize=13, color="white")

    # Legenda
    if legenda:
        ax.legend(loc="upper right",
                  fontsize=18,
                  facecolor="none",
                  frameon=False,
                  prop={"family": "Arial"})
    else:
        if ax.get_legend():
            ax.get_legend().remove()

    plt.tight_layout()

    # Salvar gráfico
    buf = io.BytesIO()
    plt.savefig(buf, format="png", transparent=True)
    plt.close(fig)
    buf.seek(0)
    grafico_img = Image.open(buf).convert("RGBA")

    # Fundo BG original sem redimensionar!
    if background_b64:
        bg = Image.open(io.BytesIO(base64.b64decode(background_b64))).convert("RGBA")
        output_img = bg.copy()
        output_img.alpha_composite(grafico_img, (x, y))
        out_buf = io.BytesIO()
        output_img.save(out_buf, format="PNG")
        out_buf.seek(0)
        return StreamingResponse(out_buf, media_type="image/png")

    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")
