# -*- coding: utf-8 -*-
"""Ce qu'un site doit tenir avant d'etre montre a quelqu'un.

Un seul endroit : les en-tetes, le robots.txt, le sitemap et le 404 humain.
Trois raisons de tout mettre la plutot qu'au fil des routes :
 - un en-tete pose route par route finit toujours par manquer sur une route ;
 - `PUBLIC_ORIGIN` decide de l'adresse publique, et un sitemap qui annonce
   localhost est un sitemap faux ;
 - la redirection HTTPS doit lire son reglage A CHAQUE requete : l'hebergeur
   l'allume, le poste de developpement ne l'a pas.
"""
import os

from fastapi import Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response

# 17/09/2026 : la page n'appelle plus AUCUN tiers. Les polices sont servies par nous
# (`static/polices/`), donc googleapis et gstatic sortent de la CSP -- et une CSP qui
# n'autorise personne d'autre est la seule qui se verifie d'un coup d'oeil.
_CSP = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self'; "
    "font-src 'self'; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "base-uri 'none'; "
    "form-action 'self'; "
    "frame-ancestors 'none'"
)

_HEADERS = {
    "strict-transport-security": "max-age=31536000; includeSubDomains",
    "x-content-type-options": "nosniff",
    "referrer-policy": "strict-origin-when-cross-origin",
    "x-frame-options": "DENY",
    "content-security-policy": _CSP,
    # Aucune de ces trois capacites ne sert a Lumenia.
    "permissions-policy": "camera=(), microphone=(), geolocation=()",
}


def public_origin() -> str:
    return os.getenv("PUBLIC_ORIGIN", "http://localhost:8000").rstrip("/")


def page(static_dir, nom: str, status_code: int = 200) -> Response:
    """Sert une page en y injectant l'origine publique.

    `og:image` et `canonical` doivent etre des URL ABSOLUES : un fichier statique
    ne peut pas les connaitre, donc la page porte `{{ORIGIN}}` et le serveur le
    remplace. Sans ca, le lien partage montre une image introuvable.
    """
    html = (static_dir / nom).read_text(encoding="utf-8").replace("{{ORIGIN}}", public_origin())
    return HTMLResponse(html, status_code=status_code)


def _wants_html(request: Request) -> bool:
    accept = request.headers.get("accept", "")
    return "text/html" in accept and "application/json" not in accept


def install(app, static_dir):
    @app.middleware("http")
    async def _quality(request: Request, call_next):
        # HEAD est traite comme GET, le corps en moins. Mesure du 18/09 : toutes les
        # pages, plus robots.txt, sitemap.xml et favicon.ico, repondaient 405 en HEAD,
        # parce que `@app.get` n'enregistre que GET. Un moniteur de disponibilite ou un
        # verificateur de liens sonde en HEAD par defaut : il aurait rapporte le site
        # en panne alors qu'il repond. RFC 9110 §9.3.2 l'exige, et le faire ICI couvre
        # aussi les pages ajoutees plus tard, sans qu'on ait a y penser.
        tete = request.method == "HEAD"
        if tete:
            request.scope["method"] = "GET"

        # Force HTTPS seulement quand l'hebergeur le demande : en local, tout
        # tourne en clair et une redirection rendrait le produit intestable.
        if os.getenv("FORCE_HTTPS") == "1":
            proto = request.headers.get("x-forwarded-proto", request.url.scheme)
            if proto == "http":
                return RedirectResponse(str(request.url).replace("http://", "https://", 1), status_code=308)

        response: Response = await call_next(request)
        for key, value in _HEADERS.items():
            response.headers.setdefault(key, value)

        # Les URL statiques ne portent pas d'empreinte (`/static/app.js`), donc un
        # cache long servirait une version perimee apres chaque correction. Constate
        # en direct le 18/09 : `app.js` corrige, fichier servi correct, et la page
        # tournait toujours sur l'ancien script. Sans `cache-control`, le navigateur
        # applique une heuristique et decide seul.
        # `no-cache` ne veut pas dire « ne cache pas » : il veut dire « redemande-moi
        # avant de reutiliser ». Avec l'ETag deja pose par StaticFiles, cette
        # revalidation coute un 304 vide.
        if request.url.path.startswith("/static/"):
            response.headers.setdefault("cache-control", "no-cache")

        if tete:
            # Memes statut, memes en-tetes (y compris HSTS et CSP), corps vide :
            # un sondage HEAD doit voir le site tel qu'il est, pas un site sans
            # en-tetes de securite.
            return Response(status_code=response.status_code,
                            headers=dict(response.headers),
                            media_type=response.media_type)
        return response

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon():
        # Un navigateur demande /favicon.ico tout seul des qu'une page n'en declare
        # pas : mesure du 17/09, chaque ouverture d'une page d'atelier laissait un
        # 404 dans la console. Servir la marque SVG coute une ligne et repond a tous
        # les clients, y compris ceux qui ne lisent pas les <link>.
        return FileResponse(static_dir / "logo-mark.svg", media_type="image/svg+xml")

    @app.get("/robots.txt", include_in_schema=False)
    def robots():
        # L'API n'a rien a faire dans un index de recherche : elle n'a pas de
        # page, et une reponse JSON indexee est une fuite tranquille.
        #
        # 17/09/2026 — cette liste etait ecrite a la main, et trois routes lui
        # echappaient deja (`/adapt`, `/resources`, `/focus`...). Une liste tenue a
        # la main derive des qu'une route est ajoutee, en silence. Elle est donc
        # DEDUITE des routes reellement exposees : on ne peut plus oublier une porte.
        publiques = {c for c, *_ in PAGES} | {"/robots.txt", "/sitemap.xml", "/healthz"}
        api = sorted({
            "/" + r.path.lstrip("/").split("/")[0]
            for r in app.routes
            if getattr(r, "methods", None)
            and r.path not in publiques
            and not r.path.startswith("/static")
        })
        lines = ["User-agent: *", "Allow: /$"]
        lines += [f"Disallow: {chemin}" for chemin in api]
        lines += [f"Sitemap: {public_origin()}/sitemap.xml", ""]
        return PlainTextResponse("\n".join(lines))

    # Les pages publiques : celles qu'un moteur peut indexer et qu'un humain peut lire.
    PAGES = [("/", "index.html", "weekly", "1.0"),
             ("/confidentialite", "confidentialite.html", "yearly", "0.3"),
             ("/cgu", "cgu.html", "yearly", "0.3")]

    @app.get("/confidentialite", include_in_schema=False)
    def confidentialite():
        return page(static_dir, "confidentialite.html")

    @app.get("/cgu", include_in_schema=False)
    def cgu():
        return page(static_dir, "cgu.html")

    @app.get("/sitemap.xml", include_in_schema=False)
    def sitemap():
        origin = public_origin()
        # Une seule liste : le sitemap ne peut pas oublier une page que le site sert.
        lignes = "".join(
            f"  <url><loc>{origin}{chemin}</loc>"
            f"<changefreq>{freq}</changefreq><priority>{prio}</priority></url>\n"
            for chemin, _, freq, prio in PAGES
        )
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f"{lignes}"
            "</urlset>\n"
        )
        return Response(xml, media_type="application/xml")

    @app.exception_handler(404)
    async def not_found(request: Request, exc):
        # Un humain recoit une page, un client d'API recoit son JSON.
        if _wants_html(request):
            return page(static_dir, "404.html", status_code=404)
        return JSONResponse({"detail": "Not Found"}, status_code=404)
