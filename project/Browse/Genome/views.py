from django.shortcuts import render
from django.http import HttpResponse
from Browse.Species.models import Species
# Create your views here.
def browse_genome(request):
    # 从数据库获取所有物种
    species_objects = Species.objects.all()
    
    # 创建字典，按Genome_type分类name字段
    genome_by_category = {}
    
    # 遍历所有物种对象
    for genome in species_objects:
        # 使用Genome_type作为分类键
        category = genome.Genome_type or 'unclassified'
        
        # 如果分类不存在，则创建一个空列表
        if category not in genome_by_category:
            genome_by_category[category] = []
        
        # 将对应的name添加到该分类下
        if genome.name:
            genome_by_category[category].append(genome.name)
    
    # 准备一个列表，每个元素是(category, sub_genome_list)的元组
    genome_categories = []
    for category, sub_genome_list in genome_by_category.items():
        genome_categories.append((category, sub_genome_list))
    
    context = {
        'title': '基因组浏览',
        'genome_categories': genome_categories  # 包含分类和对应子基因组列表的元组列表
    }
    return render(request, 'Genome/index.html', context)
    #return HttpResponse("Hello, world. You're at the Species browse.")

def single_show(request, species):
    """显示单个物种的详细信息"""
    # No need to convert spaces back here as the path converter handles URL-encoding automatically
    context = {
        'title': f'{species} 详情',
        'species': species,
    }
    return render(request, 'single/single_show.html', context)
