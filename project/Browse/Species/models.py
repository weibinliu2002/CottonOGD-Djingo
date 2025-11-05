from django.db import models

# Create your models here.
class Species(models.Model):
    Cotton_Species = models.CharField(max_length=100)
    Genome_type = models.CharField(max_length=100)
    Category = models.CharField(max_length=100)
    Accession = models.CharField(max_length=100)
    Ploidy = models.CharField(max_length=100)
    Assembling_institution = models.CharField(max_length=100)
    Website = models.CharField(max_length=100)
    name = models.CharField(max_length=100)
    Article = models.CharField(max_length=100)
    LAI_value = models.CharField(max_length=100)
    Busco = models.CharField(max_length=100)
    Genome_size = models.CharField(max_length=100)
    description = models.TextField()
    def __str__(self):
        return self.name

class   Genome(models.Model):       
    species = models.ForeignKey(Species, on_delete=models.CASCADE)
    file_path = models.CharField(max_length=255)
    def __str__(self):
        return self.file_path
