import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// 语言配置文件路径
const enConfigPath = path.resolve(__dirname, '../src/locales/i18n/en-US.json');
const zhConfigPath = path.resolve(__dirname, '../src/locales/i18n/zh-CN.json');

// 加载配置文件
function loadConfig(filePath) {
  try {
    const content = fs.readFileSync(filePath, 'utf8');
    return JSON.parse(content);
  } catch (error) {
    console.error(`Error loading config file ${filePath}:`, error);
    return { message: {} };
  }
}

// 保存配置文件
function saveConfig(filePath, config) {
  try {
    fs.writeFileSync(filePath, JSON.stringify(config, null, 2), 'utf8');
    console.log(`Saved config to ${filePath}`);
  } catch (error) {
    console.error(`Error saving config file ${filePath}:`, error);
  }
}

// 翻译映射
const translationMap = {
  "a_comprehensive_cotton_orthogroups_database": "一个综合性棉花直系同源群数据库",
  "about_ogd": "关于OGD",
  "annotated_transcription_factors": "注释的转录因子",
  "biological_process": "生物学过程",
  "blast_description_long": "使用BLAST算法对棉花基因组数据库进行序列相似性搜索。选择不同的BLAST类型并自定义搜索参数。",
  "category_label": "类别标签",
  "cellular_component": "细胞组分",
  "click_row_details": "点击一行以查看所选基因的详细信息",
  "close_download_copy": "关闭 下载FASTA 复制序列",
  "cottonogd_description": "CottonOGD提供棉花研究的整合基因组、转录组和功能注释资源，使研究人员能够探索棉花物种间的直系同源群、基因家族和进化关系。",
  "design_parameters": "设计参数",
  "download_data": "下载数据",
  "download_genome_files": "下载棉花研究相关的基因组文件",
  "enter_gene_id_symbol_keyword_or_sequence": "输入基因ID、符号、关键词或序列...",
  "expression_data": "表达数据",
  "gene_basic_information": "基因基本信息",
  "gene_expression_analysis": "基因表达分析",
  "gene_expression_analysis_results": "基因表达分析结果",
  "gene_expression_in_efp": "eFP中的基因表达",
  "genometype_label": "基因组类型标签",
  "get_in_touch": "与CottonOGD团队取得联系",
  "gettranscript_label": "getTranscriptLabel(transcript)",
  "go": "GO注释分布",
  "go_annotation_analysis": "GO注释分析",
  "go_enrichment_analysis": "GO富集分析",
  "go_enrichment_analysis_results": "GO富集分析结果",
  "id": "ID搜索结果汇总",
  "input_gene_ids": "输入基因ID",
  "jbrowse_view": "JBrowse视图",
  "jbrowse_views_": "JBrowse视图 ",
  "jbrowse_visualization": "JBrowse可视化",
  "kegg_annotation_results": "KEGG注释结果",
  "kegg_annotation_search": "KEGG注释搜索",
  "kegg_enrichment_plot": "KEGG富集分析图",
  "kegg_pathway": "KEGG通路",
  "kegg_pathway_enrichment_analysis": "KEGG通路富集分析",
  "kegg_pathway_enrichment_analysis_results": "KEGG通路富集分析结果",
  "load_example": "加载示例",
  "load_example_sequence": " 加载示例序列",
  "molecular_function": "分子功能",
  "no_enrichment_results_found": "未找到富集分析结果",
  "no_genome_data_available": "暂无基因组数据",
  "no_kegg_enrichment_results": "未找到显著的KEGG通路富集分析结果",
  "no_results_found": "未找到结果。请尝试使用不同的基因ID。",
  "ogd_is_a": "OGD是一个用于探索和分析遗传数据的平台。",
  "page_under_development": "此页面正在开发中...",
  "pathway_id": "通路ID",
  "please_enter_gene_id_eg_gh_a01g0001": "请输入基因ID，例如：Gh_A01G0001",
  "please_enter_gene_ids_one_per_line": "请输入基因ID，每行一个",
  "query_id": "查询ID",
  "refresh_data": " 刷新数据",
  "refresh_view": "刷新视图",
  "reset_form": " 重置表单",
  "results_per_page": "每页结果数：",
  "return_to_search": "返回搜索",
  "run_blast_search": " 运行BLAST搜索",
  "search_by_id": "按ID搜索",
  "search_results": "搜索结果",
  "select_a_genome": " 选择一个基因组",
  "select_file": " 选择文件",
  "select_genome": "选择基因组",
  "select_genome_category": "选择基因组类别",
  "selectedblasttype__blastp": "selectedBlastType === 'blastp' || selectedBlastType === 'blastx' ? '请输入FASTA或纯文本格式的蛋白质序列' : '请输入FASTA或纯文本格式的核苷酸序列'",
  "show": "显示：",
  "tf_class": "转录因子类别",
  "tf_name": "转录因子名称",
  "transcription_factors_": "转录因子 ",
  "type_label": "类型标签",
  "upload_file": " 上传文件",
  "welcome_to_cottonogd": "欢迎使用CottonOGD",
  "youve_successfully_created": "您已成功创建了一个Vite + Vue 3项目。接下来做什么？"
};

// 翻译配置文件
function translateConfig() {
  console.log('Translating Chinese i18n configuration file...');
  
  // 加载配置
  const enConfig = loadConfig(enConfigPath);
  const zhConfig = loadConfig(zhConfigPath);
  
  // 确保message对象存在
  if (!enConfig.message) enConfig.message = {};
  if (!zhConfig.message) zhConfig.message = {};
  
  // 翻译每个键
  Object.keys(enConfig.message).forEach(key => {
    // 如果中文配置中没有该键或值为空，进行翻译
    if (!zhConfig.message[key] || zhConfig.message[key] === '') {
      if (translationMap[key]) {
        zhConfig.message[key] = translationMap[key];
      } else {
        // 对于没有映射的键，进行简单处理
        let translation = enConfig.message[key];
        // 一些常见的翻译
        translation = translation.replace(/BLAST/g, 'BLAST');
        translation = translation.replace(/FASTA/g, 'FASTA');
        translation = translation.replace(/GO/g, 'GO');
        translation = translation.replace(/KEGG/g, 'KEGG');
        translation = translation.replace(/eFP/g, 'eFP');
        translation = translation.replace(/JBrowse/g, 'JBrowse');
        translation = translation.replace(/Gene ID/g, '基因ID');
        translation = translation.replace(/Genome/g, '基因组');
        translation = translation.replace(/Sequence/g, '序列');
        translation = translation.replace(/Results/g, '结果');
        translation = translation.replace(/Search/g, '搜索');
        translation = translation.replace(/Analysis/g, '分析');
        translation = translation.replace(/Annotation/g, '注释');
        translation = translation.replace(/Enrichment/g, '富集');
        translation = translation.replace(/Pathway/g, '通路');
        translation = translation.replace(/Expression/g, '表达');
        translation = translation.replace(/Transcript/g, '转录本');
        translation = translation.replace(/Protein/g, '蛋白质');
        translation = translation.replace(/Primer/g, '引物');
        translation = translation.replace(/Length/g, '长度');
        translation = translation.replace(/Score/g, '得分');
        translation = translation.replace(/Value/g, '值');
        translation = translation.replace(/Type/g, '类型');
        translation = translation.replace(/Database/g, '数据库');
        translation = translation.replace(/File/g, '文件');
        translation = translation.replace(/Download/g, '下载');
        translation = translation.replace(/Upload/g, '上传');
        translation = translation.replace(/Copy/g, '复制');
        translation = translation.replace(/Close/g, '关闭');
        translation = translation.replace(/Open/g, '打开');
        translation = translation.replace(/Save/g, '保存');
        translation = translation.replace(/Delete/g, '删除');
        translation = translation.replace(/Edit/g, '编辑');
        translation = translation.replace(/Reset/g, '重置');
        translation = translation.replace(/Clear/g, '清空');
        translation = translation.replace(/Submit/g, '提交');
        translation = translation.replace(/Cancel/g, '取消');
        translation = translation.replace(/Confirm/g, '确认');
        translation = translation.replace(/Select/g, '选择');
        translation = translation.replace(/All/g, '全部');
        translation = translation.replace(/None/g, '无');
        translation = translation.replace(/First/g, '首页');
        translation = translation.replace(/Last/g, '末页');
        translation = translation.replace(/Previous/g, '上一页');
        translation = translation.replace(/Next/g, '下一页');
        translation = translation.replace(/Please/g, '请');
        translation = translation.replace(/Enter/g, '输入');
        translation = translation.replace(/Input/g, '输入');
        translation = translation.replace(/Choose/g, '选择');
        translation = translation.replace(/Customize/g, '自定义');
        translation = translation.replace(/Parameters/g, '参数');
        translation = translation.replace(/Options/g, '选项');
        translation = translation.replace(/Settings/g, '设置');
        translation = translation.replace(/Info/g, '信息');
        translation = translation.replace(/Error/g, '错误');
        translation = translation.replace(/Warning/g, '警告');
        translation = translation.replace(/Success/g, '成功');
        translation = translation.replace(/Loading/g, '加载中');
        translation = translation.replace(/Waiting/g, '等待中');
        translation = translation.replace(/Processing/g, '处理中');
        translation = translation.replace(/Complete/g, '完成');
        translation = translation.replace(/Failed/g, '失败');
        translation = translation.replace(/Found/g, '找到');
        translation = translation.replace(/NotFound/g, '未找到');
        translation = translation.replace(/Available/g, '可用');
        translation = translation.replace(/Unavailable/g, '不可用');
        translation = translation.replace(/Under Development/g, '正在开发中');
        translation = translation.replace(/Coming Soon/g, '即将推出');
        
        zhConfig.message[key] = translation;
      }
    }
  });
  
  // 保存配置
  saveConfig(zhConfigPath, zhConfig);
  
  console.log('Chinese translation completed successfully!');
  console.log(`Total keys: ${Object.keys(zhConfig.message).length}`);
}

// 运行翻译
translateConfig();
