from django.db import models

class FPKM4(models.Model):
    gene_id = models.CharField(max_length=200,primary_key=True)
    Root = models.FloatField(max_length=100, blank=True, null=True)
    Stem = models.FloatField(max_length=100, blank=True, null=True)
    Cotyledon = models.FloatField(max_length=100, blank=True, null=True)
    Leaf = models.FloatField(max_length=100, blank=True, null=True)
    Pholem = models.FloatField(max_length=100, blank=True, null=True)
    Sepal = models.FloatField(max_length=100, blank=True, null=True)
    Bract = models.FloatField(max_length=100, blank=True, null=True)
    Petal = models.FloatField(max_length=100, blank=True, null=True)
    Anther = models.FloatField(max_length=100, blank=True, null=True)
    Stigma = models.FloatField(max_length=100, blank=True, null=True)
    number_0_DPA_ovules = models.FloatField(db_column='0_DPA_ovules', max_length=100, blank=True, null=True)  # Field renamed because it wasn't a valid Python identifier.
    number_3_DPA_fibers = models.FloatField(db_column='3_dpa_fibers', max_length=100, blank=True, null=True)  # Field renamed because it wasn't a valid Python identifier.
    number_6_DPA_fibers = models.FloatField(db_column='6_dpa_fibers', max_length=100, blank=True, null=True)  # Field renamed because it wasn't a valid Python identifier.
    number_9_DPA_fibers = models.FloatField(db_column='9_dpa_fibers', max_length=100, blank=True, null=True)  # Field renamed because it wasn't a valid Python identifier.
    number_12_DPA_fibers = models.FloatField(db_column='12_dpa_fibers', max_length=100, blank=True, null=True)  # Field renamed because it wasn't a valid Python identifier.
    number_15_DPA_fibers = models.FloatField(db_column='15_dpa_fibers', max_length=100, blank=True, null=True)  # Field renamed because it wasn't a valid Python identifier.
    number_18_DPA_fibers = models.FloatField(db_column='18_dpa_fibers', max_length=100, blank=True, null=True)  # Field renamed because it wasn't a valid Python identifier.
    number_21_DPA_fibers = models.FloatField(db_column='21_dpa_fibers', max_length=100, blank=True, null=True)  # Field renamed because it wasn't a valid Python identifier.
    number_24_DPA_fibers = models.FloatField(db_column='24_dpa_fibers', max_length=100, blank=True, null=True)  # Field renamed because it wasn't a valid Python identifier.
    dpa0 = models.FloatField(max_length=100, blank=True, null=True)
    number_5_DPA_ovules = models.FloatField(db_column='5_dpa_ovules', max_length=100, blank=True, null=True)  # Field renamed because it wasn't a valid Python identifier.
    number_10_DPA_ovules = models.FloatField(db_column='10_dpa_ovules', max_length=100, blank=True, null=True)  # Field renamed because it wasn't a valid Python identifier.
    number_20_DPA_ovules = models.FloatField(db_column='20_dpa_ovules', max_length=100, blank=True, null=True)  # Field renamed because it wasn't a valid Python identifier.
    Seed = models.FloatField(max_length=100, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'fpkm4'