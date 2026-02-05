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

// 清理键名
function cleanKey(key) {
  // 移除前导和尾随空格
  key = key.trim();
  
  // 移除前导下划线
  key = key.replace(/^_+/, '');
  
  // 移除尾随冒号
  key = key.replace(/:$/, '');
  
  // 移除括号内的内容
  key = key.replace(/\([^)]+\)/g, '');
  
  // 移除特殊字符，只保留字母、数字、下划线和连字符
  key = key.replace(/[^a-zA-Z0-9_\-]/g, '');
  
  // 转换为小写
  key = key.toLowerCase();
  
  // 替换多个连续的下划线为单个下划线
  key = key.replace(/_+/g, '_');
  
  // 确保键不为空
  if (!key) {
    return null;
  }
  
  return key;
}

// 统一配置文件
function unifyConfig() {
  console.log('Unifying i18n configuration files...');
  
  // 加载配置
  const enConfig = loadConfig(enConfigPath);
  const zhConfig = loadConfig(zhConfigPath);
  
  // 确保message对象存在
  if (!enConfig.message) enConfig.message = {};
  if (!zhConfig.message) zhConfig.message = {};
  
  // 提取所有键
  const enKeys = Object.keys(enConfig.message);
  const zhKeys = Object.keys(zhConfig.message);
  
  // 合并所有键
  const allKeys = [...new Set([...enKeys, ...zhKeys])];
  
  // 创建新的配置对象
  const newEnConfig = { message: {} };
  const newZhConfig = { message: {} };
  
  // 处理每个键
  allKeys.forEach(key => {
    // 清理键名
    const cleanedKey = cleanKey(key);
    if (!cleanedKey) {
      console.log(`Skipping invalid key: ${key}`);
      return;
    }
    
    // 获取值
    const enValue = enConfig.message[key] || '';
    const zhValue = zhConfig.message[key] || '';
    
    // 跳过空值
    if (!enValue && !zhValue) {
      console.log(`Skipping empty key: ${key}`);
      return;
    }
    
    // 添加到新配置
    newEnConfig.message[cleanedKey] = enValue;
    newZhConfig.message[cleanedKey] = zhValue;
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
  
  console.log('Configuration files unified successfully!');
  console.log(`English config: ${Object.keys(sortedEnConfig.message).length} keys`);
  console.log(`Chinese config: ${Object.keys(sortedZhConfig.message).length} keys`);
}

// 运行清理
unifyConfig();
