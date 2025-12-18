from django.db import models

# Create your models here.
class TF(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    TF_name = models.CharField(max_length=100)
    TF_class = models.CharField(max_length=100)
    TF_gene = models.CharField(max_length=100)
    TF_genome = models.CharField(max_length=100)