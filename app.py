from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
import io
import base64

app = FastAPI()

def hex_rgb(color):
    if isinstance(color, tuple):  # já está em formato correto
        return color
    if color.startswith('rgb'):
        parts = color.replace('rgb', '').replace('(', '').replace(')', '').split(',')
        return tuple(int(p.strip()) / 255 for p in parts)
    if color.startswith('#'):
        color = color.lstrip('#')
        if len(color) == 3:
            color = ''.join([c*2 for c in color])
        return '#' + color
    return color

@app.post("/grafico")
async def gerar_grafico(request: Request):
    req = await request.json()

    insumos = req.get("insumos", [])
    settings = req.get("personalizacao", {})

    largura = int(settings.get("largura", 1200))   # largura do gráfico
    altura = int(settings.get("altura", 400))      # altura do gráfico
    cor_verde = hex_rgb(settings.get("cor_verde", "#25ad60"))
    cor_amarelo = hex_rgb(settings.get("cor_amarelo", "#f4cb33"))
    cor_azul = hex_rgb(settings.get("cor_azul", "#2986cc"))
    legenda = settings.get("legenda", True)
    x = int(settings.get("x", 0))
    y = int(settings.get("y", 0))
    background_b64 = settings.get("background_b64", None)

    labels = [item["titulo"] for item in insumos]
    verdes = [item.get("valor_verde", 0.0) for item in insumos]
    amarelos = [item.get("valor_amarelo", 0.0) for item in insumos]
    totais = [v+a for v, a in zip(verdes, amarelos)]
    indices = range(len(labels))

    # ==== CRIA GRÁFICO PNG TRANSPARENTE =====
    dpi = 100
    fig, ax = plt.subplots(figsize=(largura/dpi, altura/dpi), dpi=dpi)

    bar_width = 0.8

    # Y sempre com 4 divisões
    max_y = max(totais) if any(totais) else 1
    num_yticks = 4
    yticks = np.linspace(0, max_y, num_yticks)
    ax.set_ylim([0, max_y * 1.05])
    ax.set_yticks(yticks)
    ylabels = [f"R$ {y/1e6:.1f} Mi" if y != 0 else "R$ 0,0 Mi" for y in yticks]
    ax.set_yticklabels(ylabels, fontsize=13, color="#fff")
    ax.tick_params(axis='y', colors='#fff')

    # Eixo X
    ax.set_xticks(range(len(labels)))
    if legenda:
        ax.set_xticklabels(labels, rotation=20, ha='right', fontsize=12, color="#fff")
    else:
        ax.set_xticklabels(['']*len(labels))

    # Barras
    barras_amarelas = ax.bar(indices, amarelos, bar_width, color=cor_amarelo, label="Amarelo", zorder=2)
    barras_verdes = ax.bar(indices, verdes, bar_width, bottom=amarelos, color=cor_verde, label="Verde", zorder=2)

    # Linhas grade horizontal
    for spine in ax.spines.values():
        spine.set_linewidth(1.2)
    ax.grid(which='major', axis='y', linestyle='--', alpha=0.4, color="white", zorder=0)

    # LÓGICA LABELS: mostra internos só para barra "alta" (mais de 30 px)
    for idx, (rect_am, rect_ve, valor_am, valor_ve, total) in enumerate(zip(
        barras_amarelas, barras_verdes, amarelos, verdes, totais)):
        # Altura da coluna em pixels no gráfico
        topo_coluna = rect_am.get_height() + rect_ve.get_height()
        _, pix0 = ax.transData.transform((0, 0))
        _, pix1 = ax.transData.transform((0, topo_coluna))
        altura_pixel = abs(pix1 - pix0)

        # Só mostrar valores internos se barra for "alta"
        show_internal = altura_pixel > 30

        # Valor total no topo
        if total > 0:
            plt.text(idx, total + max_y*0.016, f'R$ {total:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.'),
                     ha="center", va="bottom", fontweight="bold", fontsize=13, color='white')
        # Valores internos só em barras grandes!
        if show_internal:
            if valor_am > 0:
                plt.text(rect_am.get_x() + rect_am.get_width()/2, valor_am / 2,
                         f'R$ {valor_am:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.'),
                         ha='center', va='center', fontsize=11, color="#fff", fontweight="bold")
            if valor_ve > 0:
                plt.text(rect_ve.get_x() + rect_ve.get_width()/2, valor_ve / 2 + valor_am,
                         f'R$ {valor_ve:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.'),
                         ha='center', va='center', fontsize=11, color="#fff", fontweight="bold")

    # Legenda visível só se legenda = true
    if legenda:
        ax.legend(loc='upper right', fontsize=13, facecolor='none', frameon=False)
    else:
        if ax.get_legend():
            ax.get_legend().remove()

    plt.tight_layout()

    # Salvar gráfico RGBA
    buf = io.BytesIO()
    plt.savefig(buf, format='png', transparent=True)
    plt.close(fig)
    buf.seek(0)
    grafico_img = Image.open(buf).convert("RGBA")

    # FUNDO: original SEM redimensionamento!
    if background_b64:
        bg = Image.open(io.BytesIO(base64.b64decode(background_b64))).convert("RGBA")
        bg_w, bg_h = bg.size
        output_img = bg.copy()
        output_img.alpha_composite(grafico_img, (x, y))
        out_buf = io.BytesIO()
        output_img.save(out_buf, format="PNG")
        out_buf.seek(0)
        return StreamingResponse(out_buf, media_type='image/png')

    # Caso não tenha background, retorna só o gráfico
    buf.seek(0)
    return StreamingResponse(buf, media_type='image/png')
