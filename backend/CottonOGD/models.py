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


# ========== OrthoFinder 直系同源（Ortholog）表 ==========
# 数据来自 OrthoFinder 结果目录下的 Orthogroups/Orthogroups.tsv。
# 物种列已 100% 对齐 Species_info.name；基因 id 即 TranscriptMaster.transcriptid。
# 一对一/一对多/多对多的判定在查询时由各物种成员数实时计算，不落表。

class OrthofinderOrthogroup(models.Model):
    og_code = models.CharField(max_length=20, primary_key=True)  # 如 OG0000000
    gene_count = models.IntegerField(default=0)
    species_count = models.IntegerField(default=0)
    is_single_copy = models.BooleanField(default=False)

    class Meta:
        db_table = 'orthofinder_orthogroup'
        indexes = [models.Index(fields=['is_single_copy'])]

    def __str__(self):
        return self.og_code


class OrthofinderOgGene(models.Model):
    og_code = models.CharField(max_length=20, db_index=True)  # 组件 idx_og
    species = models.ForeignKey(
        Species_info, on_delete=models.CASCADE, to_field='name', db_column='species'
    )  # 物种头，对齐 Species_info.name
    geneid = models.CharField(max_length=200, db_index=True)  # OrthoFinder transcript id

    class Meta:
        db_table = 'orthofinder_og_gene'
        # 保证 (og_code, species, geneid) 唯一，避免重复导入
        constraints = [
            models.UniqueConstraint(
                fields=['og_code', 'species', 'geneid'], name='uk_og_species_gene'
            )
        ]

    def __str__(self):
        return f"{self.og_code}|{self.species_id}|{self.geneid}"


class OrthofinderDuplication(models.Model):
    """OrthoFinder 基因复制事件（来自 Gene_Duplication_Events/Duplications.tsv）。

    每行一个复制事件：某 OG、某物种树节点（分支）上、某基因树节点处的复制，
    把该分支的基因分成两组（Genes 1 / Genes 2）。
    Type ∈ {Terminal, Non-Terminal, Non-Terminal: STRIDE}。
    用于 tandem / wgd 端点，按 og_code 建索引实现 O(log n) 查询。
    """
    og_code = models.CharField(max_length=20, db_index=True)  # 组件 idx_og
    species_node = models.CharField(max_length=255)  # 复制发生的物种/分支，如 G.anomalumB1_HAU_v1
    gene_tree_node = models.CharField(max_length=64, blank=True, null=True)
    support = models.FloatField(blank=True, null=True)
    dup_type = models.CharField(max_length=32)  # Terminal / Non-Terminal / Non-Terminal: STRIDE
    genes1 = models.TextField(blank=True, default='')  # 逗号分隔的干净基因 id
    genes2 = models.TextField(blank=True, default='')  # 逗号分隔的干净基因 id

    class Meta:
        db_table = 'orthofinder_duplication'
        indexes = [models.Index(fields=['og_code', 'species_node'])]

    def __str__(self):
        return f"{self.og_code}|{self.species_node}|{self.dup_type}"


# ======================================================================
# 基因组结构变异（Genome SV）数据模型
#
# 设计依据：docs/Genome_SV_数据库设计说明.md
# SyRI 成对比较被纵向拆分：
#   - 结构重排（SR：SYN/INV/TRANS/INVTR/DUP/INVDP）→ SyriSR
#   - 序列级注释（SEQ：INS/DEL/CPG/CPL/HDR/TDM）   → SyriSeq
# 对齐注释（SYNAL/NOTAL 等）不落库。
# 群体 multi-sample VCF 单独成 B 域（Variant + 稀疏三表）。
# 短变异（SNP/短 Indel）明细不进库，仅登记文件台账 + 统计汇总。
#
# 惯例对齐：genome 引用沿用项目既有整数引用（Genome_Synteny.Ref_genome），
# 不建硬 FK；基因组维表为 species（name 唯一）。
# ======================================================================


class GenomePair(models.Model):
    """一次 SyRI 成对比较的批次锚点（幂等重跑靠它）。

    每个 (ref_genome_id, query_genome_id) 唯一。旧 genome_synteny 数据可保持
    genome_pair_id 为 NULL 向后兼容。
    """
    id = models.BigAutoField(primary_key=True)
    ref_genome_id = models.IntegerField(default=0)     # → species.id（整数引用，非硬 FK）
    query_genome_id = models.IntegerField(default=0)   # → species.id
    minimap2_params = models.CharField(max_length=255, blank=True, null=True)  # 如 asm5 --eqx
    syri_version = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=20, blank=True, null=True,
                              default='running')  # running/imported/verified/retired
    summary_json = models.JSONField(blank=True, null=True)  # syri.summary 结构化
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'genome_pair'
        constraints = [
            models.UniqueConstraint(
                fields=['ref_genome_id', 'query_genome_id'],
                name='uk_genome_pair_ref_query')
        ]
        indexes = [
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"pair({self.ref_genome_id}x{self.query_genome_id})"


class SyriSR(models.Model):
    """SyRI 结构重排（SR）：共线性块/倒位/易位/重复等。

    字段对齐 syri.out 12 列 + 设计稿 §1.1。ref/query 双向区间。
    """
    id = models.BigAutoField(primary_key=True)
    genome_pair_id = models.IntegerField(blank=True, null=True)  # → genome_pair.id（新数据带，旧 NULL）
    ref_genome_id = models.IntegerField(default=0)
    query_genome_id = models.IntegerField(default=0)
    ref_genome_chr = models.CharField(max_length=100, blank=True, null=True)
    ref_start = models.IntegerField()
    ref_end = models.IntegerField()
    ref_seq = models.TextField(blank=True, null=True)    # 结构变异通常为 '-'，可空
    alt_seq = models.TextField(blank=True, null=True)    # 插入序列（长序列截断存前 1kb + 全长标记）
    query_genome_chr = models.CharField(max_length=100, blank=True, null=True)
    query_start = models.IntegerField()
    query_end = models.IntegerField()
    event_id = models.CharField(max_length=100, blank=True, null=True)   # 第 9 列事件 ID，如 DUP100
    parent_event = models.CharField(max_length=100, blank=True, null=True)  # 第 10 列父事件 ID
    son_type = models.CharField(max_length=100, blank=True, null=True)  # 类型代码：SYN/INV/TRANS/DUP/...
    copygain = models.CharField(max_length=100, blank=True, null=True)  # 仅 DUP 类：copygain/copyloss
    sv_length = models.IntegerField(blank=True, null=True)  # 导入时算 ref_end-ref_start+1

    class Meta:
        db_table = 'syri_sr'
        indexes = [
            models.Index(fields=['genome_pair_id']),
            models.Index(fields=['ref_genome_id', 'query_genome_id', 'ref_genome_chr', 'son_type']),
            models.Index(fields=['query_genome_chr']),
            models.Index(fields=['son_type']),
        ]

    def __str__(self):
        return f"{self.ref_genome_chr}:{self.ref_start}-{self.ref_end}|{self.son_type}"


class SyriSeq(models.Model):
    """SyRI 序列级注释（SEQ）：插入/缺失/拷贝变化/高分化区/串联重复。

    与 SyriSR 同形但数据类别不同（HDR/TDM 等长序列需截断防表膨胀）。
    """
    id = models.BigAutoField(primary_key=True)
    genome_pair_id = models.IntegerField(blank=True, null=True)
    ref_genome_id = models.IntegerField(default=0)
    query_genome_id = models.IntegerField(default=0)
    ref_genome_chr = models.CharField(max_length=100, blank=True, null=True)
    ref_start = models.IntegerField()
    ref_end = models.IntegerField()
    ref_seq = models.TextField(blank=True, null=True)
    alt_seq = models.TextField(blank=True, null=True)    # 插入序列可很长，导入时截断
    query_genome_chr = models.CharField(max_length=100, blank=True, null=True)
    query_start = models.IntegerField()
    query_end = models.IntegerField()
    event_id = models.CharField(max_length=100, blank=True, null=True)
    parent_event = models.CharField(max_length=100, blank=True, null=True)
    son_type = models.CharField(max_length=100, blank=True, null=True)  # INS/DEL/CPG/CPL/HDR/TDM
    copygain = models.CharField(max_length=100, blank=True, null=True)
    sv_length = models.IntegerField(blank=True, null=True)

    class Meta:
        db_table = 'syri_seq'
        indexes = [
            models.Index(fields=['genome_pair_id']),
            models.Index(fields=['ref_genome_id', 'query_genome_id', 'ref_genome_chr', 'son_type']),
            models.Index(fields=['query_genome_chr']),
            models.Index(fields=['son_type']),
        ]

    def __str__(self):
        return f"{self.ref_genome_chr}:{self.ref_start}-{self.ref_end}|{self.son_type}"


class PopulationsInfo(models.Model):
    """群体维表（对齐 maizevarmap.populations_info）。"""
    population_id = models.PositiveIntegerField(primary_key=True)
    population = models.CharField(max_length=30)
    population_count = models.CharField(max_length=30)
    # 可选亚组（野生/地方种/栽培种），与 sample.population_group 对应
    population_group = models.CharField(max_length=30, blank=True, null=True)

    class Meta:
        db_table = 'populations_info'

    def __str__(self):
        return self.population


class VariationSet(models.Model):
    """一次群体 calling 的数据集（对应 maize 隐含的单参考 B73，此处显式化）。"""
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)  # 如 cotton_pan_sv_v1
    reference_genome = models.IntegerField(default=0)     # → species.id
    caller = models.CharField(max_length=100, blank=True, null=True)  # 工具+版本
    sample_count = models.IntegerField(blank=True, null=True)
    version = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'variation_set'

    def __str__(self):
        return self.name


class Sample(models.Model):
    """样本维表（矩阵的"列"，对齐 maizevarmap.samples）。"""
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)     # VCF 表头样本名
    population = models.CharField(max_length=30, blank=True, null=True)
    population_group_id = models.ForeignKey(
        PopulationsInfo, on_delete=models.SET_NULL, null=True,
        blank=True, db_column='population_group_id')
    species_id = models.IntegerField(blank=True, null=True)  # 若该材料同时有组装则互链 species.id
    source = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=30, blank=True, null=True)
    latitude = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    longitude = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    accession_id = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'sample'
        indexes = [models.Index(fields=['population'])]

    def __str__(self):
        return self.name


class Variant(models.Model):
    """群体变异位点主表（矩阵的"行"，对齐 maizevarmap *_variants，推广为通用）。

    chrom 冗余到子表做分片键；ref/alt 短变异 VARCHAR(1/4)，
    符号等位 <DEL> 与长插入序列用 TEXT（对齐设计稿 §2.5.2 第 3 点）。
    """
    id = models.BigAutoField(primary_key=True)
    set_id = models.BigIntegerField()                         # → variation_set.id
    chrom = models.CharField(max_length=50)                   # 冗余分片键
    pos = models.IntegerField()
    end_pos = models.IntegerField(blank=True, null=True)
    show_id = models.CharField(max_length=20, blank=True, null=True)  # 展示稳定 ID
    svtype = models.CharField(max_length=20, blank=True, null=True)   # DEL/INS/DUP/INV/BND/CNV
    svlen = models.IntegerField(blank=True, null=True)
    ref = models.CharField(max_length=4, blank=True, null=True)
    alt = models.TextField(blank=True, null=True)
    qual = models.FloatField(blank=True, null=True)
    filter = models.CharField(max_length=20, blank=True, null=True)
    info_json = models.JSONField(blank=True, null=True)

    class Meta:
        db_table = 'variant'
        indexes = [
            models.Index(fields=['set_id', 'chrom', 'pos']),
            models.Index(fields=['set_id', 'svtype']),
        ]
        constraints = [
            # 注：alt 为 TEXT（长插入序列/<DEL> 符号），MySQL 不支持在复合唯一键里
            # 直接索引 TEXT 列。去重靠导入时按 set_id 整集 DELETE+重载（设计稿 §5.2），
            # 故唯一约束收敛到 (set_id, chrom, pos, svtype)。
            models.UniqueConstraint(
                fields=['set_id', 'chrom', 'pos', 'svtype'],
                name='uk_variant_set_chrom_pos_type')
        ]

    def __str__(self):
        return f"{self.chrom}:{self.pos}|{self.svtype}"


class VariantGenotype(models.Model):
    """稀疏基因型表：只存非 0/0 的格子（对齐 maizevarmap *_genotypes）。"""
    id = models.BigAutoField(primary_key=True)
    chrom = models.CharField(max_length=50)        # 冗余分片键
    variant_id = models.BigIntegerField()          # → variant.id
    sample_id = models.IntegerField()              # → sample.id
    gt = models.PositiveSmallIntegerField()        # 1=杂合 2=纯合变异（0/0 不落库）
    copy_number = models.FloatField(blank=True, null=True)  # CNV 类可选

    class Meta:
        db_table = 'variant_genotype'
        indexes = [
            models.Index(fields=['chrom', 'sample_id']),
            models.Index(fields=['chrom', 'variant_id']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['chrom', 'variant_id', 'sample_id'],
                name='uk_variant_gt_chrom_var_sample')
        ]

    def __str__(self):
        return f"{self.chrom}|v{self.variant_id}|s{self.sample_id}"


class VariantPopulation(models.Model):
    """群体级 AC 预聚合表（对齐 maizevarmap *_populations，设计稿 §2.5.2 第 1 点）。

    频率/携带数查询免扫基因型大表；ac 存 JSON {ref:N, alt:M}。
    """
    id = models.BigAutoField(primary_key=True)
    chrom = models.CharField(max_length=50)        # 冗余分片键
    variant_id = models.BigIntegerField()          # → variant.id
    population_id = models.IntegerField()          # → populations_info.population_id
    ac = models.CharField(max_length=40, blank=True, null=True)  # {ref:N, alt:M} JSON

    class Meta:
        db_table = 'variant_population'
        indexes = [
            models.Index(fields=['chrom', 'variant_id']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['chrom', 'variant_id', 'population_id'],
                name='uk_variant_pop_chrom_var_pop')
        ]

    def __str__(self):
        return f"{self.chrom}|v{self.variant_id}|pop{self.population_id}"


class VariationFile(models.Model):
    """变异类文件台账：全库变异文件的唯一登记处（C 域数据管理抓手）。"""
    id = models.BigAutoField(primary_key=True)
    path = models.CharField(max_length=500, unique=True)  # 相对 backend/data/ 的路径
    category = models.CharField(max_length=30, blank=True, null=True)  # syri.out/syri.vcf.gz/snps.vcf.gz/pop_vcf
    ref_genome = models.IntegerField(blank=True, null=True)     # 成对文件填
    query_genome = models.IntegerField(blank=True, null=True)   # 成对文件填
    set_id = models.BigIntegerField(blank=True, null=True)      # 群体文件填
    tabix_ready = models.BooleanField(default=False)            # 是否已 bgzip+tabix
    md5 = models.CharField(max_length=64, blank=True, null=True)
    size = models.BigIntegerField(blank=True, null=True)
    status = models.CharField(max_length=20, blank=True, null=True,
                              default='pending')   # pending/indexed/imported/failed
    imported_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'variation_file'
        indexes = [models.Index(fields=['category'])]

    def __str__(self):
        return self.path


class SnpStat(models.Model):
    """统计汇总表（页面展示用，永远 <10 万行）。

    按 genome_pair 或 variation_set 汇总 SNP/Ins/Del/SV 计数 + 分 bin 密度。
    """
    id = models.BigAutoField(primary_key=True)
    subject_type = models.CharField(max_length=20, blank=True, null=True)  # genome_pair / variation_set
    subject_id = models.BigIntegerField(blank=True, null=True)
    population_id = models.IntegerField(blank=True, null=True)  # 可选按群体分层
    chrom = models.CharField(max_length=50, blank=True, null=True)  # 染色体或 'all'
    snp_count = models.IntegerField(blank=True, null=True)
    ins_count = models.IntegerField(blank=True, null=True)
    del_count = models.IntegerField(blank=True, null=True)
    sv_count = models.IntegerField(blank=True, null=True)
    density_json = models.JSONField(blank=True, null=True)  # 分 bin 密度（JBrowse histogram 直读）

    class Meta:
        db_table = 'snp_stat'
        indexes = [
            models.Index(fields=['subject_type', 'subject_id']),
            models.Index(fields=['chrom']),
        ]

    def __str__(self):
        return f"{self.subject_type}:{self.subject_id}|{self.chrom}"


# ======================================================================
# GWAS 数据模型
#
# 数据来源：cotton_Pan-genmone/snp2
#   - 890.hmp.biallele.vcf  (890 份 G. hirsutum 的 SNP 基因型)
#   - 419.CNV.MAF0.05.vcf   (419 份 G. hirsutum 的 CNV 基因型)
#   - 890Gh_Fiber_traits.txt (890 份材料的 5 个纤维性状 BLUP 值：FE/FL/FM/FS/FU)
#
# 设计：GWAS 的"基因型标记"复用 B 域 variant 表（各自 variation_set）；
# 表型 BLUP 值单独成 gwas_phenotype（trait × accession 稀疏）；
# gwas_association 预留给未来计算的关联结果（pvalue/effect/...），当前为空。
# ======================================================================


class GwasTrait(models.Model):
    """GWAS 性状元数据（FE/FL/FM/FS/FU 等纤维性状）。"""
    id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=20, unique=True)   # FE / FL / FM / FS / FU
    name = models.CharField(max_length=100, blank=True, null=True)  # 展示名
    unit = models.CharField(max_length=50, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'gwas_trait'

    def __str__(self):
        return f"{self.code}:{self.name}"


class GwasAccession(models.Model):
    """GWAS 群体中的材料（GWAS 基因型/表型的"列"）。

    与 B 域 sample 解耦：GWAS 材料命名（HBAU1...）与泛基因组样本
    （H84021...）不直接同名，单独建维表，便于 join 表型与基因型。
    """
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)       # HBAU1 ...
    species = models.CharField(max_length=50, blank=True, null=True)  # G. hirsutum
    population = models.CharField(max_length=50, blank=True, null=True)
    note = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'gwas_accession'
        indexes = [models.Index(fields=['species'])]

    def __str__(self):
        return self.name


class GwasPhenotype(models.Model):
    """性状 BLUP 值（accession × trait 稀疏矩阵，对齐 maize 思路）。"""
    id = models.BigAutoField(primary_key=True)
    accession_id = models.IntegerField()   # → gwas_accession.id
    trait_id = models.IntegerField()       # → gwas_trait.id
    value = models.FloatField(blank=True, null=True)

    class Meta:
        db_table = 'gwas_phenotype'
        indexes = [
            models.Index(fields=['trait_id', 'accession_id']),
            models.Index(fields=['accession_id']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['accession_id', 'trait_id'],
                name='uk_gwas_pheno_acc_trait')
        ]

    def __str__(self):
        return f"acc{self.accession_id}|trait{self.trait_id}={self.value}"


class GwasAssociation(models.Model):
    """GWAS 关联结果（预留：未来由 VCF+表型计算后写入，当前为空）。

    每 (chrom, pos, trait) 一个峰值：pvalue / effect / r2 / maf 等。
    """
    id = models.BigAutoField(primary_key=True)
    set_id = models.BigIntegerField(blank=True, null=True)     # → variation_set.id（标记集）
    trait_id = models.IntegerField()                           # → gwas_trait.id
    chrom = models.CharField(max_length=50)
    pos = models.IntegerField()
    variant_id = models.BigIntegerField(blank=True, null=True)  # 可回链到 variant
    ref = models.CharField(max_length=4, blank=True, null=True)
    alt = models.CharField(max_length=4, blank=True, null=True)
    pvalue = models.FloatField(blank=True, null=True)
    effect = models.FloatField(blank=True, null=True)
    r2 = models.FloatField(blank=True, null=True)
    maf = models.FloatField(blank=True, null=True)
    information_json = models.JSONField(blank=True, null=True)

    class Meta:
        db_table = 'gwas_association'
        indexes = [
            models.Index(fields=['trait_id', 'chrom', 'pos']),
            models.Index(fields=['trait_id', 'pvalue']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['chrom', 'pos', 'trait_id'],
                name='uk_gwas_assoc_chrom_pos_trait')
        ]

    def __str__(self):
        return f"{self.chrom}:{self.pos}|trait{self.trait_id}|p={self.pvalue}"
