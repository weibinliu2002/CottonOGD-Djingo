from django.db import models

# TF模型定义
class TF(models.Model):
    TF_gene = models.CharField(db_column='TF_gene', max_length=100)  # Field name made lowercase in DB
    TF_genome = models.CharField(db_column='TF_genome', max_length=100)  # Field name made lowercase in DB
    TF_class = models.CharField(db_column='TF_class', max_length=100)  # Field name made lowercase in DB
    TF_name = models.CharField(db_column='TF_name', max_length=100)  # Field name made lowercase in DB

    class Meta:
        db_table = 'tf_tf'  # 指定数据库中实际存在的表名
        #managed = False  # 防止Django尝试修改这个表

# Species模型定义
class Species(models.Model):
    """物种模型，用于存储物种信息"""
    # 基本信息字段
    name = models.CharField(max_length=255, blank=True, null=True, verbose_name='名称')
    
    # 导入数据中的字段
    Cotton_Species = models.CharField(max_length=255, blank=True, null=True, verbose_name='棉花物种')
    Genome_type = models.CharField(max_length=100, blank=True, null=True, verbose_name='基因组类型')
    Category = models.CharField(max_length=100, blank=True, null=True, verbose_name='类别')
    Accession = models.CharField(max_length=100, blank=True, null=True, verbose_name='登录号')
    Ploidy = models.CharField(max_length=50, blank=True, null=True, verbose_name='倍性')
    Assembling_institution = models.CharField(max_length=255, blank=True, null=True, verbose_name='组装机构')
    Website = models.TextField(blank=True, null=True, verbose_name='网站')
    Article = models.CharField(max_length=255, blank=True, null=True, verbose_name='文章')
    LAI_value = models.CharField(max_length=100, blank=True, null=True, verbose_name='LAI值')
    Busco = models.CharField(max_length=100, blank=True, null=True, verbose_name='BUSCO值')
    Genome_size = models.BigIntegerField(blank=True, null=True, verbose_name='基因组大小')
    description = models.TextField(blank=True, null=True, verbose_name='描述')
    
    class Meta:
        db_table = 'species'  # 确保表名与导入数据匹配
        managed = False  # 防止Django尝试修改这个表
    
    def __str__(self):
        # 如果name为空，使用Cotton_Species作为显示名称
        return self.name if self.name else self.Cotton_Species