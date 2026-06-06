import os
import requests
import json

# 从环境变量读取 API Key，不再硬编码
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
BASE_URL = os.environ.get("TARGET_LLM", "https://api.deepseek.com")

def test_deepseek_api():
    """测试 DeepSeek API 连通性"""
    if not DEEPSEEK_API_KEY:
        print("❌ 请设置环境变量 DEEPSEEK_API_KEY")
        return False

    print(f"🔍 测试 API 连通性...")
    print(f"   Base URL: {BASE_URL}")
    print(f"   API Key: {DEEPSEEK_API_KEY[:4]}...{DEEPSEEK_API_KEY[-4:]}")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": "请回复一句话测试"}
        ],
        "stream": False,
        "max_tokens": 100
    }

    try:
        response = requests.post(
            f"{BASE_URL}/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        print(f"\n✅ API 请求成功，状态码: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"\n📤 响应: {json.dumps(result, indent=2, ensure_ascii=False)}")

            if "choices" in result:
                content = result["choices"][0]["message"]["content"]
                print(f"\n💬 模型回复: {content}")
                return True
        return False

    except Exception as e:
        print(f"\n❌ 请求失败: {e}")
        return False

if __name__ == "__main__":
    test_deepseek_api()
