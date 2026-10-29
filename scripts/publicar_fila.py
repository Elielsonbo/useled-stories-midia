"""Publica o próximo story da fila (fila/fila.json) no Instagram da @useledluminarias.

Roda no GitHub Actions às ~9h e ~20h (horário de Brasília). Regras:
- publica no máximo 1 story por execução;
- prioridade: item "pendente" cujo horário já chegou (até 40 min de antecedência);
- se não houver item para o horário, usa uma reserva (horario = null);
- itens que perderam o horário há mais de 6h viram reserva (nada se perde);
- se algo foi publicado nas últimas 3h, não publica de novo (evita duplicar).

Variáveis de ambiente: IG_ACCESS_TOKEN (segredo), IG_USER_ID, MODO=publicar|teste
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
FILA = Path(__file__).resolve().parents[1] / "fila" / "fila.json"


def chamar(metodo, url, **params):
    params["access_token"] = os.environ["IG_ACCESS_TOKEN"]
    dados = urllib.parse.urlencode(params).encode()
    req = (urllib.request.Request(f"{url}?{dados.decode()}") if metodo == "GET"
           else urllib.request.Request(url, data=dados, method="POST"))
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode(errors='ignore')[:400]}")


def publicar(url_imagem: str) -> dict:
    uid = os.environ["IG_USER_ID"]
    cid = chamar("POST", f"{API}/{uid}/media", image_url=url_imagem, media_type="STORIES")["id"]
    for _ in range(30):
        st = chamar("GET", f"{API}/{cid}", fields="status_code").get("status_code")
        if st == "FINISHED":
            break
        if st in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"container {cid}: {st}")
        time.sleep(4)
    else:
        raise RuntimeError(f"container {cid} não ficou pronto")
    mid = chamar("POST", f"{API}/{uid}/media_publish", creation_id=cid)["id"]
    return {"media_id": mid}


def url_ok(url: str) -> bool:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=30) as r:
            return r.status == 200 and "image" in r.headers.get("Content-Type", "")
    except Exception:
        return False


def main():
    modo = os.environ.get("MODO", "publicar")
    agora = datetime.now(SP)
    fila = json.loads(FILA.read_text(encoding="utf-8"))
    itens = fila["itens"]

    def h(i):
        return datetime.fromisoformat(i["horario"]) if i.get("horario") else None

    # itens que perderam o horário há mais de 6h viram reserva
    for i in itens:
        if i["status"] == "pendente" and h(i) and h(i) < agora - timedelta(hours=6):
            i["nota"] = f"horário {i['horario']} perdido; virou reserva"
            i["horario"] = None

    # um story por turno: manhã (antes das 16h) ou noite, no mesmo dia
    def turno(d):
        return (d.date(), d.hour < 16)
    recentes = [i for i in itens if i["status"] == "publicado"
                and (datetime.fromisoformat(i["publicado_em"]) > agora - timedelta(hours=3)
                     or turno(datetime.fromisoformat(i["publicado_em"]).astimezone(SP)) == turno(agora))]
    pend = [i for i in itens if i["status"] == "pendente"]
    devidos = sorted([i for i in pend if h(i) and h(i) <= agora + timedelta(minutes=60)], key=h)
    reservas = [i for i in pend if not h(i)]
    futuros = [i for i in pend if h(i) and h(i) > agora + timedelta(minutes=60)]

    resumo = {"agora": agora.isoformat(timespec="minutes"), "devidos": len(devidos),
              "reservas": len(reservas), "agendados_futuros": len(futuros)}

    if modo == "teste":
        me = chamar("GET", f"{API}/me", fields="username")
        resumo.update(conta=me.get("username"),
                      urls_ok=all(url_ok(i["url"]) for i in pend),
                      proximo=(devidos or reservas or futuros or [{}])[0].get("id"))
        print(json.dumps(resumo, ensure_ascii=False))
        return 0

    # O GitHub às vezes dispara com horas de atraso. Fora das janelas da manhã
    # (8h-14h) e da noite (19h-23h) não publica nada, para não sair story de madrugada.
    if modo == "publicar" and not (8 <= agora.hour < 14 or 19 <= agora.hour < 23) \
            and not os.environ.get("FORCAR"):
        print(json.dumps({**resumo, "acao": "nada (fora da janela 8-14h / 19-23h)"}, ensure_ascii=False))
        FILA.write_text(json.dumps(fila, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 0

    if recentes:
        print(json.dumps({**resumo, "acao": "nada (já publicado neste turno)"}, ensure_ascii=False))
        FILA.write_text(json.dumps(fila, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 0

    item = devidos[0] if devidos else (reservas[0] if reservas else None)
    if not item:
        print(json.dumps({**resumo, "acao": "SEM STORY PARA ESTE HORÁRIO (fila vazia e sem reservas)"}, ensure_ascii=False))
        return 1

    erro = None
    for tentativa in (1, 2):
        try:
            res = publicar(item["url"])
            item.update(status="publicado", media_id=res["media_id"],
                        publicado_em=datetime.now(SP).isoformat(timespec="seconds"))
            erro = None
            break
        except Exception as e:  # noqa: BLE001
            erro = str(e)
            item["tentativas"] = item.get("tentativas", 0) + 1
            if tentativa == 1:
                time.sleep(60)
    if erro:
        item["ultimo_erro"] = erro[:300]

    FILA.write_text(json.dumps(fila, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({**resumo, "acao": "erro" if erro else "publicado", "item": item["id"],
                      "erro": erro}, ensure_ascii=False))
    return 1 if erro else 0


if __name__ == "__main__":
    sys.exit(main())
