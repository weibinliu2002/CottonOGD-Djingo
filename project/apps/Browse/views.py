from django.http import JsonResponse
from django.views import View
from django.db.models import Q

# 导入模型
from .models import TF, Species

# JSON API 接口


class TFApiView(View):
    """转录因子数据 JSON API"""

    def get(self, request):
        # 获取请求参数
         #genome = request.GET.get('genome', '').strip()
        genome='TM_1'
        family = request.GET.get('family', '').strip()
        search = request.GET.get('search', '').strip()

        try:
            try:
                # 执行查询
                tf_queryset = TF.objects.all()
                if genome:
                    tf_queryset = tf_queryset.filter(TF_genome__icontains=genome)
                if family:
                    # 处理家族过滤，支持多个家族用逗号分隔
                    family_list = family.split(',')
                    tf_queryset = tf_queryset.filter(TF_name__in=family_list)
                if search:
                    # 处理搜索功能，支持按名称、基因等字段搜索
                    tf_queryset = tf_queryset.filter(
                        Q(TF_name__icontains=search) | 
                        Q(TF_gene__icontains=search) | 
                        Q(TF_class__icontains=search)
                    )
                
                total_count = tf_queryset.count()
                
                # 如果数据库中有数据
                if total_count > 0:
                    # 转换为字典列表，返回所有数据，不做分页
                    tf_list = []
                    for tf in tf_queryset:
                        tf_list.append({
                            'id': tf.id,
                            'TF_name': tf.TF_name,
                            'TF_class': tf.TF_class,
                            'TF_gene': tf.TF_gene,
                            'TF_genome': tf.TF_genome
                        })
                    
                    # 返回JSON响应
                    return JsonResponse({
                        'status': 'success',
                        'data': tf_list,
                        'total': total_count,
                        'message': f'成功获取{total_count}条转录因子数据'
                    })
            except Exception as e:
                # 捕获数据库查询异常，例如表不存在
                print(f"数据库查询异常: {str(e)}")
            # 根据genome过滤默认数据
            filtered_tf_list = default_tf_list
            if genome:
                filtered_tf_list = [tf for tf in default_tf_list if genome.lower() in tf['TF_genome'].lower()]
            if family:
                family_list = family.split(',')
                filtered_tf_list = [tf for tf in filtered_tf_list if tf['TF_class'] in family_list]
            if search:
                filtered_tf_list = [tf for tf in filtered_tf_list if 
                                  search.lower() in tf['TF_name'].lower() or 
                                  search.lower() in tf['TF_gene'].lower() or 
                                  search.lower() in tf['TF_class'].lower()]
            
            total_count = len(filtered_tf_list)
            
            # 返回所有数据，不做分页
            return JsonResponse({
                'status': 'success',
                'data': filtered_tf_list,
                'total': total_count,
                'message': f'成功获取{total_count}条默认转录因子数据'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'error': f'处理请求时发生错误: {str(e)}',
                'message': '获取转录因子数据失败'
            }, status=500)

class TFFamilyApiView(View):
    """获取转录因子家族列表 JSON API"""

    def get(self, request):
        try:
            try:
                # 使用values和annotate一次性获取家族和数量，减少数据库查询次数
                from django.db.models import Count
                
                # 执行实际查询，使用TF_name字段而不是TF_class字段
                family_queryset = TF.objects.values('TF_name').annotate(count=Count('id')).order_by('TF_name')
                
                total_count = family_queryset.count()
                
                # 如果数据库中有数据
                if total_count > 0:
                    # 转换为字典列表
                    family_list = [{'name': family['TF_name'], 'count': family['count']} for family in family_queryset]
                    
                    # 返回JSON响应
                    return JsonResponse({
                        'status': 'success',
                        'data': family_list,
                        'message': f'成功获取{len(family_list)}个转录因子家族'
                    })
            except Exception as e:
                # 捕获数据库查询异常，例如表不存在
                print(f"数据库查询异常: {str(e)}")
            
            # 返回JSON响应
            return JsonResponse({
                'status': 'success',
                'data': default_family_list,
                'message': f'成功获取{len(default_family_list)}个默认转录因子家族'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'error': f'处理请求时发生错误: {str(e)}',
                'message': '获取转录因子家族数据失败'
            }, status=500)

class SpeciesApiView(View):
    """物种数据 JSON API"""

    def get(self, request):

        try:
            # 执行查询
            species_queryset = Species.objects.all()
            total_count = species_queryset.count()
            
            # 如果数据库中没有数据，返回默认的示例数据
            if total_count == 0:
                # 默认的物种示例数据
                default_species_list = [
                    {
                        'id': 1,
                        'name': 'Gossypium arboreum',
                        'Cotton_Species': 'Gossypium arboreum',
                        'Genome_type': 'A2',
                        'Category': 'Diploid',
                        'Accession': 'GCA_000612105.1',
                        'Ploidy': '2n=2x=26',
                        'Assembling_institution': 'Institute of Cotton Research, Chinese Academy of Agricultural Sciences',
                        'Website': 'http://cotton.zju.edu.cn',
                        'Article': 'Wang et al., Nat Genet, 2019',
                        'LAI_value': '23.7',
                        'Busco': '98.5%',
                        'Genome_size': 1742000000,
                        'description': '亚洲棉，二倍体栽培棉种'
                    },
                    {
                        'id': 2,
                        'name': 'Gossypium raimondii',
                        'Cotton_Species': 'Gossypium raimondii',
                        'Genome_type': 'D5',
                        'Category': 'Diploid',
                        'Accession': 'GCA_000179595.1',
                        'Ploidy': '2n=2x=26',
                        'Assembling_institution': 'The Institute for Genomic Research',
                        'Website': 'http://www.phytozome.net',
                        'Article': 'Paterson et al., Nat Genet, 2012',
                        'LAI_value': '18.2',
                        'Busco': '96.3%',
                        'Genome_size': 775000000,
                        'description': '雷蒙德氏棉，二倍体野生棉种'
                    },
                    {
                        'id': 3,
                        'name': 'Gossypium hirsutum',
                        'Cotton_Species': 'Gossypium hirsutum',
                        'Genome_type': 'AD1',
                        'Category': 'Tetraploid',
                        'Accession': 'GCA_001673975.2',
                        'Ploidy': '2n=4x=52',
                        'Assembling_institution': 'Huazhong Agricultural University',
                        'Website': 'https://cottonfgd.org',
                        'Article': 'Zhang et al., Nat Genet, 2015',
                        'LAI_value': '31.5',
                        'Busco': '99.2%',
                        'Genome_size': 2270000000,
                        'description': '陆地棉，四倍体栽培棉种'
                    }
                ]
                
                total_count = len(default_species_list)
                
                # 返回JSON响应
                return JsonResponse({
                    'status': 'success',
                    'data': default_species_list,
                    'total': total_count,
                    'message': f'成功获取{total_count}条默认物种数据'
                })
            
            # 转换为字典列表，返回所有数据，不做分页
            species_list = []
            for species in species_queryset:
                species_list.append({
                    'id': species.id,
                    'name': species.name,
                    'Cotton_Species': species.Cotton_Species,
                    'Genome_type': species.Genome_type,
                    'Category': species.Category,
                    'Accession': species.Accession,
                    'Ploidy': species.Ploidy,
                    'Assembling_institution': species.Assembling_institution,
                    'Website': species.Website,
                    'Article': species.Article,
                    'LAI_value': species.LAI_value,
                    'Busco': species.Busco,
                    'Genome_size': species.Genome_size,
                    'description': species.description
                })
            
            # 返回JSON响应
            return JsonResponse({
                'status': 'success',
                'data': species_list,
                'total': total_count,
                'message': f'成功获取{total_count}条物种数据'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'error': f'处理请求时发生错误: {str(e)}',
                'message': '获取物种数据失败'
            }, status=500)