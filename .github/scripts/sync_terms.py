import os
import requests
import json
import time
from pathlib import Path

# Paratranz API配置
PARATRANZ_API = "https://paratranz.cn/api"
PROJECT_ID = os.getenv("PARATRANZ_PROJECT_ID")
API_KEY = os.getenv("PARATRANZ_API_KEY")

# GitHub术语表路径
TERMS_DIR = Path(__file__).parent.parent.parent  # 指向项目根目录
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
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    all_terms = []
    page = 1
    per_page = 100
    
    while True:
        try:
            # 添加分页参数
            params = {
                "page": page,
                "per_page": per_page
            }
            
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            # 解析响应数据
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError("远程术语表格式错误：期望字典类型")
                
            # 验证分页数据结构
            if 'results' not in data or not isinstance(data['results'], list):
                raise ValueError("远程术语表格式错误：缺少results字段或格式不正确")
                
            # 验证每个术语项格式
            for term in data['results']:
                if not isinstance(term, dict):
                    raise ValueError("术语项格式错误：期望字典类型")
                if 'id' not in term:
                    raise ValueError("术语项缺少id字段")
                    
            all_terms.extend(data['results'])
            
            # 检查是否还有更多数据
            if len(data['results']) < per_page:
                break
                
            page += 1
            time.sleep(1)  # 添加延迟避免触发频率限制
            
        except requests.exceptions.RequestException as e:
            if response.status_code == 500:
                # 记录详细错误信息
                error_detail = {
                    "url": url,
                    "status_code": response.status_code,
                    "response": response.text
                }
                raise Exception(f"API请求失败: {str(e)}\n详细信息: {json.dumps(error_detail, indent=2)}")
            raise Exception(f"API请求失败: {str(e)}")
            
    return all_terms

def update_remote_terms(terms):
    """更新远程术语表"""
    url = f"{PARATRANZ_API}/projects/{PROJECT_ID}/terms"
    headers = {"Authorization": API_KEY}
    try:
        # 验证输入数据格式
        if not isinstance(terms, list):
            raise ValueError("术语表格式错误：期望列表类型")
            
        response = requests.post(url, json=terms, headers=headers)
        response.raise_for_status()
        
        # 验证响应数据
        result = response.json()
        if not isinstance(result, dict) or 'message' not in result:
            raise ValueError("API响应格式错误")
            
        return result
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"API请求失败: {str(e)}")
    except ValueError as e:
        raise Exception(f"数据格式错误: {str(e)}")

def merge_terms(local_terms, remote_terms):
    """合并本地和远程术语表"""
    # 将列表转换为字典，统一使用id作为key
    local_dict = {term.get('id', term.get('term_id')): term for term in local_terms}
    remote_dict = {term['id']: term for term in remote_terms}
    
    # 合并逻辑：远程优先
    merged_dict = {**local_dict, **remote_dict}
    
    # 确保所有术语都有id字段
    for term in merged_dict.values():
        if 'id' not in term:
            term['id'] = term.get('term_id')
            if 'term_id' in term:
                del term['term_id']
                
    return list(merged_dict.values())

def sync_terms():
    """同步术语表"""
    try:
        # 加载本地和远程术语表
        local_terms = load_local_terms()
        remote_terms = get_remote_terms()
        
        # 合并逻辑
        merged_terms = merge_terms(local_terms, remote_terms)
        
        # 更新两端
        save_local_terms(merged_terms)
        update_remote_terms(merged_terms)
        return True
    except Exception as e:
        print(f"同步过程中发生错误: {str(e)}", file=sys.stderr)
        return False

if __name__ == "__main__":
    # 设置系统默认编码为UTF-8
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    if not sync_terms():
        print("术语表同步失败", file=sys.stderr)
        exit(1)
    print("术语表同步成功")
