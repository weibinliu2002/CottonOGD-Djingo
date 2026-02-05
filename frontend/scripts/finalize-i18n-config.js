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

// 清理重复项和优化配置
function finalizeConfig() {
  console.log('Finalizing i18n configuration files...');
  
  // 加载配置
  const enConfig = loadConfig(enConfigPath);
  const zhConfig = loadConfig(zhConfigPath);
  
  // 确保message对象存在
  if (!enConfig.message) enConfig.message = {};
  if (!zhConfig.message) zhConfig.message = {};
  
  // 定义重复键映射（保留一个，删除其他）
  const duplicateMap = {
    'contact': 'contact_us',
    'gene_basic_info': 'gene_basic_information',
    'gene_expression_efp': 'gene_expression_in_efp',
    'evalue': 'e_value'
  };
  
  // 创建新的配置对象
  const newEnConfig = { message: {} };
  const newZhConfig = { message: {} };
  
  // 处理英文配置
  Object.keys(enConfig.message).forEach(key => {
    // 跳过重复键
    if (Object.keys(duplicateMap).includes(key)) {
      return;
    }
    
    // 优化键名
    let optimizedKey = key;
    if (optimizedKey === 'download_genome-related_files_for_cotton_research') {
      optimizedKey = 'download_genome_files';
    } else if (optimizedKey === 'get_in_touch_with_the_cottonogd_team') {
      optimizedKey = 'get_in_touch';
    } else if (optimizedKey === 'this_page_is_under_development') {
      optimizedKey = 'page_under_development';
    }
    
    newEnConfig.message[optimizedKey] = enConfig.message[key];
  });
  
  // 处理中文配置
  Object.keys(zhConfig.message).forEach(key => {
    // 跳过重复键
    if (Object.keys(duplicateMap).includes(key)) {
      return;
    }
    
    // 优化键名
    let optimizedKey = key;
    if (optimizedKey === 'download_genome-related_files_for_cotton_research') {
      optimizedKey = 'download_genome_files';
    } else if (optimizedKey === 'get_in_touch_with_the_cottonogd_team') {
      optimizedKey = 'get_in_touch';
    } else if (optimizedKey === 'this_page_is_under_development') {
      optimizedKey = 'page_under_development';
    }
    
    newZhConfig.message[optimizedKey] = zhConfig.message[key];
  });
  
  // 确保两个配置文件的键一致
  const enKeys = Object.keys(newEnConfig.message);
  const zhKeys = Object.keys(newZhConfig.message);
  
  // 添加缺失的键
  enKeys.forEach(key => {
    if (!newZhConfig.message[key]) {
      newZhConfig.message[key] = '';
    }
  });
  
  zhKeys.forEach(key => {
    if (!newEnConfig.message[key]) {
      newEnConfig.message[key] = '';
    }
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
  
  console.log('Configuration files finalized successfully!');
  console.log(`English config: ${Object.keys(sortedEnConfig.message).length} keys`);
  console.log(`Chinese config: ${Object.keys(sortedZhConfig.message).length} keys`);
}

// 运行最终优化
finalizeConfig();
