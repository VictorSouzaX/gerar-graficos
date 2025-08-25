from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import matplotlib.pyplot as plt
import matplotlib as mpl
import io

app = FastAPI()

@app.post("/grafico")
async def gerar_grafico(request: Request):
    req = await request.json()

    insumos = req.get("insumos", [])

    labels = [item["titulo"] for item in insumos]
    verdes = [item.get("verde_valor", 0.0) for item in insumos]
    amarelos = [item.get("amarelo_valor", 0.0) for item in insumos]

    total = [verde + amarelo for verde, amarelo in zip(verdes, amarelos)]

    fig, ax = plt.subplots(figsize=(16,6))

    bar_width = 0.8
    indices = range(len(labels))

    # Fundo transparente
    fig.patch.set_alpha(0.0)
    ax.set_facecolor('none')
    plt.grid(axis='y', linestyle='--', alpha=0.4, color="white", zorder=0)

    # Barras empilhadas
    barras_amarelas = ax.bar(indices, amarelos, bar_width, color="#f4cb33", label="Amarelo", zorder=2)
    barras_verdes = ax.bar(indices, verdes, bar_width, bottom=amarelos, color="#25ad60", label="Verde", zorder=2)

    # Rótulos totais no topo
    for i, t in enumerate(total):
        if t > 0:
            plt.text(i, t+max(total)*0.02, f'R$ {t:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.'), 
                     ha="center", va="bottom", fontweight="bold", fontsize=13, color='white')

    # Rótulos no meio de cada barra
    for idx, (rect, valor) in enumerate(zip(barras_amarelas, amarelos)):
        if valor > 0:
            h = rect.get_height()
            plt.text(rect.get_x() + rect.get_width()/2, h/2, 
                     f'R$ {valor:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.'), 
                     ha='center', va='center', fontsize=11, color="#fff", fontweight="bold")
    for idx, (rect, valor, amarelo) in enumerate(zip(barras_verdes, verdes, amarelos)):
        if valor > 0:
            plt.text(rect.get_x() + rect.get_width()/2, valor/2+amarelo, 
                     f'R$ {valor:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.'), 
                     ha='center', va='center', fontsize=11, color="#fff", fontweight="bold")

    # Eixo y customizado
    ax.set_yticks([0, max(total)/3, 2*max(total)/3, max(total)])
    ylabels = [f"R$ {y/1e6:.1f} Mi" for y in ax.get_yticks()]
    ax.set_yticklabels(ylabels, fontsize=13, color="#fff")
    ax.tick_params(axis='y', colors='#fff')

    # Eixo x customizado
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=20, ha='right', fontsize=12, color="#fff")
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#fff')
    ax.spines['bottom'].set_color('#fff')

    # Remover box do gráfico
    for spine in ax.spines.values():
        spine.set_linewidth(1.2)

    # Ajustar layout
    plt.tight_layout()

    # Fundo preto transparente
    fig.patch.set_facecolor('none')
    ax.set_facecolor('none')

    buf = io.BytesIO()
    plt.savefig(buf, format='png', transparent=True)
    plt.close(fig)
    buf.seek(0)
    return StreamingResponse(buf, media_type='image/png')
