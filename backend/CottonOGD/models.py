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
    # Metadata supplied by the submitter; genome_size/LAI/BUSCO stay on the
    # legacy columns and are always filled from computed QC results.
    common_name = models.CharField(max_length=255, blank=True, null=True, verbose_name='通用名')
    assembly_version = models.CharField(max_length=100, blank=True, null=True, verbose_name='组装版本')
    annotation_version = models.CharField(max_length=100, blank=True, null=True, verbose_name='注释版本')
    submitter = models.CharField(max_length=255, blank=True, null=True, verbose_name='提交者')
    
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


class SpeciesLiterature(models.Model):
    """Per-species literature list (replaces the single Article field)."""
    species = models.ForeignKey(
        Species_info, on_delete=models.CASCADE, to_field='name',
        db_column='species_id', related_name='literature')
    title = models.TextField()
    authors = models.TextField(blank=True, null=True)
    journal = models.CharField(max_length=255, blank=True, null=True)
    year = models.IntegerField(blank=True, null=True)
    doi = models.CharField(max_length=255, blank=True, null=True)
    url = models.TextField(blank=True, null=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'species_literature'
        indexes = [models.Index(fields=['species'])]


class SpeciesQC(models.Model):
    """Detailed QC values for one annotation version.

    `species.Genome_size/LAI_value/Busco` remain the fast-access summary
    columns; this table keeps the full counts and raw report.
    """
    species = models.ForeignKey(
        Species_info, on_delete=models.CASCADE, to_field='name',
        db_column='species_id', related_name='qc_records')
    annotation_version = models.CharField(max_length=100)
    genome_size = models.BigIntegerField(blank=True, null=True)
    lai = models.DecimalField(max_digits=8, decimal_places=4, blank=True, null=True)
    busco_complete = models.IntegerField(blank=True, null=True)
    busco_single = models.IntegerField(blank=True, null=True)
    busco_duplicated = models.IntegerField(blank=True, null=True)
    busco_fragmented = models.IntegerField(blank=True, null=True)
    busco_missing = models.IntegerField(blank=True, null=True)
    busco_total = models.IntegerField(blank=True, null=True)
    busco_lineage = models.CharField(max_length=100, blank=True, null=True)
    busco_fraction = models.FloatField(blank=True, null=True)
    te_content_pct = models.FloatField(blank=True, null=True)
    ltr_count = models.IntegerField(blank=True, null=True)
    intact_ltr_count = models.IntegerField(blank=True, null=True)
    qc_json = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'species_qc'
        constraints = [
            models.UniqueConstraint(fields=['species', 'annotation_version'],
                                    name='species_qc_version')
        ]
        indexes = [models.Index(fields=['species'])]


class SpeciesUploadState(models.Model):
    """Idempotency/audit record for the unified uploader."""
    species = models.ForeignKey(
        Species_info, on_delete=models.CASCADE, to_field='name',
        db_column='species_id', related_name='upload_states')
    annotation_version = models.CharField(max_length=100)
    genome_sha256 = models.CharField(max_length=64, blank=True, null=True)
    gff_sha256 = models.CharField(max_length=64, blank=True, null=True)
    status = models.CharField(max_length=20, default='pending')
    conflict_policy = models.CharField(max_length=20, default='skip')
    upload_report = models.JSONField(blank=True, null=True)
    uploader = models.CharField(max_length=100, blank=True, null=True)
    uploaded_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'species_upload_state'
        constraints = [
            models.UniqueConstraint(fields=['species', 'annotation_version'],
                                    name='species_upload_version')
        ]
        indexes = [models.Index(fields=['species'])]


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

class TranscriptMaster(models.Model):
    id = models.BigAutoField(primary_key=True)
    id_id = models.IntegerField(default='0')
    transcriptid = models.CharField(max_length=200,unique=False)
    genome = models.ForeignKey(Species_info, on_delete=models.CASCADE, to_field='id')
    class Meta:
        db_table = 'transcriptmaster'  # 确保表名与导入数据匹配
        constraints = [
            models.UniqueConstraint(fields=['genome','transcriptid'], name='genome_transcript')
        ]
        indexes = [
            models.Index(fields=['transcriptid']),
            models.Index(fields=['genome']),
        ]
    def save(self, *args, **kwargs):
        # 自动生成 alias
        self.alias = f"{self.genome_id}::{self.transcriptid}"
        super().save(*args, **kwargs)
    def __str__(self):
        return f"{self.genome.name}:{self.transcriptid}"

class Family(models.Model):
    id = models.OneToOneField(GeneMaster, on_delete=models.CASCADE, to_field='id',primary_key=True)
    
    # 关联 GeneMaster 的字段（新增）
    geneid=models.CharField(max_length=200,blank=True, null=True)
    genome = models.ForeignKey(Species_info, on_delete=models.CASCADE, to_field='id') 
    TF_class = models.CharField(db_column='TF_class', max_length=100)  # Field name made lowercase in DB
    class_name=models.CharField(db_column='class_name', max_length=100)  
    TF_name = models.CharField(db_column='TF_name', max_length=100)  # Field name made lowercase in DB

    class Meta:
        db_table = 'genefamily'  # 指定数据库中实际存在的表名
        indexes = [
            models.Index(fields=['geneid','genome','id_id',]),           
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
    #geneid_id=models.CharField(max_length=200,unique=False,default='0')
    #parent_id=models.CharField(max_length=200,unique=False,default='0')
    genome = models.ForeignKey(Species_info, on_delete=models.CASCADE, to_field='id') 
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
            models.Index(fields=['seqid','start','end'], name='idx_seqid_start_end'),
        ]
    def __str__(self):
        return self.geneid.geneid


class AnnotationSource(models.Model):
    """表1：注释来源类型表（如 uniprot, interproscan, eggnog, pfam 等）"""
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)  # 如 'uniprot', 'interproscan'
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'annotation_source'
    
    def __str__(self):
        return self.name


class AnnotationDetail(models.Model):
    """表2：注释详细信息表（通过 source_id 关联表1）"""
    id = models.BigAutoField(primary_key=True)
    source = models.ForeignKey(AnnotationSource, on_delete=models.CASCADE, related_name='details')
    annotation_id = models.CharField(max_length=100)  # 如 UniProt ID, PFAM ID, GO ID 等
    description = models.TextField(blank=True, null=True)
    
    # UniProt专用字段
    protein_name = models.TextField(blank=True, null=True)  # 蛋白名称
    gene_name = models.CharField(max_length=200, blank=True, null=True)  # 基因名
    species = models.CharField(max_length=500, blank=True, null=True)  # 物种
    ox = models.IntegerField(blank=True, null=True)  # OX号
    pe = models.IntegerField(blank=True, null=True)  # PE号
    sv = models.IntegerField(blank=True, null=True)  # SV号
    full_header = models.TextField(blank=True, null=True)  # 完整header
    
    # Pfam/SMART等结构域数据库字段
    accession = models.CharField(max_length=50, blank=True, null=True)  # 如 PF00001.20
    pfam_type = models.CharField(max_length=20, blank=True, null=True)  # Family, Domain, Repeat等
    clan = models.CharField(max_length=20, blank=True, null=True)  # 家族分类
    model_length = models.IntegerField(blank=True, null=True)  # 模型长度
    gathering_threshold = models.FloatField(blank=True, null=True)  # 聚集阈值
    
    # eggNOG字段
    cog_category = models.CharField(max_length=50, blank=True, null=True)  # COG/KOG类别
    cog_class = models.CharField(max_length=50, blank=True, null=True)  # 功能类别
    eggnog_og = models.CharField(max_length=50, blank=True, null=True)  # eggNOG orthologous group
    
    other_info = models.JSONField(blank=True, null=True)  # 存储其他相关信息，如 evalue, score, interpro_match 等
    
    class Meta:
        db_table = 'annotation_detail'
        unique_together = [['source', 'annotation_id']]
        indexes = [
            models.Index(fields=['source', 'annotation_id']),
            models.Index(fields=['gene_name']),
            models.Index(fields=['species']),
            models.Index(fields=['accession']),
            models.Index(fields=['clan']),
        ]
    
    def __str__(self):
        return f"{self.source.name}:{self.annotation_id}"


class gene_annotation(models.Model):
    """表3：基因注释关联表（只存储关联关系，节省空间）"""
    id = models.BigAutoField(primary_key=True)
    id_id = models.ForeignKey(GeneMaster, on_delete=models.CASCADE, to_field='id',db_column='id_id', null=True)
    genome = models.ForeignKey(Species_info, on_delete=models.CASCADE, to_field='id', null=True)
    source = models.ForeignKey(AnnotationSource, on_delete=models.CASCADE, to_field='id', null=True)
    annotation_detail = models.ForeignKey(AnnotationDetail, on_delete=models.CASCADE, null=True)
    
    class Meta:
        db_table = 'gene_annotation'
        indexes = [
            models.Index(fields=['id_id']),
            models.Index(fields=['source']),
            models.Index(fields=['annotation_detail']),
        ]
    
    def __str__(self):
        return f"{self.id_id}:{self.source.name if self.source else 'None'}"

class gene_seq(models.Model):
    id = models.BigAutoField(primary_key=True)
    id_id = models.IntegerField(default='0')
    tr_id = models.CharField(max_length=100, blank=True, null=True)
    #geneid_id=models.CharField(max_length=200,unique=False,default='0')
    genome = models.ForeignKey(Species_info, on_delete=models.CASCADE, to_field='id') 
    mrna_id = models.CharField(max_length=100, blank=True, null=True)
    gene_type = models.CharField(max_length=100, blank=True, null=True)
    sequence = models.TextField(blank=True, null=True)
    def __str__(self):
        return f"{self.mrna_id}:{self.gene_type}"
    class Meta:
        db_table = 'gene_seq'
        indexes = [
            models.Index(fields=['id_id']),
        ]

class gene_go(models.Model):
    id = models.BigAutoField(primary_key=True)
    id_id = models.ForeignKey(GeneMaster, on_delete=models.CASCADE, to_field='id',db_column='id_id', null=True)
    #geneid_id=models.CharField(max_length=200,unique=False,default='0')
    #geneid = models.CharField(max_length=100, blank=True, null=True)
    #genome = models.IntegerField(default='0') 
    go_id = models.ForeignKey(
        'GoTerm', 
        on_delete=models.SET_NULL, 
        to_field='id',
        blank=True, 
        null=True,
        db_column='go_id'
    )
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
    id_id = models.ForeignKey(GeneMaster, on_delete=models.CASCADE, to_field='id',db_column='id_id', null=True)
    #geneid_id=models.CharField(max_length=200,unique=False,default='0')
    #geneid = models.CharField(max_length=100, blank=True, null=True)
    #genome = models.IntegerField(default='0') 
    kegg_id = models.ForeignKey(
        'KOTerm', 
        on_delete=models.SET_NULL, 
        to_field='ko_id',
        blank=True, 
        null=True,
        db_column='kegg_id'
    )
    pathway = models.ForeignKey(
        'MetabolicPathway', 
        on_delete=models.SET_NULL, 
        to_field='pathway_id',
        blank=True, 
        null=True,
        db_column='pathway_id',
        verbose_name='KEGG通路'
    )
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
