# management/commands/build_genesets.py
from django.core.management.base import BaseCommand
from CottonOGD.cache_models import GenomeGenesetCache

class Command(BaseCommand):
    help = '重建基因集缓存 (写入 Redis)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('开始构建...'))
        # ★ 一行代码触发全量构建 ★
        GenomeGenesetCache.objects.build_all()
        self.stdout.write(self.style.SUCCESS('构建完成！'))
