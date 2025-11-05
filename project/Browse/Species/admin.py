from django.contrib import admin

# Register your models here.
from .models import Species, Genome

admin.site.register(Species)
admin.site.register(Genome)