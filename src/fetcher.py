"""
外部依赖下载器
处理@require指定的外部库下载
"""

import requests
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


class DependencyFetcher:
    """外部依赖下载器"""

    def __init__(self, lib_dir: Path, timeout: int = 30):
        self.lib_dir = lib_dir
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

    def fetch_all(self, urls: List[str]) -> List[str]:
        """下载所有外部依赖，返回文件名列表"""
        if not urls:
            return []

        # Chrome Web Store警告：检查是否使用了远程依赖
        logger.warning(
            "Chrome Web Store policy: All code must be included in the extension package. "
            f"Downloading {len(urls)} remote dependenc{(y if len(urls) == 1 else 'ies')}. "
            "Ensure these libraries comply with Chrome Web Store policies."
        )

        self.lib_dir.mkdir(parents=True, exist_ok=True)
        downloaded = []

        for url in urls:
            try:
                filename = self.fetch(url)
                if filename:
                    downloaded.append(filename)
                    logger.info(f"Downloaded: {url} -> {filename}")
            except Exception as e:
                logger.error(f"Failed to download {url}: {e}")

        return downloaded

    def fetch(self, url: str) -> Optional[str]:
        """下载单个依赖，返回文件名"""
        # 解析URL获取文件名
        parsed = urlparse(url)
        filename = parsed.path.split('/')[-1]

        # 如果没有扩展名，添加.js
        if not filename.endswith('.js') and '.' not in filename:
            filename += '.js'

        output_path = self.lib_dir / filename

        # 如果文件已存在，跳过
        if output_path.exists():
            logger.info(f"File already exists: {output_path.name}")
            return filename

        # 下载文件
        logger.info(f"Downloading {url}...")
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            # 保存文件
            output_path.write_bytes(response.content)
            return filename

        except requests.RequestException as e:
            logger.error(f"Download failed: {e}")
            return None

    def clear(self):
        """清空lib目录"""
        if self.lib_dir.exists():
            for file in self.lib_dir.iterdir():
                file.unlink()
            logger.info(f"Cleared lib directory: {self.lib_dir}")
