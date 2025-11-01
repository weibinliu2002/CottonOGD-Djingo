import csv
from django.core.management.base import BaseCommand
from tools.models import Orthogroup, Gene, Genome

class Command(BaseCommand):
    help = '导入宽格式基因数据'

    def handle(self, *args, **options):
        csv_path = 'D:/ex/eg.csv'
        csv.field_size_limit(10 * 1024 * 1024)  # 设置字段大小限制
        
        with open(csv_path, encoding='utf-8-sig') as f:
            # 打印列名（调试用）
            sample = f.readline()
            f.seek(0)  # 重置文件指针
            print("文件列名：", sample.strip().split('\t'))  # 假设是制表符分隔
            
            # 正式读取CSV
            reader = csv.reader(f, delimiter='\t')  # 根据实际分隔符调整
            headers = [h.strip() for h in next(reader)]  # 读取列名
            
            # 查找Orthogroup列位置
            try:
                orthogroup_col = headers.index('Orthogroup')  # 注意大小写
            except ValueError:
                self.stderr.write(f"错误：未找到Orthogroup列，可用列名：{headers}")
                return
            
            # 开始处理数据
            for row in reader:
                if not row:  # 跳过空行
                    continue
                
                # 1. 处理Orthogroup
                ortho, _ = Orthogroup.objects.get_or_create(
                    orthogroup_id=row[orthogroup_col].strip()
                )
                
                # 2. 处理其他基因组列
                for col_idx, cell in enumerate(row):
                    if col_idx == orthogroup_col:  # 跳过Orthogroup列
                        continue
                        
                    # 2.1 解析基因组信息
                    genome_header = headers[col_idx]
                    if '_genome_' in genome_header:
                        genome_name = genome_header.split('_genome_')[0]
                        genome_version = genome_header.split('_genome_')[-1].split('.')[0]
                    else:
                        genome_name = genome_header
                        genome_version = 'v1'
                    
                    # 2.2 创建Genome记录
                    genome, _ = Genome.objects.get_or_create(
                        name=genome_name,
                        defaults={'version': genome_version}
                    )
                    
                    # 2.3 分割并导入基因ID
                    for gene_id in cell.split(','):
                        gene_id = gene_id.strip()
                        if gene_id:  # 跳过空值
                            Gene.objects.get_or_create(
                                gene_id=gene_id,
                                orthogroup=ortho,
                                genome=genome
                            )
                
                # 打印进度（每100行）
                if reader.line_num % 100 == 0:
                    self.stdout.write(f"已处理 {reader.line_num} 行...")
        
        self.stdout.write(self.style.SUCCESS(f'成功导入 {reader.line_num - 1} 条数据'))