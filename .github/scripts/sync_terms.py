import os
import requests
import json
import time
import sys
from pathlib import Path
from typing import List, Dict, Any

# 配置参数
PARATRANZ_API = "https://paratranz.cn/api"
PROJECT_ID = os.getenv("PARATRANZ_PROJECT_ID")
API_KEY = os.getenv("PARATRANZ_API_KEY")
MAX_RETRIES = 3  # 最大重试次数
RETRY_DELAY = 5  # 重试延迟时间（秒）
REQUEST_TIMEOUT = 30  # 请求超时时间（秒）

# 文件路径
TERMS_DIR = Path(__file__).parent.parent.parent
TERMS_FILE = TERMS_DIR / "terms-13798.json"
LOG_FILE = TERMS_DIR / ".github/logs/sync_terms.log"

def setup_logging():
    """配置日志记录"""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    sys.stdout = sys.stderr = open(LOG_FILE, "a", encoding="utf-8")

def log_error(message: str, error: Exception = None):
    """记录错误日志"""
    error_detail = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "message": message,
        "error": str(error) if error else None
    }
    print(json.dumps(error_detail, ensure_ascii=False, indent=2))

def make_request(method: str, url: str, **kwargs) -> requests.Response:
    """带重试机制的请求函数"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.request(
                method,
                url,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
                **kwargs
            )
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                log_error(f"请求失败，第{attempt + 1}次重试", e)
                time.sleep(RETRY_DELAY)
            else:
                raise

def get_remote_terms() -> List[Dict[str, Any]]:
    """获取远程术语表"""
    url = f"{PARATRANZ_API}/projects/{PROJECT_ID}/terms"
    all_terms = []
    page = 1
    per_page = 100
    
    while True:
        try:
            params = {"page": page, "per_page": per_page}
            response = make_request("GET", url, params=params)
            data = response.json()
            
            if not isinstance(data, dict) or 'results' not in data:
                raise ValueError("远程术语表格式错误")
                
            all_terms.extend(data['results'])
            
            if len(data['results']) < per_page:
                break
                
            page += 1
            time.sleep(1)  # 避免触发频率限制
            
        except Exception as e:
            log_error("获取远程术语表失败", e)
            raise

    return all_terms

def update_remote_terms(terms: List[Dict[str, Any]]) -> Dict[str, Any]:
    """更新远程术语表"""
    url = f"{PARATRANZ_API}/projects/{PROJECT_ID}/terms"
    
    try:
        page_size = 100
        total_pages = (len(terms) + page_size - 1) // page_size
        
        for page in range(total_pages):
            start = page * page_size
            end = start + page_size
            page_terms = terms[start:end]
            
            print(f"正在更新第 {page + 1}/{total_pages} 页，共 {len(page_terms)} 条术语")
            
            response = make_request("POST", url, json=page_terms)
            result = response.json()
            
            if not isinstance(result, dict) or 'message' not in result:
                raise ValueError("API响应格式错误")
                
            print(f"第 {page + 1} 页更新成功")
            time.sleep(1)  # 避免触发频率限制
            
        return {"message": "所有术语更新成功"}
        
    except Exception as e:
        log_error("更新远程术语表失败", e)
        raise

def load_local_terms() -> List[Dict[str, Any]]:
    """加载本地术语表"""
    if not TERMS_FILE.exists():
        return []
    try:
        with open(TERMS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log_error("加载本地术语表失败", e)
        raise

def save_local_terms(terms: List[Dict[str, Any]]):
    """保存本地术语表"""
    try:
        TERMS_DIR.mkdir(exist_ok=True)
        with open(TERMS_FILE, "w", encoding="utf-8") as f:
            json.dump(terms, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log_error("保存本地术语表失败", e)
        raise

def merge_terms(local_terms: List[Dict[str, Any]], remote_terms: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """合并本地和远程术语表"""
    try:
        local_dict = {term.get('id', term.get('term_id')): term for term in local_terms}
        remote_dict = {term['id']: term for term in remote_terms}
        merged_dict = {**local_dict, **remote_dict}
        
        for term in merged_dict.values():
            if 'id' not in term:
                term['id'] = term.get('term_id')
                if 'term_id' in term:
                    del term['term_id']
                    
        return list(merged_dict.values())
    except Exception as e:
        log_error("合并术语表失败", e)
        raise

def sync_terms() -> bool:
    """同步术语表"""
    try:
        setup_logging()
        
        local_terms = load_local_terms()
        remote_terms = get_remote_terms()
        merged_terms = merge_terms(local_terms, remote_terms)
        
        save_local_terms(merged_terms)
        update_remote_terms(merged_terms)
        return True
    except Exception as e:
        log_error("术语表同步失败", e)
        return False

if __name__ == "__main__":
    if not sync_terms():
        sys.exit(1)
    print("术语表同步成功")
