import json
import os
import math
import logging
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from CottonOGD.models import gene_expression
from io import BytesIO
import base64
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from django.conf import settings
from django.http import JsonResponse


logger = logging.getLogger(__name__)

# 全局变量，标记rpy2是否可用
rpy2_available = False

# 尝试导入rpy2包（仅检查是否存在，不初始化）
try:
    # 设置R_HOME环境变量，解决路径包含空格的问题
    # R安装在 D:\Program Files\R\R-4.5.2
    r_home = r'D:\Program Files\R\R-4.5.2'
    if os.path.exists(r_home):
        os.environ['R_HOME'] = r_home
        logger.info(f'Set R_HOME to: {r_home}')
        
        # 使用rpy2的situation模块来设置R路径
        import rpy2.situation as rpy2_situation
        # 覆盖R的路径设置
        rpy2_situation.R_HOME = r_home
        logger.info(f'Set rpy2.situation.R_HOME to: {r_home}')
    else:
        logger.warning(f'R installation path not found: {r_home}')
    
    import rpy2
    # 尝试初始化R，检查是否真的可用
    try:
        import rpy2.rinterface as rinterface
        # 尝试初始化R（使用系统默认R路径）
        rinterface.initr()
        # 如果成功，标记为可用
        rpy2_available = True
        logger.info('rpy2 package and R initialization successful, will use R for EFP drawing when possible')
    except Exception as init_error:
        # R初始化失败，禁用rpy2
        rpy2_available = False
        logger.warning(f'rpy2 found but R initialization failed: {str(init_error)}, falling back to PIL')
        logger.warning('This is likely due to R installation issues. Please ensure R is properly installed.')
except ImportError as e:
    logger.warning(f'rpy2 not available: {str(e)}, falling back to PIL')
except Exception as e:
    logger.warning(f'Error checking rpy2: {str(e)}, falling back to PIL')

@csrf_exempt
def expression_EFP_image(request):
    """生成热图API - 优化版本"""
    
    try:
        # 1. 参数解析
        data = _parse_request_data(request)
        gene_id = data.get('gene_id')
        if not gene_id:
            return JsonResponse({'success': False, 'error': '请输入基因ID'})

        low_color = data.get('low_color', '#0000FF')
        mid_color = data.get('mid_color', '#00FF00')
        high_color = data.get('high_color', '#FF0000')
        genome_id = data.get('genome_id', 'G.hirsutumAD1_Jin668_HAU_v1T2T')

        logger.info(f'Request: gene_id={gene_id}, genome={genome_id}, '
                   f'colors=({low_color}, {mid_color}, {high_color})')

        # 2. 获取基因数据
        gene_data = list(gene_expression.objects.filter(
            geneid=gene_id, 
            genome=genome_id
        ))
        
        if not gene_data:
            logger.error(f'Gene not found: {gene_id} in {genome_id}')
            return JsonResponse({
                'success': False, 
                'error': f'基因ID "{gene_id}" 在基因组 "{genome_id}" 中不存在'
            })

        # 3. 构建表达值映射
        stage_tissue_map = _build_expression_map(gene_data)
        
        # 4. 加载配置和图像
        regions_config = _load_regions_config()
        base_image = _load_base_image()
        
        # 5. 处理区域数据（单次循环）
        regions_info, values = _process_regions(
            regions_config, 
            stage_tissue_map, 
            base_image
        )

        # 6. 计算值范围（使用对数分位数，避免IQR问题）
        min_val, max_val, min_log, max_log = _calculate_value_range(values)

        # 7. 绘制热图 - 优先使用R绘制
        image = None
        logger.info(f'rpy2_available: {rpy2_available}')
        if rpy2_available:
            try:
                logger.info('Attempting to use R for EFP drawing')
                # 尝试使用R绘制
                image, regions_info = _draw_heatmap_with_r(
                    regions_info, 
                    values,
                    min_val, max_val, min_log, max_log,
                    low_color, mid_color, high_color
                )
                logger.info('Successfully used R for EFP drawing')
            except Exception as e:
                logger.error(f'Error using R: {str(e)}', exc_info=True)
                # 回退到PIL绘制
                image = None
        
        if image is None:
            logger.info('Falling back to PIL for EFP drawing')
            # 使用PIL绘制
            image, regions_info = _draw_heatmap(
                base_image, 
                regions_info, 
                values,
                min_val, max_val, min_log, max_log,
                low_color, mid_color, high_color
            )
            logger.info('Successfully used PIL for EFP drawing')

        # 8. 添加图例和信息（如果是PIL绘制的）
        if isinstance(image, Image.Image):
            draw = ImageDraw.Draw(image, 'RGBA')
            add_colorbar(draw, image.width, image.height, 
                        min_val, max_val, 
                        hex_to_rgb(low_color), 
                        hex_to_rgb(mid_color), 
                        hex_to_rgb(high_color))
            add_gene_info(draw, image.width, gene_id, len(values), len(regions_config['regions']))

        # 9. 生成响应
        if isinstance(image, Image.Image):
            img_str = _image_to_base64(image)
        else:
            # R生成的图像已经是base64
            img_str = image
        
        return JsonResponse({
            'success': True,
            'image': f'data:image/png;base64,{img_str}',
            'regions_info': regions_info,
            'image_width': getattr(image, 'width', 800),
            'image_height': getattr(image, 'height', 600),
            'gene_id': gene_id,
            'genome_id': genome_id,
            'min_value': float(min_val),
            'max_value': float(max_val),
            'valid_regions': len(values),
            'total_regions': len(regions_config['regions']),
            'drawing_method': 'R' if rpy2_available and not isinstance(image, Image.Image) else 'PIL'
        })

    except Exception as e:
        logger.error(f'Error generating heatmap: {str(e)}', exc_info=True)
        return JsonResponse({
            'success': False, 
            'error': f'生成热图时发生错误: {str(e)}'
        })


def _parse_request_data(request):
    """解析请求数据"""
    if request.content_type == 'application/json':
        return json.loads(request.body)
    return request.POST


def _build_expression_map(gene_data):
    """构建阶段-组织到表达值的映射"""
    stage_tissue_map = {}
    
    for item in gene_data:
        stage = (item.stage or '').strip()
        tissue = (item.tissue or '').strip()
        
        if not stage and not tissue:
            continue
            
        # 生成所有可能的键格式
        keys = set()
        base_key = f'{stage}_{tissue}'.lower() if stage and tissue else (stage or tissue).lower()
        keys.add(base_key)
        
        # 添加无下划线版本
        if stage and tissue:
            keys.add(f'{stage}{tissue}'.lower())
            
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


def _process_regions(regions_config, stage_tissue_map, base_image):
    """预处理所有区域，收集值和信息"""
    regions_info = []
    values = []
    
    region_to_tissue = {
        'Stem': 'stem', 'Root': 'root', 'Leaf': 'leaf',
        'Bract': 'bract', 'Sepal': 'sepal', 'Petal': 'petal',
        'Stigma': 'stigma', 'Anther': 'anther', 'Cotyledon': 'cotyledon',
        'Phloem': 'phloem', 'Ovules': 'ovule', 'Seed': 'seed', 'Fiber': 'fiber'
    }
    
    for region in regions_config['regions']:
        region_name = region['name']
        polygon = region.get('polygon', [])
        
        # 验证多边形
        if not polygon:
            regions_info.append({
                'name': region_name,
                'value': 'No Polygon',
                'polygon': []
            })
            continue
            
        try:
            polygon = [(int(x), int(y)) for x, y in polygon]
        except (ValueError, TypeError) as e:
            logger.error(f'Invalid polygon for {region_name}: {e}')
            regions_info.append({
                'name': region_name,
                'value': 'Invalid Polygon',
                'polygon': []
            })
            continue
        
        # 查找表达值
        region_values = _find_region_values(region_name, stage_tissue_map, region_to_tissue)
        
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
        
        # 无数据情况
        regions_info.append({
            'name': region_name,
            'value': 'NA',
            'polygon': polygon,
            'has_data': False
        })
    
    return regions_info, values


def _find_region_values(region_name, stage_tissue_map, region_to_tissue):
    """查找区域的表达值"""
    # 策略1: 直接匹配区域名
    key = region_name.lower()
    if key in stage_tissue_map:
        return stage_tissue_map[key]
    
    # 策略2: 匹配组织类型
    tissue_key = region_to_tissue.get(region_name, region_name).lower()
    if tissue_key in stage_tissue_map:
        return stage_tissue_map[tissue_key]
    
    # 策略3: 模糊匹配
    values = []
    for k, v in stage_tissue_map.items():
        if tissue_key in k:
            values.extend(v)
    return values


def _calculate_value_range(values):
    """计算对数缩放的值范围（修复IQR问题）"""
    if not values:
        min_val, max_val = 0, 10
    else:
        # 使用对数分位数，但确保范围有效
        log_values = np.log10(np.array(values) + 1)
        
        # 使用5%-95%分位数而非IQR，避免异常值过度影响
        min_log = np.percentile(log_values, 5)
        max_log = np.percentile(log_values, 95)
        
        # 确保最小范围，避免除零
        if max_log - min_log < 0.1:
            mean_log = (min_log + max_log) / 2
            min_log = mean_log - 0.05
            max_log = mean_log + 0.05
        
        min_val = 10 ** min_log - 1
        max_val = 10 ** max_log - 1
    
    return min_val, max_val, min_log, max_log


def _draw_heatmap(base_image, regions_info, values, min_val, max_val, 
                  min_log, max_log, low_color, mid_color, high_color):
    """绘制热图"""
    image = base_image.copy()
    draw = ImageDraw.Draw(image, 'RGBA')
    
    low_rgb = hex_to_rgb(low_color)
    mid_rgb = hex_to_rgb(mid_color)
    high_rgb = hex_to_rgb(high_color)
    
    for region in regions_info:
        polygon = region['polygon']
        if not polygon or not region.get('has_data'):
            # 绘制灰色边框表示无数据
            if len(polygon) > 1:
                closed = polygon + [polygon[0]]
                draw.line(closed, fill='gray', width=2, joint='curve')
            continue
        
        # 计算颜色
        value = region['value']
        log_value = math.log10(value + 1)
        
        # 对数归一化
        if max_log > min_log:
            normalized = (log_value - min_log) / (max_log - min_log)
            normalized = max(0, min(1, normalized))
        else:
            normalized = 0.5
        
        # 使用对数感知的颜色映射
        color = _log_aware_color_map(normalized, low_rgb, mid_rgb, high_rgb)
        
        # 绘制
        draw.polygon(polygon, fill=color)
        if len(polygon) > 1:
            closed = polygon + [polygon[0]]
            draw.line(closed, fill='black', width=2, joint='curve')
        
        # 更新区域信息
        region['color'] = color
        region['normalized'] = normalized
    
    return image, regions_info


def _log_aware_color_map(normalized, low_rgb, mid_rgb, high_rgb, alpha=100):
    """对数感知的颜色映射（保持视觉线性）"""
    # 使用指数插值使颜色过渡更符合对数感知
    if normalized < 0.5:
        t = (normalized * 2) ** 0.5  # 指数调整
        r = int(low_rgb[0] + (mid_rgb[0] - low_rgb[0]) * t)
        g = int(low_rgb[1] + (mid_rgb[1] - low_rgb[1]) * t)
        b = int(low_rgb[2] + (mid_rgb[2] - low_rgb[2]) * t)
    else:
        t = ((normalized - 0.5) * 2) ** 2  # 平方调整
        r = int(mid_rgb[0] + (high_rgb[0] - mid_rgb[0]) * t)
        g = int(mid_rgb[1] + (high_rgb[1] - mid_rgb[1]) * t)
        b = int(mid_rgb[2] + (high_rgb[2] - mid_rgb[2]) * t)
    
    return (
        max(0, min(255, r)),
        max(0, min(255, g)),
        max(0, min(255, b)),
        max(0, min(255, alpha))
    )


def _draw_heatmap_with_r(regions_info, values, min_val, max_val, min_log, max_log, low_color, mid_color, high_color):
    """使用R的ggplot2绘制热图"""
    import pandas as pd
    
    # 准备数据
    region_data = []
    for region in regions_info:
        if region.get('has_data'):
            region_data.append({
                'name': region['name'],
                'value': region['value'],
                'normalized': (math.log10(region['value'] + 1) - min_log) / (max_log - min_log) if max_log > min_log else 0.5
            })
    
    if not region_data:
        # 无数据情况，返回空图像
        image = Image.new('RGBA', (800, 600), (255, 255, 255, 255))
        draw = ImageDraw.Draw(image)
        draw.text((400, 300), 'No data available', fill='black', anchor='mm')
        return image, regions_info
    
    # 创建DataFrame
    df = pd.DataFrame(region_data)
    
    try:
        # 延迟导入rpy2组件
        import rpy2.robjects as robjects
        from rpy2.robjects import pandas2ri
        from rpy2.robjects.packages import importr
        
        # 激活pandas2ri
        pandas2ri.activate()
        
        # 设置R选项
        robjects.r('options(warn = -1)')
        
        # 传递数据到R环境
        robjects.globalenv['df'] = pandas2ri.py2rpy(df)
        robjects.globalenv['low_color'] = low_color
        robjects.globalenv['mid_color'] = mid_color
        robjects.globalenv['high_color'] = high_color
        
        # 构建R代码
        r_code = """
        # 设置R库路径
        .libPaths("D:/software/R/Rlib")
        
        # 加载必要的包
        library(ggplot2)
        library(base64enc)
        
        # 保存为临时文件
        temp_file <- tempfile(fileext = '.png')
        
        # 绘制EFP图
        # 尝试使用ggplot2
        try {
            # 直接使用ggplot2绘制
            p <- ggplot(df, aes(x = name, y = 1, fill = normalized)) +
              geom_tile() +
              scale_fill_gradient2(
                low = low_color,
                mid = mid_color,
                high = high_color,
                midpoint = 0.5,
                limits = c(0, 1),
                name = 'Expression Level'
              ) +
              theme_minimal() +
              theme(
                axis.text.x = element_text(angle = 90, hjust = 1, vjust = 0.5),
                axis.title = element_blank(),
                axis.text.y = element_blank(),
                axis.ticks = element_blank(),
                panel.grid = element_blank()
              ) +
              labs(title = 'Expression Pattern')
            
            # 保存为临时文件
            ggsave(temp_file, plot = p, width = 10, height = 6, dpi = 150)
        } catch (error) {
            # 如果出错，使用更简单的绘图方法
            # 创建一个空白图像并添加错误信息
            png(temp_file, width = 10, height = 6, units = "in", res = 150)
            plot(1, type = "n", axes = FALSE, xlab = "", ylab = "")
            text(1, 1, paste("R Error:", as.character(error)), cex = 1.2)
            dev.off()
        }
        
        # 读取文件并转换为base64
        img_data <- readBin(temp_file, 'raw', n = file.size(temp_file))
        base64_str <- base64encode(img_data)
        
        # 返回结果
        list(base64_str = base64_str)
        """
        
        # 执行R代码
        logger.info('Executing R code...')
        result = robjects.r(r_code)
        logger.info(f'R code result type: {type(result)}')
        logger.info(f'R code result: {result}')
        
        # 获取base64字符串
        if result is None:
            raise ValueError('R code returned None')
        
        base64_str = result.rx2('base64_str')
        if base64_str is None:
            raise ValueError('base64_str not found in R result')
        
        base64_str = base64_str[0]
        logger.info(f'Generated base64 string length: {len(base64_str)}')
        return base64_str, regions_info
        
    except Exception as e:
        logger.error(f'Error in R code: {str(e)}', exc_info=True)
        # 回退到默认实现
        image = Image.new('RGBA', (800, 600), (255, 255, 255, 255))
        draw = ImageDraw.Draw(image)
        draw.text((400, 300), f'Error in R drawing: {str(e)}', fill='black', anchor='mm')
        return image, regions_info


def _image_to_base64(image):
    """图像转Base64"""
    with BytesIO() as buffer:
        image.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode()


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


def add_colorbar(draw, image_width, image_height, min_val, max_val, 
                 low_rgb, mid_rgb, high_rgb):
    """添加颜色条图例（修复字体问题）"""
    colorbar_width = 25
    colorbar_height = 150
    margin = 20
    colorbar_x = int(image_width - margin - colorbar_width - 50)
    colorbar_y = int(margin + 50)

    # 绘制渐变色条
    for i in range(colorbar_height):
        normalized = i / colorbar_height
        color = _log_aware_color_map(normalized, low_rgb, mid_rgb, high_rgb, alpha=255)
        y_pos = colorbar_y + colorbar_height - i  # 反转：高值在上
        draw.line([(colorbar_x, y_pos), (colorbar_x + colorbar_width, y_pos)], 
                 fill=color, width=1)

    # 边框
    draw.rectangle([
        (colorbar_x, colorbar_y),
        (colorbar_x + colorbar_width, colorbar_y + colorbar_height)
    ], outline='black', width=2)

    # 标签
    def format_val(v):
        return f"{v:.2f}" if v < 10 else f"{v:.1f}"
    
    # 尝试加载字体，失败则使用默认
    try:
        font = ImageFont.truetype("arial.ttf", 12)
    except:
        font = ImageFont.load_default()

    draw.text((colorbar_x + colorbar_width + 5, colorbar_y + colorbar_height - 10), 
             format_val(min_val), fill='black', font=font)
    draw.text((colorbar_x + colorbar_width + 5, colorbar_y), 
             format_val(max_val), fill='black', font=font)
    
    mid_val = 10 ** ((math.log10(min_val + 1) + math.log10(max_val + 1)) / 2) - 1
    draw.text((colorbar_x + colorbar_width + 5, colorbar_y + colorbar_height//2 - 6), 
             format_val(mid_val), fill='black', font=font)

    draw.text((colorbar_x - 10, colorbar_y - 30), "Expression Level", fill='black', font=font)
    draw.text((colorbar_x - 10, colorbar_y - 15), "(log scale)", fill='black', font=font)


def add_gene_info(draw, image_width, gene_id, valid_count, total_count):
    """添加基因信息和统计（修复坐标计算）"""
    try:
        font = ImageFont.truetype("arial.ttf", 16)
        small_font = ImageFont.truetype("arial.ttf", 12)
    except:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    
    # 标题居中
    title = f"Gene: {gene_id}"
    bbox = draw.textbbox((0, 0), title, font=font)
    title_width = bbox[2] - bbox[0]
    title_x = (image_width - title_width) // 2
    draw.text((title_x, 15), title, fill='black', font=font)

    # 图例说明
    legend = f"Valid: {valid_count}/{total_count} | Gray: NA/Invalid"
    draw.text((20, image_width - 30 if image_width > 600 else 50), 
             legend, fill='gray', font=small_font)
