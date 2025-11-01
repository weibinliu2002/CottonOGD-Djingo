from django.db import models

class Blastp(models.Model):
    gene_id = models.CharField(max_length=50)
    protein_id = models.CharField(unique=True, max_length=100)
    description = models.TextField(blank=True, null=True)
    sequence = models.TextField()
    file_source = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'blastp'
