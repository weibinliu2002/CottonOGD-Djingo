from django.db import models

class OutGhirsutumTm1WhuStandard(models.Model):
    field_query = models.CharField(db_column='_query', max_length=20, primary_key=True)  # Field renamed because it started with '_'.
    seed_ortholog = models.CharField(max_length=40)
    evalue = models.CharField(max_length=10, blank=True, null=True)
    score = models.SmallIntegerField()
    eggnog_ogs = models.CharField(max_length=190)
    max_annot_lvl = models.CharField(max_length=40)
    cog_category = models.CharField(max_length=10)
    description = models.TextField()
    preferred_name = models.CharField(max_length=10)
    gos = models.TextField()
    ec = models.CharField(max_length=80)
    kegg_ko = models.CharField(max_length=100)
    kegg_pathway = models.TextField()
    kegg_module = models.CharField(max_length=80)
    kegg_reaction = models.TextField()
    kegg_rclass = models.CharField(max_length=190)
    brite = models.CharField(max_length=100)
    kegg_tc = models.CharField(max_length=60)
    cazy = models.CharField(max_length=20)
    bigg_reaction = models.CharField(max_length=30)
    pfams = models.CharField(max_length=120)

    class Meta:
        managed = False
        db_table = 'out_ghirsutum_tm_1_whu_standard'


class GOEnrichmentResult(models.Model):
    input_genes = models.TextField()
    background_genes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    results_json = models.JSONField()
    
    def __str__(self):
        return f"GO Enrichment Analysis {self.id}"
