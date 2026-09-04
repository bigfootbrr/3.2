"""Login automático da plataforma DENTRO do bot (BFT WIN).

Ciclo de automação completo por plataforma:
1. CONFIGURAÇÃO ÚNICA (uma vez): operador ensina as posições dos campos
   (e-mail, senha, botão entrar) via click_memory — igual à calibração
   de botões de compra/venda.
2. CREDENCIAIS: e-mail e senha ficam no macOS KEYCHAIN (security
   add-generic-password) — NUNCA em arquivos do projeto.
3. LOGIN AUTOMÁTICO: sempre que necessário, o bot foca a janela da
   plataforma, digita as credenciais (keystroke) e clica em entrar.
4. GERENCIAMENTO: após logado, disparos/análises seguem automáticos.

Nota: automação de plataformas de trading deve respeitar os termos da
corretora; use na sua própria conta e por sua conta e risco.
"""

import getpass
import subprocess

CAMPOS_PADRAO = ("email", "senha", "entrar")


def _keychain_servico(plataforma: str) -> str:
    return f"BFT-{plataforma.strip().upper()}"


def salvar_credenciais(plataforma: str, email: str, senha: str) -> bool:
    """Guarda credenciais no Keychain do macOS (por plataforma)."""
    if not plataforma or not email or not senha:
        raise ValueError("plataforma, e-mail e senha são obrigatórios")
    servico = _keychain_servico(plataforma)
    usuario = email.strip()
    # -U atualiza o item se já existir.
    resultado = subprocess.run(
        [
            "/usr/bin/security", "add-generic-password",
            "-s", servico,
            "-a", usuario,
            "-w", senha,
            "-U",
        ],
        capture_output=True, text=True, timeout=10, check=False,
    )
    if resultado.returncode != 0:
        raise RuntimeError(f"Keychain recusou o item: {resultado.stderr.strip()}")
    return True


def obter_credenciais(plataforma: str, email: str | None = None):
    """Lê as credenciais do Keychain. Retorna (email, senha) ou (None, None)."""
    servico = _keychain_servico(plataforma)
    busca = ["/usr/bin/security", "find-generic-password", "-s", servico]
    if email:
        busca += ["-a", email.strip()]
    busca += ["-w"]
    resultado = subprocess.run(
        busca, capture_output=True, text=True, timeout=10, check=False,
    )
    if resultado.returncode != 0:
        return None, None
    senha = resultado.stdout.strip()
    # Recupera a conta (e-mail) do item.
    if email:
        return email.strip(), senha
    conta = subprocess.run(
        ["/usr/bin/security", "find-generic-password", "-s", servico],
        capture_output=True, text=True, timeout=10, check=False,
    )
    usuario = None
    for linha in conta.stdout.splitlines():
        campo = linha.strip()
        if campo.startswith('"acct"<blob>='):
            usuario = campo.split('=', 1)[-1].strip('" ')
            break
    return usuario, (senha or None)


def tem_credenciais(plataforma: str) -> bool:
    _, senha = obter_credenciais(plataforma)
    return bool(senha)


def logar_plataforma(
    plataforma: str,
    posicoes: dict,
    processos=None,
    digitador=None,
):
    """Executa o login na plataforma aberta na tela.

    posicoes: {"email": (x, y), "senha": (x, y), "entrar": (x, y)} em
    coordenadas de tela (as mesmas do click_memory).
    Retorna (ok, mensagem).
    """
    email, senha = obter_credenciais(plataforma)
    if not email or not senha:
        return False, (
            f"sem credenciais da {plataforma} no Keychain — salve e-mail e "
            f"senha no painel (ficam criptografados no macOS)"
        )
    faltando = [campo for campo in CAMPOS_PADRAO if campo not in posicoes]
    if faltando:
        return False, (
            "campos não calibrados: " + ", ".join(faltando) +
            " — use a calibração da plataforma com os campos visíveis"
        )

    if digitador is None:
        def digitador(comando_script):
            return subprocess.run(
                ["/usr/bin/osascript", "-e", comando_script],
                capture_output=True, text=True, timeout=15, check=False,
            )

    processos = processos or (plataforma,)
    condicoes = "\n".join(
        ("if" if i == 0 else "else if")
        + f' exists process "{nome}" then\n    set frontmost of process "{nome}" to true'
        for i, nome in enumerate(processos)
    )
    email_seguro = email.replace('"', '\\"')
    senha_segura = senha.replace('"', '\\"')
    x_email, y_email = int(posicoes["email"][0]), int(posicoes["email"][1])
    x_senha, y_senha = int(posicoes["senha"][0]), int(posicoes["senha"][1])
    x_entrar, y_entrar = int(posicoes["entrar"][0]), int(posicoes["entrar"][1])
    script = (
        'tell application "System Events"\n'
        f"{condicoes}\n"
        "else\n"
        f'    error "aplicativo {plataforma} não encontrado"\n'
        "end if\n"
        "delay 0.4\n"
        f"click at {{{x_email}, {y_email}}}\n"
        "delay 0.3\n"
        f'keystroke "{email_seguro}"\n'
        "delay 0.3\n"
        f"click at {{{x_senha}, {y_senha}}}\n"
        "delay 0.3\n"
        f'keystroke "{senha_segura}"\n'
        "delay 0.3\n"
        f"click at {{{x_entrar}, {y_entrar}}}\n"
        "end tell"
    )
    resultado = digitador(script)
    if resultado.returncode != 0:
        detalhe = (resultado.stderr or resultado.stdout or "").strip()
        return False, f"login não executou: {detalhe}"
    return True, f"login da {plataforma} enviado — aguarde a plataforma carregar"