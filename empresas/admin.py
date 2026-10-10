from django.contrib import admin

from .models import EmpresaESG, Parceiro


@admin.register(EmpresaESG)
class EmpresaESGAdmin(admin.ModelAdmin):
    list_display = ("nome", "cnpj", "cidade", "estado", "setor")
    list_filter = ("estado", "setor")
    search_fields = ("nome", "cnpj", "cidade")


@admin.register(Parceiro)
class ParceiroAdmin(admin.ModelAdmin):
    list_display = ("nome", "tipo", "cidade", "estado", "produtos", "aceita_doacao")
    list_filter = ("tipo", "estado", "aceita_doacao")
    search_fields = ("nome", "cidade", "produtos")