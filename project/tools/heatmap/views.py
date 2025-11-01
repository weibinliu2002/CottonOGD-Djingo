import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
import io
import base64
from django.shortcuts import render
from django.http import HttpResponse

def heatmap(request):
    if request.method == 'POST':
        # 获取用户输入的表格数据
        table_data = request.POST.get('table_data', '')
        
        try:
            # 处理数据并生成热图
            img_data = generate_heatmap(table_data)
            
            # 将图像数据传递给模板
            context = {
                'heatmap_image': img_data,
                'original_data': table_data
            }
            return render(request, 'tools/result.html', context)
            
        except Exception as e:
            error_msg = f"处理数据时出错: {str(e)}"
            return render(request, 'tools/input.html', {'error': error_msg, 'original_data': table_data})
    
    # GET请求显示输入表单
    return render(request, 'tools/input.html')

def generate_heatmap(table_data):
    # 将文本数据转换为DataFrame
    lines = [line.split('\t') for line in table_data.split('\n') if line.strip()]
    
    # 确保数据有效
    if len(lines) < 2:
        raise ValueError("输入数据格式不正确")
    
    # 第一行是表头
    headers = [h.strip() for h in lines[0]]
    data_rows = lines[1:]
    
    # 创建DataFrame
    df = pd.DataFrame(data_rows, columns=headers)
    
    # 设置gene_id为索引
    df.set_index(headers[0], inplace=True)
    
    # 转换数据类型并处理NA值
    df = df.replace(['NA', 'na', 'N/A', ''], np.nan)
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # 创建热图
    plt.figure(figsize=(12, 8))
    sns.heatmap(
        df,
        cmap="YlOrRd",
        annot=False,  # 不显示数字
        linewidths=0,  # 移除色块间的小间隔
        cbar_kws={'label': 'Expression Level'},
        mask=df.isna()  # NA值显示为空白
    )
    plt.title('Gene Expression Heatmap')
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # 将图像转换为base64编码
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
    plt.close()
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    return f"data:image/png;base64,{image_base64}"