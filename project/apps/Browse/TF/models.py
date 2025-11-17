from django.db import models

# Create your models here.
class TF(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=100)
    species = models.CharField(max_length=100)
    genome = models.CharField(max_length=100)
    start = models.IntegerField()
    end = models.IntegerField()
    strand = models.CharField(max_length=10)
    type = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)