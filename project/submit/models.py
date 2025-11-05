from django.db import models

# 数据提交模型，用于批量插入各种类型的数据
class SubmittedData(models.Model):
    # 数据类型选择
    DATA_TYPE_CHOICES = [
        ('gene', '基因序列'),
        ('annotation', '功能注释'),
        ('expression', '表达数据'),
        ('variation', '变异数据'),
        ('other', '其他数据'),
    ]
    
    # 基本字段
    data_name = models.CharField(max_length=255, verbose_name='数据名称')
    data_type = models.CharField(max_length=50, choices=DATA_TYPE_CHOICES, verbose_name='数据类型')
    description = models.TextField(blank=True, null=True, verbose_name='数据描述')
    
    # 关联信息
    gene_id = models.CharField(max_length=100, blank=True, null=True, verbose_name='关联基因ID')
    species_name = models.CharField(max_length=100, blank=True, null=True, verbose_name='物种名称')
    
    # 数据值
    data_value = models.TextField(blank=True, null=True, verbose_name='数据值')
    
    # 元数据和时间戳
    submitter = models.CharField(max_length=100, blank=True, null=True, verbose_name='提交者')
    reference = models.CharField(max_length=255, blank=True, null=True, verbose_name='参考文献')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '提交数据'
        verbose_name_plural = '提交数据'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.data_name} ({self.get_data_type_display()})"

# 批次提交记录模型
class BatchSubmission(models.Model):
    batch_name = models.CharField(max_length=255, verbose_name='批次名称')
    total_records = models.IntegerField(verbose_name='总记录数')
    success_count = models.IntegerField(verbose_name='成功插入数')
    error_count = models.IntegerField(verbose_name='失败数')
    submitter = models.CharField(max_length=100, blank=True, null=True, verbose_name='提交者')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='提交时间')
    error_log = models.TextField(blank=True, null=True, verbose_name='错误日志')
    
    class Meta:
        verbose_name = '批次提交记录'
        verbose_name_plural = '批次提交记录'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.batch_name} - {self.created_at}"
