from django.http import JsonResponse
from django.shortcuts import render

from .models import EmpresaESG


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