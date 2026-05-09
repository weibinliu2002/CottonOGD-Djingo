from Bio import SeqIO
from BioSQL import BioSeqDatabase
import bcbio_gff as gffutils
import os

# 1. 连接数据库
server = BioSeqDatabase.open_database(
    driver="pymysql", # 如果是mysql用 pymysql
    user="root",
    password="1234",
    host="localhost",
    database="cottonogd-ortho" # 连接到包含biosql schema的数据库
)

# 2. 创建/选择一个命名空间
db = server["cottonogd-ortho"]

# 假设你的100个基因组放在一个文件夹里，结构如下：
# genome_1/
#   - genome.fa
#   - annotation.gff
#   - cds.fa
#   - protein.fa
genomes_dir = "/data/web/CottonOGD/OGD/backend/data/genome"

for genome_name in os.listdir(genomes_dir):
    genome_path = os.path.join(genomes_dir, genome_name)
    gff_file = os.path.join(genome_path, "annotation.gff")
    genome_fa = os.path.join(genome_path, "genome.fa")
    
    print(f"正在处理: {genome_name}")
    
    # 3. 使用 bcbio-gff 解析 GFF，建立内存数据库
    # 这一步会自动处理 GFF 中的 Parent/Child 层级关系
    gff_db = gffutils.create_db(
        gff_file, 
        dbfn=f":memory:", 
        force=True, 
        keep_order=True, 
        merge_strategy="merge",
        disable_infer_genes=True, # 防止它瞎猜基因结构
        disable_infer_transcripts=True
    )

    # 4. 解析全基因组 FASTA，并将 GFF 特征挂载上去
    # 注意：BioSQL 需要接收带有 features 的 SeqRecord
    seq_records = []
    for seq_record in SeqIO.parse(genome_fa, "fasta"):
        seq_id = seq_record.id
        
        # 从 gff_db 中提取该序列上的所有特征
        try:
            features = list(gff_db.features_of_type(seq_id))
        except:
            features = []
            
        # 将 gff 特征转换为 Biopython 的 SeqFeature 对象并附加到序列上
        # (这里需要写一个转换函数，把 gffutils 的 feature 转成 Bio.SeqFeature)
        # 为了简洁，这里示意核心逻辑：
        for gff_feature in features:
            biopython_feature = convert_gff_to_biopython_feature(gff_feature)
            seq_record.features.append(biopython_feature)
            
        seq_records.append(seq_record)

    # 5. 写入 BioSQL
    # db.load 会自动处理 bioentry, biosequence, seqfeature 及其关系的插入
    count = db.load(seq_records)
    print(f"成功导入 {count} 条染色体/Contig 序列及其注释")

# 6. 提交事务并关闭
server.commit()
server.close()


from Bio.SeqFeature import SeqFeature, FeatureLocation

def convert_gff_to_biopython_feature(gff_feature):
    # 处理位置
    start = gff_feature.start - 1 # GFF 是 1-based，Biopython 是 0-based
    end = gff_feature.end
    strand = 1 if gff_feature.strand == '+' else -1
    if gff_feature.strand == '.': strand = 0
    
    location = FeatureLocation(start, end, strand=strand)
    
    # 提取 qualifiers (ID, Name, Parent, product 等)
    qualifiers = dict(gff_feature.attributes)
    
    # 构建 Biopython Feature
    bp_feature = SeqFeature(
        location=location,
        type=gff_feature.featuretype, # 比如 "gene", "mRNA", "CDS"
        id=qualifiers.get("ID", [None])[0],
        qualifiers=qualifiers
    )
    return bp_feature
