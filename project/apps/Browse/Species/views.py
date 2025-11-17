from django.shortcuts import render
from django.http import HttpResponse
from Browse.Species.models import Species
# Create your views here.
def browse_species(request):
    # 从数据库获取所有物种
    species_objects = Species.objects.all()
    
    # 创建字典，按Cotton_Species分类name字段
    species_by_category = {}
    
    # 遍历所有物种对象
    for species in species_objects:
        # 使用Cotton_Species作为分类键
        category = species.Cotton_Species or '未分类'
        
        # 如果分类不存在，则创建一个空列表
        if category not in species_by_category:
            species_by_category[category] = []
        
        # 将对应的name添加到该分类下
        if species.name:
            species_by_category[category].append(species.name)
    
    # 准备一个列表，每个元素是(category, sub_species_list)的元组
    species_categories = []
    for category, sub_species_list in species_by_category.items():
        species_categories.append((category, sub_species_list))
    
    context = {
        'title': '物种浏览',
        'species_categories': species_categories  # 包含分类和对应子物种列表的元组列表
    }
    
    return render(request, 'Browse/Species/index.html', context)
    #return HttpResponse("Hello, world. You're at the Species browse.")

def single_show(request, species):
    """显示单个物种的详细信息"""
    try:
        # 验证species参数不为空
        if not species or species.strip() == '':
            return HttpResponse("错误: 物种参数不能为空", status=400)
            
        # 尝试通过name字段查找，如果找不到再尝试Cotton_Species字段
        species_obj = Species.objects.filter(name=species).first()
        if not species_obj:
            species_obj = Species.objects.filter(Cotton_Species=species).first()
        
        # 构建表格数据 - 注意使用arguement而不是verbose_name，因为模板已更新
        if species_obj:
            # 找到了物种，使用模型的_meta属性动态获取字段信息
            table_data = []
            
            # 获取模型的所有字段（排除内部字段）
            for field in Species._meta.fields:
                # 跳过Django内部字段和_id字段
                if field.name.startswith('_') or field.name == 'id':
                    continue
                
                # 获取字段值，处理None值为'N/A'
                value = getattr(species_obj, field.name, None)
                
                # 为字段创建一个用户友好的显示名称
                display_name = field.name.replace('_', ' ').title()
                
                table_data.append({
                    'argument': display_name,  # 使用友好的显示名称
                    'value': value if value is not None else ' '
                })
            # 只打印一次完整的table_data，方便调试
            #print(f"Table data: {table_data}")
        else:
            # 找不到物种，显示默认数据
            table_data = [
                {'argument': '错误信息', 'value': f'未找到物种: {species}'},
                {'argument': '请求参数', 'value': species},
                {'argument': '状态', 'value': '未找到记录'}
            ]
        
        # 设置上下文，传递给模板
        context = {
            'title': f'{species} 详情',
            'species': species,
            'table_data': table_data  # 确保传递table_data变量
        }
        
        # 使用模板渲染响应
        return render(request, 'Browse/single/single_show.html', context)
    except Exception as e:
        # 捕获其他可能的异常，返回错误信息
        return HttpResponse(f"错误：{str(e)}", status=500)
