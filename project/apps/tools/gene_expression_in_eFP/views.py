import json
import os
import math
from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from .models import FPKM4
from PIL import Image, ImageDraw
from io import BytesIO
import base64
import numpy as np

def gene_expression_in_eFP_view(request):
    """显示热图页面"""
    return render(request, 'tools/gene_expression_in_eFP/gene_expression_in_eFP.html')

@csrf_exempt
def generate_thermal_image(request):
    """生成热图API"""
    if request.method == 'POST':
        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body)
                gene_id = data.get('gene_id')
                low_color = data.get('low_color', '#0000FF')    # 默认蓝色
                mid_color = data.get('mid_color', '#00FF00')    # 默认绿色
                high_color = data.get('high_color', '#FF0000')  # 默认红色
            else:
                gene_id = request.POST.get('gene_id')
                low_color = request.POST.get('low_color', '#0000FF')
                mid_color = request.POST.get('mid_color', '#00FF00')
                high_color = request.POST.get('high_color', '#FF0000')
            
            if not gene_id:
                return JsonResponse({'success': False, 'error': '请输入基因ID'})
            
            try:
                gene_data = FPKM4.objects.get(gene_id=gene_id)
            except FPKM4.DoesNotExist:
                return JsonResponse({'success': False, 'error': f'基因ID "{gene_id}" 不存在'})
            
            regions_config_path = os.path.join(settings.BASE_DIR, 'static', 'ccc.json')
            
            if not os.path.exists(regions_config_path):
                return JsonResponse({
                    'success': False, 
                    'error': '区域配置文件不存在'
                })
            
            with open(regions_config_path, 'r', encoding='utf-8') as f:
                regions_config = json.load(f)
            
            base_image_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'egg.jpg')
            
            if not os.path.exists(base_image_path):
                return JsonResponse({
                    'success': False, 
                    'error': '基础图像文件不存在'
                })
            
            image = Image.open(base_image_path).convert('RGBA')
            draw = ImageDraw.Draw(image, 'RGBA')
            
            values = []
            region_info_list = []
            
            for region_data in regions_config['regions']:
                region_name = region_data['name']
                value_str = str(getattr(gene_data, region_name, "NA"))
                
                if value_str.upper() == 'NA' or value_str.strip() == '':
                    continue
                
                try:
                    value = float(value_str)
                    if not math.isnan(value):
                        values.append(value)
                except (ValueError, TypeError):
                    continue
            
            if values:
                values_array = np.array(values)
                log_values = np.log10(values_array + 1)
                
                q1 = np.percentile(log_values, 25)
                q3 = np.percentile(log_values, 75)
                iqr = q3 - q1
                lower_bound = max(log_values.min(), q1 - 1.5 * iqr)
                upper_bound = min(log_values.max(), q3 + 1.5 * iqr)
                
                min_log = lower_bound
                max_log = upper_bound
                
                min_val = 10 ** min_log - 1
                max_val = 10 ** max_log - 1
            else:
                min_val = 0
                max_val = 10
                # Calculate log values for the default min_val and max_val
                min_log = math.log10(min_val + 1)
                max_log = math.log10(max_val + 1)
            
            # 解析颜色值
            low_rgb = hex_to_rgb(low_color)
            mid_rgb = hex_to_rgb(mid_color)
            high_rgb = hex_to_rgb(high_color)
            
            for region_data in regions_config['regions']:
                region_name = region_data['name']
                polygon = region_data['polygon']
                # 确保坐标是整数类型
                polygon = [(int(x), int(y)) for x, y in polygon]
                value_str = str(getattr(gene_data, region_name, "NA"))
                
                if value_str.upper() == 'NA' or value_str.strip() == '':
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
                    value = float(value_str)
                    if math.isnan(value):
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
                    # 防止除以零
                    if max_log > min_log:
                        normalized = (log_value - min_log) / (max_log - min_log)
                        normalized = max(0, min(1, normalized))
                    else:
                        normalized = 0.5  # 当所有值相同时，使用中间色
                    
                    # 使用用户选择的颜色
                    color = custom_value_to_color(normalized, low_rgb, mid_rgb, high_rgb)
                    
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
                    if len(polygon) > 1:
                        closed_polygon = polygon + [polygon[0]]
                        draw.line(closed_polygon, fill='gray', width=2, joint='curve')
                    
                    region_info = {
                        'name': region_name,
                        'value': 'Invalid',
                        'polygon': polygon
                    }
                    region_info_list.append(region_info)
            
            add_colorbar(draw, image.width, image.height, min_val, max_val, low_rgb, mid_rgb, high_rgb)
            add_gene_info(draw, image.width, gene_id, len(values), len(regions_config['regions']))
            
            buffered = BytesIO()
            image.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            return JsonResponse({
                'success': True, 
                'image': f'data:image/png;base64,{img_str}',
                'gene_id': gene_id,
                'min_value': float(min_val),
                'max_value': float(max_val),
                'valid_regions': len(values),
                'total_regions': len(regions_config['regions']),
                'regions_info': region_info_list,
                'image_width': image.width,
                'image_height': image.height
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False, 
                'error': f'生成热图时发生错误: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'error': '请使用POST请求'})

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
    
    return (r, g, b, 200)

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