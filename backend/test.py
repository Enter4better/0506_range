# test_direct.py - 直接在代码中写 Key 测试
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# 直接使用 API Key 测试
API_KEY = "sk-065f6a2d4f1b4e06acfaba479a237bbc"

print("=" * 50)
print("直接测试 DeepSeek API")
print("=" * 50)

import requests

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

data = {
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "1+1等于几？"}],
    "max_tokens": 50
}

try:
    print("发送请求...")
    response = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers=headers,
        json=data,
        timeout=30
    )
    
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        content = result['choices'][0]['message']['content']
        print(f"回答: {content}")
        print("✅ API 正常工作")
    else:
        print(f"错误: {response.text}")
        
except Exception as e:
    print(f"异常: {e}")