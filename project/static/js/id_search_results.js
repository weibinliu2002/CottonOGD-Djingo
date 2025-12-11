// 下载Fasta格式序列
function downloadFasta(geneId, seqType, sequence) {
    if (!sequence || sequence === 'N/A') {
        alert('No available sequence to download.');
        return;
    }
    
    // 准备序列标题
    let title = `>${geneId} ${seqType}`;
    if (seqType === 'protein') {
        title = `>${geneId} protein`;
    }
    
    // 准备Fasta内容（每60个字符换行）
    let fastaContent = title + '\n';
    for (let i = 0; i < sequence.length; i += 60) {
        fastaContent += sequence.substring(i, i + 60) + '\n';
    }
    
    // 创建Blob对象
    const blob = new Blob([fastaContent], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    
    // 创建下载链接并触发下载
    const a = document.createElement('a');
    a.href = url;
    a.download = `${geneId}_${seqType}.fasta`;
    document.body.appendChild(a);
    a.click();
    
    // 清理
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// 复制Fasta格式序列到剪贴板
function copyFasta(geneId, seqType, sequence) {
    if (!sequence || sequence === 'N/A') {
        alert('No available sequence to copy.');
        return;
    }
    
    // 准备序列标题
    let title = `>${geneId} ${seqType}`;
    if (seqType === 'protein') {
        title = `>${geneId} protein`;
    }
    
    // 准备Fasta内容（每60个字符换行）
    let fastaContent = title + '\n';
    for (let i = 0; i < sequence.length; i += 60) {
        fastaContent += sequence.substring(i, i + 60) + '\n';
    }
    
    // 复制到剪贴板
    navigator.clipboard.writeText(fastaContent)
        .then(() => {
            showNotification('Sequence copied to clipboard');
        })
        .catch(err => {
            console.error('Copy failed:', err);
            showNotification('Copy failed. Please copy the sequence manually', 'error');
        });
}

// 更新上下游序列函数
function updateFlankingSequences() {
    // 获取选择的长度值
    const upstreamLength = document.getElementById('upstream_length_selector').value;
    
    // 获取当前基因ID（假设每个基因结果都有对应的元素结构）
    const geneResults = document.querySelectorAll('.gene-result');
    
    geneResults.forEach(resultElement => {
        const geneId = resultElement.getAttribute('data-gene-id');
        
        // 显示加载状态
        const upstreamSeqElement = resultElement.querySelector('.upstream-sequence');
        const downstreamSeqElement = resultElement.querySelector('.downstream-sequence');
        
        if (upstreamSeqElement) upstreamSeqElement.textContent = 'Loading...';
        if (downstreamSeqElement) downstreamSeqElement.textContent = 'Loading...';
        
        // 发送AJAX请求获取新长度的序列
        fetch(`/tools/id_search/get_flanking_sequences/${geneId}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({
                upstream_length: upstreamLength,
                downstream_length: upstreamLength
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // 更新显示的序列
                if (upstreamSeqElement) upstreamSeqElement.textContent = data.upstream_seq || 'N/A';
                if (downstreamSeqElement) downstreamSeqElement.textContent = data.downstream_seq || 'N/A';
                
                // 更新区域信息
                if (data.upstream_region && resultElement.querySelector('.upstream-region')) {
                    resultElement.querySelector('.upstream-region').textContent = data.upstream_region;
                }
                if (data.downstream_region && resultElement.querySelector('.downstream-region')) {
                    resultElement.querySelector('.downstream-region').textContent = data.downstream_region;
                }
            } else {
                showNotification(data.error || 'Failed to update sequences', 'error');
                if (upstreamSeqElement) upstreamSeqElement.textContent = 'Error';
                if (downstreamSeqElement) downstreamSeqElement.textContent = 'Error';
            }
        })
        .catch(error => {
            console.error('Error updating flanking sequences:', error);
            showNotification('Error updating sequences', 'error');
            if (upstreamSeqElement) upstreamSeqElement.textContent = 'Error';
            if (downstreamSeqElement) downstreamSeqElement.textContent = 'Error';
        });
    });
}

// 获取CSRF Token的辅助函数
function getCSRFToken() {
    const cookieValue = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrftoken='))
        ?.split('=')[1];
    return cookieValue || '';
}

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