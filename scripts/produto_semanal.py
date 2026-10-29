"""Story semanal de produto da loja (Shopee useled3d), em rodízio.

Roda no GitHub Actions aos domingos à tarde. Etapas (mesmo padrão do compartilhar_feed.py):

  python scripts/produto_semanal.py decidir   -> é domingo, na janela e ainda não postou nesta semana?
  python scripts/produto_semanal.py gerar     -> escolhe o próximo produto e gera out/story_produto.jpg + out/escolha.json
  python scripts/produto_semanal.py publicar  -> publica a imagem já enviada à branch `stories` e grava o histórico

Produtos em fila/produtos.json (foto em stories:produtos/<id>.jpg). Histórico em fila/produtos_hist.json.
Variáveis: IG_ACCESS_TOKEN (segredo), IG_USER_ID, MODO=publicar|teste, FORCAR=1, URL_BASE.
"""
import json
import os
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from publicar_fila import SP, publicar  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
PRODUTOS = RAIZ / "fila" / "produtos.json"
HIST = RAIZ / "fila" / "produtos_hist.json"
OUT = RAIZ / "out"
JANELA = (14, 19)   # horas de Brasília
DIA = 6             # domingo (segunda = 0)
URL_FOTO = "https://raw.githubusercontent.com/Elielsonbo/useled-stories-midia/stories/produtos/{id}.jpg"


def ler_hist():
    return json.loads(HIST.read_text(encoding="utf-8")) if HIST.exists() else {"itens": []}


def decidir():
    forcar = bool(os.environ.get("FORCAR"))
    agora = datetime.now(SP)
    hist = ler_hist()
    semana = agora.isocalendar()[:2]
    ja = any(tuple(datetime.fromisoformat(i["em"]).isocalendar()[:2]) == tuple(semana) for i in hist["itens"])
    resumo = {"agora": agora.isoformat(timespec="minutes"), "domingo": agora.weekday() == DIA,
              "na_janela": JANELA[0] <= agora.hour < JANELA[1], "ja_postou_semana": ja, "forcar": forcar}
    return forcar or (resumo["domingo"] and resumo["na_janela"] and not ja), resumo


def proximo(hist):
    lista = json.loads(PRODUTOS.read_text(encoding="utf-8"))["produtos"]
    if not hist["itens"]:
        return lista[0]
    ultimo = hist["itens"][-1]["id"]
    ids = [p["id"] for p in lista]
    i = (ids.index(ultimo) + 1) % len(lista) if ultimo in ids else 0
    return lista[i]


def gerar_arte(p):
    from playwright.sync_api import sync_playwright
    OUT.mkdir(exist_ok=True)
    foto = OUT / "produto.jpg"
    req = urllib.request.Request(URL_FOTO.format(id=p["id"]), headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        foto.write_bytes(r.read())
    campos = {"kicker": "Na nossa loja", "titulo": p["titulo"],
              "legenda": f'{p["legenda"]}<br><b>{p["preco"]}</b>',
              "cta": "Procure useled3d na Shopee", "imagem": foto.resolve().as_uri()}
    tpl = (RAIZ / "arte" / "story_feed.html").read_text(encoding="utf-8")
    for k, v in campos.items():
        tpl = tpl.replace("{{" + k + "}}", v)
    pag = RAIZ / "arte" / "_render.html"
    pag.write_text(tpl, encoding="utf-8")
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": 1920})
        pg.goto(pag.as_uri()); pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(500)
        pg.evaluate("""() => {const i=document.querySelector('.card img'); const s=Math.min(856/i.naturalWidth, 900/i.naturalHeight);
                       i.style.maxWidth='none'; i.style.maxHeight='none';
                       i.style.width=Math.round(i.naturalWidth*s)+'px'; i.style.height=Math.round(i.naturalHeight*s)+'px';}""")
        pg.screenshot(path=str(OUT / "story_produto.jpg"), type="jpeg", quality=90)
        b.close()
    pag.unlink()


def etapa_decidir():
    ok, resumo = decidir()
    print(json.dumps({**resumo, "acao": "seguir" if ok else "nada"}, ensure_ascii=False))
    if ok and os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write("seguir=1\n")
    return 0


def etapa_gerar():
    modo = os.environ.get("MODO", "publicar")
    ok, resumo = decidir()
    if not ok:
        print(json.dumps({**resumo, "acao": "nada"}, ensure_ascii=False)); return 0
    p = proximo(ler_hist())
    gerar_arte(p)
    agora = datetime.now(SP)
    nome = f"produtos/stories/{'teste_' if modo != 'publicar' else ''}{agora:%Y-%m-%d}_{p['id']}.jpg"
    esc = {"id": p["id"], "arquivo": nome, "modo": modo}
    (OUT / "escolha.json").write_text(json.dumps(esc, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({**resumo, "acao": "arte gerada", **esc}, ensure_ascii=False))
    return 0


def etapa_publicar():
    f = OUT / "escolha.json"
    if not f.exists():
        print("nada a publicar"); return 0
    esc = json.loads(f.read_text(encoding="utf-8"))
    if esc["modo"] != "publicar":
        print("modo teste: arte gerada, nada publicado"); return 0
    url = os.environ["URL_BASE"].rstrip("/") + "/" + esc["arquivo"]
    res = publicar(url)
    hist = ler_hist()
    hist["itens"].append({"id": esc["id"], "em": datetime.now(SP).isoformat(timespec="seconds"),
                          "story_id": res["media_id"], "imagem": url})
    HIST.write_text(json.dumps(hist, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"acao": "publicado", **esc, "story_id": res["media_id"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    etapa = sys.argv[1] if len(sys.argv) > 1 else "gerar"
    sys.exit({"decidir": etapa_decidir, "gerar": etapa_gerar, "publicar": etapa_publicar}[etapa]())
