// static/js/main.js
// 收藏功能相关
document.addEventListener('DOMContentLoaded', () => {
    // 初始化收藏状态
    document.querySelectorAll('.heart-icon').forEach(heart => {
        const isLiked = heart.dataset.liked === 'true';
        heart.classList.toggle('liked', isLiked);
        heart.classList.toggle('unliked', !isLiked);
    });

    // 处理图片加载
    document.querySelectorAll('.image-item').forEach(img => {
        const wrapper = img.closest('.image-wrapper');
        
        const handleLoad = () => {
            wrapper.classList.add('loaded');
            wrapper.querySelector('.heart-icon').style.visibility = 'visible'; // 显式设置可见
        };

        if (img.complete) {
            handleLoad();
        } else {
            img.addEventListener('load', handleLoad);
            img.addEventListener('error', handleLoad); // 容错处理
        }
    });
});

// 图片信息展示
const showImageInfo = (path, faceScores, landmarkScores) => {
    const formatScore = (arr) => {
        if (!arr || arr.length === 0) return '无可用数据';
        const avg = arr.reduce((a, b) => a + b, 0) / arr.length;
        return avg.toFixed(4) + ` (${arr.length}个检测结果)`;
    };

    document.getElementById('infoPath').textContent = path;
    document.getElementById('infoFaceScore').textContent = formatScore(faceScores);
    document.getElementById('infoLandmarkScore').textContent = formatScore(landmarkScores);
    document.getElementById('infoModal').style.display = 'flex';
};

// 模态框控制
const closeModal = () => {
    document.getElementById('infoModal').style.display = 'none';
};

window.onclick = (event) => {
    const modal = document.getElementById('infoModal');
    if (event.target === modal) closeModal();
};

// 收藏操作
const toggleLike = (event, path) => {
    event.stopPropagation();
    const heart = event.target;
    const isLiked = heart.classList.contains('liked');

    fetch('/like_image', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 
            path: path,
            action: isLiked ? 'unlike' : 'like' // 根据当前状态切换动作
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 直接切换类，不操作localStorage
            heart.classList.toggle('liked');
            heart.classList.toggle('unliked');
            alert(data.action === 'like' ? '收藏成功' : '已取消收藏');
        } else {
            alert('操作失败');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('操作失败');
    });
};