#from backend.apps.Browse.models import Species
from cmath import phase
from typing import Sequence
from django.db import models

# Create your models here.
# TF模型定义

# Species模型定义
class Species_info(models.Model):
    """物种模型，用于存储物种信息"""
    # 基本信息字段
    name = models.CharField(max_length=255, blank=True, null=False, verbose_name='名称',unique=True, default='')
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
    alias = models.CharField(max_length=255, blank=True, null=True, verbose_name='实际显示名', unique=True)
    
    class Meta:
        db_table = 'species'  # 确保表名与导入数据匹配
        indexes = [
            models.Index(fields=['alias']),
            models.Index(fields=['name']),
        ]
        #managed = True  # 防止Django尝试修改这个表
    
    def __str__(self):
        # 如果name为空，使用Cotton_Species作为显示名称
        return self.name if self.name else self.alias

class blastdb_path(models.Model):
    db_type=models.CharField(max_length=100, blank=True, null=True)
    db_name=models.CharField(max_length=100, blank=True, null=False,primary_key=True)
    path=models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'blastdb'
        indexes = [
            models.Index(fields=['db_name']),
        ]

class GeneMaster(models.Model):
    id = models.BigAutoField(primary_key=True)
    geneid = models.CharField(max_length=200,unique=True)
    genome = models.ForeignKey(Species_info, on_delete=models.CASCADE, to_field='name')
    alias = models.CharField(max_length=200, blank=True, null=True, verbose_name='检索名')
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = 'genemaster'  # 确保表名与导入数据匹配
        constraints = [
            models.UniqueConstraint(fields=['genome','geneid'], name='genome_gene')
        ]
        indexes = [
            models.Index(fields=['geneid']),
            models.Index(fields=['genome']),
        ]
    def save(self, *args, **kwargs):
        # 自动生成 alias
        self.alias = f"{self.genome_id}::{self.geneid}"
        super().save(*args, **kwargs)
    def __str__(self):
        return f"{self.genome.name}:{self.geneid}"

class Family(models.Model):
    id = models.OneToOneField(GeneMaster, on_delete=models.CASCADE, to_field='id',primary_key=True)
    
    # 关联 GeneMaster 的字段（新增）
    geneid=models.CharField(max_length=200,blank=True, null=True)
    genome = models.ForeignKey(Species_info, on_delete=models.CASCADE, to_field='name') 
    TF_class = models.CharField(db_column='TF_class', max_length=100)  # Field name made lowercase in DB
    TF_name = models.CharField(db_column='TF_name', max_length=100)  # Field name made lowercase in DB

    class Meta:
        db_table = 'genefamily'  # 指定数据库中实际存在的表名
        indexes = [
            models.Index(fields=['geneid','genome',]),           
        ]
        #managed = False  # 防止Django尝试修改这个表


class gene_expression(models.Model):
    id = models.AutoField(primary_key=True)
    id_id = models.IntegerField(default='0')
    geneid=models.ForeignKey(GeneMaster, on_delete=models.CASCADE,  null=True,to_field='geneid')
    genome = models.ForeignKey(Species_info, on_delete=models.CASCADE, to_field='name') 
    tissue = models.CharField(max_length=50)
    stage = models.CharField(max_length=50, null=True)
    value = models.FloatField()


    class Meta:
        #managed = True
        indexes = [
            models.Index(fields=['geneid','genome']),
        ]
        db_table = 'expression'




class gene_info(models.Model):
    id=models.BigAutoField(primary_key=True)
    id_id = models.IntegerField(default='0')
    geneid=models.ForeignKey(GeneMaster, on_delete=models.CASCADE, null=True,to_field='geneid')
    genome = models.ForeignKey(Species_info, on_delete=models.CASCADE, to_field='name') 
    seqid = models.CharField(max_length=100)
    source = models.CharField(max_length=100)
    type = models.CharField(max_length=100)
    start = models.IntegerField()
    end = models.IntegerField()
    strand = models.CharField(max_length=10)
    phase = models.CharField(max_length=10)
    value = models.CharField(max_length=10)
    attributes = models.TextField(blank=True, null=True)
    class Meta:
        db_table = 'gene_assembly'
    def __str__(self):
        return self.geneid.geneid

class gene_annotation(models.Model):
    id=models.BigAutoField(primary_key=True)
    id_id = models.IntegerField(default='0')
    geneid=models.ForeignKey(GeneMaster, on_delete=models.CASCADE, to_field='geneid', null=True)
    genome = models.ForeignKey(Species_info, on_delete=models.CASCADE, to_field='name') 
    annoation_source=models.CharField(max_length=100, blank=True, null=True)
    annotation = models.TextField(blank=True, null=True)
    def __str__(self):
        return self.geneid
    class Meta:
        db_table = 'gene_annotation'

class gene_seq(models.Model):
    id = models.BigAutoField(primary_key=True)
    id_id = models.IntegerField(default='0')
    geneid=models.ForeignKey(GeneMaster, on_delete=models.CASCADE, to_field='geneid', null=True)
    genome = models.ForeignKey(Species_info, on_delete=models.CASCADE, to_field='name') 
    mrna_id = models.CharField(max_length=100, blank=True, null=True)
    gene_type = models.CharField(max_length=100, blank=True, null=True)
    sequence = models.TextField(blank=True, null=True)
    def __str__(self):
        return str(self.geneid)
    class Meta:
        db_table = 'gene_seq'
