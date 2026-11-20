"""Publica posts agendados (feed, Reels e stories) de fila/posts.json no Instagram da @useledluminarias.

Tipos: carrossel (imagens JPEG), reels (vídeo + capa), story_imagem, story_video.
Cada item: id, horario (ISO com fuso), tipo, midias (caminhos na branch stories), legenda, status.
Opcional: "ate" (ISO) = não publica depois desse horário; "capa" (reels).

Regras:
- publica itens "pendente" cujo horário já chegou (até 3 min antes), em ordem;
- se o próximo item é daqui a até ESPERA_MAX minutos, espera até o horário e publica;
- itens atrasados ainda saem até 4h depois do horário (ou até "ate"); depois disso viram "perdido".
- MODO=teste: cria os containers (confere mídia e formato) sem publicar nada.
Variáveis: IG_ACCESS_TOKEN (segredo), IG_USER_ID, MODO, SHA_MIDIA (commit da branch stories).
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

SP = ZoneInfo("America/Sao_Paulo")
API = "https://graph.instagram.com/v21.0"
RAIZ = Path(__file__).resolve().parents[1]
FILA = RAIZ / "fila" / "posts.json"
REPO = "Elielsonbo/useled-stories-midia"
ESPERA_MAX = int(os.environ.get("ESPERA_MAX", "330"))  # minutos (o job tem limite de 6h)
ATRASO_MAX = timedelta(hours=4)
INICIO = time.time()


def chamar(metodo, url, **params):
    params["access_token"] = os.environ["IG_ACCESS_TOKEN"]
    dados = urllib.parse.urlencode(params).encode()
    req = (urllib.request.Request(f"{url}?{dados.decode()}") if metodo == "GET"
           else urllib.request.Request(url, data=dados, method="POST"))
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode(errors='ignore')[:500]}")


def url_ok(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=30) as r:
            return r.status == 200
    except Exception:
        return False


def url_midia(caminho, sha):
    for u in (f"https://cdn.jsdelivr.net/gh/{REPO}@{sha}/{caminho}",
              f"https://raw.githubusercontent.com/{REPO}/{sha}/{caminho}"):
        if url_ok(u):
            return u
    raise RuntimeError(f"mídia inacessível: {caminho}")


def esperar(cid, video=False):
    for _ in range(90 if video else 30):
        r = chamar("GET", f"{API}/{cid}", fields="status_code,status")
        st = r.get("status_code")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"container {cid}: {st} {r.get('status', '')}")
        time.sleep(5)
    raise RuntimeError(f"container {cid} não ficou pronto")


def upload_direto(uid, arquivo, **params):
    """Plano B para vídeo: envia o arquivo (rupload) em vez de URL."""
    cont = chamar("POST", f"{API}/{uid}/media", upload_type="resumable", **params)
    cid, uri = cont["id"], cont["uri"]
    dados = Path(arquivo).read_bytes()
    req = urllib.request.Request(uri, data=dados, method="POST", headers={
        "Authorization": f"OAuth {os.environ['IG_ACCESS_TOKEN']}", "offset": "0",
        "file_size": str(len(dados))})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            r.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"upload HTTP {e.code}: {e.read().decode(errors='ignore')[:300]}")
    return cid


def container_video(uid, caminho, sha, **params):
    try:
        cid = chamar("POST", f"{API}/{uid}/media", video_url=url_midia(caminho, sha), **params)["id"]
        esperar(cid, video=True)
        return cid
    except RuntimeError as e:
        print(f"video_url falhou ({e}); tentando upload direto", flush=True)
        cid = upload_direto(uid, RAIZ / "_midia" / caminho, **params)
        esperar(cid, video=True)
        return cid


def criar(item, sha):
    uid = os.environ["IG_USER_ID"]
    t, m, leg = item["tipo"], item["midias"], item.get("legenda", "")
    if t == "carrossel":
        filhos = []
        for c in m:
            cid = chamar("POST", f"{API}/{uid}/media", image_url=url_midia(c, sha), is_carousel_item="true")["id"]
            esperar(cid)
            filhos.append(cid)
        cid = chamar("POST", f"{API}/{uid}/media", media_type="CAROUSEL", children=",".join(filhos), caption=leg)["id"]
        esperar(cid)
        return cid
    if t == "reels":
        extra = {"cover_url": url_midia(item["capa"], sha)} if item.get("capa") else {}
        return container_video(uid, m[0], sha, media_type="REELS", caption=leg, share_to_feed="true", **extra)
    if t == "story_video":
        return container_video(uid, m[0], sha, media_type="STORIES")
    if t == "story_imagem":
        cid = chamar("POST", f"{API}/{uid}/media", image_url=url_midia(m[0], sha), media_type="STORIES")["id"]
        esperar(cid)
        return cid
    raise RuntimeError(f"tipo desconhecido: {t}")


def publicar(cid):
    uid = os.environ["IG_USER_ID"]
    for tentativa in range(6):
        try:
            return chamar("POST", f"{API}/{uid}/media_publish", creation_id=cid)["id"]
        except RuntimeError as e:
            if ("9007" not in str(e) and "not ready" not in str(e)) or tentativa == 5:
                raise
            time.sleep(10 * (tentativa + 1))


def salvar(fila):
    FILA.write_text(json.dumps(fila, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def h(i):
    return datetime.fromisoformat(i["horario"])


def main():
    modo = os.environ.get("MODO", "publicar")
    sha = os.environ["SHA_MIDIA"]
    fila = json.loads(FILA.read_text(encoding="utf-8"))
    erros = 0

    if modo == "teste":
        for i in [x for x in fila["itens"] if x["status"] == "pendente"]:
            try:
                cid = criar(i, sha)
                print(f"TESTE ok: {i['id']} ({i['tipo']}) container {cid} pronto, não publicado", flush=True)
            except Exception as e:  # noqa: BLE001
                erros += 1
                print(f"TESTE ERRO: {i['id']}: {e}", flush=True)
        return 1 if erros else 0

    while True:
        agora = datetime.now(SP)
        for i in fila["itens"]:
            limite = datetime.fromisoformat(i["ate"]) if i.get("ate") else h(i) + ATRASO_MAX
            if i["status"] == "pendente" and agora > limite:
                i["status"] = "perdido"
                print(f"perdido (passou do limite): {i['id']}", flush=True)
        pend = sorted([i for i in fila["itens"] if i["status"] == "pendente"], key=h)
        devidos = [i for i in pend if h(i) <= agora + timedelta(minutes=3)]
        for i in devidos:
            try:
                cid = criar(i, sha)
                mid = publicar(cid)
                i.update(status="publicado", media_id=mid,
                         publicado_em=datetime.now(SP).isoformat(timespec="seconds"))
                i.pop("ultimo_erro", None)
                print(f"publicado: {i['id']} -> {mid}", flush=True)
            except Exception as e:  # noqa: BLE001
                erros += 1
                i["tentativas"] = i.get("tentativas", 0) + 1
                i["ultimo_erro"] = str(e)[:300]
                print(f"ERRO {i['id']}: {e}", flush=True)
                if i["tentativas"] >= 3:
                    i["status"] = "erro"
            salvar(fila)
        pend = sorted([i for i in fila["itens"] if i["status"] == "pendente"], key=h)
        if not pend:
            break
        falta = (h(pend[0]) - datetime.now(SP)).total_seconds()
        if falta <= 180:
            time.sleep(60)  # um item falhou: tenta de novo daqui a pouco
            continue
        if falta > ESPERA_MAX * 60 - (time.time() - INICIO):
            print(f"próximo: {pend[0]['id']} às {pend[0]['horario']} (fora da janela de espera)", flush=True)
            break
        print(f"esperando {int(falta)}s até {pend[0]['id']}", flush=True)
        time.sleep(max(falta - 60, 5))
    salvar(fila)
    return 1 if erros else 0


if __name__ == "__main__":
    sys.exit(main())
