from django.shortcuts import render
from .models import TF
# Create your views here.
def tf(request):
    # 从数据库获取所有TF
    tf_objects = TF.objects.all()
    # 创建字典，按genome分类TF
    tf_by_genome = {}
    
    # 遍历所有TF对象
    for tf in tf_objects:
        # 使用genome作为分类键
        genome = tf.genome or '未分类'
        
        # 如果分类不存在，则创建一个空列表
        if genome not in tf_by_genome:
            tf_by_genome[genome] = []
        
        # 将对应的TF添加到该分类下
        if tf.name:
            tf_by_genome[genome].append(tf.name)
    
    # 准备一个列表，每个元素是(genome, tf_list)的元组
    tf_genomes = []
    for genome, tf_list in tf_by_genome.items():
        tf_genomes.append((genome, tf_list))
    
    context = {
        'title': 'TF浏览',
        'tf_genomes': tf_genomes  # 包含分类和对应TF列表的元组列表
    }
    
    return render(request, 'Browse/TF/index.html', context)
def sign_show(request):

    return render(request, 'Browse/TF/index.html')
def sign_show(request):
    return render(request, 'TF/sign_show.html')
