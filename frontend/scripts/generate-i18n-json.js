import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// 要处理的目录
const directories = [
  '../src/components',
  '../src/views'
];

// 语言配置文件路径
const enConfigPath = path.resolve(__dirname, '../src/locales/i18n/en-US.json');
const zhConfigPath = path.resolve(__dirname, '../src/locales/i18n/zh-CN.json');

// 正则表达式用于提取Vue模板中的文本
const textPatterns = [
  // 提取模板中的纯文本
  /<template[\s\S]*?>([\s\S]*?)<\/template>/,
  // 提取{{}}中的文本
  /{{([^}]+)}}/g,
  // 提取placeholder属性
  /placeholder="([^"]+)"/g,
  // 提取label属性
  /label="([^"]+)"/g,
  // 提取title属性
  /title="([^"]+)"/g,
  // 提取按钮文本
  /<button[^>]*>([\s\S]*?)<\/button>/g,
  // 提取el-button文本
  /<el-button[^>]*>([\s\S]*?)<\/el-button>/g,
  // 提取h1-h6标题
  /<h[1-6][^>]*>([\s\S]*?)<\/h[1-6]>/g,
  // 提取p标签文本
  /<p[^>]*>([\s\S]*?)<\/p>/g,
  // 提取span标签文本
  /<span[^>]*>([\s\S]*?)<\/span>/g
];

// 清理文本函数
function cleanText(text) {
  return text
    .trim()
    .replace(/\s+/g, ' ')
    .replace(/<[^>]+>/g, '') // 移除HTML标签
    .replace(/&nbsp;/g, ' ') // 移除空格实体
    .replace(/&lt;/g, '<') // 还原小于号
    .replace(/&gt;/g, '>') // 还原大于号
    .replace(/&quot;/g, '"') // 还原引号
    .replace(/&#39;/g, "'") // 还原单引号
    .replace(/&amp;/g, '&'); // 还原&符号
}

// 检查文本是否应该被提取
function shouldExtractText(text) {
  // 跳过空文本
  if (!text || text.trim() === '') return false;
  // 跳过纯数字
  if (/^\d+$/.test(text.trim())) return false;
  // 跳过变量表达式（如{{ variable }}）
  if (/^\s*\w+\s*$/.test(text.trim())) return false;
  // 跳过包含模板语法的文本
  if (text.includes('{{') || text.includes('}}')) return false;
  // 跳过只包含特殊字符的文本
  if (/^[^a-zA-Z0-9\u4e00-\u9fa5]+$/.test(text)) return false;
  return true;
}

// 提取Vue文件中的文本
function extractTextFromVueFile(filePath) {
  try {
    const content = fs.readFileSync(filePath, 'utf8');
    const extractedTexts = new Set();
    
    // 提取模板部分
    const templateMatch = content.match(/<template[\s\S]*?>([\s\S]*?)<\/template>/);
    if (!templateMatch) return [];
    
    const templateContent = templateMatch[1];
    
    // 提取placeholder属性
    const placeholderMatches = templateContent.matchAll(/placeholder="([^"]+)"/g);
    for (const match of placeholderMatches) {
      const text = cleanText(match[1]);
      if (shouldExtractText(text)) {
        extractedTexts.add(text);
      }
    }
    
    // 提取label属性
    const labelMatches = templateContent.matchAll(/label="([^"]+)"/g);
    for (const match of labelMatches) {
      const text = cleanText(match[1]);
      if (shouldExtractText(text)) {
        extractedTexts.add(text);
      }
    }
    
    // 提取title属性
    const titleMatches = templateContent.matchAll(/title="([^"]+)"/g);
    for (const match of titleMatches) {
      const text = cleanText(match[1]);
      if (shouldExtractText(text)) {
        extractedTexts.add(text);
      }
    }
    
    // 提取按钮文本
    const buttonMatches = templateContent.matchAll(/<button[^>]*>([\s\S]*?)<\/button>/g);
    for (const match of buttonMatches) {
      const text = cleanText(match[1]);
      if (shouldExtractText(text)) {
        extractedTexts.add(text);
      }
    }
    
    // 提取el-button文本
    const elButtonMatches = templateContent.matchAll(/<el-button[^>]*>([\s\S]*?)<\/el-button>/g);
    for (const match of elButtonMatches) {
      const text = cleanText(match[1]);
      if (shouldExtractText(text)) {
        extractedTexts.add(text);
      }
    }
    
    // 提取h1-h6标题
    const hMatches = templateContent.matchAll(/<h[1-6][^>]*>([\s\S]*?)<\/h[1-6]>/g);
    for (const match of hMatches) {
      const text = cleanText(match[1]);
      if (shouldExtractText(text)) {
        extractedTexts.add(text);
      }
    }
    
    // 提取p标签文本
    const pMatches = templateContent.matchAll(/<p[^>]*>([\s\S]*?)<\/p>/g);
    for (const match of pMatches) {
      const text = cleanText(match[1]);
      if (shouldExtractText(text)) {
        extractedTexts.add(text);
      }
    }
    
    // 提取span标签文本
    const spanMatches = templateContent.matchAll(/<span[^>]*>([\s\S]*?)<\/span>/g);
    for (const match of spanMatches) {
      const text = cleanText(match[1]);
      if (shouldExtractText(text)) {
        extractedTexts.add(text);
      }
    }
    
    return Array.from(extractedTexts);
  } catch (error) {
    console.error(`Error reading file ${filePath}:`, error);
    return [];
  }
}

// 加载现有的语言配置
function loadLanguageConfig(filePath) {
  try {
    const content = fs.readFileSync(filePath, 'utf8');
    return JSON.parse(content);
  } catch (error) {
    console.error(`Error loading language config ${filePath}:`, error);
    return { message: {} };
  }
}

// 保存语言配置
function saveLanguageConfig(filePath, config) {
  try {
    fs.writeFileSync(filePath, JSON.stringify(config, null, 2), 'utf8');
    console.log(`Saved language config to ${filePath}`);
  } catch (error) {
    console.error(`Error saving language config ${filePath}:`, error);
  }
}

// 更新语言配置
function updateLanguageConfig(extractedTexts) {
  // 加载现有配置
  const enConfig = loadLanguageConfig(enConfigPath);
  const zhConfig = loadLanguageConfig(zhConfigPath);
  
  // 确保message对象存在
  if (!enConfig.message) enConfig.message = {};
  if (!zhConfig.message) zhConfig.message = {};
  
  // 更新配置
  extractedTexts.forEach(text => {
    // 生成键名（将文本转换为小写，空格替换为下划线）
    const key = text.toLowerCase().replace(/\s+/g, '_');
    
    // 跳过已经存在的键
    if (enConfig.message[key]) return;
    
    // 添加到英文配置（使用原文）
    enConfig.message[key] = text;
    
    // 添加到中文配置（留空让用户填写）
    zhConfig.message[key] = '';
  });
  
  // 保存配置
  saveLanguageConfig(enConfigPath, enConfig);
  saveLanguageConfig(zhConfigPath, zhConfig);
}

// 遍历目录处理Vue文件
function processDirectory(dirPath) {
  const fullPath = path.resolve(__dirname, dirPath);
  
  if (!fs.existsSync(fullPath)) {
    console.error(`Directory ${fullPath} does not exist`);
    return;
  }
  
  const files = fs.readdirSync(fullPath, { withFileTypes: true });
  
  files.forEach(file => {
    const filePath = path.join(fullPath, file.name);
    
    if (file.isDirectory()) {
      // 递归处理子目录
      processDirectory(path.join(dirPath, file.name));
    } else if (file.isFile() && file.name.endsWith('.vue')) {
      // 处理Vue文件
      console.log(`Processing file: ${filePath}`);
      const texts = extractTextFromVueFile(filePath);
      if (texts.length > 0) {
        console.log(`Extracted ${texts.length} texts from ${filePath}`);
        updateLanguageConfig(texts);
      }
    }
  });
}

// 开始处理
console.log('Generating language configuration files...');

// 清空现有的配置（可选，根据需要取消注释）
// const emptyConfig = { message: {} };
// saveLanguageConfig(enConfigPath, emptyConfig);
// saveLanguageConfig(zhConfigPath, emptyConfig);

directories.forEach(dir => {
  console.log(`Processing directory: ${dir}`);
  processDirectory(dir);
});

console.log('Language configuration files generated successfully!');

