"""
EFP（电子荧光伪彩图）视图：POST /CottonOGD_api/expression_EFP_image/

渲染策略（eFP Browser 风格）：
  - 底图是多器官棉株插画（自带器官标签与引线，位于多边形外部）；
  - 每个器官多边形先铺白色底遮住插画本身的绿/蓝色，再填高不透明度
    表达色，保证组织颜色不受底图干扰、器官之间边界清晰；
  - 大面积区域内叠加数值标签（白色描边），无数据区域填浅灰；
  - 颜色映射使用 matplotlib 三段线性色图，对数值做 log10 归一化。
"""
import json
import math
import os
import logging
import base64
from io import BytesIO

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from matplotlib.colors import LinearSegmentedColormap

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from CottonOGD.models import gene_expression

logger = logging.getLogger(__name__)

# 表达色填充不透明度（0-255）。高于 220 时底图纹理基本不可见，只保留轮廓感
FILL_ALPHA = 235
# 多边形面积（像素^2）超过该阈值才绘制数值标签，避免小器官文字挤成一团
VALUE_LABEL_MIN_AREA = 6000
# 同名器官只在最大的一块上标注器官名，避免 Leaf 的 8 个多边形重复标字
NAME_LABEL_MIN_AREA_RATIO = 1.0

# 组织名别名：ccc.json 区域名 / 其他命名习惯 -> 数据库 tissue 字段的规范名
REGION_ALIASES = {
    'fiber': 'fibers',
    'fibers': 'fibers',
    'ovule': 'ovules',
    'ovules': 'ovules',
    'phloem': 'pholem',
    'pholem': 'pholem',
    'cotyledon': 'cotyledon',
}

# 缓存已创建的色图（按颜色组合复用）
_COLORMAP_CACHE = {}


def _get_colormap(low_color, mid_color, high_color):
    """三段线性色图，带缓存。"""
    cache_key = (low_color, mid_color, high_color)
    if cache_key not in _COLORMAP_CACHE:
        _COLORMAP_CACHE[cache_key] = LinearSegmentedColormap.from_list(
            'efp', [low_color, mid_color, high_color], N=256)
    return _COLORMAP_CACHE[cache_key]


@csrf_exempt
def expression_EFP_image(request):
    """生成 EFP 伪彩图 API"""
    try:
        data = _parse_request_data(request)
        gene_id = data.get('gene_id')
        if not gene_id:
            return JsonResponse({'success': False, 'error': '请输入基因ID'})

        low_color = data.get('low_color', '#0000FF')
        mid_color = data.get('mid_color', '#00FF00')
        high_color = data.get('high_color', '#FF0000')
        genome_id = data.get('genome_id', 'G.hirsutumAD1_Jin668_HAU_v1T2T')

        logger.info('Request: gene_id=%s, genome=%s, colors=(%s, %s, %s)',
                    gene_id, genome_id, low_color, mid_color, high_color)

        # 2. 获取基因数据
        gene_data = list(gene_expression.objects.filter(
            geneid=gene_id,
            genome=genome_id
        ))
        if not gene_data:
            logger.error('Gene not found: %s in %s', gene_id, genome_id)
            return JsonResponse({
                'success': False,
                'error': f'基因ID "{gene_id}" 在基因组 "{genome_id}" 中不存在'
            })

        # 3. 构建表达值映射
        stage_tissue_map = _build_expression_map(gene_data)

        # 4. 加载配置和图像
        regions_config = _load_regions_config()
        base_image = _load_base_image()

        # 5. 处理区域数据
        regions_info, values = _process_regions(regions_config, stage_tissue_map)

        # 6. 计算值范围（log 分位数）
        min_val, max_val, min_log, max_log = _calculate_value_range(values)

        # 7. 绘制伪彩图
        image = _draw_heatmap(
            base_image,
            regions_info,
            min_log, max_log,
            low_color, mid_color, high_color
        )

        # 8. 图例与标题
        draw = ImageDraw.Draw(image, 'RGBA')
        add_colorbar(draw, image.width, image.height,
                     min_val, max_val,
                     low_color, mid_color, high_color)
        add_gene_info(draw, image.width, image.height, gene_id,
                      len(values), len(regions_config['regions']))

        # 9. 生成响应
        img_str = _image_to_base64(image)
        return JsonResponse({
            'success': True,
            'image': f'data:image/png;base64,{img_str}',
            'regions_info': regions_info,
            'image_width': image.width,
            'image_height': image.height,
            'gene_id': gene_id,
            'genome_id': genome_id,
            'min_value': float(min_val),
            'max_value': float(max_val),
            'valid_regions': len(values),
            'total_regions': len(regions_config['regions']),
            'drawing_method': 'PIL'
        })

    except Exception as e:
        logger.error('Error generating EFP image: %s', e, exc_info=True)
        return JsonResponse({'success': False, 'error': f'生成热图时发生错误: {e}'})


def _parse_request_data(request):
    """解析请求数据"""
    if request.content_type == 'application/json':
        return json.loads(request.body)
    return request.POST


def _build_expression_map(gene_data):
    """构建 stage_tissue -> 表达值列表 的映射（键统一小写）"""
    stage_tissue_map = {}
    for item in gene_data:
        stage = (item.stage or '').strip()
        tissue = (item.tissue or '').strip()
        if not stage and not tissue:
            continue

        keys = set()
        base_key = f'{stage}_{tissue}'.lower() if stage and tissue else (stage or tissue).lower()
        keys.add(base_key)
        if stage and tissue:
            keys.add(f'{stage}{tissue}'.lower())
            # 器官单独键（如 3DPA_fibers 区域聚合所有时期取均值时用不到，
            # 但无 stage 信息的器官如 Leaf 依赖此键）
            keys.add(tissue.lower())

        for key in keys:
            stage_tissue_map.setdefault(key, []).append(item.value)
    return stage_tissue_map


def _load_regions_config():
    """加载区域配置"""
    config_path = os.path.join(settings.BASE_DIR, 'static', 'ccc.json')
    if not os.path.exists(config_path):
        raise FileNotFoundError('区域配置文件不存在')
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _load_base_image():
    """加载基础图像"""
    image_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'egg.jpg')
    if not os.path.exists(image_path):
        raise FileNotFoundError('基础图像文件不存在')
    return Image.open(image_path).convert('RGBA')


def _process_regions(regions_config, stage_tissue_map):
    """为每个区域查找表达值，返回 (regions_info, values)"""
    regions_info = []
    values = []

    for region in regions_config['regions']:
        region_name = region['name']
        polygon = region.get('polygon', [])

        if not polygon:
            regions_info.append({'name': region_name, 'value': 'No Polygon', 'polygon': []})
            continue

        try:
            polygon = [(int(x), int(y)) for x, y in polygon]
        except (ValueError, TypeError) as e:
            logger.error('Invalid polygon for %s: %s', region_name, e)
            regions_info.append({'name': region_name, 'value': 'Invalid Polygon', 'polygon': []})
            continue

        region_values = _find_region_values(region_name, stage_tissue_map)

        if region_values:
            value = sum(region_values) / len(region_values)
            if not math.isnan(value):
                values.append(value)
                regions_info.append({
                    'name': region_name,
                    'value': value,
                    'polygon': polygon,
                    'has_data': True
                })
                continue

        regions_info.append({
            'name': region_name,
            'value': 'NA',
            'polygon': polygon,
            'has_data': False
        })

    return regions_info, values


def _find_region_values(region_name, stage_tissue_map):
    """查找区域的表达值：精确 -> 别名 -> 模糊包含"""
    key = region_name.lower()
    # 策略1: 区域名精确匹配（覆盖 0DPA_ovules / 3DPA_fibers 等阶段区域）
    if key in stage_tissue_map:
        return stage_tissue_map[key]

    # 策略2: 别名归一后的组织名匹配
    tissue_key = REGION_ALIASES.get(key, key)
    if tissue_key in stage_tissue_map:
        return stage_tissue_map[tissue_key]

    # 策略3: 模糊包含（兼容 stage 拼写差异）
    values = []
    for k, v in stage_tissue_map.items():
        if tissue_key in k or k in tissue_key:
            values.extend(v)
    return values


def _calculate_value_range(values):
    """计算 log10 缩放的值范围（5%-95% 分位数抗异常值）"""
    if not values:
        return 0, 10, 0, 1

    log_values = np.log10(np.array(values) + 1)
    min_log = np.percentile(log_values, 5)
    max_log = np.percentile(log_values, 95)

    if max_log - min_log < 0.1:
        mean_log = (min_log + max_log) / 2
        min_log = mean_log - 0.05
        max_log = mean_log + 0.05

    return 10 ** min_log - 1, 10 ** max_log - 1, min_log, max_log


def _polygon_area(polygon):
    """鞋带公式计算多边形面积"""
    n = len(polygon)
    if n < 3:
        return 0
    area = 0
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2


def _polygon_centroid(polygon):
    """多边形质心"""
    n = len(polygon)
    if n == 0:
        return (0, 0)
    cx = sum(p[0] for p in polygon) / n
    cy = sum(p[1] for p in polygon) / n
    return (int(cx), int(cy))


def _normalized_value(value, min_log, max_log):
    """log10 归一化到 [0, 1]"""
    log_value = math.log10(value + 1)
    if max_log > min_log:
        return max(0.0, min(1.0, (log_value - min_log) / (max_log - min_log)))
    return 0.5


def _value_color(normalized, cmap):
    """归一化值 -> RGBA 颜色元组"""
    r, g, b, _ = cmap(normalized)
    return (int(r * 255), int(g * 255), int(b * 255))


def _load_font(size):
    """加载字体，失败回退默认"""
    try:
        return ImageFont.truetype('arial.ttf', size)
    except OSError:
        return ImageFont.load_default()


def _draw_heatmap(base_image, regions_info, min_log, max_log,
                  low_color, mid_color, high_color):
    """绘制 EFP 伪彩图：白底遮罩 + 高不透明度纯色 + 深色描边 + 数值标签"""
    image = base_image.copy()
    draw = ImageDraw.Draw(image, 'RGBA')
    cmap = _get_colormap(low_color, mid_color, high_color)

    # 每个器官名对应的最大多边形面积，用于决定是否标注器官名
    name_area = {}
    for region in regions_info:
        if region.get('has_data'):
            area = _polygon_area(region['polygon'])
            if area > name_area.get(region['name'], 0):
                name_area[region['name']] = area

    label_font = _load_font(22)
    value_font = _load_font(20)

    for region in regions_info:
        polygon = region['polygon']
        if not polygon:
            continue

        if not region.get('has_data'):
            # 无数据：浅灰填充 + 灰色描边
            draw.polygon(polygon, fill=(238, 238, 238, FILL_ALPHA))
            closed = polygon + [polygon[0]]
            draw.line(closed, fill=(150, 150, 150, 255), width=3, joint='curve')
            continue

        value = region['value']
        normalized = _normalized_value(value, min_log, max_log)
        color = _value_color(normalized, cmap)

        # 白色打底压住底图本身的颜色，再叠表达色，保证颜色不被底图干扰
        draw.polygon(polygon, fill=(255, 255, 255, 255))
        draw.polygon(polygon, fill=color + (FILL_ALPHA,))
        closed = polygon + [polygon[0]]
        draw.line(closed, fill=(45, 45, 45, 255), width=3, joint='curve')

        region['color'] = color
        region['normalized'] = round(float(normalized), 4)

        # 面积足够大时在质心标注器官名 + 表达值
        area = _polygon_area(polygon)
        if area >= VALUE_LABEL_MIN_AREA:
            cx, cy = _polygon_centroid(polygon)
            # 展示名：去掉下划线换空格（0DPA_ovules -> 0 DPA ovules）
            display = region['name'].replace('_', ' ')
            show_name = area >= name_area[region['name']] * NAME_LABEL_MIN_AREA_RATIO
            text = f'{display}\n{value:.2f}' if show_name else f'{value:.2f}'
            # 白色描边保证任何底色上可读
            draw.text((cx, cy), text, fill=(20, 20, 20, 255), font=value_font,
                      anchor='mm', align='center',
                      stroke_width=2, stroke_fill=(255, 255, 255, 255))
            _ = label_font  # 保留字体变量备用

    return image


def _image_to_base64(image):
    """图像转 Base64"""
    with BytesIO() as buffer:
        image.save(buffer, format='PNG')
        return base64.b64encode(buffer.getvalue()).decode()


def hex_to_rgb(hex_color):
    """十六进制颜色 -> RGB 元组"""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c * 2 for c in hex_color])
    return (
        int(hex_color[0:2], 16),
        int(hex_color[2:4], 16),
        int(hex_color[4:6], 16),
    )


def add_colorbar(draw, image_width, image_height, min_val, max_val,
                 low_color, mid_color, high_color):
    """右侧颜色条图例（白色半透明背板，避免与底图元素混淆）"""
    cmap = _get_colormap(low_color, mid_color, high_color)

    bar_width = 30
    bar_height = 240
    margin = 20
    bar_x = image_width - margin - bar_width - 60
    bar_y = int(image_height * 0.30)

    # 半透明白色背板（含标签区域）
    panel = [
        (bar_x - 14, bar_y - 44),
        (bar_x + bar_width + 92, bar_y + bar_height + 14),
    ]
    draw.rounded_rectangle(panel, radius=10, fill=(255, 255, 255, 215),
                           outline=(120, 120, 120, 255), width=2)

    # 渐变色条
    for i in range(bar_height):
        normalized = i / bar_height
        color = _value_color(normalized, cmap) + (255,)
        y_pos = bar_y + bar_height - i  # 高值在上
        draw.line([(bar_x, y_pos), (bar_x + bar_width, y_pos)], fill=color, width=1)
    draw.rectangle([(bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height)],
                   outline='black', width=2)

    font = _load_font(16)
    title_font = _load_font(17)

    def format_val(v):
        return f'{v:.2f}' if v < 10 else f'{v:.1f}'

    draw.text((bar_x + bar_width + 8, bar_y + bar_height - 8),
              format_val(min_val), fill='black', font=font, anchor='lm')
    draw.text((bar_x + bar_width + 8, bar_y),
              format_val(max_val), fill='black', font=font, anchor='lm')

    mid_val = 10 ** ((math.log10(min_val + 1) + math.log10(max_val + 1)) / 2) - 1
    draw.text((bar_x + bar_width + 8, bar_y + bar_height // 2),
              format_val(mid_val), fill='black', font=font, anchor='lm')

    draw.text((bar_x - 8, bar_y - 36), 'Expression', fill='black',
              font=title_font, anchor='lm')
    draw.text((bar_x - 8, bar_y - 16), '(log scale)', fill=(90, 90, 90),
              font=font, anchor='lm')


def add_gene_info(draw, image_width, image_height, gene_id, valid_count, total_count):
    """顶部标题与统计信息"""
    font = _load_font(26)
    small_font = _load_font(16)

    title = f'Gene: {gene_id}'
    bbox = draw.textbbox((0, 0), title, font=font)
    title_width = bbox[2] - bbox[0]
    draw.text(((image_width - title_width) // 2, 12), title,
              fill='black', font=font,
              stroke_width=1, stroke_fill=(255, 255, 255, 180))

    legend = f'Valid: {valid_count}/{total_count} | Gray: NA'
    draw.text((20, image_height - 30), legend, fill=(90, 90, 90), font=small_font)
