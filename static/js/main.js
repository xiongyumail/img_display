// static/js/main.js
// 收藏功能相关
document.addEventListener('DOMContentLoaded', () => {
    const heartIcons = document.querySelectorAll('.heart-icon');
    const imageItems = document.querySelectorAll('.image-item');

    // 初始化收藏状态
    heartIcons.forEach(heart => {
        const isLiked = heart.dataset.liked === 'true';
        heart.classList.toggle('liked', isLiked);
        heart.classList.toggle('unliked', !isLiked);
    });

    // 处理图片加载
    imageItems.forEach(img => {
        const wrapper = img.closest('.image-wrapper');
        
        const handleLoad = () => {
            wrapper.classList.add('loaded');
            wrapper.querySelector('.heart-icon').style.visibility = 'visible';
        };

        if (img.complete) {
            handleLoad();
        } else {
            img.addEventListener('load', handleLoad);
            img.addEventListener('error', handleLoad);
        }
    });
});

// 图片信息展示
const showImageInfo = (category, path, faceScores, landmarkScores) => {
    const formatScore = (arr) => {
        if (!arr || arr.length === 0) return '无可用数据';
        const avg = arr.reduce((a, b) => a + b, 0) / arr.length;
        return avg.toFixed(4) + ` (${arr.length}个检测结果)`;
    };

    document.getElementById('infoPath').textContent = path;
    document.getElementById('infoFaceScore').textContent = formatScore(faceScores);
    document.getElementById('infoLandmarkScore').textContent = formatScore(landmarkScores);

    // 更新分类链接
    const categoryLink = document.getElementById('infoCategoryLink');
    categoryLink.href = `/category/${category}`;
    categoryLink.textContent = category;

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
            action: isLiked ? 'unlike' : 'like'
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            heart.classList.toggle('liked');
            heart.classList.toggle('unliked');
        } else {
            alert(`操作失败: ${data.message || '未知错误'}`);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert(`操作失败: ${error.message}`);
    });
};

// 一键点赞所有图片
function BatchLike() {
    const hearts = document.querySelectorAll('.heart-icon');
    const paths = Array.from(hearts).map(heart => heart.dataset.path);

    if (!paths.length) {
        alert('当前页面没有可操作的图片');
        return;
    }

    fetch('/like_image', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            paths: paths,
            action: 'like'
        })
    })
    .then(async response => {
        const data = await response.json();
        if (!response.ok) throw data;
        return data;
    })
    .then(data => {
        hearts.forEach(heart => {
            const path = heart.dataset.path;
            if (data.found.includes(path)) {
                heart.classList.add('liked');
                heart.classList.remove('unliked');
                heart.dataset.liked = 'true';
            }
        });
        
        let message = `成功点赞${data.found.length}张图片`;
        if (data.not_found.length) {
            message += `, ${data.not_found.length}张未找到`;
        }
        alert(message + '!');
    })
    .catch(error => {
        console.error('Error:', error);
        alert(`操作失败: ${error.message || '服务器错误'}`);
    });
}