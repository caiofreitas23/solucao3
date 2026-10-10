from django.contrib import admin
from .models import EmpresaESG


@admin.register(EmpresaESG)
class EmpresaESGAdmin(admin.ModelAdmin):
    list_display = ("nome", "cnpj", "cidade", "estado", "setor")
    list_filter = ("estado", "setor")
    search_fields = ("nome", "cnpj", "cidade")