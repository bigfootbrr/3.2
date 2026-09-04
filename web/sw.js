/* BFT WIN — Service Worker (PWA)
 * Estratégia: network-first para API/dados (tempo real acima de tudo),
 * cache-first para assets estáticos (logo, ícones).
 * O painel de trading é AO VIVO — nunca servir dados de mercado velhos.
 */
const CACHE = "bft-win-v1";
const ASSETS_ESTATICOS = [
  "/assets/logo-bft.jpg",
  "/manifest.json",
];

self.addEventListener("install", (evento) => {
  evento.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(ASSETS_ESTATICOS))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (evento) => {
  evento.waitUntil(
    caches.keys().then((chaves) =>
      Promise.all(
        chaves.filter((chave) => chave !== CACHE).map((chave) => caches.delete(chave))
      )
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (evento) => {
  const url = new URL(evento.request.url);

  // API e página principal: SEMPRE da rede (dados reais ao vivo).
  if (url.pathname.startsWith("/api/") || url.pathname === "/") {
    evento.respondWith(
      fetch(evento.request).catch(() =>
        new Response(
          JSON.stringify({ erro: "offline", mensagem: "Sem conexão com o BFT WIN" }),
          { status: 503, headers: { "Content-Type": "application/json" } }
        )
      )
    );
    return;
  }

  // Assets estáticos: cache-first (instantâneo).
  evento.respondWith(
    caches.match(evento.request).then(
      (do_cache) =>
        do_cache ||
        fetch(evento.request).then((resposta) => {
          if (resposta.ok) {
            const copia = resposta.clone();
            caches.open(CACHE).then((cache) => cache.put(evento.request, copia));
          }
          return resposta;
        })
    )
  );
});