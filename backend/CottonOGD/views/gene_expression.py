from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status
from CottonOGD.views.base import UuidManager
from CottonOGD.views.location_ID import Id_map
from CottonOGD.models import gene_expression, GenomeTissue
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
import json
import io ,re
import base64
import logging
from django.core.cache import cache
logger = logging.getLogger(__name__)

# 尝试导入Clustergrammer-PY
try:
    from clustergrammer import Network
    CLUSTERGRAMMER_AVAILABLE = True
except ImportError:
    CLUSTERGRAMMER_AVAILABLE = False
    logger.warning('Clustergrammer-PY not available, will use basic JSON format')

TISSUE_ORDER = [
    'Root', 'Stem', 'Cotyledon', 'Leaf', 'Pholem', 
    'Sepal', 'Bract', 'Petal', 'Anther', 'Stigma', 
    'Ovules', 'Fibers', 'Seed','武汉','海南','新疆'
]

# ===== 特殊排序规则 =====
STAGE_ORDER_MAP = {
    ('G.hirsutumAD1_TM-1_HAU_v1.1', '新疆'): [
        "m2_10","m2_14","m2_18","m2_22","m1_2","m1_6","m1_10","m1_14","m1_18","m1_22","0_2","0_6","0_10","0_14","0_18","0_22","1_2","1_6","1_10","1_14","1_18","1_22","2_2","2_6","2_10","2_14","2_18","2_22","3_2","3_6","3_10","3_14","3_18","3_22","4_2","4_6","4_10","4_14","4_18","4_22","5_2","5_6","5_10","5_14","5_18","5_22","6_2","6_6","6_10","6_14","6_18","6_22","7_2","7_6","7_10","7_14","7_18","7_22","8_2","8_6","8_10","8_14","8_18","8_22","9_2","9_6","9_10","9_14","9_18","9_22","10_2","10_6","10_10","10_14","10_18","10_22","11_2","11_6","11_10","11_14","11_18","11_22","12_2","12_6","12_10","12_14","12_18","12_22","13_2","13_6","13_10","13_14","13_18","13_22","14_2","14_6","14_10","14_14","14_18","14_22","15_2","15_6","15_10","15_14","15_18","15_22","16_2","16_6","16_10","16_14","16_18","16_22","17_2","17_6","17_10","17_14","17_18","17_22","18_2","18_6","18_10","18_14","18_18","18_22","19_2","19_6","19_10","19_14","19_18","19_22","20_2","20_6","20_10"
    ],
    
    ('G.hirsutumAD1_TM-1_HAU_v1.1', '武汉'): [
        "m2D08","m2D12","m2D16","m2D20","Nm1D00","Nm1D04","Nm1D08","Nm1D12","Nm1D16","Nm1D20","X0D00","X0D04","X0D08","X0D12","X0D16","X0D20","X1D00","X1D04","X1D08","X1D12","X1D16","X1D20","X2D00","X2D04","X2D08","X2D12","X2D16","X2D20","X3D00","X3D04","X3D08","X3D12","X3D16","X3D20","X4D00","X4D04","X4D08","X4D12","X4D16","X4D20","X5D00","X5D04","X5D08","X5D12","X5D16","X5D20","X6D00","X6D04","X6D08","X6D12","X6D16","X6D20","X7D00","X7D04","X7D08","X7D12","X7D16","X7D20","X8D00","X8D04","X8D08","X8D12","X8D16","X8D20","X9D00","X9D04","X9D08","X9D12","X9D16","X9D20","X10D00","X10D04","X10D08","X10D12","X10D16","X10D20","X11D00","X11D04","X11D08","X11D12","X11D16","X11D20","X12D00","X12D04","X12D08","X12D12","X12D16","X12D20","X13D00","X13D04","X13D08","X13D12","X13D16","X13D20","X14D00","X14D04","X14D08","X14D12","X14D16","X14D20","X15D00","X15D04","X15D08","X15D12","X15D16","X15D20","X16D00","X16D04","X16D08","X16D12","X16D16","X16D20","X17D00","X17D04","X17D08","X17D12","X17D16","X17D20","X18D00","X18D04","X18D08","X18D12","X18D16","X18D20","X19D00","X19D04","X19D08","X19D12","X19D16","X19D20","X20D00","X20D04","X20D08"
    ],
    
    ('G.hirsutumAD1_TM-1_HAU_v1.1', '海南'): [
        "m2-8","m2-12","m2-16","m2-20","m1-0","m1-4","m1-8","m1-12","m1-16","m1-20","0-0","0-4","0-8","0-12","0-16","0-20","1-0","1-4","1-8","1-12","1-16","1-20","2-0","2-4","2-8","2-12","2-16","2-20","3-0","3-4","3-8","3-12","3-16","3-20","4-0","4-4","4-8","4-12","4-16","4-20","5-0","5-4","5-8","5-12","5-16","5-20","6-0","6-4","6-8","6-12","6-16","6-20","7-0","7-4","7-8","7-12","7-16","7-20","8-0","8-4","8-8","8-12","8-16","8-20","9-0","9-4","9-8","9-12","9-16","9-20","10-0","10-4","10-8","10-12","10-16","10-20","11-0","11-4","11-8","11-12","11-16","11-20","12-0","12-4","12-8","12-12","12-16","12-20","13-0","13-4","13-8","13-12","13-16","13-20","14-0","14-4","14-8","14-12","14-16","14-20","15-0","15-4","15-8","15-12","15-16","15-20","16-0","16-4","16-8","16-12","16-16","16-20","17-0","17-4","17-8","17-12","17-16","17-20","18-0","18-4","18-8","18-12","18-16","18-20","19-0","19-4","19-8","19-12","19-16","19-20","20-0","20-4","20-8"
    ]
}

@api_view(['GET'])
def get_tissues(request):
    """
    获取指定基因组的组织类型列表
    """
    try:
        # 获取genome_id参数
        genome_id = request.query_params.get('genome_id')
        
        # 生成缓存键
        cache_key = f"tissues:{genome_id or 'all'}"
        
        # 尝试从缓存获取
        cached_tissues = cache.get(cache_key)
        if cached_tissues:
            return Response(cached_tissues, status=status.HTTP_200_OK)
        
     
        
        # 优化查询：只选择tissue字段，使用distinct()直接在数据库层面去重
        if genome_id:
            # 如果提供了genome_id，根据genome字段过滤
            tissues = GenomeTissue.objects.filter(genome=genome_id).values_list('tissue', flat=True).distinct()
        else:
            # 不提供genome_id时，获取所有tissue
            tissues = GenomeTissue.objects.values_list('tissue', flat=True).distinct()
        
        # 过滤空值
        tissues = [tissue for tissue in tissues if tissue]
        
        # 缓存结果，设置过期时间为1小时
        cache.set(cache_key, tissues, 3600 * 24 * 7)
        
        return Response(tissues, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error('Error getting tissues: %s', e)
        return Response([], status=status.HTTP_200_OK)

@api_view(['GET'])
def get_genomes_with_tissue(request):
    """
    获取genome_tissue表中所有唯一的genome_id列表
    """
    try:
        # 生成缓存键
        cache_key = "genomes_with_tissue"
        
        # 尝试从缓存获取
        cached_genomes = cache.get(cache_key)
        if cached_genomes:
            return Response(cached_genomes, status=status.HTTP_200_OK)
        
        # 从genome_tissue表中获取所有唯一的genome_id
        genomes = GenomeTissue.objects.values_list('genome', flat=True).distinct()
        # 过滤空值并转换为列表
        genome_list = [genome for genome in genomes if genome]
        
        # 缓存结果，设置过期时间为7天
        cache.set(cache_key, genome_list, 3600 * 24 * 7)
        
        return Response(genome_list, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error('Error getting genomes with tissue: %s', e)
        return Response([], status=status.HTTP_200_OK)

def get_sort_key(row):
    tissue = row['tissue']
    stage = row['stage'] if row['stage'] else ''
    try:
        tissue_idx = TISSUE_ORDER.index(tissue)
    except ValueError:
        tissue_idx = len(TISSUE_ORDER)
    return (tissue_idx, stage)

def generate_heatmap_image(numeric_data, gene_ids_list, selected_columns, config=None):
    # 默配置
    if config is None:
        config = {}
    
    # 提取配置参数
    low_color = config.get('low_color', '#0000FF')
    mid_color = config.get('mid_color', '#00FF00')
    high_color = config.get('high_color', '#FF0000')
    font_family = config.get('font_family', 'Arial')
    font_size = config.get('font_size', 12)
    use_log2 = config.get('use_log2', False)
    show_values = config.get('show_values', False)
    value_type = config.get('value_type', 'original')  # 'original' 或 'log2'
    color_range = config.get('color_range', None)  # None表示使用数据的最小最大值
    
    # 生成缓存键
    import hashlib
    # 将输入参数转换为字符串，用于生成缓存键
    input_str = f"{gene_ids_list}{selected_columns}{low_color}{mid_color}{high_color}{font_family}{font_size}{use_log2}{show_values}{value_type}{color_range}"
    # 添加数值数据的摘要，确保数据变化时缓存失效
    data_hash = hashlib.md5(str(numeric_data).encode()).hexdigest()
    cache_key = f"heatmap:{data_hash}:{hashlib.md5(input_str.encode()).hexdigest()}"
    
    # 尝试从缓存获取
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result
    
    # 处理rgb()格式的颜色
    def parse_color(color):
        if isinstance(color, str):
            # 处理rgb格式: rgb(0, 149, 255)
            if color.startswith('rgb('):
                try:
                    # 提取RGB值
                    rgb_values = color.replace('rgb(', '').replace(')', '').split(',')
                    r, g, b = [int(val.strip()) for val in rgb_values]
                    # 转换为十六进制格式
                    return f'#{r:02x}{g:02x}{b:02x}'
                except:
                    pass
            # 处理rgba格式: rgba(0, 149, 255, 1)
            elif color.startswith('rgba('):
                try:
                    # 提取RGBA值
                    rgba_values = color.replace('rgba(', '').replace(')', '').split(',')
                    r, g, b, a = [float(val.strip()) for val in rgba_values]
                    r = int(r)
                    g = int(g)
                    b = int(b)
                    # 转换为十六进制格式
                    return f'#{r:02x}{g:02x}{b:02x}'
                except:
                    pass
        return color
    
    # 解析颜色
    low_color = parse_color(low_color)
    mid_color = parse_color(mid_color)
    high_color = parse_color(high_color)
    
    # 创建DataFrame
    df = pd.DataFrame(numeric_data, index=gene_ids_list, columns=selected_columns)
    
    # 保存原始数据用于显示
    original_df = df.copy()
    
    # 如果启用log2转换，进行log2(x+1)转换
    if use_log2:
        df = np.log2(df + 1)
    
    # 根据value_type决定显示什么值，只有在使用log2转换且显示值时才生效
    if use_log2 and show_values and value_type == 'log2':
        # 显示log2转换后的值
        display_df = df
    else:
        # 默认显示原始值
        display_df = original_df
    
    # 设置图形大小
    # 计算合适的图形大小
    # 根据基因数量和组织数量动态调整
    num_genes = len(gene_ids_list)
    num_tissues = len(selected_columns)
    
    # 基础宽度和高度
    base_width = max(12, num_tissues * 0.8)  # 每个组织至少0.8英寸，减少宽度
    base_height = max(5, num_genes * 0.4)    # 每个基因至少0.4英寸，减少高度
    
    # 限制最大大小，避免内存问题
    max_width = 20  # 进一步减小最大宽度
    max_height = 15  # 进一步减小最大高度
    
    fig_width = min(base_width, max_width)
    fig_height = min(base_height, max_height)
    
    # 创建自定义颜色映射
    from matplotlib.colors import LinearSegmentedColormap
    colors = [low_color, mid_color, high_color]
    n_bins = 100
    cmap = LinearSegmentedColormap.from_list('custom', colors, N=n_bins)
    
    # 创建图形和轴
    f, ax = plt.subplots(figsize=(fig_width, fig_height))
    
    # 设置字体
    plt.rcParams['font.family'] = font_family
    plt.rcParams['font.size'] = font_size
    
    # 计算颜色范围
    if color_range:
        vmin, vmax = color_range
    else:
        vmin = df.values.min()
        vmax = df.values.max()
    
    # 使用seaborn绘制热图，添加数值显示（仅当数据量适中时）
    annot = False
    fmt = '.2f'
    
    # 通过show_values参数决定是否显示数值
    if show_values:
        annot = True
    
    # 绘制热图
    # 如果需要显示数值，使用display_df作为annot的数据源
    annot_data = display_df if show_values else False
    
    ax = sns.heatmap(df, 
                    cmap=cmap,
                    vmin=vmin, 
                    vmax=vmax,
                    xticklabels=True, 
                    yticklabels=True, 
                    cbar_kws={'label': 'Log2(FPKM+1)' if use_log2 else 'FPKM'},
                    annot=annot_data,  # 显示数值（使用display_df作为数据源）
                    fmt=fmt,  # 数值格式，保留2位小数
                    linewidths=.5,  # 网格线宽度
                    ax=ax)  # 指定轴
    
    # 设置x轴标签旋转和字体大小
    ax.set_xticklabels(ax.get_xticklabels(), rotation=60, ha='right', fontsize=font_size)
    ax.set_yticklabels(ax.get_yticklabels(), fontsize=font_size)
    
    # 设置标题
    title = 'Gene Expression Heatmap'
    if use_log2:
        title += ' (Log2 Transformed)'
    ax.set_title(title, fontsize=font_size + 2)
    
    # 调整布局
    plt.tight_layout()
    
    # 将图形转换为base64字符串，降低DPI提高速度
    with io.BytesIO() as buffer:
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')  # 降低DPI从150到100
        buffer.seek(0)
        # 转换为base64
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close()
    
    # 保存到缓存，设置过期时间为1小时
    cache.set(cache_key, image_base64, 3600)
    
    return image_base64


@api_view(['POST'])
def extract_expression(request):
    if request.method == 'POST':
        '''
        uuid = request.headers.get('uuid')
        if not uuid or uuid not in UuidManager.uuid_storage:
            return Response({'error': 'uuid is required'}, status=status.HTTP_400_BAD_REQUEST)
        db_id = request.data.get('db_id')'''
        db_id  = request.data.get('db_id') or request.query_params.get('db_id')
        if not db_id:
             # 从多个来源获取 gene_id：请求体、查询参数
            gene_id = request.data.get('gene_id') or request.query_params.get('gene_id')
            genome_id = request.data.get('genome_id') or request.query_params.get('genome_id')
            logger.info(f"genome_id: {genome_id}, gene_id: {gene_id}")
            
            # 检查gene_id和genome_id是否都有值
            if not gene_id or not genome_id:
                return Response({'error': 'gene_id and genome_id are required when db_id is not provided'}, status=status.HTTP_400_BAD_REQUEST)
                
            id_map_result = Id_map(gene_id, genome_id)
            
            # 从 id_map_result 中提取 db_id 值
            db_id = []
            if isinstance(id_map_result, dict):
                for gid, info in id_map_result.items():
                    if info.get('db_id'):
                        db_id.append(info['db_id'])
            logger.info(f"Extracted db_id: {db_id}")
        if isinstance(db_id, str):
            # 如果是逗号分割的字符串，分割并转换为整数
            db_id = db_id.split(',')
        
        # 确保 db_id 是一个列表
        if not isinstance(db_id, list):
            db_id = [db_id]
        
        # 尝试将每个值转换为整数
        converted_db_id = []
        for id_value in db_id:
            try:
                converted_id = int(float(id_value))
                logger.info(f"Converted db_id value: {converted_id}")
                converted_db_id.append(converted_id)
            except (ValueError, TypeError):
                # 跳过无法转换为整数的值
                logger.warning(f"Invalid db_id value skipped: {id_value}")
        
        db_id = converted_db_id
        
        if not db_id:
            return Response({'error': 'db_id must contain valid integers'}, status=status.HTTP_400_BAD_REQUEST)

        tissues = request.data.get('tissue') or request.query_params.get('tissue')
        if tissues:
            tissues = tissues.split(',')
        # 当tissue参数为空时，提取所有组织的表达量
        if tissues:
            gene_expr=gene_expression.objects.filter(id_id__in=db_id, tissue__in=tissues).values('id_id','geneid','stage','tissue','value')
        else:
            gene_expr=gene_expression.objects.filter(id_id__in=db_id).values('id_id','geneid','stage','tissue','value')
        df = pd.DataFrame(list(gene_expr))
        
        # 处理空值
        df['stage'] = df['stage'].fillna('')
        df['tissue'] = df['tissue'].fillna('Unknown')
        
        # 构建sample列名，处理空stage的情况
        df['sample'] = df.apply(lambda row: 
            re.sub(r'^X(\d+)', r'\1', row['stage']) + row['tissue'] if row['stage'] else row['tissue'], 
            axis=1
        )
        genome_id = request.data.get('genome_id') or request.query_params.get('genome_id')

        # 判断是否命中特殊排序
        custom_order = None
        if tissues and len(tissues) == 1:
            key = (genome_id, tissues[0])
            if key in STAGE_ORDER_MAP:
                custom_order = STAGE_ORDER_MAP[key]
        # 对数据进行排序：先按组织，再按时期（数字顺序）
        # 添加组织索引列用于排序
        df['tissue_idx'] = df['tissue'].apply(lambda x: TISSUE_ORDER.index(x) if x in TISSUE_ORDER else len(TISSUE_ORDER))
        # 从stage中提取数字部分用于排序
        #df['stage_num'] = df['stage'].str.extract(r'(\d+)').astype(float).fillna(0)
        # 按组织索引和时期数字排序
        #df = df.sort_values(by=['tissue_idx', 'stage_num'], ascending=[True, True])
       #genome_id = request.data.get('genome_id') or request.query_params.get('genome_id')

        def get_stage_order(row):
            key = (genome_id, row['tissue'])
            
            if key in STAGE_ORDER_MAP:
                order_list = STAGE_ORDER_MAP[key]
                order_dict = {stage: i for i, stage in enumerate(order_list)}
                return order_dict.get(row['stage'], len(order_list))
            
            # fallback：默认规则
            match = re.search(r'(\d+)', str(row['stage']))
            return int(match.group(1)) if match else 9999

        # 👇 每一行按“各自tissue规则”算排序值
        df['stage_order'] = df.apply(get_stage_order, axis=1)

        # 👇 排序
        df = df.sort_values(by=['tissue_idx', 'stage_order'], ascending=[True, True])
        # 直接使用pivot_table，不创建中间副本
        result = df.pivot_table(
            index=['id_id', 'geneid'],  # 保持不变的ID列
            columns='sample',               # stage_tissue 组合成列名
            values='value',                 # 表达量作为值
            aggfunc='mean'                  # 如果有重复值，取平均（可选：'first', 'sum'）
        ).reset_index()
        result.columns.name = None
        
        # 确保列的顺序也是按照排序后的顺序
        sample_order = df['sample'].unique()
        existing_columns = [col for col in sample_order if col in result.columns]
        id_columns = ['id_id', 'geneid']
        result = result[id_columns + existing_columns]
       
        # 准备前端需要的数据格式
        genes_data = []
        tissues = existing_columns
        
        for _, row in result.iterrows():
            gene_data = {
                'gene_id': row['geneid'],
                'expression': {}
            }
            for tissue in tissues:
                gene_data['expression'][tissue] = float(row[tissue]) if pd.notna(row[tissue]) else 0
            genes_data.append(gene_data)
        # 生成热图
        # 计算数据范围
        numeric_values = result.drop(columns=['id_id', 'geneid']).values
        data_min = numeric_values.min()
        data_max = numeric_values.max()
        
        # 生成热图，使用默认配置
        heatmap_image = generate_heatmap_image(
            numeric_data=numeric_values,
            gene_ids_list=result['geneid'].tolist(),
            selected_columns=result.columns[2:],  # 从第3列开始是样本列
            config={
                'use_log2': False  # 明确设置不使用log转换
            }
        )
        # 使用Clustergrammer-PY生成可视化JSON（如果可用）
        if CLUSTERGRAMMER_AVAILABLE:
            try:
                net = Network()
                # 转换数据为Clustergrammer格式
                for _, row in result.iterrows():
                    gene_id = row['geneid']
                    for tissue in tissues:
                        value = float(row[tissue]) if pd.notna(row[tissue]) else 0
                        net.add_row(gene_id, tissue, value)
                
                # 聚类数据
                net.make_clust()
                
                # 获取可视化JSON
                clustergrammer_json = net.export_net_json()
                
                return Response({
                    'expression': result.to_dict(orient='records'),
                    'genes': genes_data,
                    'tissues': tissues,
                    'clustergrammer_data': clustergrammer_json,
                    'heatmap_image': heatmap_image,
                    
                }, status=status.HTTP_200_OK)
            except Exception as e:
                logger.error('Error generating Clustergrammer JSON: %s', e)
                # 如果生成失败，返回基本格式
                return Response({
                    'expression': result.to_dict(orient='records'),
                    'genes': genes_data,
                    'tissues': tissues,
                  
                    'heatmap_image': heatmap_image,
                }, status=status.HTTP_200_OK)
        else:
            # Clustergrammer-PY不可用时，返回基本格式
            return Response({
                'expression': result.to_dict(orient='records'),
                'genes': genes_data,
                'tissues': tissues,
                'heatmap_image': heatmap_image,
            }, status=status.HTTP_200_OK)
@api_view(['POST'])
def regenerate_heatmap(request):
    """
    根据前端配置重新生成热图
    """
    try:
        # 获取请求数据
        genes = request.data.get('genes', [])
        tissues = request.data.get('tissues', [])
        config = request.data.get('config', {})
        
        if not genes or not tissues:
            return Response({
                'success': False,
                'error': 'Genes and tissues data are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 准备数据
        gene_ids_list = []
        numeric_data = []
        
        for gene in genes:
            gene_id = gene.get('gene_id')
            expression = gene.get('expression', {})
            
            if gene_id:
                gene_ids_list.append(gene_id)
                row_data = []
                for tissue in tissues:
                    value = expression.get(tissue, 0)
                    row_data.append(value)
                numeric_data.append(row_data)
        
        # 使用通用的generate_heatmap_image函数生成热图
        image_base64 = generate_heatmap_image(
            numeric_data=numeric_data,
            gene_ids_list=gene_ids_list,
            selected_columns=tissues,
            config=config
        )
        
        return Response({
            'success': True,
            'image': image_base64
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f'Error regenerating heatmap: {str(e)}', exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)