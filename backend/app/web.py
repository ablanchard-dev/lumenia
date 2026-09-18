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
import logging
import os

from fastapi import Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response

log = logging.getLogger("lumenia.web")

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


def public_origin(request: Request | None = None) -> str:
    """L'adresse publique du site, dans l'ordre de ce qui SAIT.

    18/09/2026. Cette fonction rendait `http://localhost:8000` des que
    `PUBLIC_ORIGIN` n'etait pas pose -- et mesure du jour : **rien ne le posait**.
    Ni le README, ni `docker-compose.yml`, ni un `.env.example`, ni le Dockerfile ;
    la variable n'existait que dans ce fichier et dans deux tests qui la posaient
    eux-memes. Un deploiement reel servait donc `localhost` dans le `canonical`,
    l'`og:url`, l'`og:image` et le `Sitemap:` de robots.txt. Tout repondait 200, et
    le lien partage restait une ligne grise : l'oubli ne se voyait nulle part.

    Documenter la variable n'aurait rien reglé : une configuration qu'il faut
    penser a poser est une configuration qu'on oublie. Le produit, lui, sait deja a
    quelle adresse on lui parle.

    1. `PUBLIC_ORIGIN` s'il est pose : derriere un proxy, c'est LUI qui sait, et
       l'en-tete `Host` ne doit pas pouvoir le contredire (sinon un client choisit
       ce que la page declare etre).
    2. Sinon l'adresse de la requete, telle que le client l'a atteinte.
    3. Sinon seulement, le defaut local -- hors requete (sitemap genere a la main,
       tests unitaires), il n'y a rien d'autre a dire.
    """
    configure = os.getenv("PUBLIC_ORIGIN")
    if configure:
        return configure.rstrip("/")
    if request is not None:
        hote = request.headers.get("host")
        if hote:
            return f"{request.url.scheme}://{hote}".rstrip("/")
    return "http://localhost:8000"


def page(static_dir, nom: str, status_code: int = 200, request: Request | None = None) -> Response:
    """Sert une page en y injectant l'origine publique.

    `og:image` et `canonical` doivent etre des URL ABSOLUES : un fichier statique
    ne peut pas les connaitre, donc la page porte `{{ORIGIN}}` et le serveur le
    remplace. Sans ca, le lien partage montre une image introuvable.
    """
    origine = public_origin(request)
    html = (static_dir / nom).read_text(encoding="utf-8").replace("{{ORIGIN}}", origine)
    return HTMLResponse(html, status_code=status_code)


def _proteger(response: Response) -> Response:
    """Pose les en-tetes de securite. UNE seule liste, deux chemins qui l'appellent :
    le middleware normal et le gestionnaire de panne. Mesure du 18/09 : le
    gestionnaire d'exception de Starlette est le middleware le PLUS EXTERNE, donc sa
    reponse ne repasse pas par le middleware qui pose les en-tetes -- il doit les
    poser lui-meme, et surtout pas depuis une seconde liste qui divergerait."""
    for key, value in _HEADERS.items():
        response.headers.setdefault(key, value)
    return response


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

        response: Response = _proteger(await call_next(request))

        # Les URL statiques ne portent pas d'empreinte (`/static/app.js`), donc un
        # cache long servirait une version perimee apres chaque correction. Constate
        # en direct le 18/09 : `app.js` corrige, fichier servi correct, et la page
        # tournait toujours sur l'ancien script. Sans `cache-control`, le navigateur
        # applique une heuristique et decide seul.
        # `no-cache` ne veut pas dire « ne cache pas » : il veut dire « redemande-moi
        # avant de reutiliser ». Avec l'ETag deja pose par StaticFiles, cette
        # revalidation coute un 304 vide.
        chemin = request.url.path
        if chemin.startswith("/static/"):
            # Une police est immuable : changer de fonte, c'est changer de fichier.
            # Mesure du 18/09 : les quatre polices pesent 134 Ko et etaient revalidees
            # a chaque visite. Elles meritent le cache maximal ; le script et la
            # feuille, qui changent sous le meme nom, gardent leur revalidation.
            immuable = chemin.startswith("/static/polices/")
            response.headers.setdefault(
                "cache-control",
                "public, max-age=31536000, immutable" if immuable else "no-cache")

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
    def robots(request: Request):
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
        # 18/09/2026 — `StaticFiles` monte TOUT le dossier : y deposer un fichier,
        # c'est le publier. Mesure du jour : trois planches de travail internes
        # (`logo-lab.html` — cinq pistes de logo, `intro-preview.html`,
        # `og-card.html`) repondaient 200 et rien ne les tenait hors des moteurs.
        # Sans titre produit, sans le 3114, sans mention legale : une planche de
        # logos qui remonte a cote du vrai site, sur une application de sante
        # mentale, n'est pas un detail de referencement.
        #
        # Deduit, pas ecrit a la main : tout `.html` du dossier servi qui n'est pas
        # un ecran du produit. Une planche ajoutee demain est couverte le jour meme.
        # Le CSS et le JS, eux, restent ouverts : les bloquer empeche les moteurs de
        # rendre le vrai site.
        ecrans = {f for _, f, *_ in PAGES} | {"404.html", "500.html"}
        ateliers = sorted(f.name for f in static_dir.glob("*.html") if f.name not in ecrans)

        lines = ["User-agent: *", "Allow: /$"]
        lines += [f"Disallow: {chemin}" for chemin in api]
        lines += [f"Disallow: /static/{nom}" for nom in ateliers]
        lines += [f"Sitemap: {public_origin(request)}/sitemap.xml", ""]
        return PlainTextResponse("\n".join(lines))

    # Les pages publiques : celles qu'un moteur peut indexer et qu'un humain peut lire.
    PAGES = [("/", "index.html", "weekly", "1.0"),
             ("/confidentialite", "confidentialite.html", "yearly", "0.3"),
             ("/cgu", "cgu.html", "yearly", "0.3")]

    # 18/09/2026 - UNE PAGE, UNE ADRESSE. Les ecrans sont des gabarits : ils portent
    # `{{ORIGIN}}` et `page()` le remplace. Mais ils vivent dans le dossier monte, donc
    # `/static/index.html` et `/static/cgu.html` repondaient 200 en servant le gabarit
    # BRUT -- avec un `canonical` qui vaut litteralement `{{ORIGIN}}/` et une `og:image`
    # introuvable. Chaque page existait a deux adresses, et la seconde ne pointait vers
    # rien. `/static/404.html` etait pire encore : 200 sur une page qui dit « introuvable »,
    # le soft 404 du manuel.
    #
    # On ne retire rien du dossier (les gabarits y sont lus par `page()`), on repond a la
    # seconde adresse avant que le montage ne la serve. 301 : permanent, c'est l'original
    # qui compte. Les planches de travail declarees, elles, restent servies telles quelles.
    # Une route par gabarit, JAMAIS `/static/{fichier}` : une route attrape-tout ne peut pas
    # rendre la main au montage (Starlette n'essaie pas la route suivante quand celle-ci a
    # repondu), et tout le dossier -- css, polices, images -- passerait par ici.
    _CANONIQUE = {f: c for c, f, *_ in PAGES} | {"404.html": "/", "500.html": "/"}

    def _vers(cible: str):
        def redirige():
            return RedirectResponse(cible, status_code=301)
        return redirige

    for _fichier, _cible in _CANONIQUE.items():
        app.add_api_route(f"/static/{_fichier}", _vers(_cible), methods=["GET"], include_in_schema=False)

    @app.get("/confidentialite", include_in_schema=False)
    def confidentialite(request: Request):
        return page(static_dir, "confidentialite.html", request=request)

    @app.get("/cgu", include_in_schema=False)
    def cgu(request: Request):
        return page(static_dir, "cgu.html", request=request)

    @app.get("/sitemap.xml", include_in_schema=False)
    def sitemap(request: Request):
        origin = public_origin(request)
        # 🔴 Corrige le 18/09/2026 : cette ligne disait « une seule liste : le sitemap ne
        # peut pas oublier une page que le site sert ». C'etait faux. `PAGES` alimente le
        # sitemap et robots.txt, mais les routes sont ecrites a la main ailleurs — juste
        # au-dessus pour `/cgu` et `/confidentialite`, dans `main.py` pour `/`. Ajouter une
        # page, c'est deux gestes, et le second s'oublie.
        #
        # L'oubli ne coute pas que du referencement : robots.txt deduit sa liste d'API de
        # tout ce qui n'est PAS dans `PAGES`, donc une page publique oubliee ici est
        # activement `Disallow:`. Ce qui tient les deux listes ensemble est desormais un
        # test qui interroge les routes reelles — `test_aucune_page_publique_ne_manque_au_plan`.
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

    @app.exception_handler(Exception)
    async def panne(request: Request, exc):
        """Une panne reste une panne, mais elle ne largue pas le client.

        Mesure du 18/09/2026 : sans ce gestionnaire, une route qui leve renvoyait
        `Internal Server Error` en text/plain -- SANS aucun en-tete de securite (CSP,
        nosniff, X-Frame-Options, Referrer-Policy) et sans le 3114. L'exception
        remontait au-dessus du middleware qui les pose : c'etait l'ordre des couches,
        pas un oubli de configuration. La seule page du site a ne pas etre protegee
        etait celle qui apparait quand ca va mal.

        Ce que ce gestionnaire ne fait PAS : deguiser la panne. Le statut reste 500 et
        le detail interne ne sort pas -- il est journalise, pas servi.
        """
        log.exception("panne non rattrapee sur %s %s", request.method, request.url.path)
        if _wants_html(request):
            return _proteger(page(static_dir, "500.html", status_code=500))
        return _proteger(JSONResponse(
            {
                "error": "internal",
                # Le 3114 voyage avec la panne : il est sur tous les ecrans et dans la
                # reponse 429 de l'anti-spam, il n'a pas de raison de disparaitre ici.
                "reply": (
                    "Ca a casse de notre cote, tu n'y es pour rien et rien n'est perdu. "
                    "Reessaie dans un instant. En cas de detresse, le 3114 (national, "
                    "gratuit, 24h/24) reste joignable directement."
                ),
            },
            status_code=500,
        ))
