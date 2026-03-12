from django.contrib import admin

# Register your models here.
from .models import *

class FamilyAdmin(admin.ModelAdmin):
    # 只显示必要的字段
    list_display = ('get_geneid', 'get_genome', 'TF_class', 'TF_name')
    # 优化查询，减少数据库查询次数
    list_select_related = ('genome',)
    # 使用raw_id_fields处理外键，避免加载所有选项
    raw_id_fields = ('id', 'genome')
    # 添加搜索功能
    search_fields = ('geneid', 'TF_class', 'TF_name')
    # 添加过滤器
    list_filter = ('genome', 'TF_class')
    # 配置编辑页面的字段
    fields = ('geneid', 'genome', 'TF_class', 'TF_name')
    # 禁用内联编辑，减少加载时间
    list_editable = []
    # 分页设置，减少每页显示的数量
    list_per_page = 20
    
    def get_geneid(self, obj):
        return obj.geneid
    get_geneid.short_description = 'Gene ID'
    
    def get_genome(self, obj):
        return obj.genome.name
    get_genome.short_description = 'Genome'

admin.site.register(Species_info)
admin.site.register(GeneMaster)
admin.site.register(gene_info)
admin.site.register(Family, FamilyAdmin)
admin.site.register(gene_annotation)
admin.site.register(gene_seq)
admin.site.register(gene_expression)
admin.site.register(gene_go)
admin.site.register(gene_kegg)
