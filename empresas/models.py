from django.db import models


class EmpresaESG(models.Model):
    nome = models.CharField(max_length=200)
    cnpj = models.CharField(max_length=18, unique=True)
    cidade = models.CharField(max_length=100)
    estado = models.CharField(max_length=2)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    setor = models.CharField(max_length=100)
    evidencias_esg = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Empresa ESG"
        verbose_name_plural = "Empresas ESG"
        ordering = ["nome"]

    def __str__(self):
        return self.nome