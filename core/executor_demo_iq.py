"""Executa um clique visual somente depois das travas da plataforma."""

from dataclasses import dataclass
import subprocess

from PIL import Image

from calibracao_iq import PERFIL_IQ_2026_08_30, perfil_compativel


def _erro_de_acessibilidade(detalhe):
    texto = str(detalhe or "").lower()
    marcadores = (
        "keine berechtigung für den hilfszugriff",
        "not allowed assistive access",
        "não tem permissão para acesso assistivo",
        "not authorized to send apple events",
        "-1719",
    )
    return any(marcador in texto for marcador in marcadores)


@dataclass(frozen=True)
class ResultadoCliqueDemo:
    sucesso: bool
    mensagem: str
    x: int | None = None
    y: int | None = None


class ExecutorDemoIq:
    _ALIASES_SINAL = {
        "ALTA": "ALTA",
        "HIGHER": "ALTA",
        "CALL": "ALTA",
        "HIGH": "ALTA",
        "BUY": "ALTA",
        "COMPRA": "ALTA",
        "COMPRAR": "ALTA",
        "BAIXA": "BAIXA",
        "LOWER": "BAIXA",
        "PUT": "BAIXA",
        "LOW": "BAIXA",
        "SELL": "BAIXA",
        "VENDA": "BAIXA",
        "VENDER": "BAIXA",
    }

    def __init__(self, executor=subprocess.run):
        self.executor = executor
        self._ultima_chave = None
        self._conta_real_armada = False

    @property
    def conta_real_armada(self):
        return self._conta_real_armada

    def armar_conta_real(self, plataforma_confirmada):
        """Arma uma única entrada real após confirmação explícita da plataforma."""
        self._conta_real_armada = plataforma_confirmada is True
        return self._conta_real_armada

    def desarmar_conta_real(self):
        self._conta_real_armada = False

    @classmethod
    def normalizar_sinal(cls, sinal):
        if sinal is None:
            return None
        return cls._ALIASES_SINAL.get(str(sinal).strip().upper())

    def executar(
        self,
        sinal,
        chave_vela,
        caminho_captura,
        conta_confirmada,
        largura_tela=None,
        altura_tela=None,
        plataforma="IQ Option",
        coordenadas=None,
        tipo_conta="DEMO",
        plataforma_confirmada=None,
    ):
        tipo_conta = str(tipo_conta or "").strip().upper()
        if tipo_conta not in {"DEMO", "REAL"}:
            return ResultadoCliqueDemo(False, "tipo de conta inválido")
        # Compatibilidade: o argumento posicional antigo agora representa a
        # confirmação operacional da plataforma, não a leitura do tipo de conta.
        if plataforma_confirmada is None:
            plataforma_confirmada = conta_confirmada
        if plataforma_confirmada is not True:
            return ResultadoCliqueDemo(False, "plataforma de operação não confirmada")
        if tipo_conta == "REAL" and not self._conta_real_armada:
            return ResultadoCliqueDemo(False, "conta real não armada para esta entrada")
        sinal_normalizado = self.normalizar_sinal(sinal)
        if sinal_normalizado not in {"ALTA", "BAIXA"}:
            return ResultadoCliqueDemo(False, "sinal sem direção")
        if not chave_vela:
            return ResultadoCliqueDemo(False, "vela do sinal não identificada")
        if chave_vela == self._ultima_chave:
            return ResultadoCliqueDemo(False, "clique duplicado bloqueado")
        largura = altura = None
        if caminho_captura:
            try:
                with Image.open(caminho_captura) as imagem:
                    largura, altura = imagem.size
            except (OSError, ValueError) as erro:
                return ResultadoCliqueDemo(False, f"captura inválida: {erro}")
        # O Tk informa pontos lógicos, que são exatamente a unidade esperada
        # pelo System Events. Não consultar o Finder evita travamento no macOS.
        largura_tela = largura if largura_tela is None else largura_tela
        altura_tela = altura if altura_tela is None else altura_tela
        if largura_tela is None or altura_tela is None:
            return ResultadoCliqueDemo(False, "tamanho da tela não informado")
        if largura_tela <= 0 or altura_tela <= 0:
            return ResultadoCliqueDemo(False, "tamanho lógico da tela inválido")
        plataforma = str(plataforma or "IQ Option").strip()
        plataformas_calibradas = {
            "Quotex": ("Quotex",),
            "Casa Trader": ("Casa Trader", "CasaTrader"),
            "Avallon": ("Avallon", "Avalon"),
        }
        if plataforma in plataformas_calibradas:
            if not coordenadas or sinal_normalizado not in coordenadas:
                return ResultadoCliqueDemo(False, f"botões da {plataforma} ainda não calibrados")
            referencia = coordenadas.get("tela")
            if referencia and tuple(referencia) != (largura_tela, altura_tela):
                return ResultadoCliqueDemo(False, f"tela diferente da calibração da {plataforma}")
            x, y = (int(valor) for valor in coordenadas[sinal_normalizado])
            processos = plataformas_calibradas[plataforma]
        else:
            if coordenadas and sinal_normalizado in coordenadas:
                referencia = coordenadas.get("tela")
                if referencia and tuple(referencia) != (largura_tela, altura_tela):
                    return ResultadoCliqueDemo(False, "tela diferente da calibração da IQ Option")
                x, y = (int(valor) for valor in coordenadas[sinal_normalizado])
            else:
                if (
                    largura is not None
                    and altura is not None
                    and not perfil_compativel(PERFIL_IQ_2026_08_30, largura, altura)
                ):
                    return ResultadoCliqueDemo(False, "geometria da tela diferente da calibração")
                regiao = (
                    PERFIL_IQ_2026_08_30.botao_higher
                    if sinal_normalizado == "ALTA"
                    else PERFIL_IQ_2026_08_30.botao_lower
                )
                centro_x = (regiao.x1 + regiao.x2) / 2
                centro_y = (regiao.y1 + regiao.y2) / 2
                x = round(largura_tela * centro_x)
                y = round(altura_tela * centro_y)
            processos = ("IQ Option", "IQOption")
        condicoes = "\n".join(
            ("if" if indice == 0 else "else if")
            + f' exists process "{nome}" then\n    set frontmost of process "{nome}" to true'
            for indice, nome in enumerate(processos)
        )
        script = f'''tell application "System Events"
{condicoes}
else
    error "aplicativo {plataforma} não encontrado"
end if
delay 0.20
click at {{{x}, {y}}}
end tell'''
        try:
            resultado = self.executor(
                ["/usr/bin/osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as erro:
            return ResultadoCliqueDemo(False, f"clique não iniciou: {erro}")
        if resultado.returncode != 0:
            detalhe = (resultado.stderr or resultado.stdout or "acesso negado").strip()
            if _erro_de_acessibilidade(detalhe):
                return ResultadoCliqueDemo(
                    False,
                    "Clique bloqueado pelo macOS: libere Python/BFT WIN em "
                    "Ajustes do Sistema > Privacidade e Segurança > Acessibilidade",
                )
            return ResultadoCliqueDemo(False, f"clique bloqueado pelo macOS: {detalhe}")
        self._ultima_chave = chave_vela
        if tipo_conta == "REAL":
            self.desarmar_conta_real()
        direcao = "HIGHER" if sinal_normalizado == "ALTA" else "LOWER"
        nome_conta = "REAL" if tipo_conta == "REAL" else "PRÁTICA"
        return ResultadoCliqueDemo(
            True,
            f"clique CONTA {nome_conta} {direcao} enviado para {plataforma}",
            x,
            y,
        )
