"""Estado exibido no painel de conexão da IQ; nenhuma automação de tela aqui."""

from dataclasses import dataclass


@dataclass(frozen=True)
class EstadoConexaoIq:
    conectada: bool = False
    conta_demo_confirmada: bool = False
    aba: int | None = None
    ativo: str | None = None
    payout: float | None = None
    tela_disponivel: bool = False
    conta_real_confirmada: bool = False
    plataforma_confirmada: bool = False

    def entrada_bloqueada_para(self, tipo_conta="DEMO"):
        tipo_conta = str(tipo_conta or "DEMO").strip().upper()
        conta_confirmada = (
            self.conta_demo_confirmada
            if tipo_conta == "DEMO"
            else self.conta_real_confirmada
        )
        if tipo_conta == "REAL":
            requisitos = (
                self.conectada
                and conta_confirmada
                and self.plataforma_confirmada
                and self.aba in range(1, 10)
                and bool(self.ativo)
                and self.payout is not None
                and self.payout > 0.80
                and self.tela_disponivel
            )
            return not requisitos
        return not (
            self.conectada
            and conta_confirmada
            and self.aba in range(1, 10)
            and bool(self.ativo)
            and self.payout is not None
            and self.payout > 0.80
            and self.tela_disponivel
        )

    @property
    def entrada_bloqueada(self):
        return self.entrada_bloqueada_para("DEMO")

    def linhas_painel(self, tipo_conta="DEMO"):
        tipo_conta = str(tipo_conta or "DEMO").strip().upper()
        conta_confirmada = (
            self.conta_demo_confirmada
            if tipo_conta == "DEMO"
            else self.conta_real_confirmada
        )
        conexao = "CONECTADA" if self.conectada else "DESCONECTADA"
        if tipo_conta == "REAL":
            conta = "REAL CONFIRMADA" if conta_confirmada else "NÃO CONFIRMADA"
            trava = "BLOQUEADA" if self.entrada_bloqueada_para("REAL") else "PRONTA PARA VALIDAR SINAL REAL"
        else:
            conta = "PRÁTICA CONFIRMADA" if conta_confirmada else "NÃO CONFIRMADA"
            trava = "BLOQUEADA" if self.entrada_bloqueada_para("DEMO") else "PRONTA PARA VALIDAR SINAL DEMO"
        aba = "—" if self.aba is None else str(self.aba)
        ativo = self.ativo or "—"
        payout = "—" if self.payout is None else f"{self.payout:.0%}"
        tela = "LIVRE" if self.tela_disponivel else "NÃO CONFIRMADA"
        return {
            "conexao": conexao,
            "conta": conta,
            "leitura": f"Aba {aba} • {ativo} • Payout {payout}",
            "tela": tela,
            "trava": trava,
        }
