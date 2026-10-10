import json
import logging
import urllib.parse
import urllib.request

from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import render

from .models import EmpresaESG, Parceiro


@login_required
def mapa_esg(request):
    return render(request, "guardiao/mapa_esg.html")


def api_empresas(request):
    empresas = EmpresaESG.objects.all()

    setor = request.GET.get("setor")
    estado = request.GET.get("estado")
    if setor:
        empresas = empresas.filter(setor__iexact=setor)
    if estado:
        empresas = empresas.filter(estado__iexact=estado)

    dados = [
        {
            "id": e.id,
            "nome": e.nome,
            "cnpj": e.cnpj,
            "cidade": e.cidade,
            "estado": e.estado,
            "latitude": float(e.latitude),
            "longitude": float(e.longitude),
            "setor": e.setor,
            "evidencias_esg": e.evidencias_esg,
        }
        for e in empresas
    ]
    return JsonResponse({"empresas": dados})


def api_parceiros(request):
    parceiros = Parceiro.objects.all()

    tipo = request.GET.get("tipo")
    if tipo:
        parceiros = parceiros.filter(tipo=tipo)

    dados = [
        {
            "id": p.id,
            "nome": p.nome,
            "tipo": p.tipo,
            "tipo_rotulo": p.get_tipo_display(),
            "cidade": p.cidade,
            "estado": p.estado,
            "latitude": float(p.latitude),
            "longitude": float(p.longitude),
            "produtos": [x.strip() for x in p.produtos.split(",") if x.strip()],
            "aceita_doacao": p.aceita_doacao,
            "contato": p.contato,
            "praticas_esg": p.praticas_esg,
        }
        for p in parceiros
    ]
    return JsonResponse({"parceiros": dados})


# ---------------------------------------------------------------
# Busca de fornecedores de insumos e pontos de doação (OpenStreetMap)
# ---------------------------------------------------------------

logger = logging.getLogger(__name__)

USER_AGENT = "MapaESG-Solucao3/1.0 (projeto academico)"

LOJAS_FORNECEDORES = {
    "farm": "Fazenda / produtor",
    "greengrocer": "Hortifruti",
    "butcher": "Açougue",
    "seafood": "Peixaria",
    "dairy": "Laticínios",
    "wholesale": "Atacado",
}


def _consultar(url, dados=None):
    pedido = urllib.request.Request(url, data=dados, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(pedido, timeout=30) as resposta:
        return json.loads(resposta.read().decode("utf-8"))


OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]


def _overpass(consulta):
    corpo = urllib.parse.urlencode({"data": consulta}).encode()
    ultimo_erro = None
    for url in OVERPASS_URLS:
        try:
            return _consultar(url, corpo)
        except Exception as erro:
            logger.warning("Overpass falhou em %s: %s", url, erro)
            ultimo_erro = erro
    raise ultimo_erro


def _classificar(tags):
    loja = tags.get("shop")
    local = tags.get("amenity")
    if loja in LOJAS_FORNECEDORES:
        return "fornecedor", LOJAS_FORNECEDORES[loja]
    if local == "marketplace":
        return "fornecedor", "Feira / mercado"
    if local == "place_of_worship":
        igreja = tags.get("religion") == "christian"
        return "doacao", "Igreja" if igreja else "Local de culto"
    if local == "social_facility":
        if tags.get("social_facility") == "food_bank":
            return "doacao", "Banco de alimentos"
        return "doacao", "Instituição social"
    if local == "community_centre":
        return "doacao", "Centro comunitário"
    return None, None


def _endereco(tags):
    rua = " ".join(p for p in [tags.get("addr:street"), tags.get("addr:housenumber")] if p)
    partes = [rua, tags.get("addr:suburb"), tags.get("addr:city")]
    return ", ".join(p for p in partes if p)


def api_locais(request):
    q = request.GET.get("q", "").strip()
    insumo = request.GET.get("insumo", "").strip().lower()

    if not q:
        return JsonResponse({"erro": "Informe um local."}, status=400)
    try:
        raio = int(request.GET.get("raio", 5000))
    except ValueError:
        raio = 5000
    raio = max(500, min(raio, 20000))

    chave = f"locais:{q.lower()}:{raio}:{insumo}"
    resultado = cache.get(chave)
    if resultado:
        return JsonResponse(resultado)

    try:
        geo = _consultar(
            "https://nominatim.openstreetmap.org/search?"
            + urllib.parse.urlencode({"q": q, "format": "jsonv2", "limit": 1})
        )
        if not geo:
            return JsonResponse({"erro": "Local não encontrado."}, status=404)
        lat, lon = float(geo[0]["lat"]), float(geo[0]["lon"])

        limite = 300
        consulta_fornecedores = f"""
        [out:json][timeout:25];
        nwr(around:{raio},{lat},{lon})["shop"~"^(farm|greengrocer|butcher|seafood|dairy|wholesale)$"];
        out center {limite + 1};
        """
        dados_fornecedores = _overpass(consulta_fornecedores)

        consulta_doacao = f"""
        [out:json][timeout:25];
        nwr(around:{raio},{lat},{lon})["amenity"~"^(marketplace|place_of_worship|social_facility|community_centre)$"];
        out center {limite + 1};
        """
        dados_doacao = _overpass(consulta_doacao)

    except Exception:
        logger.exception("Falha na busca de locais para %r", q)
        return JsonResponse(
            {"erro": "Não foi possível consultar os mapas agora. Tente de novo."},
            status=502,
        )

    elementos_fornecedores = dados_fornecedores.get("elements", [])
    elementos_doacao = dados_doacao.get("elements", [])

    limite_fornecedores = len(elementos_fornecedores) > limite
    limite_doacao = len(elementos_doacao) > limite

    elementos = elementos_fornecedores[:limite] + elementos_doacao[:limite]

    locais = []
    ids_encontrados = set()
    for el in elementos:
        tags = el.get("tags", {})
        categoria, tipo = _classificar(tags)
        ponto = el if "lat" in el else el.get("center")
        if not categoria or not ponto:
            continue

        nome = tags.get("name") or tipo

        if insumo and categoria == "fornecedor":
            texto_busca = f"{nome} {tipo} {tags.get('description', '')} {tags.get('craft', '')}".lower()
            if insumo not in texto_busca:
                continue

        identificador = f'{el["type"]}{el["id"]}'
        if identificador in ids_encontrados:
            continue
        ids_encontrados.add(identificador)

        locais.append({
            "id": identificador,
            "nome": nome,
            "categoria": categoria,
            "tipo": tipo,
            "latitude": ponto["lat"],
            "longitude": ponto["lon"],
            "endereco": _endereco(tags),
            "telefone": tags.get("phone", ""),
            "site": tags.get("website", ""),
        })

    resultado = {
        "centro": {
            "nome": geo[0]["display_name"],
            "latitude": lat,
            "longitude": lon,
            "raio": raio,
        },
        "locais": locais,
        "limites": {
            "fornecedores": limite_fornecedores,
            "doacao": limite_doacao,
            "limite_por_consulta": limite,
        },
        "aviso": (
            "Uma ou mais consultas atingiram o limite. "
            "Pode haver outros locais não exibidos. "
            "Reduza o raio para ver resultados mais detalhados."
            if limite_fornecedores or limite_doacao
            else ""
        ),
    }
    cache.set(chave, resultado, 3600)
    return JsonResponse(resultado)