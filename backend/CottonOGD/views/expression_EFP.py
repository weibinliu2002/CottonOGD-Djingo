import json
import os
import math
import logging

from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from CottonOGD.models import gene_expression
from PIL import Image, ImageDraw
from io import BytesIO
import base64
import numpy as np

# 配置日志
logger = logging.getLogger(__name__)


@api_view(['POST'])
@csrf_exempt
def expression_EFP_image(request):
    """生成热图API"""
    
    try:
        # 尝试解析 JSON 数据
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            gene_id = data.get('gene_id')
            low_color = data.get('low_color', '#0000FF')
            mid_color = data.get('mid_color', '#00FF00')
            high_color = data.get('high_color', '#FF0000')
            genome_id = data.get('genome_id', 'G.hirsutumAD1_Jin668_HAU_v1T2T')
        else:
            # 表单数据
            gene_id = request.POST.get('gene_id')
            low_color = request.POST.get('low_color', '#0000FF')
            mid_color = request.POST.get('mid_color', '#00FF00')
            high_color = request.POST.get('high_color', '#FF0000')
            genome_id = request.POST.get('genome_id', 'G.hirsutumAD1_Jin668_HAU_v1T2T')

        if not gene_id:
            return JsonResponse({'success': False, 'error': '请输入基因ID'})

        # 记录请求信息
        logger.info(f'gene_id: {gene_id}, genome_id: {genome_id}, low_color: {low_color}, mid_color: {mid_color}, high_color: {high_color}')

        # 获取基因数据
        gene_data = gene_expression.objects.filter(geneid=gene_id, genome=genome_id)
        if not gene_data:
            logger.error(f'Gene not found: {gene_id} in genome {genome_id}')
            return JsonResponse({'success': False, 'error': f'基因ID "{gene_id}" 在基因组 "{genome_id}" 中不存在'})
        logger.info(f'gene_data count: {gene_data.count()}')

        # 创建阶段到表达值的映射（因为tissue字段为空）
        stage_value_map = {}
        for item in gene_data:
            # 检查stage字段是否为空或只包含空格
            if not item.stage or not item.stage.strip():
                logger.warning(f'Skipping item with empty or whitespace-only stage: {item}')
                continue
            # 去除stage字段中的空格并转换为小写
            stage_key = item.stage.strip().lower()
            if stage_key not in stage_value_map:
                stage_value_map[stage_key] = []
            stage_value_map[stage_key].append(item.value)
            logger.debug(f'Added value {item.value} for stage {stage_key}')
        logger.info(f'stage_value_map: {stage_value_map}')
        logger.info(f'Available stage keys: {list(stage_value_map.keys())}')

        # 加载区域配置文件
        regions_config_path = os.path.join(settings.BASE_DIR, 'static', 'ccc.json')
        if not os.path.exists(regions_config_path):
            return JsonResponse({
                'success': False, 
                'error': '区域配置文件不存在'
            })

        with open(regions_config_path, 'r', encoding='utf-8') as f:
            regions_config = json.load(f)

        # 加载基础图像
        base_image_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'egg.jpg')
        if not os.path.exists(base_image_path):
            return JsonResponse({
                'success': False, 
                'error': '基础图像文件不存在'
            })

        # 打开图像并创建绘图对象
        image = Image.open(base_image_path).convert('RGBA')
        draw = ImageDraw.Draw(image, 'RGBA')

        # 收集有效值
        values = []
        region_info_list = []

        # 定义区域名称到组织类型的映射
        region_to_tissue = {
            'Stem': 'stem',
            'Root': 'root',
            'Leaf': 'leaf',
            'Bract': 'bract',
            'Sepal': 'sepal',
            'Petal': 'petal',
            'Stigma': 'stigma',
            'Anther': 'anther',
            'Cotyledon': 'cotyledon',
            'Phloem': 'phloem',
            'Ovules': 'ovule',
            'Seed': 'seed',
            'Fiber': 'fiber'
        }

        for region in regions_config['regions']:
            region_name = region['name']
            # 将区域名称映射到阶段类型
            stage_key = region_to_tissue.get(region_name, region_name).lower()
            logger.info(f'Processing region: {region_name}, mapped to stage: {stage_key}')
            
            # 获取该阶段的表达值
            region_values = stage_value_map.get(stage_key, [])
            logger.info(f'Values for {region_name} ({stage_key}): {region_values}')
            if region_values:
                # 取平均值作为该区域的表达值
                value = sum(region_values) / len(region_values)
                logger.info(f'Value for {region_name} ({stage_key}): {value}')
                values.append(value)
            else:
                # 尝试直接使用区域名称作为阶段类型
                alternative_key = region_name.lower()
                if alternative_key != stage_key:
                    alternative_values = stage_value_map.get(alternative_key, [])
                    logger.info(f'Trying alternative key {alternative_key} for {region_name}: {alternative_values}')
                    if alternative_values:
                        value = sum(alternative_values) / len(alternative_values)
                        logger.info(f'Alternative value for {region_name} ({alternative_key}): {value}')
                        values.append(value)
                continue

        # 计算值范围
        if values:
            logger.info(f'Values: {values}')
            values_array = np.array(values)
            log_values = np.log10(values_array + 1)
            logger.info(f'Log values: {log_values}')
            
            q1 = np.percentile(log_values, 25)
            q3 = np.percentile(log_values, 75)
            iqr = q3 - q1
            lower_bound = max(log_values.min(), q1 - 1.5 * iqr)
            upper_bound = min(log_values.max(), q3 + 1.5 * iqr)
            
            logger.info(f'q1: {q1}, q3: {q3}, iqr: {iqr}, lower_bound: {lower_bound}, upper_bound: {upper_bound}')
            
            min_log = lower_bound
            max_log = upper_bound
            
            min_val = 10 ** min_log - 1
            max_val = 10 ** max_log - 1
            logger.info(f'min_val: {min_val}, max_val: {max_val}')
        else:
            logger.info('No valid values found, using default range')
            min_val = 0
            max_val = 10
            # 计算默认值的对数
            min_log = math.log10(min_val + 1)
            max_log = math.log10(max_val + 1)
            logger.info(f'Default min_val: {min_val}, default max_val: {max_val}')

        # 解析颜色值
        low_rgb = hex_to_rgb(low_color)
        mid_rgb = hex_to_rgb(mid_color)
        high_rgb = hex_to_rgb(high_color)

        # 绘制每个区域
        for region_data in regions_config['regions']:
            region_name = region_data['name']
            logger.info(f'Drawing region: {region_name}')
            # 检查 region_data 是否包含 polygon 字段
            if 'polygon' not in region_data:
                logger.warning(f'Region {region_name} missing polygon data, skipping')
                region_info = {
                    'name': region_name,
                    'value': 'No Polygon',
                    'polygon': []
                }
                region_info_list.append(region_info)
                continue
            polygon = region_data['polygon']
            # 确保坐标是整数类型
            try:
                polygon = [(int(x), int(y)) for x, y in polygon]
            except (ValueError, TypeError) as e:
                logger.error(f'Error parsing polygon for region {region_name}: {str(e)}')
                region_info = {
                    'name': region_name,
                    'value': 'Invalid Polygon',
                    'polygon': []
                }
                region_info_list.append(region_info)
                continue
            
            # 使用前面创建的映射获取该区域的表达值
            stage_key = region_to_tissue.get(region_name, region_name).lower()
            region_values = stage_value_map.get(stage_key, [])
            
            if not region_values:
                # 尝试直接使用区域名称作为阶段类型
                alternative_key = region_name.lower()
                if alternative_key != stage_key:
                    region_values = stage_value_map.get(alternative_key, [])
                
                if not region_values:
                    logger.info(f'Region {region_name} has no expression values')
                    if len(polygon) > 1:
                        closed_polygon = polygon + [polygon[0]]
                        draw.line(closed_polygon, fill='gray', width=2, joint='curve')

                    region_info = {
                        'name': region_name,
                        'value': 'NA',
                        'polygon': polygon
                    }
                    region_info_list.append(region_info)
                    continue

            try:
                # 取平均值作为该区域的表达值
                value = sum(region_values) / len(region_values)
                if math.isnan(value):
                    logger.info(f'Region {region_name} has NaN value')
                    if len(polygon) > 1:
                        closed_polygon = polygon + [polygon[0]]
                        draw.line(closed_polygon, fill='gray', width=2, joint='curve')

                    region_info = {
                        'name': region_name,
                        'value': 'NaN',
                        'polygon': polygon
                    }
                    region_info_list.append(region_info)
                    continue

                log_value = math.log10(value + 1)
                logger.info(f'Region {region_name} value: {value}, log_value: {log_value}')
                # 防止除以零
                if max_log > min_log:
                    normalized = (log_value - min_log) / (max_log - min_log)
                    normalized = max(0, min(1, normalized))
                    logger.info(f'Region {region_name} normalized: {normalized}')
                else:
                    normalized = 0.5  # 当所有值相同时，使用中间色
                    logger.info(f'Region {region_name} all values same, normalized: {normalized}')

                # 使用用户选择的颜色
                color = custom_value_to_color(normalized, low_rgb, mid_rgb, high_rgb)
                logger.info(f'Region {region_name} color: {color}')

                draw.polygon(polygon, fill=color)
                if len(polygon) > 1:
                    closed_polygon = polygon + [polygon[0]]
                    draw.line(closed_polygon, fill='black', width=2, joint='curve')

                region_info = {
                    'name': region_name,
                    'value': float(value),
                    'polygon': polygon,
                    'color': color,
                    'normalized': normalized
                }
                region_info_list.append(region_info)

            except (ValueError, TypeError) as e:
                logger.error(f'Error processing region {region_name}: {str(e)}')
                if len(polygon) > 1:
                    closed_polygon = polygon + [polygon[0]]
                    draw.line(closed_polygon, fill='gray', width=2, joint='curve')

                region_info = {
                    'name': region_name,
                    'value': 'Invalid',
                    'polygon': polygon
                }
                region_info_list.append(region_info)

        # 保存图像为base64编码
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()

        # 返回响应
        return JsonResponse({
            'image': f'data:image/png;base64,{img_str}',
            'regions_info': region_info_list,
            'image_width': image.width,
            'image_height': image.height,
            'success': True,
            'gene_id': gene_id,
            'genome_id': genome_id,
            'min_value': float(min_val),
            'max_value': float(max_val),
            'valid_regions': len(values),
            'total_regions': len(regions_config['regions'])
        })

    except gene_expression.DoesNotExist:
        logger.error(f'Gene not found: {gene_id}')
        return JsonResponse({'success': False, 'error': f'基因ID "{gene_id}" 不存在'})
    except Exception as e:
        logger.error(f'Error generating heatmap: {str(e)}', exc_info=True)
        return JsonResponse({
            'success': False, 
            'error': f'生成热图时发生错误: {str(e)}'
        })



def hex_to_rgb(hex_color):
    """将十六进制颜色转换为RGB元组"""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c * 2 for c in hex_color])

    return (
        int(hex_color[0:2], 16),
        int(hex_color[2:4], 16),
        int(hex_color[4:6], 16)
    )


def custom_value_to_color(normalized, low_rgb, mid_rgb, high_rgb):
    """使用自定义颜色映射"""
    logger.info(f'Normalized value: {normalized}, low_rgb: {low_rgb}, mid_rgb: {mid_rgb}, high_rgb: {high_rgb}')
    if normalized < 0.5:
        # 低值到中间值的渐变
        t = normalized * 2  # 映射到0-1
        r = int(low_rgb[0] + (mid_rgb[0] - low_rgb[0]) * t)
        g = int(low_rgb[1] + (mid_rgb[1] - low_rgb[1]) * t)
        b = int(low_rgb[2] + (mid_rgb[2] - low_rgb[2]) * t)
    else:
        # 中间值到高值的渐变
        t = (normalized - 0.5) * 2  # 映射到0-1
        r = int(mid_rgb[0] + (high_rgb[0] - mid_rgb[0]) * t)
        g = int(mid_rgb[1] + (high_rgb[1] - mid_rgb[1]) * t)
        b = int(mid_rgb[2] + (high_rgb[2] - mid_rgb[2]) * t)
    # 确保颜色值在有效范围内
    r = max(0, min(255, r))
    g = max(0, min(255, g))
    b = max(0, min(255, b))
    color = (r, g, b, 200)
    logger.info(f'Calculated color: {color}')
    return color


def add_colorbar(draw, image_width, image_height, min_val, max_val, low_rgb, mid_rgb, high_rgb):
    """添加颜色条图例"""
    colorbar_width = 25
    colorbar_height = 150
    margin = 20
    colorbar_x = image_width - margin - colorbar_width - 50
    colorbar_y = margin + 50

    # 确保坐标是整数类型
    colorbar_x = int(colorbar_x)
    colorbar_y = int(colorbar_y)

    for i in range(colorbar_height):
        normalized = i / colorbar_height
        color = custom_value_to_color(normalized, low_rgb, mid_rgb, high_rgb)
        y_pos = colorbar_y + i
        draw.line([(colorbar_x, y_pos), (colorbar_x + colorbar_width, y_pos)], fill=color, width=1)

    draw.rectangle([
        (colorbar_x, colorbar_y),
        (colorbar_x + colorbar_width, colorbar_y + colorbar_height)
    ], outline='black', width=2)

    min_display = f"{min_val:.2f}" if min_val < 10 else f"{min_val:.1f}"
    draw.text((colorbar_x + colorbar_width + 5, colorbar_y + colorbar_height - 15), min_display, fill='black')

    max_display = f"{max_val:.2f}" if max_val < 10 else f"{max_val:.1f}"
    draw.text((colorbar_x + colorbar_width + 5, colorbar_y), max_display, fill='black')

    mid_val_display = 10 ** ((math.log10(min_val + 1) + math.log10(max_val + 1)) / 2) - 1
    mid_display = f"{mid_val_display:.2f}" if mid_val_display < 10 else f"{mid_val_display:.1f}"
    draw.text((colorbar_x + colorbar_width + 5, colorbar_y + colorbar_height//2 - 7), mid_display, fill='black')

    draw.text((colorbar_x - 10, colorbar_y - 30), "Expression Level", fill='black')
    draw.text((colorbar_x - 10, colorbar_y - 15), "(log scale)", fill='black')


def add_gene_info(draw, image_width, gene_id, valid_count, total_count):
    """添加基因信息和统计"""
    title = f"Gene: {gene_id}"
    # 确保标题位置坐标是整数类型
    title_x = int(image_width // 2 - len(title) * 3)
    draw.text((title_x, 15), title, fill='black')

    legend_text = "Gray outline: NA/Invalid values"
    # 确保图例位置坐标是整数类型
    legend_y = int(image_width - 40 if image_width > 600 else 50)
    draw.text((20, legend_y), legend_text, fill='gray')
