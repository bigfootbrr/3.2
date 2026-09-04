"""Acumulador de velas para o fluxo OTC (chegar a 105 sem repaint).

Problema: a captura da janela redimensionada mostra 50-100 velas fechadas,
mas o motor de confluência exige 105 (mínimo da EMA 100 + margem). Forçar
zoom out degrada a leitura dos pixels; repetir leitura não adiciona nada.

Solução: acumular as velas FECHADAS entre capturas, deduplicando pelo eixo x
relativo à linha de expiração. Cada vela nova (à esquerda da linha) entra
uma única vez; a vela em formação nunca entra (no-repaint).

Uso:
    acumulador = AcumuladorVelas(minimo=105)
    for _ in range(n_capturas):
        resultado = ler_velas(captura)
        if resultado.sucesso:
            acumulador.adicionar(resultado.velas, resultado.linha_expiracao_x)
        if acumulador.pronto():
            motor.analisar_confluencia(acumulador.vento_janela_mais_recente(150))
"""

from dataclasses import dataclass, field

from leitor_velas_iq import VelaVisual


@dataclass
class AcumuladorVelas:
    """Junta velas fechadas de várias capturas, sem duplicar nem repintar."""

    minimo: int = 105
    maximo: int = 300
    _velas: list = field(default_factory=list, repr=False)
    _chaves: set = field(default_factory=set, repr=False)

    def adicionar(self, velas, linha_expiracao_x=None) -> int:
        """Adiciona apenas velas NOVAS (nunca vistas).

        Chave de deduplicação: distância da vela até a linha de expiração
        (o eixo x muda a cada captura quando a janela rola, mas a distância
        da vela fechada mais recente até a linha é estável enquanto o
        gráfico não rola mais que o passo de uma vela).

        Retorna quantas velas novas entraram.
        """
        novas = 0
        for vela in velas:
            chave = self._chave(vela, linha_expiracao_x)
            if chave is None or chave in self._chaves:
                continue
            self._chaves.add(chave)
            self._velas.append(vela)
            novas += 1
        # Mantém somente a janela mais recente (evita memória infinita)
        if len(self._velas) > self.maximo:
            excedente = len(self._velas) - self.maximo
            self._velas = self._velas[excedente:]
        return novas

    def _chave(self, vela, linha_expiracao_x):
        if linha_expiracao_x is None:
            return None
        distancia = linha_expiracao_x - vela.x
        if distancia < 0:
            return None  # vela à direita da linha ainda está formando
        return (distancia, vela.direcao)

    def pronto(self) -> bool:
        return len(self._velas) >= self.minimo

    def quantidade(self) -> int:
        return len(self._velas)

    def como_listas(self, quantidade=None):
        """Exporta as velas mais recentes no formato do motor (O/H/L/C).

        As coordenadas são em pixels do eixo y (menor = preço mais alto),
        escala relativa consistente com o que `analisar_confluencia` espera.
        """
        velas = self._velas if quantidade is None else self._velas[-quantidade:]
        return [
            [v.abertura_y, v.maxima_y, v.minima_y, v.fechamento_y]
            for v in velas
        ]

    def zerar(self):
        self._velas.clear()
        self._chaves.clear()