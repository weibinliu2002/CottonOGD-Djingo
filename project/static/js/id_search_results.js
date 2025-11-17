// 基因结构图渲染函数 - 接受参数而不是直接使用模板变量
function renderGeneStructure(canvasId, geneData) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    
    // 清除画布
    ctx.clearRect(0, 0, width, height);
    
    // 设置样式
    ctx.font = '12px Arial';
    ctx.fillStyle = '#333';
    
    // 计算缩放比例
    const geneLength = geneData.end - geneData.start + 1;
    const padding = 50;
    const availableWidth = width - 2 * padding;
    const scale = availableWidth / geneLength;
    
    // 绘制基因区域背景
    ctx.fillStyle = '#f0f0f0';
    ctx.fillRect(padding, height/2 - 10, availableWidth, 20);
    ctx.strokeStyle = '#999';
    ctx.strokeRect(padding, height/2 - 10, availableWidth, 20);
    
    // 绘制坐标轴刻度和标签
    ctx.fillStyle = '#333';
    const numTicks = 5;
    for (let i = 0; i <= numTicks; i++) {
        const x = padding + (availableWidth / numTicks) * i;
        const pos = geneData.start + (geneLength / numTicks) * i;
        
        // 刻度线
        ctx.beginPath();
        ctx.moveTo(x, height/2 - 15);
        ctx.lineTo(x, height/2 + 15);
        ctx.stroke();
        
        // 标签
        ctx.fillText(pos.toLocaleString(), x - 20, height/2 + 30);
    }
    
    // 绘制外显子
    if (geneData.exons && geneData.exons.length > 0) {
        geneData.exons.forEach(exon => {
            const exonStartX = padding + (exon.start - geneData.start) * scale;
            const exonWidth = (exon.end - exon.start + 1) * scale;
            
            // 外显子矩形
            ctx.fillStyle = '#4285f4';
            ctx.fillRect(exonStartX, height/2 - 15, exonWidth, 30);
            ctx.strokeStyle = '#2b5797';
            ctx.strokeRect(exonStartX, height/2 - 15, exonWidth, 30);
        });
    }
    // 绘制内含子连接线（如果有多个外显子）
    if (geneData.exons && geneData.exons.length > 1) {
        ctx.strokeStyle = '#333';
        ctx.lineWidth = 2;
        
        for (let i = 0; i < geneData.exons.length - 1; i++) {
            const currentExon = geneData.exons[i];
            const nextExon = geneData.exons[i + 1];
            
            const currentEndX = padding + (currentExon.end - geneData.start) * scale;
            const nextStartX = padding + (nextExon.start - geneData.start) * scale;
            
            ctx.beginPath();
            ctx.moveTo(currentEndX, height/2);
            ctx.lineTo(nextStartX, height/2);
            ctx.stroke();
        }
    }
    
    // 绘制CDS区域（如果有）
    if (geneData.cds_regions && geneData.cds_regions.length > 0) {
        geneData.cds_regions.forEach(cds => {
            const cdsStartX = padding + (cds.start - geneData.start) * scale;
            const cdsWidth = (cds.end - cds.start + 1) * scale;
            
            // CDS矩形（在现有外显子上覆盖更深的颜色）
            ctx.fillStyle = '#34a853';
            ctx.fillRect(cdsStartX, height/2 - 12, cdsWidth, 24);
        });
    }
    
    // 绘制转录方向箭头
    const arrowX = geneData.strand === '+' 
        ? padding + availableWidth - 10 
        : padding + 10;
    
    ctx.fillStyle = '#ea4335';
    ctx.beginPath();
    if (geneData.strand === '+') {
        // 向右箭头
        ctx.moveTo(arrowX, height/2 - 10);
        ctx.lineTo(arrowX + 15, height/2);
        ctx.lineTo(arrowX, height/2 + 10);
    } else {
        // 向左箭头
        ctx.moveTo(arrowX, height/2 - 10);
        ctx.lineTo(arrowX - 15, height/2);
        ctx.lineTo(arrowX, height/2 + 10);
    }
    ctx.closePath();
    ctx.fill();
}

// 显示/隐藏ID列表函数
function toggleIDs(button) {
    const hiddenIDs = button.previousElementSibling;
    if (hiddenIDs.style.display === 'none') {
        hiddenIDs.style.display = 'inline';
        button.textContent = '收起';
    } else {
        hiddenIDs.style.display = 'none';
        button.textContent = '展开';
    }
}

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