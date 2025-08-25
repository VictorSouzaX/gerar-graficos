from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import matplotlib.pyplot as plt
import matplotlib as mpl
from PIL import Image
import io
import base64

app = FastAPI()

def hex_rgb(color):
    # Recebe 'rgb(r,g,b)', '#abc', ou '#aabbcc' -> retorna formato matplotlib
    if color.startswith('rgb'):
        parts = color.replace('rgb', '').replace('(', '').replace(')', '').split(',')
        return tuple(int(p.strip())/255 for p in parts)
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

    # --- Personalização ---
    largura = int(settings.get("largura", 1600))
    altura = int(settings.get("altura", 600))
    cor_verde = hex_rgb(settings.get("cor_verde", "#25ad60"))
    cor_amarelo = hex_rgb(settings.get("cor_amarelo", "#f4cb33"))
    cor_azul = hex_rgb(settings.get("cor_azul", "#2986cc"))
    legenda = settings.get("legenda", True)
    x = int(settings.get("x", 0))
    y = int(settings.get("y", 0))
    background_b64 = settings.get("background_b64")

    # --- Dados dinâmicos ---
    labels = [item["titulo"] for item in insumos]
    verdes = [item.get("valor_verde", 0.0) for item in insumos]
    amarelos = [item.get("valor_amarelo", 0.0) for item in insumos]
    totais = [v+a for v, a in zip(verdes, amarelos)]

    # --- Gráfico base ---
    dpi = 100
    fig, ax = plt.subplots(figsize=(largura/dpi, altura/dpi), dpi=dpi)

    bar_width = 0.8
    indices = range(len(labels))

    plt.grid(axis='y', linestyle='--', alpha=0.4, color="white", zorder=0)

    barras_amarelas = ax.bar(indices, amarelos, bar_width, color=cor_amarelo, label="Amarelo", zorder=2)
    barras_verdes = ax.bar(indices, verdes, bar_width, bottom=amarelos, color=cor_verde, label="Verde", zorder=2)

    # Rótulos totais em cima
    for i, t in enumerate(totais):
        if t > 0:
            plt.text(i, t + max(totais)*0.02, f'R$ {t:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.'),
                     ha="center", va="bottom", fontweight="bold", fontsize=13, color='white')

    # Rótulos internos das barras
    for rect, valor in zip(barras_amarelas, amarelos):
        if valor > 0:
            plt.text(rect.get_x() + rect.get_width() / 2, valor / 2,
                     f'R$ {valor:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.'),
                     ha='center', va='center', fontsize=11, color="#fff", fontweight="bold")
    for rect, valor_verde, valor_amarelo in zip(barras_verdes, verdes, amarelos):
        if valor_verde > 0:
            plt.text(rect.get_x() + rect.get_width() / 2, valor_verde / 2 + valor_amarelo,
                     f'R$ {valor_verde:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.'),
                     ha='center', va='center', fontsize=11, color="#fff", fontweight="bold")

    # Eixo y
    max_y = max(totais) if any(totais) else 1
    ax.set_ylim([0, max_y * 1.2])
    yticks = [0, max_y/2, max_y]
    ax.set_yticks(yticks)
    ylabels = [f"R$ {y/1e6:.1f} Mi" if y != 0 else "R$ 0,0 Mi" for y in yticks]
    ax.set_yticklabels(ylabels, fontsize=13, color="#fff")
    ax.tick_params(axis='y', colors='#fff')

    # Eixo x
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=20, ha='right', fontsize=12, color="#fff")
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#fff')
    ax.spines['bottom'].set_color('#fff')
    for spine in ax.spines.values():
        spine.set_linewidth(1.2)

    # Legenda
    if legenda:
        ax.legend(loc='upper right', fontsize=13, facecolor='none', frameon=False)
    else:
        ax.get_legend().remove() if ax.get_legend() else None

    plt.tight_layout()

    # Salva gráfico com fundo transparente (canal alpha mantido)
    buf = io.BytesIO()
    plt.savefig(buf, format='png', transparent=True)
    plt.close(fig)
    buf.seek(0)

    # Se houver background base64, será inserido aqui!
    if background_b64:
        bg = Image.open(io.BytesIO(base64.b64decode(background_b64)))
        bg = bg.convert("RGBA")
        # Garante que o background tenha o tamanho correto
        bg = bg.resize((largura, altura))

        g = Image.open(buf)
        # Posiciona o gráfico segundo x, y sobre bg
        bg.paste(g, (x, y), g)
        out_buf = io.BytesIO()
        bg.save(out_buf, format="PNG")
        out_buf.seek(0)
        return StreamingResponse(out_buf, media_type='image/png')

    # Caso não tenha background, retorna só o gráfico
    return StreamingResponse(buf, media_type='image/png')
