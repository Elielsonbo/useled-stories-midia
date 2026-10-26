"""Compartilha nos stories um post do próprio feed da @useledluminarias.

Roda no GitHub Actions a cada 2 dias (dias pares contados a partir de 26/10/2026),
à tarde, entre os stories das 9h e das 20h. Duas etapas:

  python scripts/compartilhar_feed.py decidir   -> hoje é dia e hora de compartilhar? (sem API)
  python scripts/compartilhar_feed.py gerar     -> escolhe o post e gera out/story_feed.jpg + out/escolha.json
  python scripts/compartilhar_feed.py publicar  -> publica a imagem já enviada à branch `stories` e grava o histórico

Regras de escolha:
- só posts do feed (foto, carrossel, vídeo/reel) dos últimos 365 dias;
- prefere o mais recente que ainda não foi compartilhado;
- se todos já foram, repete o que foi compartilhado há mais tempo (mínimo 30 dias atrás);
- no máximo 1 compartilhamento por dia.

A API do Instagram não oferece o "compartilhar post no story" nativo (com adesivo clicável).
Por isso a arte mostra a imagem do post, um trecho da legenda e o convite para ver no perfil.

Variáveis: IG_ACCESS_TOKEN (segredo), IG_USER_ID, MODO=publicar|teste, FORCAR=1 (ignora dia/janela),
           URL_BASE (raw da branch stories, para a etapa publicar).
"""
import html
import json
import os
import re
import sys
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from publicar_fila import API, SP, chamar, publicar  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
HIST = RAIZ / "fila" / "compartilhados.json"
OUT = RAIZ / "out"
INICIO = date(2026, 10, 26)
JANELA = (11, 18)  # horas de Brasília em que pode publicar


def ler_hist():
    return json.loads(HIST.read_text(encoding="utf-8")) if HIST.exists() else {"itens": []}


def legenda_curta(cap: str, limite: int = 110) -> str:
    cap = re.sub(r"[#@]\S+", "", cap or "")            # tira hashtags e menções
    cap = re.sub(r"\s+", " ", cap).strip(" .-–—\n")
    if not cap:
        return ""
    frase = re.split(r"(?<=[.!?])\s", cap)[0]
    txt = frase if 12 <= len(frase) <= limite else cap
    if len(txt) > limite:
        txt = txt[:limite].rsplit(" ", 1)[0].rstrip(",;:") + "…"
    return txt


def buscar_posts():
    uid = os.environ["IG_USER_ID"]
    campos = "id,media_type,media_url,thumbnail_url,permalink,caption,timestamp,media_product_type"
    url, posts = f"{API}/{uid}/media", []
    params = {"fields": campos, "limit": 50}
    for _ in range(4):  # até 200 posts
        r = chamar("GET", url, **params)
        posts += r.get("data", [])
        nxt = r.get("paging", {}).get("cursors", {}).get("after")
        if not nxt or not r.get("paging", {}).get("next"):
            break
        params["after"] = nxt
    return posts


def escolher(posts, hist, agora):
    limite = agora - timedelta(days=365)
    ok = []
    for p in posts:
        ts = datetime.strptime(p["timestamp"], "%Y-%m-%dT%H:%M:%S%z").astimezone(SP)
        img = p.get("thumbnail_url") if p.get("media_type") == "VIDEO" else p.get("media_url")
        if ts >= limite and img:
            ok.append({**p, "_ts": ts, "_img": img})
    ok.sort(key=lambda p: p["_ts"], reverse=True)
    feitos = {}
    for i in hist["itens"]:
        feitos[i["media_id"]] = max(feitos.get(i["media_id"], ""), i["compartilhado_em"])
    novos = [p for p in ok if p["id"] not in feitos]
    if novos:
        return novos[0], len(ok), len(novos)
    antigos = [p for p in ok if feitos[p["id"]] < (agora - timedelta(days=30)).isoformat()]
    antigos.sort(key=lambda p: feitos[p["id"]])
    return (antigos[0] if antigos else None), len(ok), 0


TITULOS_RECENTE = ["Acabou de sair<br>da nossa impressora", "Produção nova<br>no feed!",
                   "Olha o que a gente<br>acabou de fazer"]
TITULOS_ANTIGO = ["Vem conferir<br>nossas produções", "Feito por nós,<br>camada por camada",
                  "Já viu essa<br>produção?"]


def titulo_da_vez(recente: bool) -> str:
    """Alterna os títulos a cada compartilhamento para não repetir."""
    lista = TITULOS_RECENTE if recente else TITULOS_ANTIGO
    return lista[len(ler_hist()["itens"]) % len(lista)]


def gerar_arte(post, agora):
    from playwright.sync_api import sync_playwright
    OUT.mkdir(exist_ok=True)
    foto = OUT / "post.jpg"
    req = urllib.request.Request(post["_img"], headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        foto.write_bytes(r.read())
    recente = (agora - post["_ts"]).days <= 14
    video = post.get("media_type") == "VIDEO"
    campos = {
        "kicker": "No nosso feed",
        "titulo": titulo_da_vez(recente),
        "legenda": html.escape(legenda_curta(post.get("caption", ""))),
        "cta": "Assista no nosso perfil" if video else "Veja o post completo no perfil",
        "imagem": foto.resolve().as_uri(),
    }
    tpl = (RAIZ / "arte" / "story_feed.html").read_text(encoding="utf-8")
    for k, v in campos.items():
        tpl = tpl.replace("{{" + k + "}}", v)
    pag = RAIZ / "arte" / "_render.html"
    pag.write_text(tpl, encoding="utf-8")
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": 1920})
        pg.goto(pag.as_uri())
        pg.wait_for_load_state("networkidle")
        pg.wait_for_timeout(500)
        # ajusta a imagem ao espaço (também AMPLIA fotos pequenas que a API às vezes entrega)
        fit = """(maxH) => {const i=document.querySelector('.card img');
                   const s=Math.min(856/i.naturalWidth, maxH/i.naturalHeight);
                   i.style.maxWidth='none'; i.style.maxHeight='none';
                   i.style.width=Math.round(i.naturalWidth*s)+'px'; i.style.height=Math.round(i.naturalHeight*s)+'px';}"""
        folga = """() => {const c=document.querySelector('.cta').getBoundingClientRect();
                   const l=document.querySelector('.leg'); const ref=l.offsetParent? l : document.querySelector('.card');
                   return c.top - ref.getBoundingClientRect().bottom}"""
        if not campos["legenda"]:
            pg.evaluate("document.querySelector('.leg').style.display='none'")
        altura = 1120 if not campos["legenda"] else 920
        pg.evaluate(fit, altura)
        while pg.evaluate(folga) < 30 and altura > 600:  # nada encosta no rodapé
            altura -= 40
            pg.evaluate(fit, altura)
        pg.screenshot(path=str(OUT / "story_feed.jpg"), type="jpeg", quality=90)
        b.close()
    pag.unlink()


def decidir():
    """Só olha data, horário e histórico (sem API). Retorna (deve_rodar, resumo)."""
    forcar = bool(os.environ.get("FORCAR"))
    agora = datetime.now(SP)
    hist = ler_hist()
    dia_par = (agora.date() - INICIO).days % 2 == 0
    na_janela = JANELA[0] <= agora.hour < JANELA[1]
    ja_hoje = any(i["compartilhado_em"][:10] == agora.date().isoformat() for i in hist["itens"])
    resumo = {"agora": agora.isoformat(timespec="minutes"), "dia_de_compartilhar": dia_par,
              "na_janela": na_janela, "ja_compartilhou_hoje": ja_hoje, "forcar": forcar}
    return forcar or (dia_par and na_janela and not ja_hoje), resumo


def etapa_decidir():
    ok, resumo = decidir()
    print(json.dumps({**resumo, "acao": "seguir" if ok else "nada"}, ensure_ascii=False))
    gh = os.environ.get("GITHUB_OUTPUT")
    if gh and ok:
        with open(gh, "a") as f:
            f.write("seguir=1\n")
    return 0


def etapa_gerar():
    modo = os.environ.get("MODO", "publicar")
    agora = datetime.now(SP)
    hist = ler_hist()
    ok, resumo = decidir()
    if not ok:
        print(json.dumps({**resumo, "acao": "nada"}, ensure_ascii=False))
        return 0
    post, total, novos = escolher(buscar_posts(), hist, agora)
    resumo.update(posts_ultimo_ano=total, ainda_nao_compartilhados=novos)
    if not post:
        print(json.dumps({**resumo, "acao": "nenhum post elegível"}, ensure_ascii=False))
        return 0
    gerar_arte(post, agora)
    nome = f"feed/{'teste_' if modo != 'publicar' else ''}{agora:%Y-%m-%d}_{post['id']}.jpg"
    escolha = {"media_id": post["id"], "permalink": post.get("permalink"), "tipo": post.get("media_type"),
               "post_em": post["_ts"].isoformat(), "arquivo": nome, "modo": modo}
    (OUT / "escolha.json").write_text(json.dumps(escolha, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({**resumo, "acao": "arte gerada", **escolha}, ensure_ascii=False))
    return 0


def etapa_publicar():
    esc_f = OUT / "escolha.json"
    if not esc_f.exists():
        print("nada a publicar")
        return 0
    esc = json.loads(esc_f.read_text(encoding="utf-8"))
    if esc["modo"] != "publicar":
        print("modo teste: arte gerada, nada publicado")
        return 0
    url = os.environ["URL_BASE"].rstrip("/") + "/" + esc["arquivo"]
    res = publicar(url)
    hist = ler_hist()
    hist["itens"].append({"media_id": esc["media_id"], "permalink": esc["permalink"],
                          "compartilhado_em": datetime.now(SP).isoformat(timespec="seconds"),
                          "story_id": res["media_id"], "imagem": url})
    HIST.write_text(json.dumps(hist, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"acao": "publicado", **esc, "story_id": res["media_id"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    etapa = sys.argv[1] if len(sys.argv) > 1 else "gerar"
    sys.exit({"decidir": etapa_decidir, "gerar": etapa_gerar, "publicar": etapa_publicar}[etapa]())
