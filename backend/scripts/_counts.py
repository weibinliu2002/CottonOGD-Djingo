import os, django, sys
sys.path.insert(0, '/data/web/CottonOGD/OGD/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
django.setup()
from CottonOGD.models import Variant, VariationSet, GwasTrait, GwasAccession, GwasPhenotype
from django.db.models import Count
print("variation_sets:", list(VariationSet.objects.values('id','name','sample_count')))
print("variant total:", Variant.objects.count())
print("variant by set:", list(Variant.objects.values('set_id','chrom').annotate(c=Count('id')).order_by('set_id')[:30]))
print("gwas traits:", list(GwasTrait.objects.values('code','name')))
print("gwas accessions:", GwasAccession.objects.count(), "| phenotypes:", GwasPhenotype.objects.count())
