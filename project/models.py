# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class AuthGroup(models.Model):
    name = models.CharField(unique=True, max_length=150)

    class Meta:
        managed = False
        db_table = 'auth_group'


class AuthGroupPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)
    permission = models.ForeignKey('AuthPermission', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_group_permissions'
        unique_together = (('group', 'permission'),)


class AuthPermission(models.Model):
    name = models.CharField(max_length=255)
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING)
    codename = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'auth_permission'
        unique_together = (('content_type', 'codename'),)


class AuthUser(models.Model):
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.IntegerField()
    username = models.CharField(unique=True, max_length=150)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.CharField(max_length=254)
    is_staff = models.IntegerField()
    is_active = models.IntegerField()
    date_joined = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'auth_user'


class AuthUserGroups(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_groups'
        unique_together = (('user', 'group'),)


class AuthUserUserPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    permission = models.ForeignKey(AuthPermission, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_user_permissions'
        unique_together = (('user', 'permission'),)


class Blastp(models.Model):
    gene_id = models.CharField(max_length=50)
    protein_id = models.CharField(unique=True, max_length=100)
    description = models.TextField(blank=True, null=True)
    sequence = models.TextField()
    file_source = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'blastp'


class CsvimportCsvimport(models.Model):
    id = models.BigAutoField(primary_key=True)
    model_name = models.CharField(max_length=255)
    field_list = models.TextField()
    upload_file = models.CharField(max_length=100)
    file_name = models.CharField(max_length=255)
    encoding = models.CharField(max_length=32)
    upload_method = models.CharField(max_length=50)
    error_log = models.TextField()
    import_date = models.DateField()
    import_user = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'csvimport_csvimport'


class CsvimportImportmodel(models.Model):
    id = models.BigAutoField(primary_key=True)
    numeric_id = models.PositiveIntegerField()
    natural_key = models.CharField(max_length=100)
    csvimport = models.ForeignKey(CsvimportCsvimport, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'csvimport_importmodel'


class DjangoAdminLog(models.Model):
    action_time = models.DateTimeField()
    object_id = models.TextField(blank=True, null=True)
    object_repr = models.CharField(max_length=200)
    action_flag = models.PositiveSmallIntegerField()
    change_message = models.TextField()
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'django_admin_log'


class DjangoContentType(models.Model):
    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'django_content_type'
        unique_together = (('app_label', 'model'),)


class DjangoMigrations(models.Model):
    id = models.BigAutoField(primary_key=True)
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_migrations'


class DjangoSession(models.Model):
    session_key = models.CharField(primary_key=True, max_length=40)
    session_data = models.TextField()
    expire_date = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_session'


class EgGoAnnotation(models.Model):
    chr = models.CharField(max_length=10)
    start = models.IntegerField()
    end = models.IntegerField()
    id = models.CharField(max_length=30)

    class Meta:
        managed = False
        db_table = 'eg_go_annotation'


class EgGoEnrichment(models.Model):
    query = models.CharField(max_length=30)
    go_id = models.CharField(max_length=10)
    description = models.CharField(max_length=160)
    gene_ontology = models.CharField(max_length=10, blank=True, null=True)
    dddd = models.CharField(max_length=10)

    class Meta:
        managed = False
        db_table = 'eg_go_enrichment'


class EgKegg(models.Model):
    query = models.CharField(max_length=30)
    match = models.CharField(max_length=10)
    description = models.CharField(max_length=60)

    class Meta:
        managed = False
        db_table = 'eg_kegg'


class Fpkm4(models.Model):
    gene_id = models.CharField(max_length=200)
    root = models.CharField(max_length=100, blank=True, null=True)
    stem = models.CharField(max_length=100, blank=True, null=True)
    cotyledon = models.CharField(max_length=100, blank=True, null=True)
    leaf = models.CharField(max_length=100, blank=True, null=True)
    pholem = models.CharField(max_length=100, blank=True, null=True)
    sepal = models.CharField(max_length=100, blank=True, null=True)
    bract = models.CharField(max_length=100, blank=True, null=True)
    petal = models.CharField(max_length=100, blank=True, null=True)
    anther = models.CharField(max_length=100, blank=True, null=True)
    stigma = models.CharField(max_length=100, blank=True, null=True)
    number_0_dpa_ovules = models.CharField(db_column='0_dpa_ovules', max_length=100, blank=True, null=True)  # Field renamed because it wasn't a valid Python identifier.
    number_3_dpa_fibers = models.CharField(db_column='3_dpa_fibers', max_length=100, blank=True, null=True)  # Field renamed because it wasn't a valid Python identifier.
    number_6_dpa_fibers = models.CharField(db_column='6_dpa_fibers', max_length=100, blank=True, null=True)  # Field renamed because it wasn't a valid Python identifier.
    number_9_dpa_fibers = models.CharField(db_column='9_dpa_fibers', max_length=100, blank=True, null=True)  # Field renamed because it wasn't a valid Python identifier.
    number_12_dpa_fibers = models.CharField(db_column='12_dpa_fibers', max_length=100, blank=True, null=True)  # Field renamed because it wasn't a valid Python identifier.
    number_15_dpa_fibers = models.CharField(db_column='15_dpa_fibers', max_length=100, blank=True, null=True)  # Field renamed because it wasn't a valid Python identifier.
    number_18_dpa_fibers = models.CharField(db_column='18_dpa_fibers', max_length=100, blank=True, null=True)  # Field renamed because it wasn't a valid Python identifier.
    number_21_dpa_fibers = models.CharField(db_column='21_dpa_fibers', max_length=100, blank=True, null=True)  # Field renamed because it wasn't a valid Python identifier.
    number_24_dpa_fibers = models.CharField(db_column='24_dpa_fibers', max_length=100, blank=True, null=True)  # Field renamed because it wasn't a valid Python identifier.
    dpa0 = models.CharField(max_length=100, blank=True, null=True)
    number_5_dpa_ovules = models.CharField(db_column='5_dpa_ovules', max_length=100, blank=True, null=True)  # Field renamed because it wasn't a valid Python identifier.
    number_10_dpa_ovules = models.CharField(db_column='10_dpa_ovules', max_length=100, blank=True, null=True)  # Field renamed because it wasn't a valid Python identifier.
    number_20_dpa_ovules = models.CharField(db_column='20_dpa_ovules', max_length=100, blank=True, null=True)  # Field renamed because it wasn't a valid Python identifier.
    seed = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'fpkm4'


class GoEnrichmentGoenrichmentresult(models.Model):
    id = models.BigAutoField(primary_key=True)
    input_genes = models.TextField()
    background_genes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField()
    results_json = models.JSONField()

    class Meta:
        managed = False
        db_table = 'go_enrichment_goenrichmentresult'


class HomeGeneSeq(models.Model):
    id = models.BigAutoField(primary_key=True)
    geneid = models.CharField(db_column='geneID', max_length=200)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'home_gene_seq'


class HomeGeneid(models.Model):
    id = models.BigAutoField(primary_key=True)
    geneid = models.CharField(db_column='geneID', max_length=200)  # Field name made lowercase.
    species = models.CharField(max_length=200)

    class Meta:
        managed = False
        db_table = 'home_geneid'


class HomeProtenSeq(models.Model):
    id = models.BigAutoField(primary_key=True)
    geneid = models.CharField(db_column='geneID', max_length=200)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'home_proten_seq'


class HomeSpecies(models.Model):
    id = models.BigAutoField(primary_key=True)
    species = models.CharField(max_length=200)
    genomes = models.CharField(max_length=200)
    source = models.CharField(db_column='Source', max_length=200)  # Field name made lowercase.
    urls = models.CharField(max_length=200)

    class Meta:
        managed = False
        db_table = 'home_species'


class Orthogroups(models.Model):
    col_0 = models.CharField(max_length=10)
    col_1 = models.TextField(blank=True, null=True)
    col_2 = models.TextField(blank=True, null=True)
    col_3 = models.TextField(blank=True, null=True)
    col_4 = models.TextField(blank=True, null=True)
    col_5 = models.TextField(blank=True, null=True)
    col_6 = models.TextField(blank=True, null=True)
    col_7 = models.TextField(blank=True, null=True)
    col_8 = models.TextField(blank=True, null=True)
    col_9 = models.TextField(blank=True, null=True)
    col_10 = models.TextField(blank=True, null=True)
    col_11 = models.TextField(blank=True, null=True)
    col_12 = models.TextField(blank=True, null=True)
    col_13 = models.TextField(blank=True, null=True)
    col_14 = models.TextField(blank=True, null=True)
    col_15 = models.TextField(blank=True, null=True)
    col_16 = models.TextField(blank=True, null=True)
    col_17 = models.TextField(blank=True, null=True)
    col_18 = models.TextField(blank=True, null=True)
    col_19 = models.TextField(blank=True, null=True)
    col_20 = models.TextField(blank=True, null=True)
    col_21 = models.TextField(blank=True, null=True)
    col_22 = models.TextField(blank=True, null=True)
    col_23 = models.TextField(blank=True, null=True)
    col_24 = models.TextField(blank=True, null=True)
    col_25 = models.TextField(blank=True, null=True)
    col_26 = models.TextField(blank=True, null=True)
    col_27 = models.TextField(blank=True, null=True)
    col_28 = models.TextField(blank=True, null=True)
    col_29 = models.TextField(blank=True, null=True)
    col_30 = models.TextField(blank=True, null=True)
    col_31 = models.TextField(blank=True, null=True)
    col_32 = models.TextField(blank=True, null=True)
    col_33 = models.TextField(blank=True, null=True)
    col_34 = models.TextField(blank=True, null=True)
    col_35 = models.TextField(blank=True, null=True)
    col_36 = models.TextField(blank=True, null=True)
    col_37 = models.TextField(blank=True, null=True)
    col_38 = models.TextField(blank=True, null=True)
    col_39 = models.TextField(blank=True, null=True)
    col_40 = models.TextField(blank=True, null=True)
    col_41 = models.TextField(blank=True, null=True)
    col_42 = models.TextField(blank=True, null=True)
    col_43 = models.TextField(blank=True, null=True)
    col_44 = models.TextField(blank=True, null=True)
    col_45 = models.TextField(blank=True, null=True)
    col_46 = models.TextField(blank=True, null=True)
    col_47 = models.TextField(blank=True, null=True)
    col_48 = models.TextField(blank=True, null=True)
    col_49 = models.TextField(blank=True, null=True)
    col_50 = models.TextField(blank=True, null=True)
    col_51 = models.TextField(blank=True, null=True)
    col_52 = models.TextField(blank=True, null=True)
    col_53 = models.TextField(blank=True, null=True)
    col_54 = models.TextField(blank=True, null=True)
    col_55 = models.TextField(blank=True, null=True)
    col_56 = models.TextField(blank=True, null=True)
    col_57 = models.TextField(blank=True, null=True)
    col_58 = models.TextField(blank=True, null=True)
    col_59 = models.TextField(blank=True, null=True)
    col_60 = models.TextField(blank=True, null=True)
    col_61 = models.TextField(blank=True, null=True)
    col_62 = models.TextField(blank=True, null=True)
    col_63 = models.TextField(blank=True, null=True)
    col_64 = models.TextField(blank=True, null=True)
    col_65 = models.TextField(blank=True, null=True)
    col_66 = models.TextField(blank=True, null=True)
    col_67 = models.TextField(blank=True, null=True)
    col_68 = models.TextField(blank=True, null=True)
    col_69 = models.TextField(blank=True, null=True)
    col_70 = models.TextField(blank=True, null=True)
    col_71 = models.TextField(blank=True, null=True)
    col_72 = models.TextField(blank=True, null=True)
    col_73 = models.TextField(blank=True, null=True)
    col_74 = models.TextField(blank=True, null=True)
    col_75 = models.TextField(blank=True, null=True)
    col_76 = models.TextField(blank=True, null=True)
    col_77 = models.TextField(blank=True, null=True)
    col_78 = models.TextField(blank=True, null=True)
    col_79 = models.TextField(blank=True, null=True)
    col_80 = models.TextField(blank=True, null=True)
    col_81 = models.TextField(blank=True, null=True)
    col_82 = models.TextField(blank=True, null=True)
    col_83 = models.TextField(blank=True, null=True)
    col_84 = models.TextField(blank=True, null=True)
    col_85 = models.TextField(blank=True, null=True)
    col_86 = models.TextField(blank=True, null=True)
    col_87 = models.TextField(blank=True, null=True)
    col_88 = models.TextField(blank=True, null=True)
    col_89 = models.TextField(blank=True, null=True)
    col_90 = models.TextField(blank=True, null=True)
    col_91 = models.TextField(blank=True, null=True)
    col_92 = models.TextField(blank=True, null=True)
    col_93 = models.TextField(blank=True, null=True)
    col_94 = models.TextField(blank=True, null=True)
    col_95 = models.TextField(blank=True, null=True)
    col_96 = models.TextField(blank=True, null=True)
    col_97 = models.TextField(blank=True, null=True)
    col_98 = models.TextField(blank=True, null=True)
    col_99 = models.TextField(blank=True, null=True)
    col_100 = models.TextField(blank=True, null=True)
    col_101 = models.TextField(blank=True, null=True)
    col_102 = models.TextField(blank=True, null=True)
    col_103 = models.TextField(blank=True, null=True)
    col_104 = models.TextField(blank=True, null=True)
    col_105 = models.TextField(blank=True, null=True)
    col_106 = models.TextField(blank=True, null=True)
    col_107 = models.TextField(blank=True, null=True)
    col_108 = models.TextField(blank=True, null=True)
    col_109 = models.TextField(blank=True, null=True)
    col_110 = models.TextField(blank=True, null=True)
    col_111 = models.TextField(blank=True, null=True)
    col_112 = models.TextField(blank=True, null=True)
    col_113 = models.TextField(blank=True, null=True)
    col_114 = models.TextField(blank=True, null=True)
    col_115 = models.TextField(blank=True, null=True)
    col_116 = models.TextField(blank=True, null=True)
    col_117 = models.TextField(blank=True, null=True)
    col_118 = models.TextField(blank=True, null=True)
    col_119 = models.TextField(blank=True, null=True)
    col_120 = models.TextField(blank=True, null=True)
    col_121 = models.TextField(blank=True, null=True)
    col_122 = models.TextField(blank=True, null=True)
    col_123 = models.TextField(blank=True, null=True)
    col_124 = models.TextField(blank=True, null=True)
    col_125 = models.TextField(blank=True, null=True)
    col_126 = models.TextField(blank=True, null=True)
    col_127 = models.TextField(blank=True, null=True)
    col_128 = models.TextField(blank=True, null=True)
    col_129 = models.TextField(blank=True, null=True)
    col_130 = models.TextField(blank=True, null=True)
    col_131 = models.TextField(blank=True, null=True)
    col_132 = models.TextField(blank=True, null=True)
    col_133 = models.TextField(blank=True, null=True)
    col_134 = models.TextField(blank=True, null=True)
    col_135 = models.TextField(blank=True, null=True)
    col_136 = models.TextField(blank=True, null=True)
    col_137 = models.TextField(blank=True, null=True)
    col_138 = models.TextField(blank=True, null=True)
    col_139 = models.TextField(blank=True, null=True)
    col_140 = models.TextField(blank=True, null=True)
    col_141 = models.TextField(blank=True, null=True)
    col_142 = models.TextField(blank=True, null=True)
    col_143 = models.TextField(blank=True, null=True)
    col_144 = models.TextField(blank=True, null=True)
    col_145 = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'orthogroups'


class PollsChoice(models.Model):
    id = models.BigAutoField(primary_key=True)
    choice_text = models.CharField(max_length=200)
    votes = models.IntegerField()
    question = models.ForeignKey('PollsQuestion', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'polls_choice'


class PollsQuestion(models.Model):
    id = models.BigAutoField(primary_key=True)
    question_text = models.CharField(max_length=200)
    pub_date = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'polls_question'


class ToolsGene(models.Model):
    id = models.BigAutoField(primary_key=True)
    gene_id = models.CharField(max_length=50)
    genome = models.CharField(max_length=50)
    orthogroup = models.ForeignKey('ToolsOrthogroup', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'tools_gene'
        unique_together = (('gene_id', 'genome'),)


class ToolsGenome(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(unique=True, max_length=100)
    version = models.CharField(max_length=50)

    class Meta:
        managed = False
        db_table = 'tools_genome'


class ToolsOrthogroup(models.Model):
    orthogroup_id = models.CharField(primary_key=True, max_length=20)

    class Meta:
        managed = False
        db_table = 'tools_orthogroup'
