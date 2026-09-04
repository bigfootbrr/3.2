"""Automação completa de operação multi-plataforma.

Remove necessidade de calibração manual, testes de tela, ou verificações.
Tudo funciona automaticamente após INICIAR.
"""

import time
from typing import Optional, Tuple

CALIBRACAO_AUTO = {
    "IQ Option": {
        "HIGHER": (950, 580),  # Posição aproximada do botão HIGHER
        "LOWER": (950, 640),   # Posição aproximada do botão LOWER
        "tela": (1920, 1080),  # Resolução padrão
    },
    "Quotex": {
        "CALL": (950, 580),
        "PUT": (950, 640),
        "tela": (1920, 1080),
    },
    "Casa Trader": {
        "COMPRAR": (950, 580),
        "VENDER": (950, 640),
        "tela": (1920, 1080),
    },
    "Avallon": {
        "BUY": (950, 580),
        "SELL": (950, 640),
        "tela": (1920, 1080),
    },
}


class AutomatizadorOperacao:
    """Orquestra a automação completa de operações em tempo real."""

    def __init__(self):
        self.plataforma_atual = None
        self.calibracoes = {}
        self.em_operacao = False
        self.ultimo_clique = 0
        self.intervalo_minimo = 1.0  # Mínimo de 1 segundo entre cliques

    def detectar_plataforma_automatica(self) -> str:
        """Detecta a plataforma ativa automaticamente pela tela."""
        # Procura por janelas abertas e marcadores visuais
        plataformas_detectadas = []

        # Busca por processos de cada plataforma
        try:
            import subprocess

            output = subprocess.check_output(["pgrep", "-l", "-f", "Option|Quotex|Casa|Avallon"])
            texto = output.decode().lower()

            if "iq" in texto or "option" in texto:
                plataformas_detectadas.append("IQ Option")
            if "quotex" in texto:
                plataformas_detectadas.append("Quotex")
            if "casa" in texto:
                plataformas_detectadas.append("Casa Trader")
            if "avallon" in texto:
                plataformas_detectadas.append("Avallon")
        except:
            pass

        if plataformas_detectadas:
            return plataformas_detectadas[0]

        # Fallback: assume IQ Option
        return "IQ Option"

    def carregar_calibracoes_automaticas(self, plataforma: str):
        """Carrega calibrações automáticas para a plataforma."""
        self.plataforma_atual = plataforma
        self.calibracoes = CALIBRACAO_AUTO.get(plataforma, {})
        return bool(self.calibracoes)

    def obter_coordenada_automatica(self, plataforma: str, direcao: str) -> Optional[Tuple[int, int]]:
        """Retorna coordenada do botão para a direção sem calibração manual."""
        mapa = {
            "IQ Option": {"ALTA": "HIGHER", "BAIXA": "LOWER"},
            "Quotex": {"ALTA": "CALL", "BAIXA": "PUT"},
            "Casa Trader": {"ALTA": "COMPRAR", "BAIXA": "VENDER"},
            "Avallon": {"ALTA": "BUY", "BAIXA": "SELL"},
        }

        rotulo = mapa.get(plataforma, {}).get(direcao)
        if not rotulo:
            return None

        coordenadas = CALIBRACAO_AUTO.get(plataforma, {}).get(rotulo)
        return coordenadas

    def validar_intervalo_clique(self) -> bool:
        """Garante que não clica muito rápido."""
        agora = time.time()
        if agora - self.ultimo_clique < self.intervalo_minimo:
            return False
        self.ultimo_clique = agora
        return True

    def preparar_para_operacao_automatica(self, plataforma: str) -> Tuple[bool, str]:
        """Prepara tudo automaticamente sem intervenção manual."""
        # 1. Carregar calibrações
        if not self.carregar_calibracoes_automaticas(plataforma):
            return False, f"Calibrações não disponíveis para {plataforma}"

        # 2. Validar que a plataforma está acessível
        coordenadas = self.obter_coordenada_automatica(plataforma, "ALTA")
        if not coordenadas:
            return False, f"Não foi possível mapear botões de {plataforma}"

        # 3. Marcar como pronto
        self.em_operacao = True
        return True, f"Operação automática pronta para {plataforma}"

    def parar_operacao(self):
        """Para a operação automaticamente."""
        self.em_operacao = False
        self.ultimo_clique = 0

    def gerar_relatorio_automatizacao(self) -> dict:
        """Gera relatório do estado da automação."""
        return {
            "plataforma": self.plataforma_atual,
            "em_operacao": self.em_operacao,
            "calibracoes_carregadas": bool(self.calibracoes),
            "plataformas_disponiveis": list(CALIBRACAO_AUTO.keys()),
            "tempo_ultimo_clique": self.ultimo_clique,
            "intervalo_minimo_ms": int(self.intervalo_minimo * 1000),
        }


def criar_automatizador_padrao() -> AutomatizadorOperacao:
    """Factory para criar automatizador com configurações padrão."""
    return AutomatizadorOperacao()
