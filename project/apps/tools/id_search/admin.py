from django.contrib import admin
from .models import gene_info, gene_seq, Genome_Assembly,gene_annotation
# Register your models here.
admin.site.register(gene_info)
admin.site.register(gene_seq)
admin.site.register(Genome_Assembly)
admin.site.register(gene_annotation)
