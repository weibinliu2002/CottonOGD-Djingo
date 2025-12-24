// 显示通知函数
function showNotification(message, type = 'success') {
    // 创建通知元素
    let notification = document.createElement('div');
    notification.className = `notification ${type} alert alert-${type === 'success' ? 'success' : 'danger'} fixed-top left-0 right-0 m-4 p-3 shadow-lg z-50 mx-auto w-50 text-center`;
    notification.textContent = message;
    notification.style.position = 'fixed';
    notification.style.top = '16px';
    notification.style.left = '50%';
    notification.style.transform = 'translateX(-50%)';
    notification.style.zIndex = '1000';
    notification.style.padding = '12px 20px';
    notification.style.borderRadius = '6px';
    notification.style.boxShadow = '0 4px 6px rgba(0, 0, 0, 0.1)';
    notification.style.backgroundColor = type === 'success' ? '#28a745' : '#dc3545';
    notification.style.color = 'white';
    notification.style.fontSize = '16px';
    notification.style.transition = 'opacity 0.5s ease';
    
    // 添加到文档
    document.body.appendChild(notification);
    
    // 3秒后淡出并移除
    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 500);
    }, 800);
}

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
        showNotification('没有可用的序列', 'error');
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
    
    // 下载成功后显示自动消失的通知
    showNotification(`所有${seqType}序列已下载成功`);
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
      // 复制到剪贴板
    navigator.clipboard.writeText(allSequences)
        .then(() => {
            showNotification('Sequence copied to clipboard');
        })
        .catch(err => {
            console.error('Copy failed:', err);
            showNotification('Copy failed. Please copy the sequence manually', 'error');
        });
    if (!hasValidSeq) {
        showNotification('没有可用的序列', 'error');
        return;
    }
    
   
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