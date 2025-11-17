// 批量下载所有指定类型的序列
function downloadAllFasta(seqType) {
    let allSequences = '';
    let hasValidSeq = false;
    
    // 直接从DOM中获取序列，避免依赖Django模板渲染的条件判断
    const sequenceBlocks = document.querySelectorAll(`.mb-3.p-2.border.rounded`);
    
    sequenceBlocks.forEach(block => {
        const title = block.querySelector('strong').textContent;
        const sequence = block.querySelector('.bg-light').textContent;
        
        // 根据标题判断序列类型
        if (seqType === 'genomic' && title.includes('genomic')) {
            allSequences += title + '\n' + formatSequence(sequence) + '\n\n';
            hasValidSeq = true;
        } else if (seqType === 'mrna' && title.includes('mrna')) {
            allSequences += title + '\n' + formatSequence(sequence) + '\n\n';
            hasValidSeq = true;
        } else if (seqType === 'cds' && title.includes('cds')) {
            allSequences += title + '\n' + formatSequence(sequence) + '\n\n';
            hasValidSeq = true;
        } else if (seqType === 'protein' && title.includes('protein')) {
            allSequences += title + '\n' + formatSequence(sequence) + '\n\n';
            hasValidSeq = true;
        }
    });
    
    if (!hasValidSeq) {
        alert('没有可用的序列');
        return;
    }
    
    const blob = new Blob([allSequences], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `all_${seqType}_sequences.fasta`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
}

// 批量复制所有指定类型的序列
function copyAllFasta(seqType) {
    let allSequences = '';
    let hasValidSeq = false;
    
    // 直接从DOM中获取序列，避免依赖Django模板渲染的条件判断
    const sequenceBlocks = document.querySelectorAll(`.mb-3.p-2.border.rounded`);
    
    sequenceBlocks.forEach(block => {
        const title = block.querySelector('strong').textContent;
        const sequence = block.querySelector('.bg-light').textContent;
        
        // 根据标题判断序列类型
        if (seqType === 'genomic' && title.includes('genomic')) {
            allSequences += title + '\n' + formatSequence(sequence) + '\n\n';
            hasValidSeq = true;
        } else if (seqType === 'mrna' && title.includes('mrna')) {
            allSequences += title + '\n' + formatSequence(sequence) + '\n\n';
            hasValidSeq = true;
        } else if (seqType === 'cds' && title.includes('cds')) {
            allSequences += title + '\n' + formatSequence(sequence) + '\n\n';
            hasValidSeq = true;
        } else if (seqType === 'protein' && title.includes('protein')) {
            allSequences += title + '\n' + formatSequence(sequence) + '\n\n';
            hasValidSeq = true;
        }
    });
    
    if (!hasValidSeq) {
        alert('没有可用的序列');
        return;
    }
    
    navigator.clipboard.writeText(allSequences).then(function() {
        alert(`所有${seqType}序列已复制到剪贴板`);
    }).catch(function(err) {
        // 降级方案
        const textArea = document.createElement('textarea');
        textArea.value = allSequences;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        alert(`所有${seqType}序列已复制到剪贴板`);
    });
}

// 更新侧翼序列长度（如果需要的话）
function updateFlankingSequences() {
    // 这个函数可以根据需要实现动态更新侧翼序列长度
    // 目前只是占位符
    console.log('侧翼序列长度更新功能');
}

// 辅助函数：格式化序列，每60个字符换行
function formatSequence(sequence) {
    let formatted = '';
    // 移除可能存在的空白字符
    const cleanSequence = sequence.replace(/\s/g, '');
    for (let i = 0; i < cleanSequence.length; i += 60) {
        formatted += cleanSequence.substring(i, i + 60) + '\n';
    }
    return formatted.trim();
}