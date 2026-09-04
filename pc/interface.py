import os
import json
import queue
import subprocess
import threading
import sys
import time
import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageTk

PASTA_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PASTA_PROJETO, "core"))
from main import (
    atualizar_historico_visual,
    atualizar_payout_atual,
    acionar_parada_emergencia,
    definir_callback_evento,
    definir_configuracao_indicadores,
    iniciar_robo,
    pausar_robo,
    parar_robo,
    snapshot_visual_disponivel,
)
from conversor_velas_visuais import converter_velas_visuais
from estado_conexao_iq import EstadoConexaoIq
from painel_abas_iq import (
    ATIVOS_MERCADO_ABERTO,
    ATIVOS_OTC_PRIORITARIOS,
    PainelAbasIq,
)
from captura_tela_macos import testar_captura
from leitor_payout_iq import ler_payout
from leitor_botoes_iq import ler_botoes
from leitor_velas_iq import ler_velas
from leitor_ativo_iq import ler_ativo
from navegacao_abas_macos import selecionar_aba
from monitoramento_iq import segundos_ate_proxima_leitura
from politica_snapshot import validar_snapshot_visual
from leitor_conta_iq import ler_tipo_conta
from executor_demo_iq import ExecutorDemoIq
from historico_entradas import carregar_entradas, registrar_entrada
from numeros import converter_numero
from catalogo_indicadores import ESTRATEGIAS_PRONTAS, INDICADORES, PADRAO_MANUAL, POR_CODIGO
from versao import NOME_COMPLETO_APP


fila_logs = queue.Queue()


class SaidaLogInterface:
    """Transforma os prints do motor em linhas para o painel da interface."""

    def __init__(self, fila):
        self.fila = fila
        self.pendente = ""

    def write(self, texto):
        self.pendente += str(texto)
        while "\n" in self.pendente:
            linha, self.pendente = self.pendente.split("\n", 1)
            if linha.strip():
                self.fila.put(linha)
        return len(texto)

    def flush(self):
        if self.pendente.strip():
            self.fila.put(self.pendente)
            self.pendente = ""


janela = tk.Tk()
janela.title(NOME_COMPLETO_APP)
janela.geometry("980x900")
janela.minsize(720, 700)
janela.configure(bg="#0d0b16")

# Paleta inspirada no painel realista fornecido pelo usuário. A alteração é
# estritamente visual: nenhuma regra de análise ou execução depende destas cores.
COR_BG = "#0d0b16"
COR_BG_DEEP = "#0d0b16"
COR_PANEL = "#171229"
COR_PANEL_ALT = "#171229"
COR_CARD = "#171229"
COR_CARD_ALT = "#171229"
COR_BORDA = "#2a2440"
COR_GLOW = "#7f77dd"
COR_TEXTO = "#ffffff"
COR_MUTED = "#8a8aa0"
COR_SUCESSO = "#97c459"
COR_ATENCAO = "#e8b34a"
COR_PERIGO = "#e24b4a"


def criar_card_premium(parent, bg=COR_CARD, padding=(10, 10), rel="raised"):
    frame = tk.Frame(
        parent,
        bg=bg,
        bd=0,
        relief="flat",
        highlightthickness=1,
        highlightbackground=COR_BORDA,
        highlightcolor=COR_GLOW,
        padx=padding[0],
        pady=padding[1],
    )
    return frame

estilo = ttk.Style()
if "clam" in estilo.theme_names():
    estilo.theme_use("clam")

estilo.configure("TFrame", background=COR_BG)
estilo.configure("TLabelframe", background=COR_PANEL_ALT, borderwidth=1, relief="flat")
estilo.configure("TLabelframe.Label", background=COR_PANEL_ALT, foreground=COR_MUTED, font=("Helvetica Neue", 10, "bold"))
estilo.configure("Premium.TLabelframe", background=COR_PANEL_ALT, borderwidth=1, relief="flat")
estilo.configure("Premium.TLabelframe.Label", background=COR_PANEL_ALT, foreground=COR_MUTED, font=("Helvetica Neue", 10, "bold"))
estilo.configure("TLabel", background=COR_BG, foreground=COR_TEXTO, font=("Helvetica Neue", 10))
estilo.configure("TEntry", fieldbackground="#151522", foreground=COR_TEXTO, borderwidth=0, padding=(12, 9))
estilo.configure("TCombobox", fieldbackground="#151522", foreground=COR_TEXTO, borderwidth=0, padding=(10, 7))
estilo.configure("TNotebook", background=COR_BG, borderwidth=0)
estilo.configure("TNotebook.Tab", background=COR_PANEL, foreground=COR_MUTED, padding=(13, 8), borderwidth=0, relief="flat", font=("Helvetica Neue", 10))
estilo.map("TNotebook.Tab", background=[("selected", "#171229"), ("active", "#171229")], foreground=[("selected", COR_TEXTO), ("active", COR_TEXTO)], bordercolor=[("selected", COR_GLOW), ("active", COR_BORDA)])
estilo.map(
    "TCombobox",
    fieldbackground=[("readonly", "#151522")],
    foreground=[("readonly", COR_TEXTO)],
)
estilo.configure("Treeview", background=COR_PANEL, fieldbackground=COR_PANEL, foreground=COR_TEXTO, rowheight=28, borderwidth=0)
estilo.configure("Treeview.Heading", background="#171229", foreground=COR_MUTED, relief="flat", font=("Helvetica Neue", 10, "bold"))
estilo.map("Treeview", background=[("selected", "#3c3489")], foreground=[("selected", "#ffffff")])
estilo.configure(
    "Dark.Vertical.TScrollbar",
    background="#211b2f",
    troughcolor="#050409",
    bordercolor="#050409",
    arrowcolor="#afa9ec",
    darkcolor="#211b2f",
    lightcolor="#211b2f",
)
estilo.map(
    "Dark.Vertical.TScrollbar",
    background=[("active", "#6d5aa8"), ("pressed", "#7f77dd")],
)

estilo.configure(
    "TButton",
    background="#151522",
    foreground="#f8f3ff",
    padding=(14, 9),
    relief="flat",
    borderwidth=0,
    focusthickness=0,
)
estilo.map(
    "TButton",
    background=[("active", "#211c36"), ("pressed", "#342d68")],
    foreground=[("active", "#ffffff"), ("pressed", "#ffffff")],
)
estilo.configure(
    "PremiumAction.TButton",
    background="#3c3489",
    foreground="#EEEDFE",
    padding=(16, 9),
    relief="flat",
    borderwidth=0,
    focusthickness=0,
)
estilo.map(
    "PremiumAction.TButton",
    background=[("active", "#655bd1"), ("pressed", "#352f75")],
    foreground=[("active", "#ffffff"), ("pressed", "#ffffff")],
)
estilo.configure(
    "PremiumGreen.TButton",
    background="#0f4a36",
    foreground="#eafff5",
    padding=(16, 10),
    relief="flat",
    borderwidth=0,
    focusthickness=0,
)
estilo.map(
    "PremiumGreen.TButton",
    background=[("active", "#1a7d56"), ("pressed", "#0b392b")],
    foreground=[("active", "#ffffff"), ("pressed", "#ffffff")],
)
estilo.configure(
    "PremiumRed.TButton",
    background="#5b1e1e",
    foreground="#fff0f0",
    padding=(16, 10),
    relief="flat",
    borderwidth=0,
    focusthickness=0,
)
estilo.map(
    "PremiumRed.TButton",
    background=[("active", "#7f2d2d"), ("pressed", "#431515")],
    foreground=[("active", "#ffffff"), ("pressed", "#ffffff")],
)

estilo.configure(
    "TNotebook",
    background=COR_BG,
    borderwidth=0,
)
estilo.configure(
    "TNotebook.Tab",
    background=COR_BG,
    foreground=COR_MUTED,
    padding=(12, 8),
    borderwidth=0,
)
estilo.map(
    "TNotebook.Tab",
    background=[("selected", "#171229"), ("active", "#171229")],
    foreground=[("selected", COR_TEXTO), ("active", COR_TEXTO)],
    bordercolor=[("selected", COR_BORDA), ("active", COR_BORDA)],
)

# A interface pode ficar compacta ao lado da IQ ou ocupar a tela inteira.
# O conteúdo interno rola sem esconder os controles e a análise inferior.
estrutura = ttk.Frame(janela)
estrutura.pack(fill="both", expand=True)
canvas = tk.Canvas(estrutura, highlightthickness=0, bg=COR_BG)
barra_vertical = ttk.Scrollbar(
    estrutura, orient="vertical", command=canvas.yview,
    style="Dark.Vertical.TScrollbar",
)
canvas.configure(yscrollcommand=barra_vertical.set)
barra_vertical.pack(side="right", fill="y")
canvas.pack(side="left", fill="both", expand=True)

conteudo = ttk.Frame(canvas)
janela_conteudo = canvas.create_window((0, 0), window=conteudo, anchor="nw")


def ajustar_rolagem(_evento=None):
    canvas.configure(scrollregion=canvas.bbox("all"))


def ajustar_largura(evento):
    canvas.itemconfigure(janela_conteudo, width=evento.width)


def rolar_com_mouse(evento):
    if evento.delta:
        canvas.yview_scroll(-1 if evento.delta > 0 else 1, "units")


def rolar_pagina_sem_alterar_controle(evento):
    """A roda move somente a página; nunca troca ativo, estratégia ou aba."""
    rolar_com_mouse(evento)
    return "break"


conteudo.bind("<Configure>", ajustar_rolagem)
canvas.bind("<Configure>", ajustar_largura)
janela.bind_all("<MouseWheel>", rolar_com_mouse)
janela.bind_class("TCombobox", "<MouseWheel>", rolar_pagina_sem_alterar_controle)
janela.bind_class("TNotebook", "<MouseWheel>", rolar_pagina_sem_alterar_controle)

CAMINHOS_LOGO = (
    os.path.join(PASTA_PROJETO, "assets", "logo-bft.jpg"),
    "/Users/bigfootbrz/Downloads/mt4/HOTMART/logo bigfootwin-100.jpg",
)
logo_bft = None
for caminho_logo in CAMINHOS_LOGO:
    try:
        imagem_logo = Image.open(caminho_logo).convert("RGBA")
        # A marca original vem sobre um quadrado branco. No cabeçalho escuro,
        # retiramos apenas esse fundo e clareamos as letras pretas, preservando
        # integralmente o símbolo roxo da Big Foot Win.
        pixels = []
        for vermelho, verde, azul, alpha in imagem_logo.getdata():
            if vermelho > 242 and verde > 242 and azul > 242:
                pixels.append((255, 255, 255, 0))
            elif vermelho < 55 and verde < 55 and azul < 55:
                pixels.append((245, 239, 255, alpha))
            else:
                pixels.append((vermelho, verde, azul, alpha))
        imagem_logo.putdata(pixels)
        imagem_logo.thumbnail((210, 210), Image.Resampling.LANCZOS)
        logo_bft = ImageTk.PhotoImage(imagem_logo)
        break
    except (FileNotFoundError, OSError):
        continue
topo = criar_card_premium(conteudo, bg=COR_PANEL_ALT, padding=(0, 0), rel="flat")
topo.pack(fill="x", padx=18, pady=(12, 10))

hero_canvas = tk.Canvas(topo, width=640, height=220, bg=COR_BG, highlightthickness=0)
hero_canvas.pack(fill="x", padx=0, pady=0)
hero_canvas.bind("<Configure>", lambda evento: None)

caminho_hero = os.path.join(PASTA_PROJETO, "assets", "hero-bft.png")
hero_image = None
hero_image_data = None


def desenhar_hero_fallback(canvas, largura, altura):
    canvas.delete("hero_fallback")
    escala_x = largura / 640.0
    escala_y = altura / 220.0

    def sx(v):
        return v * escala_x

    def sy(v):
        return v * escala_y

    canvas.create_rectangle(0, 0, largura, altura, fill=COR_BG, outline="", tags=("hero_fallback",))
    for y in (42, 84, 126, 168, 210):
        canvas.create_line(0, sy(y), largura, sy(y), fill=COR_BORDA, width=1, tags=("hero_fallback",))

    pontos = ((410, 180, 132), (438, 150, 102), (466, 170, 118),
              (494, 128, 72), (522, 148, 92), (550, 104, 48),
              (578, 122, 66), (606, 82, 26))
    for indice, (x, base, topo) in enumerate(pontos):
        cor = "#356c55" if indice % 3 else "#744044"
        canvas.create_line(sx(x), sy(topo - 14), sx(x), sy(base + 14), fill=cor, width=2, tags=("hero_fallback",))
        canvas.create_rectangle(sx(x - 9), sy(topo), sx(x + 9), sy(base), fill=cor, outline="", tags=("hero_fallback",))
    canvas.create_line(sx(390), sy(180), sx(620), sy(38), fill=COR_GLOW, width=3, smooth=True, tags=("hero_fallback",))

    centro_x = largura * 0.57
    if logo_bft is not None:
        canvas.create_image(155, 108, image=logo_bft, anchor="center", tags=("hero_fallback",))
    else:
        canvas.create_text(155, 108, text="BIG FOOT\nWIN", fill=COR_TEXTO,
                           font=("Arial", 20, "bold"), justify="center", tags=("hero_fallback",))

    canvas.create_text(
        centro_x, sy(88), text=NOME_COMPLETO_APP, fill=COR_TEXTO,
        font=("Arial", 36, "bold"),
        anchor="center", tags=("hero_fallback",),
    )
    canvas.create_text(
        centro_x, sy(132), text="ULTRA POWER • CONFLUÊNCIA • EXECUÇÃO",
        fill="#afa9ec", font=("Arial", 12, "bold"),
        anchor="center", tags=("hero_fallback",),
    )

    return

    for y, cor in enumerate(["#0a0813", "#150d22", "#1d1235", "#171229"]):
        canvas.create_rectangle(sx(0), sy(y * 60), sx(640), sy((y + 1) * 60), fill=cor, outline="", tags=("hero_fallback",))

    canvas.create_rectangle(sx(0), sy(0), sx(640), sy(260), fill="", outline="")
    for x in range(20, 620, 28):
        altura_val = 100 + ((x // 28) % 4) * 25
        x1 = sx(x)
        x2 = sx(x + 12)
        y_top = sy(205 - altura_val)
        y_bottom = sy(205)
        canvas.create_rectangle(x1, y_top, x2, y_bottom, fill="#20c997", outline="", tags=("hero_fallback",))
        canvas.create_rectangle(x1, sy(205 - altura_val - 28), x2, y_top, fill="#ef4444", outline="", tags=("hero_fallback",))
        canvas.create_line(x1 + sx(6), y_bottom, x1 + sx(6), y_top, fill="#c5f7ea", width=max(1, round(1 * escala_x)), tags=("hero_fallback",))

    for x in range(10, 580, 26):
        canvas.create_line(sx(x), sy(150), sx(x + 15), sy(82), fill="#4c1d95", width=max(1, round(2 * escala_x)), tags=("hero_fallback",))
        canvas.create_line(sx(x + 10), sy(82), sx(x + 28), sy(150), fill="#7f77dd", width=max(1, round(2 * escala_x)), tags=("hero_fallback",))

    canvas.create_rectangle(sx(38), sy(58), sx(330), sy(220), fill="#0b1220", outline="#7f77dd", width=max(1, round(2 * escala_x)), tags=("hero_fallback",))
    canvas.create_line(sx(44), sy(87), sx(322), sy(87), fill="#58f0c5", width=max(1, round(2 * escala_x)), tags=("hero_fallback",))
    canvas.create_line(sx(44), sy(132), sx(322), sy(132), fill="#44b6ff", width=max(1, round(2 * escala_x)), tags=("hero_fallback",))
    canvas.create_line(sx(44), sy(178), sx(322), sy(178), fill="#f59e0b", width=max(1, round(2 * escala_x)), tags=("hero_fallback",))
    for i in range(10):
        x1 = sx(60 + i * 25)
        y1 = sy(195 - (i % 5) * 14)
        y2 = sy(195)
        canvas.create_rectangle(x1, y1, x1 + sx(12), y2, fill="#34d399" if i % 2 else "#f87171", outline="", tags=("hero_fallback",))

    canvas.create_oval(sx(410), sy(40), sx(620), sy(170), fill="#a78bfa", outline="#f3e8ff", width=max(1, round(2 * escala_x)), tags=("hero_fallback",))
    canvas.create_polygon(
        sx(430), sy(180),
        sx(490), sy(80),
        sx(545), sy(70),
        sx(585), sy(22),
        sx(636), sy(75),
        sx(670), sy(180),
        sx(640), sy(225),
        sx(585), sy(240),
        sx(533), sy(234),
        sx(485), sy(252),
        sx(435), sy(225),
        fill="#a78bfa",
        outline="#e9d5ff",
        width=max(1, round(2 * escala_x)),
        tags=("hero_fallback",),
    )
    canvas.create_polygon(
        sx(465), sy(230),
        sx(500), sy(170),
        sx(548), sy(165),
        sx(599), sy(233),
        sx(642), sy(255),
        sx(606), sy(283),
        sx(530), sy(286),
        sx(472), sy(272),
        fill="#7c3aed",
        outline="#d8b4fe",
        width=max(1, round(2 * escala_x)),
        tags=("hero_fallback",),
    )
    canvas.create_line(sx(490), sy(235), sx(520), sy(285), fill="#f5d0fe", width=max(2, round(4 * escala_x)), tags=("hero_fallback",))
    canvas.create_line(sx(585), sy(240), sx(615), sy(292), fill="#f5d0fe", width=max(2, round(4 * escala_x)), tags=("hero_fallback",))
    canvas.create_line(sx(545), sy(170), sx(562), sy(110), fill="#ffffff", width=max(2, round(3 * escala_x)), tags=("hero_fallback",))
    canvas.create_oval(sx(474), sy(80), sx(514), sy(124), fill="#f0abfc", outline="", tags=("hero_fallback",))
    canvas.create_oval(sx(535), sy(55), sx(600), sy(124), fill="#f0abfc", outline="", tags=("hero_fallback",))
    canvas.create_oval(sx(590), sy(82), sx(628), sy(120), fill="#f0abfc", outline="", tags=("hero_fallback",))

    canvas.create_rectangle(sx(220), sy(18), sx(670), sy(120), fill="#100b18", outline="#7f77dd", width=max(1, round(2 * escala_x)), tags=("hero_fallback",))
    canvas.create_rectangle(sx(232), sy(26), sx(658), sy(112), fill="#140f22", outline="#afa9ec", width=max(1, round(1.5 * escala_x)), tags=("hero_fallback",))
    canvas.create_line(sx(240), sy(54), sx(650), sy(54), fill="#7c3aed", width=max(1, round(2 * escala_x)), tags=("hero_fallback",))
    canvas.create_line(sx(240), sy(78), sx(650), sy(78), fill="#a78bfa", width=max(1, round(1.7 * escala_x)), tags=("hero_fallback",))
    canvas.create_text(sx(258), sy(38), text=NOME_COMPLETO_APP, fill="#4c1d95", font=("Arial", max(24, round(44 * escala_x)), "bold"), anchor="w", tags=("hero_fallback",))
    canvas.create_text(sx(256), sy(36), text=NOME_COMPLETO_APP, fill="#f1effb", font=("Arial", max(24, round(44 * escala_x)), "bold"), anchor="w", tags=("hero_fallback",))

    if logo_bft is not None:
        canvas.create_image(sx(108), sy(152), image=logo_bft, anchor="center", tags=("hero_fallback",))


def atualizar_hero_canvas(evento=None):
    largura = max(640, int(topo.winfo_width() - 10))
    altura = 220
    hero_canvas.configure(width=largura, height=altura)
    hero_canvas.delete("all")
    global hero_image
    if os.path.exists(caminho_hero):
        try:
            imagem_hero = Image.open(caminho_hero)
            imagem_hero = imagem_hero.resize((largura, altura), Image.Resampling.LANCZOS)
            hero_image = ImageTk.PhotoImage(imagem_hero)
            hero_canvas.create_image(0, 0, image=hero_image, anchor="nw")
        except Exception:
            hero_image = None
            desenhar_hero_fallback(hero_canvas, largura, altura)
    else:
        desenhar_hero_fallback(hero_canvas, largura, altura)


topo.bind("<Configure>", atualizar_hero_canvas)
if os.path.exists(caminho_hero):
    try:
        imagem_hero = Image.open(caminho_hero)
        imagem_hero = imagem_hero.resize((640, 220), Image.Resampling.LANCZOS)
        hero_image = ImageTk.PhotoImage(imagem_hero)
        hero_canvas.create_image(0, 0, image=hero_image, anchor="nw")
    except Exception:
        hero_image = None
        desenhar_hero_fallback(hero_canvas, 640, 220)
else:
    desenhar_hero_fallback(hero_canvas, 640, 220)

linha_titulo = tk.Frame(topo, bg=COR_PANEL_ALT)
linha_titulo.pack(fill="x", pady=(0, 4), padx=12)

status = tk.Label(
    linha_titulo, text="Status: PARADO — MODO TESTE",
    font=("Arial", 11, "bold"), bg=COR_PANEL_ALT, fg=COR_TEXTO,
)
status.pack(side="left", pady=8)
tk.Label(
    linha_titulo, text="●  BFT WIN LAB",
    font=("Arial", 9, "bold"), bg=COR_PANEL_ALT, fg="#97c459",
).pack(side="right", pady=8)

# O antigo hero permanece apenas como implementação de fallback, mas deixa de
# ocupar a tela. A referência HTML usa uma barra compacta com marca, produto e
# estado operacional; esta é agora a única abertura visual do aplicativo.
topo.pack_forget()
topbar = criar_card_premium(conteudo, bg=COR_PANEL, padding=(14, 12), rel="flat")
topbar.pack(fill="x", padx=18, pady=(14, 12))

marca = tk.Frame(topbar, bg="#3c3489", width=42, height=42, highlightthickness=1,
                 highlightbackground="#655bd1")
marca.pack(side="left")
marca.pack_propagate(False)

logo_topbar = None
try:
    imagem_marca = Image.open(CAMINHOS_LOGO[0]).convert("RGBA")
    pixels_marca = []
    for vermelho, verde, azul, alpha in imagem_marca.getdata():
        if vermelho > 242 and verde > 242 and azul > 242:
            pixels_marca.append((255, 255, 255, 0))
        elif vermelho < 55 and verde < 55 and azul < 55:
            pixels_marca.append((241, 239, 251, alpha))
        else:
            pixels_marca.append((vermelho, verde, azul, alpha))
    imagem_marca.putdata(pixels_marca)
    bbox_marca = imagem_marca.getbbox()
    if bbox_marca:
        esquerda, topo_bbox, direita, base_bbox = bbox_marca
        altura_simbolo = max(1, int((base_bbox - topo_bbox) * 0.66))
        imagem_marca = imagem_marca.crop(
            (esquerda, topo_bbox, direita, min(base_bbox, topo_bbox + altura_simbolo))
        )
    imagem_marca.thumbnail((34, 34), Image.Resampling.LANCZOS)
    logo_topbar = ImageTk.PhotoImage(imagem_marca)
except (FileNotFoundError, OSError):
    logo_topbar = None

if logo_topbar is not None:
    tk.Label(marca, image=logo_topbar, bg="#3c3489").pack(expand=True)
else:
    canvas_marca = tk.Canvas(marca, width=40, height=40, bg="#3c3489", highlightthickness=0)
    canvas_marca.pack(fill="both", expand=True)
    canvas_marca.create_line(8, 29, 17, 20, 23, 25, 33, 12, fill="#eeedfe", width=2)
    canvas_marca.create_line(28, 12, 33, 12, 33, 17, fill="#eeedfe", width=2)

identidade = tk.Frame(topbar, bg=COR_PANEL)
identidade.pack(side="left", padx=(12, 0))
tk.Label(
    identidade, text="BFT Winbot", bg=COR_PANEL, fg=COR_TEXTO,
    font=("Helvetica Neue", 14, "bold"), anchor="w",
).pack(anchor="w")
tk.Label(
    identidade, text="Cinematic Trading Intelligence • 3.0", bg=COR_PANEL,
    fg=COR_MUTED, font=("Helvetica Neue", 9), anchor="w",
).pack(anchor="w", pady=(2, 0))

status_pill = tk.Frame(
    topbar, bg="#151522", highlightthickness=1,
    highlightbackground=COR_BORDA, padx=12, pady=7,
)
status_pill.pack(side="right")
tk.Label(
    status_pill, text="●", bg="#151522", fg=COR_ATENCAO,
    font=("Helvetica Neue", 10, "bold"),
).pack(side="left", padx=(0, 6))
status = tk.Label(
    status_pill, text="Parado — modo teste", bg="#151522", fg="#cecbf6",
    font=("Helvetica Neue", 9, "bold"),
)
status.pack(side="left")

# Começa obrigatoriamente desconectado. Uma futura leitora visual atualizará
# estes campos somente depois de confirmar a tela e a conta de prática.
estado_iq = EstadoConexaoIq()
linhas_iq = estado_iq.linhas_painel()
painel_iq = criar_card_premium(conteudo, bg=COR_PANEL, padding=(14, 14), rel="flat")
painel_iq.pack(fill="x", padx=18, pady=(0, 8))
try:
    painel_iq.configure(style="Premium.TLabelframe")
except Exception:
    pass

for child in painel_iq.winfo_children():
    try:
        child.configure(background=COR_PANEL_ALT)
    except Exception:
        pass

iq_conexao_var = tk.StringVar(value=f"IQ: {linhas_iq['conexao']}")
iq_conta_var = tk.StringVar(value="Plataforma: AGUARDANDO CONFIRMAÇÃO")
iq_leitura_var = tk.StringVar(value=linhas_iq["leitura"])
iq_trava_var = tk.StringVar(value="Entrada: AGUARDANDO LEITURA")
conta_tipo_var = tk.StringVar(value="DEMO")
conta_status_var = tk.StringVar(value="Confirmação de conta: não exigida nesta fase")

cards = tk.Frame(painel_iq, bg=COR_PANEL)
cards.pack(fill="x")

banca_var = tk.StringVar(value="—")
payout_resumo_var = tk.StringVar(value="—")
confluencia_resumo_var = tk.StringVar(value="—")
entrada_resumo_var = tk.StringVar(value="Aguardando")

metricas = tk.Frame(cards, bg=COR_PANEL)
metricas.pack(fill="x", pady=(0, 12))

for nome, valor_var, cor_card, cor_label in (
    ("Banca operacional", banca_var, "#151522", "#F1EFFB"),
    ("Payout / fonte", payout_resumo_var, "#151522", "#97C459"),
    ("Confluência", confluencia_resumo_var, "#151522", "#AFA9EC"),
    ("Status entrada", entrada_resumo_var, "#1b1117", "#F09595"),
):
    frame_metric = tk.Frame(
        metricas, bg=cor_card, bd=0, relief="flat", padx=14, pady=11,
        highlightthickness=1, highlightbackground=COR_BORDA,
    )
    frame_metric.pack(
        side="left", fill="both", expand=True,
        padx=(0, 8) if nome != "Entrada" else (0, 0),
    )
    tk.Label(
        frame_metric, text=nome, font=("Helvetica Neue", 9),
        fg=COR_MUTED if nome != "Entrada" else "#F09595",
        bg=cor_card, anchor="w",
    ).pack(fill="x")
    tk.Label(
        frame_metric, textvariable=valor_var,
        font=("Helvetica Neue", 14, "bold"), fg=cor_label,
        bg=cor_card, anchor="w",
    ).pack(fill="x", pady=(4, 0))

chart_header = tk.Frame(cards, bg=COR_PANEL)
chart_header.pack(fill="x", pady=(0, 8))
tk.Label(
    chart_header, textvariable=iq_leitura_var, bg="#151522", fg=COR_MUTED,
    font=("Helvetica Neue", 9), padx=10, pady=5,
).pack(side="left")
tk.Label(
    chart_header, textvariable=payout_resumo_var, bg=COR_PANEL,
    fg="#97C459", font=("Helvetica Neue", 9, "bold"),
).pack(side="right")

chart_area = tk.Frame(
    cards, bg=COR_BG_DEEP, bd=0, relief="flat",
    highlightthickness=1, highlightbackground=COR_BORDA,
)
chart_area.pack(fill="x", pady=(0, 12))

chart_canvas = tk.Canvas(chart_area, width=900, height=220, bg=COR_BG_DEEP, highlightthickness=0)
chart_canvas.pack(fill="both", expand=True)
ultimo_evento_dashboard = None


def desenhar_grafico_responsivo(canvas, largura=900, altura=220):
    canvas.delete("chart")
    largura_real = max(620, largura)
    escala_x = largura_real / 900.0
    escala_y = altura / 220.0

    for y in (30, 80, 130, 180):
        canvas.create_line(
            18, int(y * escala_y), largura_real - 18, int(y * escala_y),
            fill="#242039", width=1, tags=("chart",)
        )

    canvas.create_text(
        largura_real / 2,
        altura / 2,
        text="AGUARDANDO DADOS REAIS",
        fill="#716b92",
        font=("Helvetica Neue", 10),
        tags=("chart",),
    )


def ajustar_grafico_canvas(evento=None):
    largura = max(620, chart_area.winfo_width() - 10)
    altura = 220
    chart_canvas.configure(width=largura, height=altura)
    if ultimo_evento_dashboard is not None and "desenhar_grafico_velas" in globals():
        desenhar_grafico_velas(
            chart_canvas,
            ultimo_evento_dashboard,
            ultimo_evento_dashboard.get("ativo", "—"),
            "DADOS REAIS BFT WIN",
        )
    else:
        desenhar_grafico_responsivo(chart_canvas, largura=largura, altura=altura)


chart_area.bind("<Configure>", ajustar_grafico_canvas)
desenhar_grafico_responsivo(chart_canvas, largura=900, altura=220)

card_status = criar_card_premium(cards, bg=COR_CARD_ALT, padding=(0, 0), rel="flat")
# O resumo técnico continua alimentado pela lógica, mas a abertura segue o HTML:
# métricas, gráfico e ações. Os detalhes aparecem nas abas operacionais.

for text_var, pad_top, pad_bottom in (
    (iq_conexao_var, 8, 2),
    (iq_trava_var, 2, 8),
):
    tk.Label(
        card_status,
        textvariable=text_var,
        foreground=COR_TEXTO if text_var in (iq_conexao_var, iq_conta_var) else "#afa9ec" if text_var is iq_leitura_var else "#f09595",
        background=COR_CARD_ALT,
        anchor="w",
        justify="left",
    ).pack(anchor="w", padx=10, pady=(pad_top, pad_bottom), fill="x")

seletor_conta = ttk.Combobox(
    painel_iq,
    textvariable=conta_tipo_var,
    values=["DEMO", "REAL"],
    state="readonly",
    width=28,
)
seletor_conta.set("DEMO")

tk.Label(
    painel_iq,
    textvariable=conta_status_var,
    bg=COR_PANEL_ALT,
    fg="#afa9ec",
    anchor="w",
    justify="left",
)

status_30s = criar_card_premium(cards, bg=COR_PANEL_ALT, padding=(0, 0), rel="flat")
# Os mesmos estados alimentam os quatro cartões superiores. Este bloco técnico
# continua existindo para preservar as atualizações, mas não duplica a leitura
# na nova composição compacta.

status_30s_payout = tk.StringVar(value="PAYOUT: —")
status_30s_confluencia = tk.StringVar(value="CONFLUÊNCIA: —")
status_30s_entrada = tk.StringVar(value="ENTRADA: AGUARDANDO LEITURA")
status_30s_frames = {}
status_30s_labels = {}

linhas_status = tk.Frame(status_30s, bg=COR_PANEL_ALT)
linhas_status.pack(fill="x")

for chave, label_var, cor in (
    ("payout", status_30s_payout, "#3c3489"),
    ("confluencia", status_30s_confluencia, "#5149a8"),
    ("entrada", status_30s_entrada, "#5a4623"),
):
    frame_item = tk.Frame(
        linhas_status,
        bg=cor,
        bd=1,
        relief="flat",
        padx=8,
        pady=6,
        highlightthickness=1,
        highlightbackground=COR_BORDA,
        highlightcolor=COR_GLOW,
    )
    frame_item.pack(fill="x", pady=3)
    label_item = tk.Label(
        frame_item,
        textvariable=label_var,
        bg=cor,
        fg="#ffffff",
        font=("Arial", 10, "bold"),
        anchor="w",
        justify="left",
    )
    label_item.pack(fill="x")
    status_30s_frames[chave] = frame_item
    status_30s_labels[chave] = label_item


def atualizar_badges_status_30s(
    payout=None, confluencia=None, mercado=None, sinal=None
):
    mercado_aberto = mercado == "MERCADO ABERTO"
    if mercado_aberto:
        status_30s_payout.set("DADOS: ONLINE")
        payout_resumo_var.set("ONLINE")
        payout_cor = "#214c3f"
    elif payout is None:
        status_30s_payout.set("PAYOUT: —")
        payout_resumo_var.set("—")
        payout_cor = "#3c3489"
    else:
        status_30s_payout.set(f"PAYOUT: {payout:.0%}")
        payout_resumo_var.set(f"{payout:.0%}")
        payout_cor = "#3c3489"

    if confluencia is None:
        status_30s_confluencia.set("CONFLUÊNCIA: —")
        confluencia_resumo_var.set("—")
        confluencia_cor = "#5149a8"
    else:
        status_30s_confluencia.set(f"CONFLUÊNCIA: {confluencia}/10 ({(confluencia/10):.0%})")
        confluencia_resumo_var.set("Alta" if confluencia >= 8 else "Média" if confluencia >= 6 else "Baixa")
        confluencia_cor = "#5149a8"

    if confluencia is None or (not mercado_aberto and payout is None):
        entrada_text = "ENTRADA: AGUARDANDO LEITURA"
        entrada_resumo_var.set("Aguardando")
        entrada_cor = "#3c3489"
    elif (
        confluencia >= 7.5
        and sinal in {"ALTA", "BAIXA", "CALL", "PUT"}
        and (mercado_aberto or payout > 0.80)
    ):
        entrada_text = "ENTRADA: LIBERADA"
        entrada_resumo_var.set("Liberada")
        entrada_cor = "#365314"
    else:
        entrada_text = "ENTRADA: FORA DOS CRITÉRIOS"
        entrada_resumo_var.set("Aguardando critérios")
        entrada_cor = "#6b4f20"

    status_30s_entrada.set(entrada_text)

    for chave, label_var, cor in (
        ("payout", status_30s_payout, payout_cor),
        ("confluencia", status_30s_confluencia, confluencia_cor),
        ("entrada", status_30s_entrada, entrada_cor),
    ):
        status_30s_frames[chave].configure(bg=cor)
        status_30s_labels[chave].configure(bg=cor)


monitoramento_automatico = False
agendamento_monitor = None
agendamento_captura_periodica = None
inicio_otc_pendente = None
conta_demo_confirmada = False
conta_real_confirmada = False
tipo_conta_ativa = "NENHUMA"
captura_visual_atual = None
payout_visual_atual = None
tentativa_permissao_pendente = False
executor_demo_iq = ExecutorDemoIq()
MODO_PRATICA_UI = "OPERAR AUTOMÁTICO — CONTA PRÁTICA"
MODO_REAL_UI = "OPERAR AUTOMÁTICO — CONTA REAL"


def invalidar_leitura_visual_atual():
    """Descarta captura e payout antigos para que o OTC sempre falhe fechado."""
    global captura_visual_atual, payout_visual_atual
    captura_visual_atual = None
    payout_visual_atual = None
    atualizar_payout_atual(None)
    campos = globals().get("campos_por_mercado", {}).get("OTC")
    if campos and campos.get("payout") is not None:
        campos["payout"].configure(state="normal")
        campos["payout"].delete(0, tk.END)
        campos["payout"].insert(0, "—")
        campos["payout"].configure(state="readonly")


def modo_para_motor(modo_interface):
    if modo_interface == MODO_PRATICA_UI:
        return "AUTOMÁTICO DEMO"
    if modo_interface == MODO_REAL_UI:
        return "AUTOMÁTICO REAL"
    return modo_interface


def plataforma_confirmada_para_modo(modo_interface):
    if modo_interface in {MODO_PRATICA_UI, MODO_REAL_UI}:
        return plataforma_confirmada == plataforma_ativa_var.get()
    return True


def conectar_conta(tipo_conta=None):
    """Espelha a sessão aberta; nunca recebe usuário ou senha."""
    global conta_demo_confirmada, conta_real_confirmada, tipo_conta_ativa
    if tipo_conta is None:
        tipo_conta = conta_tipo_var.get().upper()
    conta_demo_confirmada = False
    conta_real_confirmada = False
    tipo_conta_ativa = "NENHUMA"
    iq_conta_var.set("Conta: aguardando confirmação visual...")
    plataforma = plataforma_ativa_var.get() if "plataforma_ativa_var" in globals() else "IQ Option"
    iq_trava_var.set(f"Entrada: AGUARDANDO — abra o seletor de conta da {plataforma}")
    conta_status_var.set(f"Status da conta: aguardando {tipo_conta.lower()}...")

    if tipo_conta == "REAL":
        texto = (
            "O BFT será escondido por 15 segundos.\n\n"
            f"Nesse tempo, abra na {plataforma} o menu do saldo/conta e deixe visível o texto "
            "REAL ACCOUNT ou CONTA REAL.\n\n"
            "Não digite sua senha no BFT."
        )
        titulo = "Espelhar conta real"
    else:
        texto = (
            "O BFT será escondido por 15 segundos.\n\n"
            f"Nesse tempo, abra na {plataforma} o menu do saldo/conta e deixe visível o texto "
            "PRACTICE ACCOUNT, DEMO ACCOUNT ou CONTA DE PRÁTICA.\n\n"
            "Não digite sua senha no BFT."
        )
        titulo = "Espelhar conta demo"

    messagebox.showinfo(titulo, texto)
    janela.withdraw()
    janela.after(15000, lambda: confirmar_conta_na_tela(tipo_conta))


def conectar_conta_demo():
    conectar_conta("DEMO")


def conectar_conta_real():
    conectar_conta("REAL")


def confirmar_conta_na_tela(tipo_conta="DEMO"):
    global conta_demo_confirmada, conta_real_confirmada, tipo_conta_ativa
    resultado = testar_captura(caminho=f"/private/tmp/bft_iq_conta_{tipo_conta.lower()}.png")
    if resultado.sucesso:
        conta = ler_tipo_conta(resultado.caminho)
    else:
        conta = None
    janela.deiconify()
    janela.lift()

    conta_demo_confirmada = bool(conta and conta.sucesso and conta.demo)
    conta_real_confirmada = bool(
        conta and conta.sucesso and conta.tipo == "REAL"
    )
    tipo_conta_ativa = "DEMO" if conta_demo_confirmada else "REAL" if conta_real_confirmada else "NENHUMA"

    if conta_demo_confirmada and tipo_conta == "DEMO":
        iq_conexao_var.set(f"{plataforma_ativa_var.get()}: SESSÃO ESPELHADA — DEMO")
        iq_conta_var.set("Conta: PRÁTICA CONFIRMADA")
        conta_status_var.set("Status da conta: DEMO confirmada")
        iq_trava_var.set("Entrada: DEMO pronta para validar sinais fortes")
        messagebox.showinfo(
            "BFT Winbot",
            "Conta de prática confirmada. Nenhuma senha foi copiada ou armazenada.",
        )
    elif conta_real_confirmada and tipo_conta == "REAL":
        iq_conexao_var.set(f"{plataforma_ativa_var.get()}: SESSÃO ESPELHADA — REAL")
        iq_conta_var.set("Conta: REAL CONFIRMADA")
        conta_status_var.set("Status da conta: REAL confirmada")
        iq_trava_var.set("Entrada: REAL confirmada — automático ainda desarmado")
        messagebox.showinfo(
            "BFT Winbot",
            "Conta real confirmada. Para armar uma entrada automática, selecione "
            "CONTA REAL no modo de operação e pressione INICIAR.",
        )
    else:
        mensagem = conta.mensagem if conta else resultado.mensagem
        iq_conta_var.set("Conta: NÃO CONFIRMADA")
        conta_status_var.set(f"Status da conta: {tipo_conta} não confirmada")
        iq_trava_var.set("Entrada: AGUARDANDO CONFIRMAÇÃO")
        messagebox.showwarning(f"Conta {tipo_conta.lower()} não confirmada", mensagem)


def confirmar_conta_demo_na_tela():
    confirmar_conta_na_tela("DEMO")


def agendar_captura_periodica():
    global agendamento_captura_periodica
    if agendamento_captura_periodica is not None:
        janela.after_cancel(agendamento_captura_periodica)
    agendamento_captura_periodica = janela.after(30000, executar_captura_periodica)


def executar_captura_periodica():
    global agendamento_captura_periodica, conta_demo_confirmada
    global conta_real_confirmada, tipo_conta_ativa, captura_visual_atual
    if not (monitoramento_automatico or plataforma_confirmada is not None):
        agendamento_captura_periodica = None
        return
    try:
        resultado = testar_captura(caminho="/private/tmp/bft_iq_30s.png")
    except Exception as erro:
        print(f"[BFT CAPTURA 30S] falha ao capturar: {erro}")
        agendamento_captura_periodica = janela.after(30000, executar_captura_periodica)
        return

    if not resultado.sucesso:
        invalidar_leitura_visual_atual()
        executor_demo_iq.desarmar_conta_real()
        iq_trava_var.set("Entrada: AGUARDANDO — leitura de 30s falhou")
        print(f"[BFT CAPTURA 30S] {resultado.mensagem}")
        agendamento_captura_periodica = janela.after(30000, executar_captura_periodica)
        return

    leitura_payout = ler_payout(resultado.caminho)
    leitura_ativo = ler_ativo(resultado.caminho)
    leitura_velas = ler_velas(resultado.caminho)
    leitura_botoes = ler_botoes(resultado.caminho)
    leitura_completa = (
        leitura_payout.sucesso
        and leitura_ativo.sucesso
        and leitura_velas.sucesso
        and plataforma_pronta_para_clique(leitura_botoes)
    )
    if not leitura_completa:
        invalidar_leitura_visual_atual()
        executor_demo_iq.desarmar_conta_real()
        iq_trava_var.set("Entrada: AGUARDANDO — leitura de 30s incompleta")
        agendamento_captura_periodica = janela.after(30000, executar_captura_periodica)
        return

    captura_visual_atual = resultado.caminho
    if leitura_payout.payout <= 0.80:
        iq_trava_var.set("Entrada: AGUARDANDO — payout abaixo de 80%")
    else:
        iq_trava_var.set("Entrada: PRONTA — payout validado em 30s e próxima vela em análise")
    iq_leitura_var.set(
        f"{leitura_ativo.ativo} • payout {leitura_payout.payout:.0%} • "
        f"{len(leitura_velas.velas)} velas • atualização a cada 30s"
    )
    atualizar_linha_central(leitura_ativo.ativo, leitura_payout.payout)
    snapshot_carregado, mensagem_snapshot = carregar_snapshot_visual_otc(
        leitura_ativo.ativo,
        leitura_velas.velas,
        leitura_payout.payout,
    )
    if not snapshot_carregado:
        invalidar_leitura_visual_atual()
        iq_trava_var.set(f"Entrada: AGUARDANDO — {mensagem_snapshot}")
    agendamento_captura_periodica = janela.after(30000, executar_captura_periodica)

def testar_permissao_iq(automatico=False):
    plataforma = plataforma_ativa_var.get() if "plataforma_ativa_var" in globals() else "IQ Option"
    iq_conexao_var.set(f"{plataforma}: PREPARANDO CAPTURA...")
    iq_trava_var.set("Entrada: AGUARDANDO LEITURA VISUAL")
    janela.withdraw()
    print("[BFT CAPTURA] Preparando captura da tela...")
    # Dá tempo para o macOS redesenhar a IQ sem o BFT na frente.
    janela.after(700, lambda: executar_teste_permissao_iq(automatico))


def abrir_ajustes_acessibilidade():
    """Abre a seção do macOS que autoriza os cliques via System Events."""
    try:
        destinos = (
            "x-apple.systempreferences:com.apple.settings.PrivacySecurity.extension?Privacy_Accessibility",
            "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
            "/System/Applications/System Settings.app",
        )
        abriu = False
        for destino in destinos:
            resultado = subprocess.run(
                ["/usr/bin/open", destino],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
            if resultado.returncode == 0:
                abriu = True
                break
        iq_trava_var.set("Entrada: AGUARDANDO — ative Python em Acessibilidade")
        if not abriu:
            messagebox.showinfo(
                "Liberar Acessibilidade",
                "Abra manualmente:\n\n"
                "Ajustes do Sistema > Privacidade e Segurança > Acessibilidade\n\n"
                "Ative PYTHON. Se ele não aparecer, use o botão + e adicione:\n"
                "/Library/Frameworks/Python.framework/Versions/3.14/Resources/Python.app\n\n"
                "Depois feche e abra novamente o BFT WIN.",
            )
    except (OSError, subprocess.SubprocessError) as erro:
        messagebox.showerror(
            "Acessibilidade do macOS",
            f"Não foi possível abrir os Ajustes automaticamente: {erro}",
        )


def abrir_interface_web():
    """Abre a interface web de tempo real em um processo separado."""
    import webbrowser
    caminho_web = os.path.join(PASTA_PROJETO, "web", "interface_tempo_real.py")
    if not os.path.exists(caminho_web):
        messagebox.showerror(
            "Interface Web",
            "Arquivo da interface web não encontrado.",
        )
        return
    subprocess.Popen(
        [sys.executable, caminho_web],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    webbrowser.open("http://127.0.0.1:8765")
    iq_trava_var.set("Entrada: INTERFACE WEB ABERTA EM http://127.0.0.1:8765")


def executar_teste_permissao_iq(automatico=False):
    global inicio_otc_pendente, monitoramento_automatico, captura_visual_atual
    global conta_demo_confirmada, conta_real_confirmada, tipo_conta_ativa
    global tentativa_permissao_pendente
    try:
        resultado = testar_captura()
    finally:
        janela.deiconify()
        janela.lift()

    if resultado.sucesso:
        print("[BFT CAPTURA] Imagem recebida. Lendo payout...")
        iq_leitura_var.set("Lendo payout da tela...")
        janela.update_idletasks()
        leitura_payout = ler_payout(resultado.caminho)
        print("[BFT CAPTURA] Lendo ativo selecionado...")
        iq_leitura_var.set("Lendo ativo selecionado...")
        janela.update_idletasks()
        leitura_ativo = ler_ativo(resultado.caminho)
        print("[BFT CAPTURA] Detectando velas fechadas...")
        iq_leitura_var.set("Detectando velas fechadas...")
        janela.update_idletasks()
        leitura_velas = ler_velas(resultado.caminho)
        print("[BFT CAPTURA] Conferindo área do gráfico...")
        leitura_botoes = ler_botoes(resultado.caminho)
        leitura_completa = (
            leitura_payout.sucesso
            and leitura_ativo.sucesso
            and leitura_velas.sucesso
            and plataforma_pronta_para_clique(leitura_botoes)
            and plataforma_confirmada == plataforma_ativa_var.get()
        )
        if leitura_completa:
            captura_visual_atual = resultado.caminho
            print("[BFT CAPTURA] Leitura completa. Validando snapshot...")
            snapshot_carregado, mensagem_snapshot = carregar_snapshot_visual_otc(
                leitura_ativo.ativo,
                leitura_velas.velas,
                leitura_payout.payout,
            )
            iq_conexao_var.set(f"{plataforma_ativa_var.get()}: LEITURA VISUAL ATIVA")
            iq_leitura_var.set(
                f"{leitura_ativo.ativo} • Payout {leitura_payout.payout:.0%} • "
                f"{len(leitura_velas.velas)} velas fechadas • "
                f"Botões: {'PRONTOS' if leitura_botoes.prontos else 'NÃO CONFIRMADOS'} • "
                f"Snapshot: {'CARREGADO' if snapshot_carregado else 'NÃO CARREGADO'}"
            )
            iq_conta_var.set(
                f"Plataforma confirmada: {plataforma_ativa_var.get()}"
            )
            iq_trava_var.set("Entrada: SINAL EM ANÁLISE")
            atualizar_linha_central(leitura_ativo.ativo, leitura_payout.payout)
            if snapshot_carregado and inicio_otc_pendente is not None:
                print("[BFT CAPTURA] Snapshot carregado. Iniciando modo selecionado...")
                continuar_inicio = inicio_otc_pendente
                inicio_otc_pendente = None
                if not monitoramento_automatico:
                    monitoramento_automatico = True
                    botao_monitor.config(text="PARAR ACOMPANHAMENTO DO ATIVO")
                    agendar_proxima_leitura()
                janela.after(100, continuar_inicio)
            if not automatico:
                messagebox.showinfo(
                    "BFT Winbot",
                    f"{leitura_ativo.mensagem}\n{leitura_payout.mensagem}\n"
                    f"{leitura_velas.mensagem}\n{leitura_botoes.mensagem}\n"
                    f"{mensagem_snapshot}\n\n"
                    "Em SOMENTE SINAIS não há clique. No OTC automático, o BFT "
                    "exige plataforma confirmada, par/gráfico reconhecido, payout e "
                    "confluência de pelo menos 80% antes da armação.",
                )
            if monitoramento_automatico or plataforma_confirmada is not None:
                agendar_captura_periodica()
        else:
            print("[BFT CAPTURA] Leitura incompleta; modo automático não iniciado.")
            # Falha fechado: uma tela de login, janela deslocada ou leitura
            # incompleta invalida a autorização demo e qualquer captura antiga.
            invalidar_leitura_visual_atual()
            executor_demo_iq.desarmar_conta_real()
            iq_conexao_var.set(f"{plataforma_ativa_var.get()}: CAPTURA OK • LEITURA INCOMPLETA")
            iq_conta_var.set(
                f"Plataforma: {plataforma_ativa_var.get()} • leitura incompleta"
            )
            iq_leitura_var.set("Leitura automática inválida • aguardando próximo ciclo")
            iq_trava_var.set("Entrada: AGUARDANDO LEITURA COMPLETA")
            motivos = [
                item.mensagem
                for item in (leitura_ativo, leitura_payout, leitura_velas, leitura_botoes)
                if not item.sucesso
            ]
            if not automatico:
                messagebox.showwarning("Leitura da IQ", "\n".join(motivos))
    else:
        print(f"[BFT CAPTURA] Falha: {resultado.mensagem}")
        invalidar_leitura_visual_atual()
        executor_demo_iq.desarmar_conta_real()
        iq_conexao_var.set(f"{plataforma_ativa_var.get()}: PERMISSÃO DE TELA NECESSÁRIA")
        iq_conta_var.set(
            f"Plataforma: {plataforma_ativa_var.get()} • tela indisponível"
        )
        iq_trava_var.set("Entrada: AGUARDANDO PERMISSÃO DA TELA")
        # Não mostrar um messagebox aqui: ele ficava em cima do botão
        # Permitir/Erlauben do próprio macOS. Damos tempo para o usuário
        # concluir o diálogo do sistema e repetimos uma única vez.
        if not automatico and not tentativa_permissao_pendente:
            tentativa_permissao_pendente = True
            iq_leitura_var.set(
                "Clique em PERMITIR na janela do macOS • nova tentativa em 8s"
            )
            iq_trava_var.set("Entrada: AGUARDANDO PERMISSÃO DA TELA")

            def repetir_apos_permissao():
                global tentativa_permissao_pendente
                tentativa_permissao_pendente = False
                testar_permissao_iq(automatico=False)

            janela.after(8000, repetir_apos_permissao)
    if automatico and monitoramento_automatico:
        agendar_proxima_leitura()
    if monitoramento_automatico or plataforma_confirmada is not None:
        agendar_captura_periodica()


ttk.Button(
    painel_iq,
    text="TESTAR LEITURA DA TELA",
    command=testar_permissao_iq,
).pack(pady=(6, 0))
ttk.Button(
    painel_iq,
    text="LIBERAR ACESSIBILIDADE PARA CLIQUES",
    command=abrir_ajustes_acessibilidade,
).pack(pady=(6, 0))
ttk.Button(
    painel_iq,
    text="ABRIR INTERFACE WEB (TEMPO REAL)",
    command=abrir_interface_web,
).pack(pady=(6, 0))


BROKER_ALIASES = {
    "IQ Option": ["IQ Option", "IQOption"],
    "Quotex": ["Quotex"],
    "Exnova": ["Exnova"],
    "Avallon": ["Avallon"],
    "Casa Trader": ["Casa Trader", "CasaTrader"],
    "Bullex": ["Bullex"],
}
plataforma_ativa_var = tk.StringVar(value="IQ Option")
plataforma_confirmada_var = tk.StringVar(
    value="Plataforma: AGUARDANDO CONFIRMAÇÃO"
)
plataforma_confirmada = None
coordenadas_iq_option = None
coordenadas_quotex = None
coordenadas_casa_trader = None
coordenadas_avallon = None
CAMINHO_CALIBRACAO_QUOTEX = os.path.expanduser(
    "~/Library/Application Support/BFT Winbot/calibracao_quotex.json"
)
CAMINHO_CALIBRACAO_IQ_OPTION = os.path.expanduser(
    "~/Library/Application Support/BFT Winbot/calibracao_iq_option.json"
)
CAMINHO_CALIBRACAO_CASA_TRADER = os.path.expanduser(
    "~/Library/Application Support/BFT Winbot/calibracao_casa_trader.json"
)
CAMINHO_CALIBRACAO_AVALLON = os.path.expanduser(
    "~/Library/Application Support/BFT Winbot/calibracao_avallon.json"
)


def rotulos_operacao_plataforma():
    return {
        "IQ Option": ("HIGHER", "LOWER"),
        "Quotex": ("CALL", "PUT"),
        "Casa Trader": ("COMPRAR", "VENDER"),
        "Avallon": ("BUY", "SELL"),
    }.get(plataforma_ativa_var.get(), ("ALTA", "BAIXA"))


def invalidar_confirmacao_plataforma(*_args):
    """Trocar a plataforma sempre exige uma nova confirmação explícita."""
    global plataforma_confirmada
    plataforma_confirmada = None
    invalidar_leitura_visual_atual()
    plataforma_confirmada_var.set("Plataforma: AGUARDANDO CONFIRMAÇÃO")
    executor = globals().get("executor_demo_iq")
    if executor is not None:
        executor.desarmar_conta_real()


def confirmar_plataforma_operacao():
    global plataforma_confirmada
    escolhida = plataforma_ativa_var.get().strip()
    if not escolhida:
        messagebox.showwarning("Plataforma", "Escolha a plataforma de operação.")
        return
    confirmou = messagebox.askyesno(
        "CONFIRMAR PLATAFORMA",
        f"Plataforma escolhida: {escolhida}\n\n"
        "Os próximos sinais armados usarão exclusivamente os botões desta "
        "plataforma. Confirma a escolha?",
        icon="warning",
    )
    if not confirmou:
        invalidar_confirmacao_plataforma()
        return
    plataforma_confirmada = escolhida
    plataforma_confirmada_var.set(f"Plataforma CONFIRMADA: {escolhida}")
    iq_conta_var.set(f"Plataforma operacional: {escolhida}")
    iq_trava_var.set("Entrada: AGUARDANDO ANÁLISE E ARMAÇÃO")


def plataforma_pronta_para_clique(leitura_botoes=None):
    """Confere a confirmação e a calibração da plataforma escolhida."""
    escolhida = plataforma_ativa_var.get()
    if plataforma_confirmada != escolhida:
        return False
    if escolhida == "IQ Option":
        return bool(
            coordenadas_iq_option
            or (leitura_botoes is not None and leitura_botoes.prontos)
        )
    calibracoes = {
        "Quotex": coordenadas_quotex,
        "Casa Trader": coordenadas_casa_trader,
        "Avallon": coordenadas_avallon,
    }
    return calibracoes.get(escolhida) is not None


def direcao_exibida(evento):
    sinal = str(evento.get("sinal") or "").upper()
    alta, baixa = rotulos_operacao_plataforma()
    if sinal == "ALTA" and float(evento.get("confluencia", 0)) >= 0.75:
        return alta
    if sinal == "BAIXA" and float(evento.get("confluencia", 0)) >= 0.75:
        return baixa
    return "AGUARDAR"


def carregar_calibracao_quotex():
    global coordenadas_quotex
    try:
        with open(CAMINHO_CALIBRACAO_QUOTEX, "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
        if all(chave in dados for chave in ("tela", "ALTA", "BAIXA")):
            coordenadas_quotex = dados
    except (OSError, ValueError, TypeError):
        coordenadas_quotex = None


def calibrar_quotex():
    """Registra os centros de CALL e PUT sem reutilizar a geometria da IQ."""
    global coordenadas_quotex
    plataforma_ativa_var.set("Quotex")
    pontos = {}

    def capturar(nome, proximo=None):
        try:
            import pyautogui
            posicao = pyautogui.position()
            pontos[nome] = [int(posicao.x), int(posicao.y)]
        except Exception as erro:
            janela.deiconify()
            messagebox.showerror("Calibração Quotex", f"Não foi possível ler o mouse: {erro}")
            return
        janela.deiconify()
        janela.lift()
        if proximo:
            messagebox.showinfo(
                "Calibração Quotex",
                "Agora coloque o ponteiro no centro do botão PUT/LOWER da Quotex. "
                "Depois de fechar esta mensagem você terá 5 segundos.",
            )
            janela.withdraw()
            janela.after(5000, lambda: capturar(proximo))
            return
        pontos["tela"] = [janela.winfo_screenwidth(), janela.winfo_screenheight()]
        coordenadas_quotex = pontos
        try:
            os.makedirs(os.path.dirname(CAMINHO_CALIBRACAO_QUOTEX), exist_ok=True)
            with open(CAMINHO_CALIBRACAO_QUOTEX, "w", encoding="utf-8") as arquivo:
                json.dump(coordenadas_quotex, arquivo)
        except OSError as erro:
            messagebox.showerror("Calibração Quotex", f"Não foi possível salvar: {erro}")
            return
        if "quotex_calibracao_status_var" in globals():
            quotex_calibracao_status_var.set("Calibração Quotex: PRONTA")
        messagebox.showinfo(
            "Calibração Quotex",
            "Botões CALL e PUT calibrados para esta tela. Faça uma operação apenas "
            "na conta prática para validar a posição.",
        )

    messagebox.showinfo(
        "Calibração Quotex",
        "Abra a Quotex na conta prática e coloque o ponteiro no centro do botão "
        "CALL/HIGHER. Depois de fechar esta mensagem você terá 5 segundos.",
    )
    janela.withdraw()
    janela.after(5000, lambda: capturar("ALTA", "BAIXA"))


carregar_calibracao_quotex()
quotex_calibracao_status_var = tk.StringVar(
    value=("Calibração Quotex: PRONTA" if coordenadas_quotex
           else "Calibração Quotex: PENDENTE")
)


def carregar_calibracao_visual(caminho):
    try:
        with open(caminho, "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
        if all(chave in dados for chave in ("tela", "ALTA", "BAIXA")):
            return dados
    except (OSError, ValueError, TypeError):
        pass
    return None


coordenadas_casa_trader = carregar_calibracao_visual(CAMINHO_CALIBRACAO_CASA_TRADER)
coordenadas_avallon = carregar_calibracao_visual(CAMINHO_CALIBRACAO_AVALLON)
coordenadas_iq_option = carregar_calibracao_visual(CAMINHO_CALIBRACAO_IQ_OPTION)
iq_option_calibracao_status_var = tk.StringVar(
    value=("Calibração IQ Option: PRONTA" if coordenadas_iq_option
           else "Calibração IQ Option: PADRÃO")
)
casa_trader_calibracao_status_var = tk.StringVar(
    value=("Calibração Casa Trader: PRONTA" if coordenadas_casa_trader
           else "Calibração Casa Trader: PENDENTE")
)
avallon_calibracao_status_var = tk.StringVar(
    value=("Calibração Avallon: PRONTA" if coordenadas_avallon
           else "Calibração Avallon: PENDENTE")
)


def calibrar_corretora_visual(plataforma, rotulo_alta, rotulo_baixa, caminho, status_var):
    """Calibra dois botões de uma corretora sem compartilhar coordenadas."""
    plataforma_ativa_var.set(plataforma)
    pontos = {}

    def capturar(nome, proximo=None):
        global coordenadas_iq_option, coordenadas_casa_trader, coordenadas_avallon
        try:
            import pyautogui
            posicao = pyautogui.position()
            pontos[nome] = [int(posicao.x), int(posicao.y)]
        except Exception as erro:
            janela.deiconify()
            messagebox.showerror(f"Calibração {plataforma}", f"Não foi possível ler o mouse: {erro}")
            return
        janela.deiconify()
        janela.lift()
        if proximo:
            messagebox.showinfo(
                f"Calibração {plataforma}",
                f"Agora coloque o ponteiro no centro do botão {rotulo_baixa}. "
                "Depois de fechar esta mensagem você terá 5 segundos.",
            )
            janela.withdraw()
            janela.after(5000, lambda: capturar(proximo))
            return
        pontos["tela"] = [janela.winfo_screenwidth(), janela.winfo_screenheight()]
        try:
            os.makedirs(os.path.dirname(caminho), exist_ok=True)
            with open(caminho, "w", encoding="utf-8") as arquivo:
                json.dump(pontos, arquivo)
        except OSError as erro:
            messagebox.showerror(f"Calibração {plataforma}", f"Não foi possível salvar: {erro}")
            return
        if plataforma == "IQ Option":
            coordenadas_iq_option = pontos
        elif plataforma == "Casa Trader":
            coordenadas_casa_trader = pontos
        else:
            coordenadas_avallon = pontos
        status_var.set(f"Calibração {plataforma}: PRONTA")
        messagebox.showinfo(
            f"Calibração {plataforma}",
            f"Botões {rotulo_alta} e {rotulo_baixa} calibrados para esta tela.",
        )

    messagebox.showinfo(
        f"Calibração {plataforma}",
        f"Abra a {plataforma} na conta prática e coloque o ponteiro no centro "
        f"do botão {rotulo_alta}. Depois de fechar esta mensagem você terá 5 segundos.",
    )
    janela.withdraw()
    janela.after(5000, lambda: capturar("ALTA", "BAIXA"))


def calibrar_casa_trader():
    calibrar_corretora_visual(
        "Casa Trader", "COMPRAR", "VENDER", CAMINHO_CALIBRACAO_CASA_TRADER,
        casa_trader_calibracao_status_var,
    )


def calibrar_iq_option():
    calibrar_corretora_visual(
        "IQ Option", "HIGHER", "LOWER", CAMINHO_CALIBRACAO_IQ_OPTION,
        iq_option_calibracao_status_var,
    )


def calibrar_avallon():
    calibrar_corretora_visual(
        "Avallon", "BUY", "SELL", CAMINHO_CALIBRACAO_AVALLON,
        avallon_calibracao_status_var,
    )


def abrir_plataforma(nome_plataforma, aliases=None, caminho_local=None):
    """Abre a plataforma escolhida sem salvar credenciais nem digitar senha."""
    candidatos = []
    if caminho_local and os.path.exists(caminho_local):
        candidatos.append(caminho_local)
    for nome in (aliases or []) + [nome_plataforma]:
        if nome and nome not in candidatos:
            candidatos.append(nome)
    for candidato in candidatos:
        try:
            if os.path.exists(candidato):
                resultado = subprocess.run(["open", candidato], capture_output=True, text=True, check=False)
            else:
                resultado = subprocess.run(["open", "-a", candidato], capture_output=True, text=True, check=False)
            if resultado.returncode == 0:
                return True
        except OSError:
            continue
    return False


def abrir_plataforma_segura(nome_plataforma):
    aliases = BROKER_ALIASES.get(nome_plataforma, [nome_plataforma])
    if abrir_plataforma(nome_plataforma, aliases=aliases):
        messagebox.showinfo(
            "Plataforma",
            f"{nome_plataforma} aberta. Faça o login manualmente e depois use a leitura da tela para validar o mercado.\n\nA senha não será salva nem digitada aqui.",
        )
        return True
    messagebox.showwarning(
        "Plataforma",
        f"Não foi possível abrir {nome_plataforma} automaticamente. Verifique se o app está instalado ou use o atalho da corretora.",
    )
    return False


def criar_aba_plataformas():
    aba = ttk.Frame(abas, padding=16)
    abas.add(aba, text="Plataformas")
    ttk.Label(
        aba,
        text="Launcher seguro de corretoras",
        font=("Arial", 17, "bold"),
    ).pack(pady=(0, 6))
    ttk.Label(
        aba,
        text=(
            "A automação começa depois do login manual. O app só abre a plataforma, "
            "confirma a tela e enxerga candles, payout e botões antes de disparar qualquer sinal."
        ),
        wraplength=620,
        justify="center",
    ).pack(pady=(0, 12))

    ttk.Label(aba, text="Plataforma ativa para leitura e clique:").pack()
    seletor_plataforma = ttk.Combobox(
        aba, textvariable=plataforma_ativa_var,
        values=["IQ Option", "Quotex", "Casa Trader", "Avallon"],
        state="readonly", width=28,
    )
    seletor_plataforma.pack(pady=(4, 12))

    ttk.Button(
        aba,
        text="CONFIRMAR PLATAFORMA PARA LEITURA E CLIQUE",
        command=confirmar_plataforma_operacao,
        style="PremiumAction.TButton",
    ).pack(fill="x", pady=(0, 6))
    ttk.Label(
        aba, textvariable=plataforma_confirmada_var,
        foreground="#97c459", font=("Arial", 10, "bold"),
    ).pack(pady=(0, 12))

    for broker in BROKER_ALIASES:
        ttk.Button(
            aba,
            text=f"ABRIR {broker.upper()}",
            command=lambda nome=broker: abrir_plataforma_segura(nome),
            width=30,
        ).pack(pady=6)

    ttk.Button(
        aba, text="CALIBRAR HIGHER/LOWER DA IQ OPTION",
        command=calibrar_iq_option, width=34,
    ).pack(pady=(12, 4))
    ttk.Button(
        aba, text="CALIBRAR BOTÕES CALL/PUT DA QUOTEX",
        command=calibrar_quotex, width=34,
    ).pack(pady=4)
    ttk.Button(
        aba, text="CALIBRAR COMPRAR/VENDER DA CASA TRADER",
        command=calibrar_casa_trader, width=38,
    ).pack(pady=4)
    ttk.Button(
        aba, text="CALIBRAR BUY/SELL DA AVALLON",
        command=calibrar_avallon, width=34,
    ).pack(pady=4)

    ttk.Label(
        aba,
        text=(
            "Mercado Aberto usa dados externos reais. OTC exige leitura visual "
            "do gráfico, par, timeframe e payout antes da armação."
        ),
        foreground="#8f7bd8",
        wraplength=620,
        justify="center",
    ).pack(pady=(12, 0))


plataforma_ativa_var.trace_add("write", invalidar_confirmacao_plataforma)


botoes_conta = tk.Frame(painel_iq, bg=COR_PANEL_ALT)
ttk.Label(
    painel_iq,
    text=(
        "Nesta fase a conta não é confirmada pelo BFT. A trava obrigatória é a "
        "plataforma escolhida; no OTC a leitura visual completa continua necessária."
    ),
    wraplength=860, justify="left",
).pack(fill="x", pady=(8, 6))

acoes_leitura = tk.Frame(painel_iq, bg=COR_PANEL)
acoes_leitura.pack(fill="x", pady=(2, 0))


def alternar_monitoramento():
    global monitoramento_automatico, agendamento_monitor
    campos = campos_por_mercado.get("OTC")
    if (
        not monitoramento_automatico
        and (not campos or campos["ativo"].get() == ATIVO_NAO_SELECIONADO)
    ):
        messagebox.showwarning(
            "Leitura por ativo",
            "Escolha na aba OTC somente o ativo que deseja acompanhar.",
        )
        return
    monitoramento_automatico = not monitoramento_automatico
    if monitoramento_automatico:
        botao_monitor.config(text="PARAR ACOMPANHAMENTO DO ATIVO")
        iq_conexao_var.set("IQ: MONITOR AUTOMÁTICO INICIANDO...")
        testar_permissao_iq(automatico=True)
    else:
        if agendamento_monitor is not None:
            janela.after_cancel(agendamento_monitor)
            agendamento_monitor = None
        botao_monitor.config(text="ACOMPANHAR SOMENTE O ATIVO ESCOLHIDO")
        iq_conexao_var.set("IQ: MONITOR AUTOMÁTICO PARADO")
        iq_trava_var.set("Entrada: AGUARDANDO SINAL")


def agendar_proxima_leitura():
    global agendamento_monitor
    espera = segundos_ate_proxima_leitura(time.time())
    iq_conexao_var.set(f"IQ: MONITOR ATIVO • próxima leitura em {int(espera)}s")
    agendamento_monitor = janela.after(
        max(1000, int(espera * 1000)),
        lambda: testar_permissao_iq(automatico=True),
    )


botao_monitor = ttk.Button(
    acoes_leitura,
    text="ACOMPANHAR SOMENTE O ATIVO ESCOLHIDO",
    command=alternar_monitoramento,
    style="PremiumAction.TButton",
)
botao_monitor.pack(side="left", fill="x", expand=True, padx=(0, 5))

calibracao_em_andamento = False
resultados_calibracao = []
ativos_vistos_calibracao = set()


def calibrar_nove_abas():
    # Desativado por segurança: na IQ o atalho pode atingir o campo Invest em
    # vez de selecionar uma aba, dependendo do foco interno da plataforma.
    iq_conexao_var.set("IQ: CALIBRAÇÃO AUTOMÁTICA DESATIVADA")
    iq_leitura_var.set("Troque a aba manualmente e use TESTAR LEITURA DA TELA")
    iq_trava_var.set("Entrada: AGUARDANDO AÇÃO MANUAL")
    messagebox.showwarning(
        "Calibração segura",
        "A troca automática por Cmd+1…9 foi desativada porque a IQ pode "
        "direcionar o comando ao campo de investimento.\n\n"
        "Selecione cada aba manualmente e clique em TESTAR LEITURA DA TELA.",
    )


def calibrar_aba(numero):
    navegacao = selecionar_aba(numero)
    if not navegacao.sucesso:
        resultados_calibracao.append(f"Aba {numero}: atalho indisponível")
        finalizar_calibracao(navegacao.mensagem)
        return
    # Espera a IQ trocar e redesenhar o gráfico antes da captura.
    janela.after(900, lambda: ler_aba_calibracao(numero))


def ler_aba_calibracao(numero):
    caminho = f"/private/tmp/bft_iq_aba_{numero}.png"
    captura = testar_captura(caminho=caminho)
    if captura.sucesso:
        ativo = ler_ativo(captura.caminho)
        payout = ler_payout(captura.caminho)
        if ativo.sucesso and payout.sucesso:
            if ativo.ativo in ativos_vistos_calibracao:
                resultados_calibracao.append(
                    f"Aba {numero}: NÃO MUDOU • ainda em {ativo.ativo}"
                )
            else:
                ativos_vistos_calibracao.add(ativo.ativo)
                atualizar_linha_central(ativo.ativo, payout.payout)
                resultados_calibracao.append(
                    f"Aba {numero}: {ativo.ativo} • {payout.payout:.0%}"
                )
        else:
            resultados_calibracao.append(f"Aba {numero}: leitura incompleta")
    else:
        resultados_calibracao.append(f"Aba {numero}: captura indisponível")

    if numero < 9:
        janela.after(250, lambda: calibrar_aba(numero + 1))
    else:
        finalizar_calibracao()


def finalizar_calibracao(erro=None):
    global calibracao_em_andamento
    calibracao_em_andamento = False
    janela.deiconify()
    janela.lift()
    botao_calibrar.config(state="normal")
    sucessos = sum(" • " in item for item in resultados_calibracao)
    iq_conexao_var.set(f"IQ: CALIBRAÇÃO CONCLUÍDA • {sucessos}/9 LIDAS")
    iq_leitura_var.set("Abra o Histórico de Entradas para conferir os registros")
    iq_trava_var.set("Entrada: AGUARDANDO CONFIRMAÇÃO MANUAL")
    resumo = "\n".join(resultados_calibracao)
    if erro:
        resumo += f"\n\n{erro}\nAutorize Python em Acessibilidade no macOS."
    messagebox.showinfo("Calibração das 9 abas", resumo or "Nenhuma aba foi lida")


botao_calibrar = ttk.Button(
    acoes_leitura,
    text="LER AGORA SOMENTE O ATIVO ESCOLHIDO",
    command=testar_permissao_iq,
)
botao_calibrar.pack(side="left", fill="x", expand=True, padx=(5, 0))

painel_log = ttk.LabelFrame(
    conteudo, text="Log do BFT", padding=10, style="Premium.TLabelframe"
)
painel_log.pack(fill="x", padx=18, pady=(8, 4))
moldura_log = ttk.Frame(painel_log)
moldura_log.pack(fill="both", expand=True)
texto_log = tk.Text(
    moldura_log,
    height=7,
    wrap="word",
    state="disabled",
    bg="#0c0a15",
    fg=COR_MUTED,
    insertbackground="white",
    selectbackground="#3c3489",
    selectforeground=COR_TEXTO,
    borderwidth=0,
    highlightthickness=1,
    highlightbackground=COR_BORDA,
    font=("Menlo", 10),
)
rolagem_log = ttk.Scrollbar(
    moldura_log, orient="vertical", command=texto_log.yview,
    style="Dark.Vertical.TScrollbar",
)
texto_log.configure(yscrollcommand=rolagem_log.set)
texto_log.pack(side="left", fill="both", expand=True)
rolagem_log.pack(side="right", fill="y")


def limpar_log():
    texto_log.configure(state="normal")
    texto_log.delete("1.0", tk.END)
    texto_log.configure(state="disabled")


ttk.Button(painel_log, text="LIMPAR LOG", command=limpar_log).pack(pady=(6, 0))


def receber_logs():
    recebeu = False
    while True:
        try:
            linha = fila_logs.get_nowait()
        except queue.Empty:
            break
        recebeu = True
        texto_log.configure(state="normal")
        texto_log.insert(tk.END, linha + "\n")
        texto_log.configure(state="disabled")
    if recebeu:
        quantidade = int(texto_log.index("end-1c").split(".")[0])
        if quantidade > 500:
            texto_log.configure(state="normal")
            texto_log.delete("1.0", f"{quantidade - 500}.0")
            texto_log.configure(state="disabled")
        texto_log.see(tk.END)
    janela.after(150, receber_logs)


sys.stdout = SaidaLogInterface(fila_logs)
sys.stderr = SaidaLogInterface(fila_logs)
janela.after(150, receber_logs)
print("[BFT] Log integrado iniciado — o Terminal não é mais necessário")

painel_abas = criar_card_premium(
    conteudo, bg=COR_PANEL, padding=(10, 10), rel="flat"
)
painel_abas.pack(fill="both", expand=True, padx=18, pady=(8, 10))
abas = ttk.Notebook(painel_abas)
abas.pack(fill="both", expand=True)
painel_log.pack_forget()
painel_log.pack(fill="x", padx=18, pady=(0, 10), after=painel_abas)
criar_aba_plataformas()
fila_eventos = queue.Queue()
ATIVO_NAO_SELECIONADO = "— ESCOLHA O ATIVO QUE VAI ANALISAR —"
paineis_resultado = {}
arvore_diagnosticos = None
resumo_indicadores_var = None
arvore_operacoes = None
arvore_radar = None
eventos_radar = {}
seletores_ativo = []
campos_por_mercado = {}
graficos_mercado_aberto = {}
graficos_otc = {}
ultimo_evento_otc = None
otc_estrategia_var = None
otc_indicadores_var = None


def desenhar_grafico_rsi(canvas_rsi, evento, ativo):
    canvas_rsi.delete("all")
    largura = max(300, canvas_rsi.winfo_width())
    altura = max(220, canvas_rsi.winfo_height())
    canvas_rsi.create_text(
        14, 12, text=f"RSI 14 • {ativo}", anchor="nw",
        fill="#f1effb", font=("Arial", 11, "bold"),
    )
    serie = [] if evento is None else list(evento.get("series_tecnicas", ()))
    valores = [(indice, item.get("rsi")) for indice, item in enumerate(serie) if item.get("rsi") is not None]
    if not valores:
        canvas_rsi.create_text(
            largura / 2, altura / 2,
            text="Aguardando RSI do ativo selecionado",
            fill="#8a8aa0", font=("Arial", 10),
        )
        return
    esquerda, direita, topo, base = 38, largura - 18, 38, altura - 28
    for nivel, cor in ((70, "#e24b4a"), (50, "#4b426b"), (30, "#18a875")):
        y = topo + (100 - nivel) / 100 * (base - topo)
        canvas_rsi.create_line(esquerda, y, direita, y, fill=cor, width=1)
        canvas_rsi.create_text(
            esquerda - 5, y, text=str(nivel), anchor="e",
            fill="#8a8aa0", font=("Arial", 7),
        )
    pontos = []
    divisor = max(1, len(serie) - 1)
    for indice, valor in valores:
        x = esquerda + indice / divisor * (direita - esquerda)
        y = topo + (100 - float(valor)) / 100 * (base - topo)
        pontos.extend((x, y))
    if len(pontos) >= 4:
        canvas_rsi.create_line(*pontos, fill="#38bdf8", width=2, smooth=True)
    ultimo = float(valores[-1][1])
    canvas_rsi.create_text(
        direita, 15, text=f"Atual {ultimo:.1f}", anchor="ne",
        fill="#38bdf8", font=("Arial", 9, "bold"),
    )
    canvas_rsi.create_text(
        esquerda, base + 8, text="sobrevendido", anchor="nw",
        fill="#18a875", font=("Arial", 7),
    )
    canvas_rsi.create_text(
        direita, base + 8, text="sobrecomprado", anchor="ne",
        fill="#e24b4a", font=("Arial", 7),
    )


def desenhar_grafico_macd(canvas_macd, evento, ativo):
    canvas_macd.delete("all")
    largura = max(310, canvas_macd.winfo_width())
    altura = max(220, canvas_macd.winfo_height())
    canvas_macd.create_text(
        14, 12, text=f"MACD 12/26/9 • {ativo}", anchor="nw",
        fill="#f1effb", font=("Arial", 11, "bold"),
    )
    serie = [] if evento is None else list(evento.get("series_tecnicas", ()))
    validos = [
        item for item in serie
        if item.get("macd") is not None or item.get("sinal_macd") is not None
    ]
    if not validos:
        canvas_macd.create_text(
            largura / 2, altura / 2,
            text="Aguardando MACD do ativo selecionado",
            fill="#8a8aa0", font=("Arial", 10),
        )
        return
    esquerda, direita, topo, base = 28, largura - 18, 38, altura - 28
    valores_escala = [
        abs(float(valor))
        for item in validos
        for valor in (item.get("macd"), item.get("sinal_macd"), item.get("histograma_macd"))
        if valor is not None
    ]
    escala = max(max(valores_escala, default=0.0), 1e-9)
    zero = (topo + base) / 2
    canvas_macd.create_line(esquerda, zero, direita, zero, fill="#4b426b", width=1)
    divisor = max(1, len(serie) - 1)
    pontos_macd = []
    pontos_sinal = []
    for indice, item in enumerate(serie):
        x = esquerda + indice / divisor * (direita - esquerda)
        histograma = item.get("histograma_macd")
        if histograma is not None:
            y_histograma = zero - float(histograma) / escala * (base - topo) * 0.44
            cor = "#18a875" if float(histograma) >= 0 else "#e24b4a"
            canvas_macd.create_rectangle(
                x - 2, min(zero, y_histograma), x + 2, max(zero, y_histograma),
                fill=cor, outline="",
            )
        macd = item.get("macd")
        if macd is not None:
            pontos_macd.extend((x, zero - float(macd) / escala * (base - topo) * 0.44))
        sinal = item.get("sinal_macd")
        if sinal is not None:
            pontos_sinal.extend((x, zero - float(sinal) / escala * (base - topo) * 0.44))
    if len(pontos_macd) >= 4:
        canvas_macd.create_line(*pontos_macd, fill="#38bdf8", width=2, smooth=True)
    if len(pontos_sinal) >= 4:
        canvas_macd.create_line(*pontos_sinal, fill="#f59e0b", width=2, smooth=True)
    canvas_macd.create_text(
        direita, 15, text="MACD", anchor="ne",
        fill="#38bdf8", font=("Arial", 8, "bold"),
    )
    canvas_macd.create_text(
        direita - 48, 15, text="SINAL", anchor="ne",
        fill="#f59e0b", font=("Arial", 8, "bold"),
    )


def desenhar_grafico_adx(canvas_adx, evento, ativo):
    canvas_adx.delete("all")
    largura = max(630, canvas_adx.winfo_width())
    altura = max(190, canvas_adx.winfo_height())
    canvas_adx.create_text(
        14, 12, text=f"ADX 14 • FORÇA E DIREÇÃO DA TENDÊNCIA • {ativo}",
        anchor="nw", fill="#f1effb", font=("Arial", 11, "bold"),
    )
    serie = [] if evento is None else list(evento.get("series_tecnicas", ()))
    validos = [item for item in serie if item.get("adx") is not None]
    if not validos:
        canvas_adx.create_text(
            largura / 2, altura / 2,
            text="Aguardando ADX do ativo selecionado",
            fill="#8a8aa0", font=("Arial", 10),
        )
        return

    esquerda, direita, topo, base = 38, largura - 18, 42, altura - 26
    for nivel, cor in ((50, "#4b426b"), (25, "#f59e0b"), (20, "#4b426b")):
        y = base - nivel / 100 * (base - topo)
        canvas_adx.create_line(esquerda, y, direita, y, fill=cor, width=1)
        canvas_adx.create_text(
            esquerda - 5, y, text=str(nivel), anchor="e",
            fill="#8a8aa0", font=("Arial", 7),
        )

    divisor = max(1, len(serie) - 1)
    pontos_adx = []
    pontos_mais = []
    pontos_menos = []
    for indice, item in enumerate(serie):
        x = esquerda + indice / divisor * (direita - esquerda)
        for chave, pontos in (
            ("adx", pontos_adx),
            ("di_mais", pontos_mais),
            ("di_menos", pontos_menos),
        ):
            valor = item.get(chave)
            if valor is not None:
                y = base - max(0.0, min(100.0, float(valor))) / 100 * (base - topo)
                pontos.extend((x, y))
    if len(pontos_adx) >= 4:
        canvas_adx.create_line(*pontos_adx, fill="#f1effb", width=2, smooth=True)
    if len(pontos_mais) >= 4:
        canvas_adx.create_line(*pontos_mais, fill="#18a875", width=2, smooth=True)
    if len(pontos_menos) >= 4:
        canvas_adx.create_line(*pontos_menos, fill="#e24b4a", width=2, smooth=True)

    ultimo = validos[-1]
    canvas_adx.create_text(
        direita, 15,
        text=(
            f"ADX {float(ultimo['adx']):.1f}   "
            f"+DI {float(ultimo['di_mais']):.1f}   "
            f"-DI {float(ultimo['di_menos']):.1f}"
        ),
        anchor="ne", fill="#f1effb", font=("Arial", 8, "bold"),
    )
    canvas_adx.create_text(
        esquerda, base + 8, text="acima de 25 = tendência com força",
        anchor="nw", fill="#f59e0b", font=("Arial", 7),
    )


def desenhar_grafico_velas(canvas_velas, evento, ativo, titulo):
    """Desenha velas já produzidas pelo motor, sem alterar a análise."""
    canvas_velas.delete("all")
    largura = max(300, canvas_velas.winfo_width())
    altura = max(140, canvas_velas.winfo_height())
    canvas_velas.create_text(
        14, 12, text=titulo, anchor="nw",
        fill=COR_TEXTO, font=("Arial", 11, "bold"),
    )
    velas = [] if evento is None else list(evento.get("velas_grafico", ()))
    if not velas:
        canvas_velas.create_text(
            largura / 2, altura / 2,
            text="Aguardando velas fechadas\ndo ativo selecionado",
            justify="center", fill=COR_MUTED, font=("Arial", 10),
        )
        return

    margem_esquerda = 42
    margem_direita = largura - 48
    topo = 44
    base = altura - 30
    maximo = max(float(item["maxima"]) for item in velas)
    minimo = min(float(item["minima"]) for item in velas)
    amplitude = max(maximo - minimo, 1e-9)
    maximo += amplitude * 0.06
    minimo -= amplitude * 0.06
    amplitude = maximo - minimo

    def y_preco(preco):
        return topo + (maximo - float(preco)) / amplitude * (base - topo)

    for nivel in range(5):
        y = topo + nivel * (base - topo) / 4
        valor = maximo - nivel * amplitude / 4
        canvas_velas.create_line(
            margem_esquerda, y, margem_direita, y,
            fill="#2a2440", width=1,
        )
        canvas_velas.create_text(
            margem_direita + 4, y, text=f"{valor:.4f}", anchor="w",
            fill="#8a8aa0", font=("Arial", 7),
        )

    passo = (margem_direita - margem_esquerda) / max(1, len(velas))
    corpo = max(2, min(8, passo * 0.55))
    for indice, item in enumerate(velas):
        x = margem_esquerda + (indice + 0.5) * passo
        abertura = y_preco(item["abertura"])
        fechamento = y_preco(item["fechamento"])
        maxima = y_preco(item["maxima"])
        minima = y_preco(item["minima"])
        cor = COR_SUCESSO if float(item["fechamento"]) >= float(item["abertura"]) else COR_PERIGO
        canvas_velas.create_line(x, maxima, x, minima, fill=cor, width=1)
        canvas_velas.create_rectangle(
            x - corpo / 2,
            min(abertura, fechamento),
            x + corpo / 2,
            max(max(abertura, fechamento), min(abertura, fechamento) + 1),
            fill=cor, outline=cor,
        )

    for indice in sorted({0, len(velas) // 2, len(velas) - 1}):
        x = margem_esquerda + (indice + 0.5) * passo
        canvas_velas.create_text(
            x, base + 7, text=velas[indice].get("horario", "—"),
            anchor="n", fill="#8a8aa0", font=("Arial", 7),
        )
    canvas_velas.create_text(
        14, 30,
        text=f"{ativo} • {evento.get('timeframe', 'M1')} • {len(velas)} velas",
        anchor="nw", fill=COR_MUTED, font=("Arial", 8),
    )


def desenhar_contribuicao_indicadores(canvas_indicadores, evento, estrategia):
    """Apresenta a contribuição que o motor já calculou para cada indicador."""
    canvas_indicadores.delete("all")
    largura = max(310, canvas_indicadores.winfo_width())
    altura = max(235, canvas_indicadores.winfo_height())
    canvas_indicadores.create_text(
        14, 12, text="INDICADORES EM USO", anchor="nw",
        fill=COR_TEXTO, font=("Arial", 11, "bold"),
    )
    canvas_indicadores.create_text(
        14, 31, text=f"Estratégia: {estrategia or '—'}", anchor="nw",
        fill="#afa9ec", font=("Arial", 8, "bold"),
    )
    diagnosticos = [] if evento is None else list(evento.get("diagnosticos", ()))
    if not diagnosticos:
        canvas_indicadores.create_text(
            largura / 2, altura / 2,
            text="Aguardando a leitura dos\nindicadores da estratégia",
            justify="center", fill=COR_MUTED, font=("Arial", 10),
        )
        return

    exibidos = diagnosticos[:3]
    max_peso = max(1, max(int(item.get("peso") or 0) for item in exibidos))
    largura_maxima = max(95, largura - 145)
    for indice, item in enumerate(exibidos):
        y = 70 + indice * 48
        nome = str(item.get("nome") or "Indicador")[:18]
        direcao = str(item.get("direcao") or "NEUTRO").upper()
        peso = int(item.get("peso") or 0)
        motivo = str(item.get("motivo") or "sem confirmação")[:34]
        cor = COR_SUCESSO if direcao == "ALTA" else COR_PERIGO if direcao == "BAIXA" else COR_GLOW
        canvas_indicadores.create_text(
            12, y - 11, text=nome, anchor="w",
            fill="#afa9ec", font=("Arial", 8, "bold"),
        )
        canvas_indicadores.create_rectangle(
            105, y - 7, 105 + largura_maxima, y + 7,
            fill="#2a2440", outline="",
        )
        largura_peso = 8 if peso == 0 else largura_maxima * peso / max_peso
        canvas_indicadores.create_rectangle(
            105, y - 7, 105 + largura_peso, y + 7,
            fill=cor, outline="",
        )
        canvas_indicadores.create_text(
            largura - 12, y - 11, text=f"{direcao} • {peso}",
            anchor="e", fill=COR_TEXTO, font=("Arial", 7, "bold"),
        )
        canvas_indicadores.create_text(
            12, y + 13, text=motivo, anchor="w",
            fill="#8a8aa0", font=("Arial", 7),
        )
    sinal = str(evento.get("sinal") or "AGUARDAR")
    confluencia = float(evento.get("confluencia", 0))
    canvas_indicadores.create_text(
        14, altura - 12,
        text=f"Resultado: {sinal} • confluência {confluencia:.0%}",
        anchor="sw", fill=COR_TEXTO, font=("Arial", 9, "bold"),
    )


def atualizar_graficos_otc(evento=None):
    """Atualiza somente a apresentação do último evento OTC recebido."""
    global ultimo_evento_otc
    if evento is not None:
        ultimo_evento_otc = evento
    evento = ultimo_evento_otc
    canvases = tuple(graficos_otc.get(chave) for chave in (
        "velas", "indicadores", "rsi", "macd", "adx",
    ))
    if any(item is None for item in canvases):
        return

    campos = campos_por_mercado.get("OTC", {})
    ativo = evento.get("ativo") if evento else None
    if not ativo and campos.get("ativo") is not None:
        ativo = campos["ativo"].get()
    ativo = "—" if not ativo or ativo == ATIVO_NAO_SELECIONADO else ativo
    estrategia = evento.get("estrategia") if evento else None
    if not estrategia and campos.get("estrategia") is not None:
        estrategia = campos["estrategia"].get()

    if otc_estrategia_var is not None:
        otc_estrategia_var.set(f"Estratégia ativa: {estrategia or '—'}")
    if otc_indicadores_var is not None:
        nomes = () if evento is None else tuple(evento.get("indicadores_ativos", ()))
        otc_indicadores_var.set(
            "Indicadores: aguardando análise"
            if not nomes else "Indicadores: " + " • ".join(map(str, nomes))
        )

    desenhar_grafico_velas(canvases[0], evento, ativo, "VELAS VISUAIS OTC")
    desenhar_contribuicao_indicadores(canvases[1], evento, estrategia)
    desenhar_grafico_rsi(canvases[2], evento, ativo)
    desenhar_grafico_macd(canvases[3], evento, ativo)
    desenhar_grafico_adx(canvases[4], evento, ativo)


def atualizar_graficos_mercado_aberto():
    """Redesenha a concentração e a confluência com os eventos reais recebidos."""
    canvas_concentracao = graficos_mercado_aberto.get("concentracao")
    canvas_resultados = graficos_mercado_aberto.get("resultados")
    canvas_velas = graficos_mercado_aberto.get("velas")
    canvas_indicadores = graficos_mercado_aberto.get("indicadores")
    canvas_rsi = graficos_mercado_aberto.get("rsi")
    canvas_macd = graficos_mercado_aberto.get("macd")
    canvas_adx = graficos_mercado_aberto.get("adx")
    if any(
        canvas_item is None
        for canvas_item in (
            canvas_concentracao,
            canvas_resultados,
            canvas_velas,
            canvas_indicadores,
            canvas_rsi,
            canvas_macd,
            canvas_adx,
        )
    ):
        return

    eventos = [
        eventos_radar[ativo]
        for ativo in ATIVOS_MERCADO_ABERTO
        if ativo in eventos_radar
    ]
    cores = {
        "CALL": "#18a875",
        "PUT": "#e24b4a",
        "AGUARDAR": "#7f77dd",
    }

    canvas_concentracao.delete("all")
    largura_concentracao = max(290, canvas_concentracao.winfo_width())
    canvas_concentracao.create_text(
        14, 12, text="CONCENTRAÇÃO", anchor="nw",
        fill="#f1effb", font=("Arial", 11, "bold"),
    )
    contagem = {"CALL": 0, "PUT": 0, "AGUARDAR": 0}
    for evento in eventos:
        direcao = str(evento.get("direcao") or "AGUARDAR").upper()
        contagem[direcao if direcao in contagem else "AGUARDAR"] += 1

    caixa = (30, 45, 175, 190)
    total = max(1, len(eventos))
    inicio = 90
    for direcao in ("CALL", "PUT", "AGUARDAR"):
        quantidade = contagem[direcao]
        if quantidade:
            extensao = -(quantidade / total) * 360
            canvas_concentracao.create_arc(
                *caixa, start=inicio, extent=extensao,
                fill=cores[direcao], outline="#171229", width=2,
            )
            inicio += extensao
    if not eventos:
        canvas_concentracao.create_oval(
            *caixa, fill="#27213c", outline="#4b426b", width=2,
        )
    canvas_concentracao.create_oval(
        68, 83, 137, 152, fill="#171229", outline="#171229",
    )
    canvas_concentracao.create_text(
        102, 108,
        text=f"{len(eventos)}/{len(ATIVOS_MERCADO_ABERTO)}",
        fill="#f1effb",
        font=("Arial", 15, "bold"),
    )
    canvas_concentracao.create_text(
        102, 130, text="pares lidos", fill="#8a8aa0", font=("Arial", 8),
    )
    legenda_x = min(205, largura_concentracao - 92)
    for indice, direcao in enumerate(("CALL", "PUT", "AGUARDAR")):
        y = 60 + indice * 45
        canvas_concentracao.create_rectangle(
            legenda_x, y, legenda_x + 13, y + 13,
            fill=cores[direcao], outline="",
        )
        canvas_concentracao.create_text(
            legenda_x + 20, y - 2, text=direcao, anchor="nw",
            fill="#afa9ec", font=("Arial", 9, "bold"),
        )
        canvas_concentracao.create_text(
            legenda_x + 20, y + 15, text=str(contagem[direcao]), anchor="nw",
            fill="#f1effb", font=("Arial", 10),
        )
    if not eventos:
        canvas_concentracao.create_text(
            14, 210, text="Clique em INICIAR para receber as velas reais",
            anchor="nw", fill="#8a8aa0", font=("Arial", 8),
        )

    canvas_resultados.delete("all")
    largura_resultados = max(310, canvas_resultados.winfo_width())
    canvas_resultados.create_text(
        14, 12, text="CONFLUÊNCIA POR PAR", anchor="nw",
        fill="#f1effb", font=("Arial", 11, "bold"),
    )
    x_inicial = 78
    altura_resultados = max(380, canvas_resultados.winfo_height())
    x_final = largura_resultados - 38
    largura_barra = max(120, x_final - x_inicial)
    for percentual in (0, 25, 50, 75, 100):
        x = x_inicial + largura_barra * percentual / 100
        canvas_resultados.create_line(
            x, 38, x, altura_resultados - 24, fill="#30294f", width=1,
        )
        canvas_resultados.create_text(
            x, altura_resultados - 18, text=f"{percentual}%", fill="#8a8aa0",
            font=("Arial", 7), anchor="n",
        )
    for indice, ativo in enumerate(ATIVOS_MERCADO_ABERTO):
        passo_y = (altura_resultados - 70) / max(1, len(ATIVOS_MERCADO_ABERTO))
        y = 45 + indice * passo_y
        evento = eventos_radar.get(ativo)
        confluencia = 0.0 if evento is None else float(evento.get("confluencia", 0))
        direcao = "AGUARDAR" if evento is None else str(evento.get("direcao") or "AGUARDAR").upper()
        cor = cores.get(direcao, cores["AGUARDAR"])
        canvas_resultados.create_text(
            8, y, text=ativo, anchor="w", fill="#afa9ec", font=("Arial", 6),
        )
        fim = x_inicial + largura_barra * max(0.0, min(1.0, confluencia))
        canvas_resultados.create_rectangle(
            x_inicial, y - 3, fim, y + 3, fill=cor, outline="",
        )
        canvas_resultados.create_text(
            min(fim + 4, largura_resultados - 28), y,
            text="—" if evento is None else f"{confluencia:.0%}",
            anchor="w", fill="#f1effb", font=("Arial", 6, "bold"),
        )

    campos_abertos = campos_por_mercado.get("MERCADO ABERTO")
    ativo_selecionado = (
        campos_abertos["ativo"].get()
        if campos_abertos is not None
        else ATIVO_NAO_SELECIONADO
    )
    evento_selecionado = eventos_radar.get(ativo_selecionado)

    canvas_velas.delete("all")
    largura_velas = max(300, canvas_velas.winfo_width())
    canvas_velas.create_text(
        14, 12, text="VELAS REAIS DO ATIVO", anchor="nw",
        fill="#f1effb", font=("Arial", 11, "bold"),
    )
    velas = [] if evento_selecionado is None else evento_selecionado.get("velas_grafico", [])
    if not velas:
        canvas_velas.create_text(
            largura_velas / 2, 112,
            text="Escolha um par e clique em INICIAR\npara carregar o gráfico real",
            justify="center", fill="#8a8aa0", font=("Arial", 10),
        )
    else:
        margem_esquerda = 42
        margem_direita = largura_velas - 45
        topo = 40
        base = 205
        maximo = max(float(vela["maxima"]) for vela in velas)
        minimo = min(float(vela["minima"]) for vela in velas)
        amplitude = max(maximo - minimo, 1e-9)
        maximo += amplitude * 0.06
        minimo -= amplitude * 0.06
        amplitude = maximo - minimo

        def y_preco(preco):
            return topo + (maximo - float(preco)) / amplitude * (base - topo)

        for nivel in range(5):
            y = topo + nivel * (base - topo) / 4
            valor = maximo - nivel * amplitude / 4
            canvas_velas.create_line(
                margem_esquerda, y, margem_direita, y,
                fill="#30294f", width=1,
            )
            canvas_velas.create_text(
                margem_direita + 4, y, text=f"{valor:.4f}", anchor="w",
                fill="#8a8aa0", font=("Arial", 7),
            )
        passo = (margem_direita - margem_esquerda) / max(1, len(velas))
        corpo = max(2, min(7, passo * 0.55))
        for indice, vela in enumerate(velas):
            x = margem_esquerda + (indice + 0.5) * passo
            abertura = y_preco(vela["abertura"])
            fechamento = y_preco(vela["fechamento"])
            maxima = y_preco(vela["maxima"])
            minima = y_preco(vela["minima"])
            cor = "#18a875" if float(vela["fechamento"]) >= float(vela["abertura"]) else "#e24b4a"
            canvas_velas.create_line(x, maxima, x, minima, fill=cor, width=1)
            canvas_velas.create_rectangle(
                x - corpo / 2,
                min(abertura, fechamento),
                x + corpo / 2,
                max(max(abertura, fechamento), min(abertura, fechamento) + 1),
                fill=cor,
                outline=cor,
            )
        for indice in sorted({0, len(velas) // 2, len(velas) - 1}):
            x = margem_esquerda + (indice + 0.5) * passo
            canvas_velas.create_text(
                x, 215, text=velas[indice].get("horario", "—"),
                anchor="n", fill="#8a8aa0", font=("Arial", 7),
            )
        canvas_velas.create_text(
            14, 30,
            text=f"{ativo_selecionado} • {evento_selecionado.get('timeframe', 'M1')} • {len(velas)} velas",
            anchor="nw", fill="#8a8aa0", font=("Arial", 8),
        )

    canvas_indicadores.delete("all")
    largura_indicadores = max(310, canvas_indicadores.winfo_width())
    canvas_indicadores.create_text(
        14, 12, text="CONTRIBUIÇÃO DOS INDICADORES", anchor="nw",
        fill="#f1effb", font=("Arial", 11, "bold"),
    )
    diagnosticos = (
        []
        if evento_selecionado is None
        else list(evento_selecionado.get("diagnosticos", ()))
    )
    if not diagnosticos:
        canvas_indicadores.create_text(
            largura_indicadores / 2, 112,
            text="Aguardando diagnóstico\ndos indicadores ativos",
            justify="center", fill="#8a8aa0", font=("Arial", 10),
        )
    else:
        max_peso = max(1, max(int(item.get("peso") or 0) for item in diagnosticos))
        largura_maxima = max(100, largura_indicadores - 135)
        for indice, item in enumerate(diagnosticos[:3]):
            y = 60 + indice * 55
            nome = str(item.get("nome") or "Indicador")[:18]
            direcao = str(item.get("direcao") or "NEUTRO").upper()
            peso = int(item.get("peso") or 0)
            motivo = str(item.get("motivo") or "sem confirmação")[:32]
            cor = (
                "#18a875" if direcao == "ALTA"
                else "#e24b4a" if direcao == "BAIXA"
                else "#7f77dd"
            )
            canvas_indicadores.create_text(
                12, y - 12, text=nome, anchor="w",
                fill="#afa9ec", font=("Arial", 8, "bold"),
            )
            canvas_indicadores.create_rectangle(
                105, y - 8, 105 + largura_maxima, y + 8,
                fill="#27213c", outline="",
            )
            largura_peso = 10 if peso == 0 else largura_maxima * peso / max_peso
            canvas_indicadores.create_rectangle(
                105, y - 8, 105 + largura_peso, y + 8,
                fill=cor, outline="",
            )
            canvas_indicadores.create_text(
                largura_indicadores - 12, y - 12,
                text=f"{direcao} • peso {peso}", anchor="e",
                fill="#f1effb", font=("Arial", 7, "bold"),
            )
            canvas_indicadores.create_text(
                12, y + 15, text=motivo, anchor="w",
                fill="#8a8aa0", font=("Arial", 7),
            )
        direcao_final = str(evento_selecionado.get("direcao") or "AGUARDAR")
        confluencia_final = float(evento_selecionado.get("confluencia", 0))
        canvas_indicadores.create_text(
            14, 220,
            text=f"Resultado: {direcao_final} • confluência {confluencia_final:.0%}",
            anchor="sw", fill="#f1effb", font=("Arial", 9, "bold"),
        )

    ativo_grafico = (
        "—" if ativo_selecionado == ATIVO_NAO_SELECIONADO
        else ativo_selecionado
    )
    desenhar_grafico_rsi(canvas_rsi, evento_selecionado, ativo_grafico)
    desenhar_grafico_macd(canvas_macd, evento_selecionado, ativo_grafico)
    desenhar_grafico_adx(canvas_adx, evento_selecionado, ativo_grafico)


def criar_graficos_mercado_aberto(aba):
    painel = ttk.LabelFrame(
        aba, text="Painel gráfico • dados reais do Mercado Aberto", padding=8,
    )
    painel.pack(fill="x", pady=(18, 10))
    ttk.Label(
        painel,
        text=(
            "CALL e PUT aparecem somente após a confluência mínima; "
            "os demais pares permanecem em AGUARDAR."
        ),
        wraplength=600,
        justify="left",
    ).pack(anchor="w", pady=(0, 8))

    linha = tk.Frame(painel, bg="#090712")
    linha.pack(fill="x")
    concentracao = tk.Canvas(
        linha, width=300, height=380, bg="#171229", highlightthickness=1,
        highlightbackground="#2a2440",
    )
    concentracao.pack(side="left", fill="both", expand=True, padx=(0, 6))
    resultados = tk.Canvas(
        linha, width=330, height=380, bg="#171229", highlightthickness=1,
        highlightbackground="#2a2440",
    )
    resultados.pack(side="left", fill="both", expand=True, padx=(6, 0))
    graficos_mercado_aberto["concentracao"] = concentracao
    graficos_mercado_aberto["resultados"] = resultados

    linha_detalhes = tk.Frame(painel, bg="#090712")
    linha_detalhes.pack(fill="x", pady=(12, 0))
    velas = tk.Canvas(
        linha_detalhes, width=300, height=235, bg="#171229",
        highlightthickness=1, highlightbackground="#2a2440",
    )
    velas.pack(side="left", fill="both", expand=True, padx=(0, 6))
    indicadores = tk.Canvas(
        linha_detalhes, width=330, height=235, bg="#171229",
        highlightthickness=1, highlightbackground="#2a2440",
    )
    indicadores.pack(side="left", fill="both", expand=True, padx=(6, 0))
    graficos_mercado_aberto["velas"] = velas
    graficos_mercado_aberto["indicadores"] = indicadores

    linha_tecnica = tk.Frame(painel, bg="#090712")
    linha_tecnica.pack(fill="x", pady=(12, 0))
    grafico_rsi = tk.Canvas(
        linha_tecnica, width=300, height=220, bg="#171229",
        highlightthickness=1, highlightbackground="#2a2440",
    )
    grafico_rsi.pack(side="left", fill="both", expand=True, padx=(0, 6))
    grafico_macd = tk.Canvas(
        linha_tecnica, width=330, height=220, bg="#171229",
        highlightthickness=1, highlightbackground="#2a2440",
    )
    grafico_macd.pack(side="left", fill="both", expand=True, padx=(6, 0))
    grafico_adx = tk.Canvas(
        painel, width=630, height=190, bg="#171229",
        highlightthickness=1, highlightbackground="#2a2440",
    )
    grafico_adx.pack(fill="x", pady=(12, 0))
    graficos_mercado_aberto["rsi"] = grafico_rsi
    graficos_mercado_aberto["macd"] = grafico_macd
    graficos_mercado_aberto["adx"] = grafico_adx
    concentracao.bind(
        "<Configure>", lambda _evento: janela.after_idle(atualizar_graficos_mercado_aberto)
    )
    resultados.bind(
        "<Configure>", lambda _evento: janela.after_idle(atualizar_graficos_mercado_aberto)
    )
    velas.bind(
        "<Configure>", lambda _evento: janela.after_idle(atualizar_graficos_mercado_aberto)
    )
    indicadores.bind(
        "<Configure>", lambda _evento: janela.after_idle(atualizar_graficos_mercado_aberto)
    )
    grafico_rsi.bind(
        "<Configure>", lambda _evento: janela.after_idle(atualizar_graficos_mercado_aberto)
    )
    grafico_macd.bind(
        "<Configure>", lambda _evento: janela.after_idle(atualizar_graficos_mercado_aberto)
    )
    grafico_adx.bind(
        "<Configure>", lambda _evento: janela.after_idle(atualizar_graficos_mercado_aberto)
    )
    janela.after_idle(atualizar_graficos_mercado_aberto)


def criar_graficos_otc(aba):
    """Monta o painel OTC realista usando apenas dados já analisados."""
    global otc_estrategia_var, otc_indicadores_var
    painel = ttk.LabelFrame(
        aba, text="Painel gráfico OTC • análise visual", padding=10,
        style="Premium.TLabelframe",
    )
    painel.pack(fill="x", pady=(18, 10))

    cabecalho = tk.Frame(painel, bg=COR_PANEL_ALT)
    cabecalho.pack(fill="x", pady=(0, 10))
    otc_estrategia_var = tk.StringVar(value="Estratégia ativa: Automático")
    otc_indicadores_var = tk.StringVar(value="Indicadores: aguardando análise")
    tk.Label(
        cabecalho, textvariable=otc_estrategia_var,
        bg=COR_PANEL_ALT, fg=COR_TEXTO,
        font=("Arial", 10, "bold"),
    ).pack(anchor="w")
    tk.Label(
        cabecalho, textvariable=otc_indicadores_var,
        bg=COR_PANEL_ALT, fg="#afa9ec",
        font=("Arial", 9), wraplength=610, justify="left",
    ).pack(anchor="w", pady=(3, 0))

    linha_principal = tk.Frame(painel, bg=COR_PANEL_ALT)
    linha_principal.pack(fill="x")
    velas = tk.Canvas(
        linha_principal, width=300, height=250, bg=COR_PANEL,
        highlightthickness=1, highlightbackground=COR_BORDA,
    )
    velas.pack(side="left", fill="both", expand=True, padx=(0, 6))
    indicadores = tk.Canvas(
        linha_principal, width=330, height=250, bg=COR_PANEL,
        highlightthickness=1, highlightbackground=COR_BORDA,
    )
    indicadores.pack(side="left", fill="both", expand=True, padx=(6, 0))

    linha_tecnica = tk.Frame(painel, bg=COR_PANEL_ALT)
    linha_tecnica.pack(fill="x", pady=(12, 0))
    grafico_rsi = tk.Canvas(
        linha_tecnica, width=300, height=220, bg=COR_PANEL,
        highlightthickness=1, highlightbackground=COR_BORDA,
    )
    grafico_rsi.pack(side="left", fill="both", expand=True, padx=(0, 6))
    grafico_macd = tk.Canvas(
        linha_tecnica, width=330, height=220, bg=COR_PANEL,
        highlightthickness=1, highlightbackground=COR_BORDA,
    )
    grafico_macd.pack(side="left", fill="both", expand=True, padx=(6, 0))
    grafico_adx = tk.Canvas(
        painel, width=630, height=190, bg=COR_PANEL,
        highlightthickness=1, highlightbackground=COR_BORDA,
    )
    grafico_adx.pack(fill="x", pady=(12, 0))

    graficos_otc.update({
        "velas": velas,
        "indicadores": indicadores,
        "rsi": grafico_rsi,
        "macd": grafico_macd,
        "adx": grafico_adx,
    })
    for item in (velas, indicadores, grafico_rsi, grafico_macd, grafico_adx):
        item.bind(
            "<Configure>",
            lambda _evento: janela.after_idle(atualizar_graficos_otc),
        )
    janela.after_idle(atualizar_graficos_otc)


def carregar_snapshot_visual_otc(ativo_lido, velas_visuais, payout_lido):
    """Valida a captura contra a seleção OTC antes de entregá-la ao core."""
    global payout_visual_atual
    campos = campos_por_mercado.get("OTC")
    if not campos:
        return False, "Snapshot visual não carregado: painel OTC indisponível."

    ativo_selecionado = campos["ativo"].get().strip()
    timeframe = campos["timeframe"].get().strip().upper()
    modo = modo_para_motor(campos["modo"].get().strip())

    if ativo_selecionado == ATIVO_NAO_SELECIONADO:
        invalidar_leitura_visual_atual()
        return False, "Escolha manualmente um ativo na aba OTC antes da leitura."

    permissao_snapshot = validar_snapshot_visual(modo)
    if not permissao_snapshot.permitido:
        invalidar_leitura_visual_atual()
        return False, f"Snapshot visual indisponível: {permissao_snapshot.motivo}."
    if ativo_lido != ativo_selecionado:
        invalidar_leitura_visual_atual()
        return False, (
            "Snapshot visual rejeitado: a tela mostra "
            f"{ativo_lido}, mas a aba OTC está em {ativo_selecionado}."
        )
    if timeframe not in {"M1", "M5", "M15"}:
        invalidar_leitura_visual_atual()
        return False, f"Snapshot visual rejeitado: timeframe {timeframe} inválido."

    velas_convertidas = converter_velas_visuais(
        velas_visuais,
        ativo_selecionado,
        timeframe,
    )
    if not atualizar_historico_visual(
        velas_convertidas,
        ativo_selecionado,
        timeframe,
    ):
        invalidar_leitura_visual_atual()
        return False, "Snapshot visual rejeitado: nenhuma vela fechada foi convertida."

    if campos["payout"] is not None:
        campos["payout"].configure(state="normal")
        campos["payout"].delete(0, tk.END)
        campos["payout"].insert(0, f"{payout_lido * 100:.0f}")
        campos["payout"].configure(state="readonly")
    payout_visual_atual = payout_lido
    atualizar_payout_atual(payout_lido)
    return True, (
        f"Snapshot visual carregado: {len(velas_convertidas)} velas • "
        f"{ativo_selecionado} • {timeframe}."
    )


def criar_aba(nome, tipo_mercado, estrategias):
    aba = ttk.Frame(abas, padding=16)
    abas.add(aba, text=nome)
    campos = {}
    campos_por_mercado[tipo_mercado] = campos

    ttk.Label(
        aba,
        text=(
            "Big Foot Win • análise de velas reais • sem captura de tela"
            if tipo_mercado == "MERCADO ABERTO"
            else "Fonte: tela da corretora • leitura visual • somente Forex OTC"
        ),
        foreground=("#78d7a3" if tipo_mercado == "MERCADO ABERTO" else "#a98cff"),
        font=("Arial", 11, "bold"),
    ).pack(pady=(0, 12))

    formulario = tk.Frame(aba, bg=COR_PANEL)
    formulario.pack(fill="x", pady=(0, 12))
    formulario.grid_columnconfigure(0, weight=1)
    formulario.grid_columnconfigure(1, weight=1)

    def campo_numerico(rotulo, valor, linha, coluna, somente_leitura=False):
        grupo = tk.Frame(formulario, bg=COR_PANEL)
        grupo.grid(row=linha, column=coluna, sticky="ew", padx=(0, 6) if coluna == 0 else (6, 0), pady=(0, 10))
        ttk.Label(grupo, text=rotulo).pack(anchor="w")
        campo = ttk.Entry(grupo)
        campo.insert(0, valor)
        if somente_leitura:
            campo.configure(state="readonly")
        campo.pack(fill="x", pady=(5, 0))
        return campo

    campos["banca"] = campo_numerico("Banca de referência", "1000", 0, 0)
    campos["entrada"] = campo_numerico("Valor da entrada", "25", 0, 1)
    campos["gain"] = campo_numerico("Stop Gain", "100", 1, 0)
    campos["loss"] = campo_numerico("Stop Loss", "100", 1, 1)
    campos["payout"] = None
    campos["recuperacao"] = None
    if tipo_mercado == "OTC":
        campos["payout"] = campo_numerico(
            "Payout reconhecido na tela (%)", "—", 2, 0,
            somente_leitura=True
        )
        campos["recuperacao"] = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            aba,
            text="Ativar recuperação controlada (simulação)",
            variable=campos["recuperacao"],
        ).pack(pady=(0, 8))

    ttk.Label(aba, text="Ativo da análise:").pack()
    ativos_disponiveis = (
        ATIVOS_OTC_PRIORITARIOS
        if tipo_mercado == "OTC"
        else ATIVOS_MERCADO_ABERTO
    )
    campos["ativo"] = ttk.Combobox(
        aba,
        values=(ATIVO_NAO_SELECIONADO,) + tuple(ativos_disponiveis),
        state="readonly",
        width=30,
    )
    campos["ativo"].set(ATIVO_NAO_SELECIONADO)
    campos["ativo"].pack(pady=(3, 9))
    seletores_ativo.append(campos["ativo"])

    if tipo_mercado == "MERCADO ABERTO":
        def atualizar_ativo_aberto_selecionado(_evento=None):
            evento_ativo = eventos_radar.get(campos["ativo"].get())
            if evento_ativo:
                atualizar_painel_mercado_aberto(evento_ativo)
            atualizar_graficos_mercado_aberto()

        campos["ativo"].bind(
            "<<ComboboxSelected>>", atualizar_ativo_aberto_selecionado
        )

    ttk.Label(aba, text="Modo de operação:").pack()
    modos_disponiveis = ["SOMENTE SINAIS"]
    if tipo_mercado == "OTC":
        modos_disponiveis.extend([MODO_PRATICA_UI, MODO_REAL_UI])
    else:
        modos_disponiveis.append(MODO_REAL_UI)
    campos["modo"] = ttk.Combobox(
        aba,
        values=modos_disponiveis,
        state="readonly",
        width=31,
    )
    campos["modo"].set("SOMENTE SINAIS")
    campos["modo"].pack(pady=(3, 9))

    ttk.Label(aba, text="Gráfico:").pack()
    campos["timeframe"] = ttk.Combobox(
        aba, values=["M1", "M5", "M15"], state="readonly", width=21
    )
    campos["timeframe"].set("M1")
    campos["timeframe"].pack(pady=(3, 9))

    ttk.Label(aba, text="Estratégia:").pack()
    campos["estrategia"] = ttk.Combobox(
        aba, values=estrategias, state="readonly", width=24
    )
    campos["estrategia"].set("Automático")
    campos["estrategia"].pack(pady=(3, 12))

    if tipo_mercado == "OTC":
        campos["ativo"].bind(
            "<<ComboboxSelected>>",
            lambda _evento: janela.after_idle(atualizar_graficos_otc),
        )
        campos["estrategia"].bind(
            "<<ComboboxSelected>>",
            lambda _evento: janela.after_idle(atualizar_graficos_otc),
        )

    if tipo_mercado == "OTC":
        ttk.Label(
            aba,
            text=(
                "OTC: captura visual • plataforma confirmada • "
                "gráfico, par, tempo e payout reconhecidos • sem gale"
            ),
            foreground="#8f7bd8",
        ).pack(pady=(0, 10))

    painel = ttk.LabelFrame(aba, text="Análise da última vela fechada", padding=10)
    painel.pack(fill="x", pady=(4, 12))
    sinal_var = tk.StringVar(value="AGUARDAR")
    pontuacao_var = tk.StringVar(value="Confluência: 0%")
    motivo_var = tk.StringVar(value="Aguardando velas fechadas...")
    probabilidade_var = tk.StringVar(
        value=(
            "Força da confluência: aguardando dados reais"
            if tipo_mercado == "MERCADO ABERTO"
            else "Probabilidade: NÃO CALIBRADA"
        )
    )
    direcao_var = tk.StringVar(value="Direção: NÃO ENTRAR")
    momento_var = tk.StringVar(
        value="Momento: aguardar análise da próxima vela M1"
    )
    payout_var = tk.StringVar(
        value=(
            "Análise: Big Foot Win"
            if tipo_mercado == "MERCADO ABERTO"
            else "Payout: —"
        )
    )
    execucao_var = tk.StringVar(
        value=(
            "Somente sinais • nenhuma ordem enviada"
            if tipo_mercado == "MERCADO ABERTO"
            else "Ordem simulada: AGUARDANDO SINAL"
        )
    )
    recuperacao_var = tk.StringVar(
        value=(
            f"Radar: aguardando os {len(ATIVOS_MERCADO_ABERTO)} pares Forex"
            if tipo_mercado == "MERCADO ABERTO"
            else "Recuperação: DESATIVADA"
        )
    )
    estado_operacao_var = tk.StringVar(
        value=(
            "Dados reais: aguardando atualização"
            if tipo_mercado == "MERCADO ABERTO"
            else "Tela da corretora: PRONTO"
        )
    )
    placar_demo_var = tk.StringVar(
        value=(
            "Ativo selecionado: aguardando primeira vela"
            if tipo_mercado == "MERCADO ABERTO"
            else "Demo: 0V / 0D / 0E • taxa observada: —"
        )
    )
    ttk.Label(painel, textvariable=sinal_var, font=("Arial", 18, "bold")).pack()
    ttk.Label(painel, textvariable=pontuacao_var).pack(pady=3)
    ttk.Label(
        painel, textvariable=motivo_var, wraplength=450, justify="center"
    ).pack()
    ttk.Label(painel, textvariable=probabilidade_var).pack(pady=(6, 1))
    ttk.Label(
        painel, textvariable=direcao_var, font=("Arial", 11, "bold")
    ).pack(pady=(5, 1))
    ttk.Label(painel, textvariable=momento_var, foreground="#b00020").pack()
    ttk.Label(painel, textvariable=payout_var).pack()
    ttk.Label(painel, textvariable=execucao_var).pack()
    ttk.Label(painel, textvariable=recuperacao_var).pack(pady=(2, 0))
    ttk.Label(painel, textvariable=estado_operacao_var).pack(pady=(2, 0))
    ttk.Label(
        painel, textvariable=placar_demo_var, font=("Arial", 11, "bold")
    ).pack(pady=(6, 0))
    paineis_resultado[tipo_mercado] = (
        sinal_var, pontuacao_var, motivo_var, probabilidade_var,
        direcao_var, momento_var, payout_var, execucao_var,
        recuperacao_var, estado_operacao_var, placar_demo_var
    )

    def iniciar():
        global inicio_otc_pendente
        try:
            if campos["ativo"].get() == ATIVO_NAO_SELECIONADO:
                raise ValueError("escolha primeiro somente o ativo que deseja analisar")
            if not plataforma_confirmada_para_modo(campos["modo"].get()):
                raise ValueError(
                    "confirme a plataforma de operação na aba Plataformas antes de iniciar"
                )
            leitura_otc_pronta = bool(
                snapshot_visual_disponivel(
                    campos["ativo"].get(), campos["timeframe"].get()
                )
                and captura_visual_atual
                and payout_visual_atual is not None
            )
            if tipo_mercado == "OTC" and not leitura_otc_pronta:
                inicio_otc_pendente = iniciar
                sinal_var.set("CARREGANDO TELA...")
                motivo_var.set(
                    "Capturando e validando gráfico, par e payout OTC antes de iniciar"
                )
                execucao_var.set("Ordens: AGUARDANDO CAPTURA VISUAL")
                status.config(text="Status: VALIDANDO GRÁFICO OTC...")
                testar_permissao_iq()
                return
            if campos["modo"].get() == MODO_REAL_UI:
                if not executor_demo_iq.armar_conta_real(
                    plataforma_confirmada == plataforma_ativa_var.get()
                ):
                    raise ValueError("não foi possível armar: plataforma não confirmada")
                iq_trava_var.set(
                    f"Disparo REAL: ARMADO na {plataforma_confirmada} para um clique"
                )
            sinal_var.set("INICIANDO...")
            banca_var.set(campos["banca"].get())
            motivo_var.set(
                f"Baixando velas reais e analisando os {len(ATIVOS_MERCADO_ABERTO)} pares Forex"
                if tipo_mercado == "MERCADO ABERTO"
                else "Aguardando a próxima vela visual fechada"
            )
            execucao_var.set(
                "Mercado aberto online • real armado para uma entrada"
                if tipo_mercado == "MERCADO ABERTO" and campos["modo"].get() == MODO_REAL_UI
                else "Mercado aberto online • somente sinais"
                if tipo_mercado == "MERCADO ABERTO"
                else (
                    "Demo visual ativo • clique apenas na conta prática"
                    if campos["modo"].get() == MODO_PRATICA_UI
                    else "Disparo real ARMADO • máximo de uma entrada automática"
                    if campos["modo"].get() == MODO_REAL_UI
                    else "Somente sinais • nenhum clique na IQ"
                )
            )
            janela.update_idletasks()
            iniciar_robo(
                converter_numero(campos["banca"].get(), "banca"),
                converter_numero(campos["entrada"].get(), "valor da entrada"),
                converter_numero(campos["gain"].get(), "stop gain"),
                converter_numero(campos["loss"].get(), "stop loss"),
                campos["estrategia"].get(),
                campos["timeframe"].get(),
                tipo_mercado,
                payout_visual_atual if tipo_mercado == "OTC" else None,
                False if campos["recuperacao"] is None else campos["recuperacao"].get(),
                modo_para_motor(campos["modo"].get()),
                campos["ativo"].get(),
            )
            status.config(
                text=(
                    f"Status: RODANDO — {campos['ativo'].get()} — "
                    f"{campos['timeframe'].get()}"
                )
            )
            botao_iniciar.config(state="disabled")
            botao_pausar.config(state="normal")
            botao_parar.config(state="normal")
            campos["modo"].config(state="disabled")
        except ValueError as erro:
            sinal_var.set("AGUARDAR")
            motivo_var.set(str(erro))
            messagebox.showerror("Erro", str(erro))

    def pausar():
        pausar_robo()
        executor_demo_iq.desarmar_conta_real()
        status.config(text=f"Status: PAUSADO — {tipo_mercado}")
        sinal_var.set("PAUSADO")
        motivo_var.set("Processamento pausado pelo usuário")
        botao_iniciar.config(state="normal")
        campos["modo"].config(state="readonly")

    def parar():
        global agendamento_captura_periodica
        parar_robo()
        executor_demo_iq.desarmar_conta_real()
        if agendamento_captura_periodica is not None:
            janela.after_cancel(agendamento_captura_periodica)
            agendamento_captura_periodica = None
        status.config(text="Status: PARADO — MODO TESTE")
        sinal_var.set("PARADO")
        motivo_var.set("Selecione o ativo e pressione INICIAR")
        botao_iniciar.config(state="normal")
        botao_pausar.config(state="disabled")
        botao_parar.config(state="disabled")
        campos["modo"].config(state="readonly")

    # Mesmos comandos e estados, com a apresentação visual da nova referência.
    linha_acoes_robo = tk.Frame(aba, bg=COR_BG)
    linha_acoes_robo.pack(fill="x", pady=(4, 10))
    botao_iniciar = ttk.Button(
        linha_acoes_robo,
        text="▶  Iniciar robô",
        style="PremiumAction.TButton",
        command=iniciar,
    )
    botao_iniciar.pack(fill="x", pady=(0, 6))
    botao_pausar = ttk.Button(
        linha_acoes_robo,
        text="⏸  Pausar robô",
        command=pausar,
        state="disabled",
    )
    botao_pausar.pack(fill="x", pady=(0, 6))
    botao_parar = ttk.Button(
        linha_acoes_robo,
        text="⏹  Parar robô",
        style="PremiumRed.TButton",
        command=parar,
        state="disabled",
    )
    botao_parar.pack(fill="x")

    if tipo_mercado == "MERCADO ABERTO":
        criar_graficos_mercado_aberto(aba)
    elif tipo_mercado == "OTC":
        criar_graficos_otc(aba)


criar_aba(
    "Mercado Aberto", "MERCADO ABERTO",
    ["Tendência + Pullback", "Rompimento", "Reversão", "Automático"],
)


def criar_aba_analise():
    global arvore_radar
    aba = ttk.Frame(abas, padding=16)
    abas.add(aba, text="Análise")

    ttk.Label(
        aba, text="Radar completo do Mercado Aberto", font=("Arial", 17, "bold")
    ).pack(anchor="w", pady=(0, 4))
    ttk.Label(
        aba,
        text=("Cada linha recebe velas reais e sua própria análise. "
              "Clique em um par para abrir os detalhes abaixo."),
        wraplength=620, justify="left",
    ).pack(anchor="w", pady=(0, 8))

    colunas_radar = ("ativo", "preco", "variacao", "regime", "confluencia", "sinal", "hora")
    quadro_radar = ttk.Frame(aba)
    quadro_radar.pack(fill="x", pady=(0, 14))
    arvore_radar = ttk.Treeview(
        quadro_radar, columns=colunas_radar, show="headings", height=12
    )
    titulos = {
        "ativo": "Ativo", "preco": "Preço", "variacao": "Variação",
        "regime": "Regime", "confluencia": "Confluência",
        "sinal": "Sinal", "hora": "Vela",
    }
    larguras = {"ativo": 95, "preco": 85, "variacao": 72, "regime": 70,
                "confluencia": 82, "sinal": 78, "hora": 52}
    for coluna in colunas_radar:
        arvore_radar.heading(coluna, text=titulos[coluna])
        arvore_radar.column(coluna, width=larguras[coluna], anchor="center")
    rolagem_radar = ttk.Scrollbar(
        quadro_radar, orient="vertical", command=arvore_radar.yview
    )
    arvore_radar.configure(yscrollcommand=rolagem_radar.set)
    arvore_radar.pack(side="left", fill="x", expand=True)
    rolagem_radar.pack(side="right", fill="y")

    resumo = {
        "regime": tk.StringVar(value="Aguardando"),
        "confluencia": tk.StringVar(value="—"),
        "payout": tk.StringVar(value="—"),
        "risco": tk.StringVar(value="—"),
        "direcao": tk.StringVar(value="AGUARDAR"),
        "entrada": tk.StringVar(value="Inicie o Mercado Aberto para carregar o radar"),
        "mercado": tk.StringVar(value="RADAR · M1"),
        "preco": tk.StringVar(value="—"),
        "maxima": tk.StringVar(value="—"),
        "suporte": tk.StringVar(value="—"),
        "resistencia": tk.StringVar(value="—"),
    }
    globals()["variaveis_analise"] = resumo

    cabecalho = tk.Frame(aba, bg="#171229")
    cabecalho.pack(fill="x", pady=(0, 12))
    tk.Label(
        cabecalho, textvariable=resumo["mercado"], fg="#f1effb",
        bg="#171229", font=("Arial", 16, "bold"), anchor="w",
    ).pack(side="left")
    tk.Label(
        cabecalho, textvariable=resumo["preco"], fg="#7CFFB7",
        bg="#171229", font=("Arial", 13, "bold"), anchor="e",
    ).pack(side="right")

    grid = tk.Frame(aba, bg="#171229")
    grid.pack(fill="x", pady=(0, 12))
    cores = [
        ("Regime", resumo["regime"], "#171229", "#AFA9EC"),
        ("Confluência", resumo["confluencia"], "#171229", "#97C459"),
        ("Payout", resumo["payout"], "#171229", "#7DD3FC"),
        ("Risco", resumo["risco"], "#2a1414", "#F7C1C1"),
    ]
    for nome, var, bg, fg in cores:
        bloco = tk.Frame(grid, bg=bg, bd=1, relief="solid", padx=12, pady=10, highlightthickness=1, highlightbackground="#2a2440")
        bloco.pack(side="left", fill="both", expand=True, padx=(0, 8))
        tk.Label(bloco, text=nome, fg="#8a8aa0", bg=bg, font=("Arial", 9)).pack(anchor="w")
        tk.Label(bloco, textvariable=var, fg=fg, bg=bg, font=("Arial", 15, "bold")).pack(anchor="w", pady=(3, 0))

    conteudo_analise = tk.Frame(aba, bg="#171229")
    conteudo_analise.pack(fill="x", pady=(0, 12))

    painel_analise = ttk.LabelFrame(conteudo_analise, text="Análise", padding=12)
    painel_analise.pack(side="left", fill="both", expand=True, padx=(0, 12))
    tk.Label(painel_analise, text="Regime", bg="#171229", fg="#8a8aa0", anchor="w", justify="left").pack(fill="x")
    tk.Label(painel_analise, textvariable=resumo["regime"], bg="#171229", fg="#f1effb", font=("Arial", 14, "bold"), anchor="w", justify="left").pack(fill="x", pady=(4, 8))
    tk.Label(painel_analise, text="Trend", bg="#171229", fg="#8a8aa0", anchor="w", justify="left").pack(fill="x")
    tk.Label(painel_analise, textvariable=resumo["direcao"], bg="#171229", fg="#f1effb", font=("Arial", 13, "bold"), anchor="w", justify="left").pack(fill="x", pady=(4, 8))
    tk.Label(painel_analise, text="RSI", bg="#171229", fg="#8a8aa0", anchor="w", justify="left").pack(fill="x")
    tk.Label(painel_analise, text="—", bg="#171229", fg="#f1effb", font=("Arial", 13, "bold"), anchor="w", justify="left").pack(fill="x", pady=(4, 0))

    painel_acoes = ttk.LabelFrame(conteudo_analise, text="Ações", padding=12)
    painel_acoes.pack(side="right", fill="y")
    alta_var = tk.StringVar()
    baixa_var = tk.StringVar()

    def atualizar_rotulos_acoes(*_args):
        alta, baixa = rotulos_operacao_plataforma()
        alta_var.set(alta)
        baixa_var.set(baixa)

    atualizar_rotulos_acoes()
    plataforma_ativa_var.trace_add("write", atualizar_rotulos_acoes)
    for texto_var, estilo in (
        (alta_var, "PremiumGreen.TButton"),
        (baixa_var, "PremiumRed.TButton"),
    ):
        ttk.Button(
            painel_acoes,
            textvariable=texto_var,
            style=estilo,
            width=15,
        ).pack(fill="x", pady=5)

    def selecionar_par(_evento=None):
        selecao = arvore_radar.selection()
        if selecao:
            evento = eventos_radar.get(selecao[0])
            if evento:
                atualizar_resumo_analise(evento)

    arvore_radar.bind("<<TreeviewSelect>>", selecionar_par)

    plano = ttk.LabelFrame(aba, text="Plano de execução", padding=12)
    plano.pack(fill="x", pady=(0, 10))
    tk.Label(plano, textvariable=resumo["direcao"], bg="#171229", fg="#f1effb", font=("Arial", 14, "bold")).pack(anchor="w")
    tk.Label(plano, textvariable=resumo["entrada"], bg="#171229", fg="#afa9ec", justify="left", wraplength=560).pack(anchor="w", pady=(8, 0))

    grafico = ttk.LabelFrame(aba, text="Estrutura de mercado", padding=8)
    grafico.pack(fill="x")
    canvas_plot = tk.Canvas(grafico, width=640, height=170, bg="#171229", highlightthickness=0)
    canvas_plot.pack(fill="both", expand=True)

    for y in (20, 55, 90, 125, 160):
        canvas_plot.create_line(0, y, 640, y, fill="#3C3489", width=1, stipple="gray50")

    canvas_plot.create_text(
        320, 85,
        text="AGUARDANDO DADOS REAIS DO PAR SELECIONADO",
        fill="#8a8aa0",
        font=("Helvetica Neue", 10, "bold"),
        anchor="center",
    )

    stats = tk.Frame(aba, bg="#171229")
    stats.pack(fill="x", pady=(12, 0))
    for label_text, var_key in (("Máxima", "maxima"), ("Suporte", "suporte"), ("Resistência", "resistencia")):
        bloco = tk.Frame(stats, bg="#171229", bd=1, relief="solid", padx=12, pady=10, highlightthickness=1, highlightbackground="#2a2440")
        bloco.pack(side="left", fill="both", expand=True, padx=(0, 8))
        tk.Label(bloco, text=label_text, fg="#8a8aa0", bg="#171229", font=("Arial", 9)).pack(anchor="w")
        tk.Label(bloco, textvariable=resumo[var_key], fg="#f1effb", bg="#171229", font=("Arial", 15, "bold")).pack(anchor="w", pady=(3, 0))



def criar_aba_indicadores():
    global arvore_diagnosticos, resumo_indicadores_var
    aba = ttk.Frame(abas, padding=16)
    abas.add(aba, text="Indicadores")
    ttk.Label(aba, text="Central de confluência M1", font=("Arial", 17, "bold")).pack(pady=(0, 4))
    ttk.Label(
        aba,
        text=("Use o modo automático para o BFT escolher os indicadores que mais "
              "confluem com o regime atual do mercado. Ele analisa quais sinais "
              "estão alinhados e prioriza a combinação com maior confluência. "
              "Se desligar, você monta a análise pessoal manualmente. Cada "
              "estratégia usa no máximo 3 indicadores; BFT PANO é opcional. "
              "No modo real, a plataforma precisa estar confirmada e cada "
              "armação permite apenas um disparo."),
        wraplength=610, justify="center",
    ).pack(pady=(0, 12))

    automatico = tk.BooleanVar(value=True)
    ttk.Checkbutton(
        aba, text="AUTOMÁTICO — escolher indicadores conforme o mercado",
        variable=automatico,
    ).pack(anchor="w", pady=(0, 10))
    selecoes = {}
    grupos = {}
    for item in INDICADORES:
        grupo = grupos.get(item.categoria)
        if grupo is None:
            grupo = ttk.LabelFrame(aba, text=item.categoria, padding=8)
            grupo.pack(fill="x", pady=4)
            grupos[item.categoria] = grupo
        variavel = tk.BooleanVar(value=item.codigo in PADRAO_MANUAL)
        selecoes[item.codigo] = variavel
        texto = item.nome if item.implementado else f"{item.nome}  • referência / fórmula fechada"
        ttk.Checkbutton(
            grupo, text=texto, variable=variavel,
            state="normal" if item.implementado else "disabled",
        ).pack(anchor="w")

    resumo_indicadores_var = tk.StringVar(value="Automático ativo • aguardando análise M1")
    ttk.Label(aba, textvariable=resumo_indicadores_var, wraplength=610,
              font=("Arial", 11, "bold")).pack(pady=10)

    def aplicar():
        ativos = {codigo for codigo, var in selecoes.items() if var.get()}
        try:
            _, aceitos = definir_configuracao_indicadores(automatico.get(), ativos)
        except ValueError as erro:
            messagebox.showerror("Indicadores", str(erro))
            return
        modo = "AUTOMÁTICO POR REGIME" if automatico.get() else "SELEÇÃO PESSOAL"
        resumo_indicadores_var.set(f"{modo} • {len(aceitos)} módulos calculáveis selecionados")
        messagebox.showinfo("Indicadores", "Configuração aplicada à próxima vela M1 fechada.")

    ttk.Button(aba, text="APLICAR NA ANÁLISE", command=aplicar).pack(pady=(0, 12))
    ttk.Label(aba, text="Diagnóstico da última confluência", font=("Arial", 12, "bold")).pack()
    moldura = ttk.Frame(aba)
    moldura.pack(fill="both", expand=True, pady=6)
    arvore_diagnosticos = ttk.Treeview(
        moldura, columns=("indicador", "direcao", "peso", "motivo"),
        show="headings", height=11,
    )
    for col, titulo, largura in (
        ("indicador", "Indicador", 150), ("direcao", "Leitura", 80),
        ("peso", "Peso", 45), ("motivo", "Motivo", 300),
    ):
        arvore_diagnosticos.heading(col, text=titulo)
        arvore_diagnosticos.column(col, width=largura, anchor="w")
    arvore_diagnosticos.pack(side="left", fill="both", expand=True)
    barra = ttk.Scrollbar(moldura, orient="vertical", command=arvore_diagnosticos.yview)
    barra.pack(side="right", fill="y")
    arvore_diagnosticos.configure(yscrollcommand=barra.set)


criar_aba_analise()
criar_aba_indicadores()


def criar_aba_estrategias():
    aba = ttk.Frame(abas, padding=16)
    abas.add(aba, text="Estratégias")
    ttk.Label(aba, text="Montador de estratégias", font=("Arial", 17, "bold")).pack(pady=(0, 4))
    ttk.Label(
        aba,
        text=("Combine livremente até 3 indicadores. Eles serão avaliados juntos "
              "como uma única estratégia na próxima vela M1 fechada."),
        wraplength=610, justify="center",
    ).pack(pady=(0, 14))

    quadro_prontas = ttk.LabelFrame(aba, text="Modelos prontos", padding=12)
    quadro_prontas.pack(fill="x", pady=5)
    preset = ttk.Combobox(
        quadro_prontas, values=tuple(ESTRATEGIAS_PRONTAS),
        state="readonly", width=30,
    )
    preset.set("Tendência M1")
    preset.pack(pady=4)

    quadro_livre = ttk.LabelFrame(aba, text="Combinação livre", padding=12)
    quadro_livre.pack(fill="x", pady=8)
    implementados = [item for item in INDICADORES if item.implementado]
    nomes = ["— nenhum —"] + [item.nome for item in implementados]
    codigo_por_nome = {item.nome: item.codigo for item in implementados}
    seletores = []
    for numero in range(1, 4):
        ttk.Label(quadro_livre, text=f"Indicador {numero}:").pack()
        seletor = ttk.Combobox(quadro_livre, values=nomes, state="readonly", width=34)
        seletor.set("— nenhum —")
        seletor.pack(pady=(3, 9))
        seletores.append(seletor)

    resumo = tk.StringVar(value="Nenhuma estratégia pessoal aplicada")
    ttk.Label(aba, textvariable=resumo, wraplength=610,
              font=("Arial", 11, "bold")).pack(pady=8)

    def carregar_modelo(_evento=None):
        codigos = ESTRATEGIAS_PRONTAS[preset.get()]
        for seletor, codigo in zip(seletores, codigos):
            seletor.set(POR_CODIGO[codigo].nome)

    def aplicar_livre():
        codigos = [codigo_por_nome[s.get()] for s in seletores if s.get() in codigo_por_nome]
        if not codigos:
            messagebox.showerror("Estratégia", "Escolha pelo menos um indicador.")
            return
        if len(codigos) != len(set(codigos)):
            messagebox.showerror("Estratégia", "Não repita o mesmo indicador na combinação.")
            return
        definir_configuracao_indicadores(False, set(codigos))
        nomes_ativos = " + ".join(POR_CODIGO[c].nome for c in codigos)
        resumo.set(f"ESTRATÉGIA PESSOAL ATIVA: {nomes_ativos}")
        if resumo_indicadores_var is not None:
            resumo_indicadores_var.set(f"Seleção pessoal • {nomes_ativos}")
        messagebox.showinfo("Estratégia", "Combinação aplicada à próxima vela M1 fechada.")

    def ativar_automatico():
        definir_configuracao_indicadores(True)
        resumo.set("AUTOMÁTICO ATIVO: o BFT escolherá uma combinação de 3 por regime")
        if resumo_indicadores_var is not None:
            resumo_indicadores_var.set("Automático por regime • máximo de 3 indicadores")

    preset.bind("<<ComboboxSelected>>", carregar_modelo)
    carregar_modelo()
    ttk.Button(aba, text="APLICAR COMBINAÇÃO", command=aplicar_livre).pack(pady=6)
    ttk.Button(aba, text="USAR AUTOMÁTICO POR REGIME", command=ativar_automatico).pack(pady=6)
    ttk.Label(
        aba,
        text=("A pontuação é uma medida experimental de confluência, não uma "
              "probabilidade garantida. No modo real, a plataforma confirmada "
              "permite somente um disparo por armação."),
        foreground="#8f7bd8", wraplength=610, justify="center",
    ).pack(pady=14)


criar_aba_estrategias()


def criar_historico_entradas():
    global arvore_operacoes, painel_abas_iq
    aba = ttk.Frame(abas, padding=14)
    abas.add(aba, text="Histórico de Entradas")
    ttk.Label(
        aba,
        text="Histórico de Entradas",
        font=("Arial", 17, "bold"),
    ).pack(pady=(0, 8))
    ttk.Label(
        aba,
        text=(
            "Cada tentativa automática fica registrada aqui, incluindo entradas "
            "enviadas e operações bloqueadas pelas travas."
        ),
        wraplength=620,
        justify="center",
    ).pack(pady=(0, 10))

    moldura_tabela = ttk.Frame(aba)
    moldura_tabela.pack(fill="both", expand=True, pady=6)
    arvore_operacoes = ttk.Treeview(
        moldura_tabela,
        columns=(
            "hora", "conta", "plataforma", "ativo", "direcao", "valor", "estado"
        ),
        show="headings",
        height=18,
    )
    for coluna, titulo, largura in (
        ("hora", "Horário", 70),
        ("conta", "Conta", 65),
        ("plataforma", "Plataforma", 90),
        ("ativo", "Ativo", 125),
        ("direcao", "Direção", 80),
        ("valor", "Valor", 70),
        ("estado", "Resultado", 260),
    ):
        arvore_operacoes.heading(coluna, text=titulo)
        arvore_operacoes.column(coluna, width=largura, anchor="center")
    arvore_operacoes.pack(side="left", fill="both", expand=True)
    rolagem_tabela = ttk.Scrollbar(
        moldura_tabela, orient="vertical", command=arvore_operacoes.yview
    )
    rolagem_tabela.pack(side="right", fill="y")
    arvore_operacoes.configure(yscrollcommand=rolagem_tabela.set)

    for indice, item in enumerate(reversed(carregar_entradas()), start=1):
        arvore_operacoes.insert(
            "", "end", iid=f"historico-{indice}", values=(
                item["horario"], item["conta"], item["plataforma"],
                item["ativo"], item["direcao"], item["valor"],
                item["resultado"],
            ),
        )

    # O painel de ativos continua apenas como estado interno da leitura visual.
    painel_abas_iq = PainelAbasIq()

    ttk.Label(
        aba,
        text="Histórico salvo localmente • nenhuma senha ou login é armazenado",
        foreground="#8f7bd8",
    ).pack(pady=12)


def atualizar_linha_central(ativo, payout):
    encontrada = None
    for linha in painel_abas_iq.linhas():
        if linha.ativo == ativo:
            encontrada = linha
            break
    estado = "PAYOUT OK" if payout >= 0.80 else "PAYOUT BAIXO"
    if encontrada is None:
        encontrada = painel_abas_iq.adicionar(ativo)
    painel_abas_iq.atualizar(
        encontrada.numero, payout=payout, estado=estado
    )
    # Um ativo OTC observado nunca substitui a lista separada de Mercado Aberto.
    seletor_otc = campos_por_mercado.get("OTC", {}).get("ativo")
    if seletor_otc is not None:
        ranking_otc = sorted(
            painel_abas_iq.linhas(),
            key=lambda linha: (linha.payout is not None, linha.payout or 0),
            reverse=True,
        )[:10]
        seletor_otc.configure(values=(ATIVO_NAO_SELECIONADO,) + tuple(
            linha.ativo for linha in ranking_otc
        ))


criar_historico_entradas()

def criar_execucao_direta():
    aba = ttk.Frame(abas, padding=16)
    abas.add(aba, text="Execução direta")
    ttk.Label(
        aba,
        text="Entrada manual direta na plataforma",
        font=("Arial", 17, "bold"),
    ).pack(pady=(0, 6))
    ttk.Label(
        aba,
        text=("Cada bloco usa exclusivamente os botões e a calibração da "
              "corretora indicada."),
        wraplength=620,
        justify="center",
    ).pack(pady=(0, 12))

    ativos = list(ATIVOS_OTC_PRIORITARIOS) + list(ATIVOS_MERCADO_ABERTO)
    ttk.Label(aba, text="Ativo:").pack(anchor="w")
    seletor_ativo_manual = ttk.Combobox(
        aba,
        values=ativos,
        state="readonly",
        width=30,
    )
    seletor_ativo_manual.set(ativos[0])
    seletor_ativo_manual.pack(pady=(3, 10))

    ttk.Label(aba, text="Valor da entrada:").pack(anchor="w")
    entrada_manual = ttk.Entry(aba, width=24)
    entrada_manual.insert(0, "25")
    entrada_manual.pack(pady=(3, 12))

    def normalizar_direcao_manual(escolha):
        texto = (escolha or "").upper()
        if any(token in texto for token in ("CALL", "HIGHER", "BUY")):
            return "ALTA"
        if any(token in texto for token in ("PUT", "LOWER", "SELL")):
            return "BAIXA"
        raise ValueError("Seleção de direção inválida. Use CALL/HIGHER ou PUT/LOWER.")

    def executar_manual(escolha, plataforma_destino):
        if plataforma_ativa_var.get() != plataforma_destino:
            messagebox.showwarning(
                plataforma_destino,
                f"Selecione {plataforma_destino} na aba Plataformas e espelhe "
                "a conta prática dessa corretora antes de usar estes botões.",
            )
            return
        if not conta_demo_confirmada:
            messagebox.showwarning(
                "Conta prática",
                "Confirme a conta demo antes de disparar a ordem direta.",
            )
            return
        calibracoes = {
            "Quotex": coordenadas_quotex,
            "Casa Trader": coordenadas_casa_trader,
            "Avallon": coordenadas_avallon,
        }
        if plataforma_destino in calibracoes and not calibracoes[plataforma_destino]:
            messagebox.showwarning(
                f"{plataforma_destino} não calibrada",
                f"Calibre primeiro os dois botões da {plataforma_destino}.",
            )
            return
        # Em execução manual de teste não exigimos análise, confluência, payout
        # nem uma leitura anterior. A captura técnica é criada na hora apenas
        # para validar a tela usada pela coordenada calibrada.
        caminho_execucao = captura_visual_atual
        if not caminho_execucao:
            captura_teste = testar_captura(caminho="/private/tmp/bft_click_manual.png")
            if not captura_teste.sucesso:
                messagebox.showwarning(
                    "Captura do macOS",
                    "Não foi possível preparar o clique. Libere a gravação de tela para o BFT.",
                )
                return
            caminho_execucao = captura_teste.caminho
        ativo = seletor_ativo_manual.get().strip()
        if not ativo:
            messagebox.showwarning("Ativo", "Escolha um ativo antes de executar.")
            return
        try:
            sinal = normalizar_direcao_manual(escolha)
            valor = converter_numero(entrada_manual.get(), "valor da entrada")
        except ValueError as erro:
            messagebox.showerror("Execução direta", str(erro))
            return

        chave = f"manual-{ativo}-{time.strftime('%H%M%S')}"
        executar_clique_assincrono(
            sinal,
            chave,
            caminho_execucao,
            conta_demo_confirmada,
            janela.winfo_screenwidth(),
            janela.winfo_screenheight(),
            "OTC",
            ativo,
            valor,
            plataforma=plataforma_destino,
        )

    def criar_comandos_corretora(titulo, plataforma_destino, alta, baixa):
        quadro = ttk.LabelFrame(aba, text=titulo, padding=14)
        quadro.pack(fill="x", pady=(4, 12))
        ttk.Label(
            quadro,
            text=f"Comandos exclusivos da {plataforma_destino}",
            font=("Arial", 11, "bold"),
        ).pack(anchor="w", pady=(0, 8))
        linha = ttk.Frame(quadro)
        linha.pack(fill="x")
        ttk.Button(
            linha, text=alta,
            command=lambda: executar_manual("ALTA", plataforma_destino),
            style="PremiumGreen.TButton",
        ).pack(side="left", fill="x", expand=True, padx=(0, 6), pady=5)
        ttk.Button(
            linha, text=baixa,
            command=lambda: executar_manual("BAIXA", plataforma_destino),
            style="PremiumRed.TButton",
        ).pack(side="left", fill="x", expand=True, padx=(6, 0), pady=5)
        return quadro

    quadro_iq = criar_comandos_corretora(
        "IQ OPTION — HIGHER / LOWER", "IQ Option", "HIGHER", "LOWER"
    )
    ttk.Label(
        quadro_iq, textvariable=iq_option_calibracao_status_var,
        foreground="#78d7a3",
    ).pack(pady=(8, 4))
    ttk.Button(
        quadro_iq, text="CALIBRAR HIGHER / LOWER DA IQ OPTION",
        command=calibrar_iq_option, style="PremiumAction.TButton",
    ).pack(fill="x", pady=(4, 2))
    quadro_quotex = criar_comandos_corretora(
        "QUOTEX — CALL / PUT", "Quotex", "CALL", "PUT"
    )
    ttk.Label(
        quadro_quotex,
        textvariable=quotex_calibracao_status_var,
        foreground="#78d7a3",
    ).pack(pady=(8, 4))
    ttk.Button(
        quadro_quotex,
        text="CALIBRAR CALL / PUT DA QUOTEX",
        command=calibrar_quotex,
        style="PremiumAction.TButton",
    ).pack(fill="x", pady=(4, 2))

    quadro_casa = criar_comandos_corretora(
        "CASA TRADER — COMPRAR / VENDER",
        "Casa Trader", "COMPRAR", "VENDER",
    )
    ttk.Label(
        quadro_casa, textvariable=casa_trader_calibracao_status_var,
        foreground="#78d7a3",
    ).pack(pady=(8, 4))
    ttk.Button(
        quadro_casa, text="CALIBRAR COMPRAR / VENDER DA CASA TRADER",
        command=calibrar_casa_trader, style="PremiumAction.TButton",
    ).pack(fill="x", pady=(4, 2))

    quadro_avallon = criar_comandos_corretora(
        "AVALLON — BUY / SELL", "Avallon", "BUY", "SELL",
    )
    ttk.Label(
        quadro_avallon, textvariable=avallon_calibracao_status_var,
        foreground="#78d7a3",
    ).pack(pady=(8, 4))
    ttk.Button(
        quadro_avallon, text="CALIBRAR BUY / SELL DA AVALLON",
        command=calibrar_avallon, style="PremiumAction.TButton",
    ).pack(fill="x", pady=(4, 2))


criar_execucao_direta()
criar_aba(
    "OTC", "OTC",
    [
        "Tendência OTC", "Reversão OTC", "Confluência OTC",
        "Kill Binary", "Automático",
    ],
)


def abrir_otc_inicial():
    """Abre na área operacional OTC, mantendo a janela em tamanho normal."""
    janela.update_idletasks()
    guias = abas.tabs()
    if guias:
        abas.select(guias[-1])
    altura_total = max(1, conteudo.winfo_reqheight())
    destino = max(0.0, min(1.0, (abas.winfo_y() - 8) / altura_total))
    canvas.yview_moveto(destino)


janela.after(250, abrir_otc_inicial)



def executar_clique_assincrono(
    sinal,
    chave,
    caminho_captura,
    conta_confirmada,
    largura_tela,
    altura_tela,
    mercado_evento,
    ativo,
    valor,
    plataforma=None,
    tipo_conta="DEMO",
):
    plataforma_destino = plataforma or plataforma_ativa_var.get()
    coordenadas_por_plataforma = {
        "IQ Option": coordenadas_iq_option,
        "Quotex": coordenadas_quotex,
        "Casa Trader": coordenadas_casa_trader,
        "Avallon": coordenadas_avallon,
    }

    def tarefa():
        clique = executor_demo_iq.executar(
            sinal,
            chave,
            caminho_captura,
            conta_confirmada,
            largura_tela,
            altura_tela,
            plataforma=plataforma_destino,
            coordenadas=coordenadas_por_plataforma.get(plataforma_destino),
            tipo_conta=tipo_conta,
            plataforma_confirmada=(
                plataforma_confirmada == plataforma_destino
            ),
        )
        rotulos = {
            "IQ Option": ("HIGHER", "LOWER"),
            "Quotex": ("CALL", "PUT"),
            "Casa Trader": ("COMPRAR", "VENDER"),
            "Avallon": ("BUY", "SELL"),
        }.get(plataforma_destino, ("ALTA", "BAIXA"))
        direcao_evento = rotulos[0] if sinal == "ALTA" else rotulos[1]
        fila_eventos.put({
            "tipo": "resultado_clique_corretora",
            "mercado": mercado_evento,
            "mensagem_clique": clique.mensagem,
            "clique_sucesso": clique.sucesso,
            "tipo_conta": tipo_conta,
            "direcao": direcao_evento,
            "plataforma": plataforma_destino,
            "ativo": ativo,
            "valor": valor,
            "horario": time.strftime("%H:%M:%S"),
            "id_operacao": str(chave),
        })

    threading.Thread(target=tarefa, daemon=True).start()


def atualizar_resumo_analise(evento):
    global ultimo_evento_dashboard
    resumo = globals().get("variaveis_analise")
    if not resumo:
        return

    sinal = str(evento.get("sinal") or "AGUARDAR").upper()
    pontuacao = evento.get("pontuacao")
    if pontuacao is None:
        valor_confluencia = "—"
    else:
        valor_confluencia = f"{max(0, min(100, float(pontuacao) * 10)):.0f}%"

    payout = evento.get("payout")
    resumo["confluencia"].set(valor_confluencia)
    resumo["payout"].set("—" if payout is None else f"{float(payout):.0%}")
    resumo["regime"].set(
        evento.get("regime")
        or ("Bull" if sinal in ("ALTA", "CALL") else "Bear" if sinal in ("BAIXA", "PUT") else "Neutro")
    )
    resumo["direcao"].set(
        evento.get("direcao")
        or ("CALL / HIGHER" if sinal == "ALTA" else "PUT / LOWER" if sinal == "BAIXA" else "AGUARDAR CONFIRMAÇÃO")
    )
    resumo["entrada"].set(
        evento.get("entrada")
        or (
            "Aguardando confirmação de vela"
            if not sinal or sinal == "AGUARDAR"
            else (
                "Executar CALL / HIGHER com confirmação da vela e payout válido"
                if sinal == "ALTA"
                else "Executar PUT / LOWER com confirmação da vela e payout válido"
                if sinal == "BAIXA"
                else "Aguardando confluência suficiente"
            )
        )
    )
    resumo["risco"].set(evento.get("risco") or "—")
    resumo["mercado"].set(
        f"{evento.get('ativo') or evento.get('mercado', 'EUR/USD')} · {evento.get('timeframe', 'M1')}"
    )
    variacao = evento.get("variacao")
    resumo["preco"].set("—" if variacao is None else f"{float(variacao):+.2f}%")
    if evento.get("suporte") is not None:
        resumo["suporte"].set(f"{evento.get('suporte'):.4f}")
    if evento.get("resistencia") is not None:
        resumo["resistencia"].set(f"{evento.get('resistencia'):.4f}")
    if evento.get("maxima") is not None:
        resumo["maxima"].set(f"{evento.get('maxima'):.4f}")
    ultimo_evento_dashboard = evento
    atualizar_badges_status_30s(
        payout,
        None if pontuacao is None else int(pontuacao),
        evento.get("mercado"),
        sinal,
    )
    desenhar_grafico_velas(
        chart_canvas,
        evento,
        evento.get("ativo", "—"),
        "DADOS REAIS BFT WIN",
    )


def atualizar_painel_mercado_aberto(evento):
    """Mostra no painel principal a confirmação do par aberto selecionado."""
    painel = paineis_resultado.get("MERCADO ABERTO")
    if painel is None:
        return
    (
        sinal_var, pontuacao_var, motivo_var, probabilidade_var,
        direcao_var, momento_var, payout_var, execucao_var,
        recuperacao_var, estado_operacao_var, placar_demo_var,
    ) = painel

    sinal_bruto = str(evento.get("sinal") or "AGUARDAR").upper()
    direcao = str(evento.get("direcao") or "AGUARDAR").upper()
    if sinal_bruto == "SEM DADOS":
        direcao = "SEM DADOS"
    pontuacao = max(0, min(10, int(evento.get("pontuacao") or 0)))
    confluencia = pontuacao / 10.0
    horario = evento.get("horario", "—")
    timeframe = evento.get("timeframe", "M1")
    ativo = evento.get("ativo", "—")

    sinal_var.set(direcao)
    pontuacao_var.set(
        f"Confluência: {confluencia:.0%} • {timeframe} • Vela {horario}"
    )
    motivo_var.set(evento.get("motivo") or "Aguardando nova vela real fechada")
    probabilidade_var.set(
        f"Força da confluência: {confluencia:.0%} • não é probabilidade"
    )
    if direcao == "CALL":
        direcao_var.set("Direção confirmada: CALL")
        momento_var.set("Confirmação válida para a próxima vela fechada")
    elif direcao == "PUT":
        direcao_var.set("Direção confirmada: PUT")
        momento_var.set("Confirmação válida para a próxima vela fechada")
    elif direcao == "SEM DADOS":
        direcao_var.set("Direção: DADOS INDISPONÍVEIS")
        momento_var.set("Aguardando a fonte real responder")
    else:
        direcao_var.set("Direção: NÃO ENTRAR")
        momento_var.set("Momento: AGUARDAR confluência mínima de 80%")

    payout_var.set("Análise online: Big Foot Win")
    modo_evento = evento.get("modo_operacao", "SOMENTE SINAIS")
    if modo_evento == "AUTOMÁTICO REAL":
        execucao_var.set(
            "Disparo real: análise online aprovada • conferindo plataforma e armação"
            if evento.get("execucao_autorizada")
            else f"Disparo real: AGUARDANDO — {evento.get('motivo_execucao', '')}"
        )
    else:
        execucao_var.set("Somente sinais • nenhum disparo enviado")
    recuperacao_var.set(
        f"Radar real: {len(eventos_radar)}/{len(ATIVOS_MERCADO_ABERTO)} "
        "pares Forex recebidos"
    )
    estado_operacao_var.set(f"Última vela real: {horario} • {timeframe}")
    preco = evento.get("preco")
    variacao = evento.get("variacao")
    preco_texto = "—" if preco is None else f"{float(preco):.5f}"
    variacao_texto = "—" if variacao is None else f"{float(variacao):+.2f}%"
    placar_demo_var.set(
        f"{ativo} • preço {preco_texto} • variação {variacao_texto}"
    )


def receber_eventos():
    while True:
        try:
            evento = fila_eventos.get_nowait()
        except queue.Empty:
            break
        if evento.get("tipo") == "radar_mercado_aberto":
            ativo = evento.get("ativo", "—")
            eventos_radar[ativo] = evento
            atualizar_graficos_mercado_aberto()
            campos_abertos = campos_por_mercado.get("MERCADO ABERTO")
            if (
                campos_abertos
                and campos_abertos["ativo"].get() == ativo
            ):
                atualizar_painel_mercado_aberto(evento)
            if arvore_radar is not None:
                preco = evento.get("preco")
                variacao = evento.get("variacao")
                valores = (
                    ativo,
                    "—" if preco is None else f"{float(preco):.5f}",
                    "—" if variacao is None else f"{float(variacao):+.2f}%",
                    evento.get("regime", "—"),
                    f"{float(evento.get('confluencia', 0)):.0%}",
                    direcao_exibida(evento),
                    evento.get("horario", "—"),
                )
                if arvore_radar.exists(ativo):
                    arvore_radar.item(ativo, values=valores)
                else:
                    arvore_radar.insert("", "end", iid=ativo, values=valores)
                # Mostra automaticamente a primeira análise; depois respeita
                # o par que o usuário selecionar no radar.
                selecao = arvore_radar.selection()
                if not selecao:
                    arvore_radar.selection_set(ativo)
                    atualizar_resumo_analise(evento)
                elif selecao[0] == ativo:
                    atualizar_resumo_analise(evento)
            if evento.get("clique_real_autorizado"):
                campos_abertos = campos_por_mercado.get("MERCADO ABERTO", {})
                painel_aberto = paineis_resultado.get("MERCADO ABERTO")
                execucao_aberta_var = painel_aberto[7] if painel_aberto else None
                ativo_escolhido = (
                    campos_abertos.get("ativo").get()
                    if campos_abertos.get("ativo") is not None else "—"
                )
                modo_aberto = (
                    campos_abertos.get("modo").get()
                    if campos_abertos.get("modo") is not None else ""
                )
                if modo_aberto != MODO_REAL_UI or ativo != ativo_escolhido:
                    executor_demo_iq.desarmar_conta_real()
                    if execucao_aberta_var is not None:
                        execucao_aberta_var.set(
                            "Disparo bloqueado — ativo ou modo operacional mudou"
                        )
                elif plataforma_confirmada != plataforma_ativa_var.get():
                    executor_demo_iq.desarmar_conta_real()
                    if execucao_aberta_var is not None:
                        execucao_aberta_var.set(
                            "Disparo bloqueado — confirme novamente a plataforma"
                        )
                elif not executor_demo_iq.conta_real_armada:
                    if execucao_aberta_var is not None:
                        execucao_aberta_var.set(
                            "Disparo real desarmado — pressione INICIAR novamente"
                        )
                else:
                    valor_operacao = campos_abertos["entrada"].get()
                    chave = (
                        "MERCADO ABERTO", evento.get("timeframe"),
                        evento.get("horario"), "REAL", ativo,
                    )
                    if arvore_operacoes is not None:
                        iid = str(chave)
                        if not arvore_operacoes.exists(iid):
                            arvore_operacoes.insert("", 0, iid=iid, values=(
                                time.strftime("%H:%M:%S"), "REAL",
                                plataforma_ativa_var.get(), ativo,
                                direcao_exibida(evento), valor_operacao,
                                "ENVIANDO APÓS ANÁLISE ONLINE...",
                            ))
                    executar_clique_assincrono(
                        evento.get("sinal"), chave, "", True,
                        janela.winfo_screenwidth(), janela.winfo_screenheight(),
                        "MERCADO ABERTO", ativo, valor_operacao,
                        tipo_conta="REAL",
                    )
                    if execucao_aberta_var is not None:
                        execucao_aberta_var.set(
                            f"Disparo real enviado para {plataforma_ativa_var.get()}"
                        )
        else:
            atualizar_resumo_analise(evento)
            if evento.get("tipo") == "sinal" and evento.get("mercado") == "OTC":
                atualizar_graficos_otc(evento)
        if evento.get("tipo") == "radar_mercado_aberto":
            continue
        painel = paineis_resultado.get(evento.get("mercado"))
        if painel is None:
            continue

        if evento.get("tipo") == "resultado_clique_corretora":
            execucao_var = painel[7]
            mensagem = evento.get("mensagem_clique", "resultado do clique indisponível")
            execucao_var.set(mensagem)
            if "Acessibilidade" in mensagem:
                iq_trava_var.set(
                    "Automação sem permissão — libere Python/BFT WIN em Acessibilidade"
                )
            print(f"[BFT CONTA {evento.get('tipo_conta', '—')}] {mensagem}")
            if arvore_operacoes is not None:
                iid = evento.get("id_operacao")
                registro = registrar_entrada({
                    "horario": evento.get("horario"),
                    "conta": evento.get("tipo_conta"),
                    "plataforma": evento.get("plataforma"),
                    "ativo": evento.get("ativo"),
                    "direcao": evento.get("direcao"),
                    "valor": evento.get("valor"),
                    "resultado": mensagem,
                    "sucesso": evento.get("clique_sucesso", False),
                })
                valores = (
                    registro["horario"], registro["conta"],
                    registro["plataforma"], registro["ativo"],
                    registro["direcao"], registro["valor"],
                    registro["resultado"],
                )
                if iid and arvore_operacoes.exists(iid):
                    arvore_operacoes.item(iid, values=valores)
                else:
                    arvore_operacoes.insert("", 0, values=valores)
            continue
        (
            sinal_var, pontuacao_var, motivo_var, probabilidade_var,
            direcao_var, momento_var, payout_var, execucao_var,
            recuperacao_var, estado_operacao_var, placar_demo_var,
        ) = painel
        sinal_var.set(evento["sinal"])
        pontuacao_var.set(
            f"Confluência: {evento['pontuacao'] * 10}% • "
            f"{evento['timeframe']} • Fechamento "
            f"{evento.get('vela_horario', evento['vela'])}"
        )
        motivo_var.set(evento["motivo"])
        probabilidade = evento.get("probabilidade")
        estimativa = evento.get("estimativa_experimental")
        if probabilidade is not None:
            probabilidade_var.set(f"Probabilidade calibrada: {probabilidade:.1%}")
        elif estimativa is not None:
            probabilidade_var.set(
                f"Estimativa experimental: {estimativa:.0%} — NÃO CALIBRADA"
            )
        else:
            probabilidade_var.set("Probabilidade: NÃO CALIBRADA")
        sinal = evento.get("sinal")
        if sinal == "ALTA":
            direcao_var.set("Direção experimental: CALL / HIGHER")
            momento_var.set(
                "Referência: PRÓXIMA VELA M1 — não entrar no meio da vela atual"
            )
        elif sinal == "BAIXA":
            direcao_var.set("Direção experimental: PUT / LOWER")
            momento_var.set(
                "Referência: PRÓXIMA VELA M1 — não entrar no meio da vela atual"
            )
        else:
            direcao_var.set("Direção: NÃO ENTRAR")
            momento_var.set("Momento: AGUARDAR nova confirmação em vela fechada")
        payout = evento.get("payout")
        payout_var.set("Payout: —" if payout is None else f"Payout: {payout:.1%}")
        modo_evento = evento.get("modo_operacao", "SOMENTE SINAIS")
        if modo_evento == "AUTOMÁTICO REAL":
            execucao_var.set(
                "Disparo real: critérios OTC aprovados • conferindo trava final"
                if evento.get("execucao_autorizada")
                else f"Disparo real: AGUARDANDO — {evento.get('motivo_execucao', '')}"
            )
        elif modo_evento == "AUTOMÁTICO DEMO":
            execucao_var.set(
                "Conta prática: critérios aprovados"
                if evento.get("execucao_autorizada")
                else f"Conta prática: AGUARDANDO — {evento.get('motivo_execucao', '')}"
            )
        else:
            execucao_var.set("Somente sinais • nenhuma ordem enviada")
        recuperacao_var.set(
            "Recuperação: ATIVADA — aguardando probabilidade ≥ 89%"
            if evento.get("recuperacao_ativada")
            else "Recuperação: DESATIVADA"
        )
        estado_operacao_var.set(
            f"Tela da corretora: {evento.get('estado_operacao', 'PRONTO')}"
        )
        demo = evento.get("demo_resumo") or {}
        taxa_demo = demo.get("taxa_acerto")
        placar_demo_var.set(
            f"Demo: {demo.get('vitorias', 0)}V / {demo.get('derrotas', 0)}D / "
            f"{demo.get('empates', 0)}E • taxa observada: "
            f"{'—' if taxa_demo is None else f'{taxa_demo:.1%}'}"
        )
        if arvore_diagnosticos is not None and evento.get("diagnosticos") is not None:
            for item in arvore_diagnosticos.get_children():
                arvore_diagnosticos.delete(item)
            for diagnostico in evento.get("diagnosticos", ()):
                arvore_diagnosticos.insert("", "end", values=(
                    diagnostico.get("nome"), diagnostico.get("direcao"),
                    diagnostico.get("peso"), diagnostico.get("motivo"),
                ))
            if resumo_indicadores_var is not None:
                nomes = evento.get("indicadores_ativos", ())
                resumo_indicadores_var.set(
                    f"Regime: {evento.get('regime', '—')} • "
                    f"{len(nomes)} indicadores ativos • M1"
                )
        if evento.get("demo_entrada_registrada"):
            execucao_var.set("Entrada prática preparada • verificando trava do clique")
        tipo_conta_clique = (
            "REAL"
            if evento.get("clique_real_autorizado")
            else "DEMO"
            if evento.get("clique_demo_autorizado")
            else None
        )
        if tipo_conta_clique is not None:
            modo_ui_atual = campos_por_mercado.get("OTC", {}).get("modo")
            modo_ui_atual = modo_ui_atual.get() if modo_ui_atual is not None else ""
            modo_esperado = (
                MODO_REAL_UI if tipo_conta_clique == "REAL" else MODO_PRATICA_UI
            )
            if modo_ui_atual != modo_esperado:
                executor_demo_iq.desarmar_conta_real()
                execucao_var.set("Clique BLOQUEADO — modo da interface foi alterado")
                continue
            plataforma_autorizada = (
                plataforma_confirmada == plataforma_ativa_var.get()
            )
            if not plataforma_autorizada:
                execucao_var.set(
                    "Clique bloqueado — confirme novamente a plataforma"
                )
                continue
            if tipo_conta_clique == "REAL" and not executor_demo_iq.conta_real_armada:
                execucao_var.set(
                    "Disparo real: DESARMADO — pressione INICIAR para uma nova entrada"
                )
                continue
            chave = (
                evento.get("mercado"),
                evento.get("timeframe"),
                evento.get("vela_horario", evento.get("vela")),
                tipo_conta_clique,
            )
            ativo_operacao = (
                campos_por_mercado.get("OTC", {}).get("ativo").get()
                if campos_por_mercado.get("OTC") else "—"
            )
            valor_operacao = (
                campos_por_mercado.get("OTC", {}).get("entrada").get()
                if campos_por_mercado.get("OTC") else "—"
            )
            if arvore_operacoes is not None:
                iid = str(chave)
                if not arvore_operacoes.exists(iid):
                    arvore_operacoes.insert("", 0, iid=iid, values=(
                        time.strftime("%H:%M:%S"), tipo_conta_clique,
                        plataforma_ativa_var.get(), ativo_operacao,
                        "HIGHER" if evento.get("sinal") == "ALTA" else "LOWER",
                        valor_operacao, f"ENVIANDO PARA A CONTA {tipo_conta_clique}...",
                    ))
            executar_clique_assincrono(
                evento.get("sinal"),
                chave,
                captura_visual_atual or "",
                True,
                janela.winfo_screenwidth(),
                janela.winfo_screenheight(),
                evento.get("mercado"),
                ativo_operacao,
                valor_operacao,
                tipo_conta=tipo_conta_clique,
            )
            execucao_var.set(
                f"Disparo {tipo_conta_clique}: enviando entrada sem travar a interface"
            )
    janela.after(200, receber_eventos)


definir_callback_evento(fila_eventos.put)
janela.after(200, receber_eventos)


def emergencia():
    executor_demo_iq.desarmar_conta_real()
    acionar_parada_emergencia()
    status.config(text="EMERGÊNCIA: TUDO INTERROMPIDO", foreground="red")


rodape = tk.Label(
    conteudo,
    text=f"BFT Winbot · {NOME_COMPLETO_APP} · interface operacional",
    bg=COR_BG,
    fg="#6b6494",
    font=("Helvetica Neue", 9),
)
rodape.pack(fill="x", padx=18, pady=(0, 18))


faixa_emergencia = tk.Frame(
    janela, bg="#741f28", bd=0, relief="flat",
    highlightthickness=1, highlightbackground="#9f303d",
)
faixa_emergencia.pack(side="bottom", fill="x", padx=18, pady=(6, 10))
botao_emergencia = tk.Label(
    faixa_emergencia,
    text="⛔  Parada de emergência — clique aqui  ⛔",
    bg="#741f28",
    fg="#ffffff",
    font=("Helvetica Neue", 11, "bold"),
    cursor="hand2",
    pady=10,
)
botao_emergencia.pack(fill="x")
botao_emergencia.bind("<Button-1>", lambda _evento: emergencia())
janela.bind("<Escape>", lambda _evento: emergencia())
janela.mainloop()
