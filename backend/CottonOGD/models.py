#from backend.apps.Browse.models import Species
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


class GeneMaster(models.Model):
    id = models.BigAutoField(primary_key=True)
    geneid = models.CharField(max_length=200,unique=False)
    genome = models.ForeignKey(Species_info, on_delete=models.CASCADE, to_field='name')
    alias = models.CharField(max_length=200, blank=True, null=True, verbose_name='检索名',unique=True)
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
    geneid=models.CharField(max_length=200,blank=True, null=True)
    genome = models.ForeignKey(Species_info, on_delete=models.CASCADE, to_field='name') 
    tissue = models.CharField(max_length=50)
    stage = models.CharField(max_length=50, null=True)
    value = models.FloatField()


    class Meta:
        #managed = True
        indexes = [
            models.Index(fields=['geneid','genome']),
            models.Index(fields=['id_id']),
        ]
        db_table = 'expression'

class GenomeTissue(models.Model):
    """维度表 - 用于快速查询"""
    genome = models.ForeignKey(
        'Species_info',
        on_delete=models.DO_NOTHING,
        to_field='name',
        db_column='genome'
    )
    tissue = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        managed = True  # ✅ Django 管理此表
        db_table = 'genome_tissue'
        unique_together = ['genome', 'tissue']  # 联合唯一约束
        indexes = [
            models.Index(fields=['genome'], name='gt_genome_idx'),
        ]
    
    @classmethod
    def sync_from_expression(cls):
        """从 Expression 表同步所有唯一组合"""
        from django.db import connection
        with connection.cursor() as cursor:
            # 清空并重新导入（或 INSERT IGNORE）
            cursor.execute("""
                INSERT IGNORE INTO genome_tissue (genome_id, tissue)
                SELECT DISTINCT genome_id, tissue FROM expression
            """)
        return cls.objects.count()
    


class gene_info(models.Model):
    id=models.BigAutoField(primary_key=True)
    #id = models.OneToOneField(GeneMaster, on_delete=models.CASCADE, to_field='id',primary_key=True)
    id_id = models.IntegerField(default='0')
    geneid_id=models.CharField(max_length=200,unique=False,default='0')
    #parent_id=models.CharField(max_length=200,unique=False,default='0')
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
        indexes = [
            models.Index(fields=['id_id']),
            models.Index(fields=['seqid']),
            models.Index(fields=['start']),
            models.Index(fields=['end']),
        ]
    def __str__(self):
        return self.geneid.geneid

class transcript_info(gene_info):
    pass    

class feature_info(gene_info):
    pass

class gene_annotation(models.Model):
    id=models.BigAutoField(primary_key=True)
    id_id = models.IntegerField(default='0')
    geneid_id=models.CharField(max_length=200,unique=False,default='0')
    geneid = models.CharField(max_length=100, blank=True, null=True)
    genome = models.ForeignKey(Species_info, on_delete=models.CASCADE, to_field='name') 
    annoation_source=models.CharField(max_length=100, blank=True, null=True)
    annoation_id=models.CharField(max_length=100, blank=True, null=True)
    annotation = models.TextField(blank=True, null=True)
    def __str__(self):
        return self.geneid
    class Meta:
        db_table = 'gene_annotation'
        indexes = [
            models.Index(fields=['id_id']),
        ]

class gene_seq(models.Model):
    id = models.BigAutoField(primary_key=True)
    id_id = models.IntegerField(default='0')
    geneid_id=models.CharField(max_length=200,unique=False,default='0')
    genome = models.ForeignKey(Species_info, on_delete=models.CASCADE, to_field='name') 
    mrna_id = models.CharField(max_length=100, blank=True, null=True)
    gene_type = models.CharField(max_length=100, blank=True, null=True)
    sequence = models.TextField(blank=True, null=True)
    def __str__(self):
        return str(self.geneid)
    class Meta:
        db_table = 'gene_seq'
        indexes = [
            models.Index(fields=['id_id']),
        ]

class gene_go(models.Model):
    id = models.BigAutoField(primary_key=True)
    id_id = models.IntegerField(default='0')
    #geneid_id=models.CharField(max_length=200,unique=False,default='0')
    #geneid = models.CharField(max_length=100, blank=True, null=True)
    #genome = models.IntegerField(default='0') 
    go_id = models.CharField(max_length=100, blank=True, null=True)
    #go_description = models.CharField(max_length=100, blank=True, null=True)
    #go_type = models.CharField(max_length=100, blank=True, null=True)
    def __str__(self):
        return str(self.geneid)
    class Meta:
        db_table = 'gene_go'
        indexes = [
            models.Index(fields=['id_id']),
        ]

class gene_kegg(models.Model):
    id = models.BigAutoField(primary_key=True)
    id_id = models.IntegerField(default='0')
    #geneid_id=models.CharField(max_length=200,unique=False,default='0')
    #geneid = models.CharField(max_length=100, blank=True, null=True)
    #genome = models.IntegerField(default='0') 
    kegg_id = models.CharField(max_length=100, blank=True, null=True)
    #kegg_description = models.CharField(max_length=100, blank=True, null=True)
    #kegg_type = models.CharField(max_length=100, blank=True, null=True)
    def __str__(self):
        return str(self.geneid)
    class Meta:
        db_table = 'gene_kegg'
        indexes = [
            models.Index(fields=['id_id']),
        ]


class SearchCache(models.Model):
    """比对结果缓存表"""
    seq_hash = models.CharField(max_length=32, primary_key=True, verbose_name="序列MD5")
    method = models.CharField(max_length=20, db_index=True, verbose_name="比对方法")
    result_json = models.JSONField(verbose_name="结果JSON数据")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table = "search_cache"
        verbose_name = "搜索缓存"

class  Genome_Synteny(models.Model):
    """基因组synteny表"""
    id = models.BigAutoField(primary_key=True)
    Ref_genome = models.IntegerField(default='0')
    Query_genome = models.IntegerField(default='0')
    
    Ref_genome_chr = models.CharField(max_length=100, blank=True, null=True)
    Ref_genome_start = models.IntegerField()
    Ref_genome_end = models.IntegerField()
    Ref_seq=models.TextField(blank=True, null=True)
    Alt_seq=models.TextField(blank=True, null=True)
    Query_genome_chr = models.CharField(max_length=100, blank=True, null=True)
    Query_genome_start = models.IntegerField(blank=True, null=True)
    Query_genome_end = models.IntegerField()
    Variation_type = models.CharField(max_length=100, blank=True, null=True)
    Parent_Variation=models.CharField(max_length=100, blank=True, null=True)
    son_type=models.CharField(max_length=100, blank=True, null=True)
    copygain=models.CharField(max_length=100, blank=True, null=True)
    def __str__(self):
        return self.Ref_genome_chr
    class Meta:
        db_table = 'genome_synteny'
        indexes = [
            models.Index(fields=['id']),
        ]


class GoTerm(models.Model):
    """GO术语模型，存储术语基本信息"""
    id = models.CharField(max_length=20, primary_key=True)  # GO ID（如GO:0008150）
    name = models.CharField(max_length=255, null=False)  # 术语名称
    definition = models.TextField()  # 术语定义
    namespace = models.CharField(
        max_length=50,
        choices=[
            ('biological_process', 'Biological Process'),
            ('molecular_function', 'Molecular Function'),
            ('cellular_component', 'Cellular Component')
        ],
        null=False
    )  # GO类型
    is_obsolete = models.BooleanField(default=False)  # 是否废弃
    comment = models.TextField(blank=True, null=True)  # 注释（可选）
    created_at = models.DateTimeField(auto_now_add=True)  # 创建时间
    updated_at = models.DateTimeField(auto_now=True)  # 更新时间

    class Meta:
        db_table = 'go_term'  # 对应MySQL表名
        verbose_name = 'GO Term'
        verbose_name_plural = 'GO Terms'

    def __str__(self):
        return self.name


class GoRelationship(models.Model):
    """GO关系模型，存储术语间的关系"""
    id = models.AutoField(primary_key=True)
    subject = models.ForeignKey(
        GoTerm,
        on_delete=models.CASCADE,
        related_name='subject_relationships'
    )
    object = models.ForeignKey(
        GoTerm,
        on_delete=models.CASCADE,
        related_name='object_relationships'
    )
    relationship_type = models.CharField(
        max_length=50,
        choices=[
            ('is_a', 'is_a'),
            ('part_of', 'part_of'),
            ('regulates', 'regulates'),
            ('negatively_regulates', 'negatively_regulates'),
            ('positively_regulates', 'positively_regulates'),
            ('replaced_by', 'replaced_by'),  # 新增：废弃术语的替代关系
            ('consider', 'consider')        # 新增：考虑的关系
        ],
        null=False
    )
    is_inferred = models.BooleanField(default=False)

    class Meta:
        db_table = 'go_relationship'
        verbose_name = 'GO Relationship'
        verbose_name_plural = 'GO Relationships'
        unique_together = ('subject', 'object', 'relationship_type')



class KOTerm(models.Model):
    """KO术语表 - 存储所有KO标识符及其基本信息"""
    ko_id = models.CharField(max_length=10, primary_key=True, verbose_name='KO ID')
    name = models.CharField(max_length=500, verbose_name='名称')
    ec_number = models.CharField(max_length=50, blank=True, null=True, verbose_name='EC编号')
    full_name = models.CharField(max_length=300, verbose_name='全称')
    is_enzyme = models.BooleanField(default=False, verbose_name='是否为酶')
    
    class Meta:
        db_table = 'ko_term'
        verbose_name = 'KO术语'
        verbose_name_plural = 'KO术语'
        indexes = [
            models.Index(fields=['ec_number']),
            models.Index(fields=['is_enzyme']),
        ]
    
    def __str__(self):
        return f"{self.ko_id} - {self.name}"


class MetabolicPathway(models.Model):
    """代谢通路表 - 存储代谢通路信息"""
    pathway_id = models.CharField(max_length=10, primary_key=True, verbose_name='通路ID')
    name = models.CharField(max_length=200, verbose_name='通路名称')
    full_name = models.CharField(max_length=300, verbose_name='通路全称')
    ko_id = models.CharField(max_length=10, verbose_name='关联KO ID')
    category = models.ForeignKey(
        'Category', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='pathways',
        verbose_name='所属分类'
    )
    
    class Meta:
        db_table = 'metabolic_pathway'
        verbose_name = '代谢通路'
        verbose_name_plural = '代谢通路'
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['ko_id']),
        ]
    
    def __str__(self):
        return f"{self.pathway_id} - {self.name}"


class PathwayEnzyme(models.Model):
    """通路-酶关联表 - 存储酶与代谢通路的多对多关系"""
    id = models.AutoField(primary_key=True)
    pathway = models.ForeignKey(
        MetabolicPathway, 
        on_delete=models.CASCADE, 
        related_name='enzymes',
        verbose_name='代谢通路'
    )
    enzyme = models.ForeignKey(
        KOTerm, 
        on_delete=models.CASCADE, 
        related_name='pathways',
        verbose_name='酶'
    )
    
    class Meta:
        db_table = 'pathway_enzyme'
        verbose_name = '通路-酶关联'
        verbose_name_plural = '通路-酶关联'
        unique_together = ('pathway', 'enzyme')
        indexes = [
            models.Index(fields=['pathway']),
            models.Index(fields=['enzyme']),
        ]
    
    def __str__(self):
        return f"{self.pathway.pathway_id} - {self.enzyme.ko_id}"


class ECNumber(models.Model):
    """EC编号表 - 存储酶分类编号"""
    ec_number = models.CharField(max_length=20, primary_key=True, verbose_name='EC编号')
    name = models.CharField(max_length=500, verbose_name='EC名称')
    
    class Meta:
        db_table = 'ec_number'
        verbose_name = 'EC编号'
        verbose_name_plural = 'EC编号'
    
    def __str__(self):
        return f"{self.ec_number} - {self.name}"


class Category(models.Model):
    """分类表 - 存储代谢通路分类"""
    category_id = models.CharField(max_length=10, primary_key=True, verbose_name='分类ID')
    name = models.CharField(max_length=500, verbose_name='分类名称')
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='children',
        verbose_name='父级分类'
    )
    
    class Meta:
        db_table = 'category'
        verbose_name = '分类'
        verbose_name_plural = '分类'
        indexes = [
            models.Index(fields=['parent']),
        ]
    
    def __str__(self):
        return f"{self.category_id} - {self.name}"
