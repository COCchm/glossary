import os
import requests
import json
from pathlib import Path

# Paratranz API配置
PARATRANZ_API = "https://paratranz.cn/api"
PROJECT_ID = os.getenv("PARATRANZ_PROJECT_ID")
API_KEY = os.getenv("PARATRANZ_API_KEY")

# GitHub术语表路径
TERMS_DIR = Path("D:/COC不全书/glossary")
TERMS_FILE = TERMS_DIR / "terms-13798.json"

def load_local_terms():
    """加载本地术语表"""
    if not TERMS_FILE.exists():
        return []
    with open(TERMS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_local_terms(terms):
    """保存本地术语表"""
    TERMS_DIR.mkdir(exist_ok=True)
    with open(TERMS_FILE, "w", encoding="utf-8") as f:
        json.dump(terms, f, ensure_ascii=False, indent=2)

def get_remote_terms():
    """获取远程术语表"""
    url = f"{PARATRANZ_API}/projects/{PROJECT_ID}/terms"
    headers = {"Authorization": API_KEY}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"获取远程术语表失败: {response.status_code}")
    return response.json()

def update_remote_terms(terms):
    """更新远程术语表"""
    url = f"{PARATRANZ_API}/projects/{PROJECT_ID}/terms"
    headers = {"Authorization": API_KEY}
    response = requests.post(url, json=terms, headers=headers)
    if response.status_code != 200:
        raise Exception(f"更新远程术语表失败: {response.status_code}")

def merge_terms(local_terms, remote_terms):
    """合并本地和远程术语表"""
    # 将列表转换为字典，以term_id为key
    local_dict = {term['term_id']: term for term in local_terms}
    remote_dict = {term['term_id']: term for term in remote_terms}
    
    # 合并逻辑：远程优先
    merged_dict = {**local_dict, **remote_dict}
    return list(merged_dict.values())

def sync_terms():
    """同步术语表"""
    # 加载本地和远程术语表
    local_terms = load_local_terms()
    remote_terms = get_remote_terms()
    
    # 合并逻辑
    merged_terms = merge_terms(local_terms, remote_terms)
    
    # 更新两端
    save_local_terms(merged_terms)
    update_remote_terms(merged_terms)

if __name__ == "__main__":
    try:
        # 设置标准输出编码为UTF-8
        import sys
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        
        sync_terms()
        print("术语表同步成功")
    except Exception as e:
        print(f"术语表同步失败: {str(e)}")
        exit(1)
