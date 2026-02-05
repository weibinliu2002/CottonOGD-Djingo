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

// 优化键名
function optimizeKey(key, value) {
  // 1. 移除过长的键名，使用更简洁的版本
  const keyMap = {
    'cottonogd_provides_integrated_genomic_transcriptomic_and_functional_annotation_resources_for_cotton_research_enabling_researchers_to_explore_orthogroups_gene_families_and_evolutionary_relationships_across_cotton_species': 'cottonogd_description',
    'selectedblasttype___blastp__selectedblasttype___blastx___please_enter_a_protein_sequence_in_fasta_or_plain_text_format___please_enter_a_nucleotide_sequence_in_fasta_or_plain_text_format': 'blast_sequence_placeholder',
    'perform_sequence_similarity_searches_against_cotton_genome_databases_using_blast_algorithms_choose_from_different_blast_types_and_customize_your_search_parameters': 'blast_description_long',
    'click_on_a_row_to_check_the_details_of_the_selected_gene': 'click_row_details',
    'close_download_fasta_copy_sequence': 'close_download_copy',
    'gettranscriptlabeltranscript': 'transcript_label',
    'no_significant_kegg_pathway_enrichment_results_found': 'no_kegg_enrichment_results',
    'please_enter_gene_id__eg__gh_a01g0001': 'enter_gene_id_example',
    'youve_successfully_created_a_project_with_vite__vue_3__whats_next': 'vite_project_created'
  };
  
  if (keyMap[key]) {
    return keyMap[key];
  }
  
  // 2. 修复格式问题
  key = key.replace(/label$/, '_label');
  key = key.replace(/^_/, '');
  
  // 3. 确保键名合理长度
  if (key.length > 50) {
    // 对于过长的键名，使用内容的前几个单词
    const words = value.toLowerCase().split(/\s+/);
    const shortKey = words.slice(0, 3).join('_').replace(/[^a-zA-Z0-9_]/g, '');
    return shortKey || key.substring(0, 50);
  }
  
  return key;
}

// 优化配置文件
function optimizeConfig() {
  console.log('Optimizing i18n configuration files...');
  
  // 加载配置
  const enConfig = loadConfig(enConfigPath);
  const zhConfig = loadConfig(zhConfigPath);
  
  // 确保message对象存在
  if (!enConfig.message) enConfig.message = {};
  if (!zhConfig.message) zhConfig.message = {};
  
  // 创建新的配置对象
  const newEnConfig = { message: {} };
  const newZhConfig = { message: {} };
  
  // 处理每个键
  const allKeys = [...new Set([...Object.keys(enConfig.message), ...Object.keys(zhConfig.message)])];
  
  allKeys.forEach(key => {
    const enValue = enConfig.message[key] || '';
    const zhValue = zhConfig.message[key] || '';
    
    // 跳过空值
    if (!enValue && !zhValue) {
      return;
    }
    
    // 优化键名
    const optimizedKey = optimizeKey(key, enValue || zhValue);
    
    // 添加到新配置
    newEnConfig.message[optimizedKey] = enValue;
    newZhConfig.message[optimizedKey] = zhValue;
  });
  
  // 按字母顺序排序
  const sortedEnKeys = Object.keys(newEnConfig.message).sort();
  const sortedZhKeys = Object.keys(newZhConfig.message).sort();
  
  const sortedEnConfig = { message: {} };
  const sortedZhConfig = { message: {} };
  
  sortedEnKeys.forEach(key => {
    sortedEnConfig.message[key] = newEnConfig.message[key];
  });
  
  sortedZhKeys.forEach(key => {
    sortedZhConfig.message[key] = newZhConfig.message[key];
  });
  
  // 保存配置
  saveConfig(enConfigPath, sortedEnConfig);
  saveConfig(zhConfigPath, sortedZhConfig);
  
  console.log('Configuration files optimized successfully!');
  console.log(`English config: ${Object.keys(sortedEnConfig.message).length} keys`);
  console.log(`Chinese config: ${Object.keys(sortedZhConfig.message).length} keys`);
}

// 运行优化
optimizeConfig();
