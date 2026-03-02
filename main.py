import requests
import re
import os
import json
import subprocess
import csv
import sys

# ============================================================
# 配置加载模块
# ============================================================
def load_config():
    """从 config.json 加载系统配置"""
    config_path = 'config.json'
    if not os.path.exists(config_path):
        print(f"错误: 配置文件 {config_path} 不存在！")
        sys.exit(1)
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

# ============================================================
# Cloudflare 数据获取助手
# ============================================================
def get_current_dns_ip(config):
    """获取域名当前在 Cloudflare 上的解析 IP"""
    dns_name = config['cloudflare']['dns_name']
    zone_id = config['cloudflare']['zone_id']
    token = config['cloudflare']['api_token']
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    api_url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
    try:
        res = requests.get(api_url, headers=headers, params={"name": dns_name})
        if res.status_code == 200:
            records = res.json().get('result', [])
            if records:
                return records[0]['content']
    except Exception as e:
        print(f"获取当前 DNS IP 失败: {e}")
    return None

# ============================================================
# IP 采集模块
# ============================================================
def fetch_ips(config, current_ip=None):
    """从多个外部源获取并合并 IP 列表，同时包含当前解析 IP"""
    sources = config.get('settings', {}).get('ip_sources', ["https://ip.v2too.top/"])
    timeout = config.get('settings', {}).get('timeout', 15)
    all_ips = set()
    
    # 如果传入了当前 IP，先加入池中
    if current_ip:
        all_ips.add(current_ip)
        print(f"已将当前解析 IP {current_ip} 加入测试池进行对比。")
    
    # 标准 IPv4 匹配正则表达式
    ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
    
    for url in sources:
        print(f"正在从 {url} 获取 IP 地址...")
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            
            ips = re.findall(ip_pattern, response.text)
            prev_len = len(all_ips)
            all_ips.update(ips)
            print(f"  从该源获取到 {len(ips)} 个 IP，新增有效 IP: {len(all_ips) - prev_len} 个。")
        except Exception as e:
            print(f"  警告: 从 {url} 获取 IP 失败: {e}")
            continue
    
    if not all_ips:
        print("错误: 所有来源均未能获取到任何 IP 地址。")
        return False
        
    print(f"汇总去重后共有 {len(all_ips)} 个待测试 IP。")
    
    # 将 IP 写入本地文件供 cfst.exe 使用
    with open('ip.txt', 'w') as f:
        for ip in all_ips:
            f.write(f"{ip}\n")
    return True

# ============================================================
# 测速与解析模块
# ============================================================
def run_speed_test(config):
    """运行 CloudflareSpeedTest 并解析生成的 CSV 结果"""
    print("正在运行 CloudflareSpeedTest...")
    if not os.path.exists('cfst.exe'):
        print("错误: 未找到 cfst.exe，请确保它位于项目根目录下。")
        return None, None
    
    # 获取配置中的参数
    max_test = config.get('settings', {}).get('max_ips', 100)
    top_n = config.get('settings', {}).get('top_n', 5)
    
    try:
        # 调用命令行工具执行测速
        # input='\n' 模拟回车，解决执行完等待用户按键的问题
        subprocess.run(
            ['cfst.exe', '-f', 'ip.txt', '-o', 'result.csv', '-n', str(max_test), '-dn', str(top_n)], 
            input='\n', text=True, check=True
        )
        
        if os.path.exists('result.csv'):
            # --- 解决 Windows 环境下的乱码问题 ---
            content = None
            for enc in ['utf-8', 'gbk', 'utf-8-sig']:
                try:
                    with open('result.csv', 'r', encoding=enc) as f:
                        content = f.read()
                        break
                except:
                    continue
            
            if content:
                with open('result.csv', 'w', encoding='utf-8-sig') as f:
                    f.write(content)

            # --- 解析 CSV 内容获取最优 IP ---
            with open('result.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                if rows:
                    first_row = rows[0]
                    # 动态匹配列名（处理不同版本可能的差异）
                    ip_key = next((k for k in first_row.keys() if 'IP' in k), 'IP 地址')
                    speed_key = next((k for k in first_row.keys() if '下载' in k and 'MB/s' in k), '下载速度(MB/s)')
                    region_key = next((k for k in first_row.keys() if '地区' in k), '地区码')
                    
                    best_ip = first_row.get(ip_key)
                    download_speed = first_row.get(speed_key)
                    region_code = first_row.get(region_key, '未知')
                    
                    if best_ip:
                        print(f"最优 IP: {best_ip}, 地区: {region_code}, 下载速度: {download_speed} MB/s")
                        return best_ip, download_speed, region_code
        return None, None, None
    except Exception as e:
        print(f"运行测速时发生错误: {e}")
        return None, None, None

# ============================================================
# Cloudflare DNS 更新模块
# ============================================================
def update_cf_dns(config, new_ip):
    """通过 Cloudflare API 更新 A 记录"""
    dns_name = config['cloudflare']['dns_name']
    zone_id = config['cloudflare']['zone_id']
    token = config['cloudflare']['api_token']
    
    print(f"正在更新 Cloudflare DNS 记录 {dns_name} 为 {new_ip}...")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    api_url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
    try:
        res = requests.get(api_url, headers=headers, params={"name": dns_name})
        if res.status_code != 200:
            print(f"API 验证失败: {res.status_code} - {res.text}")
            return False
        
        records = res.json().get('result', [])
        if not records:
            print(f"错误: 未找到域名 {dns_name} 的解析记录。")
            return False
            
        record_id = records[0]['id']
        current_ip = records[0]['content']
        
        if current_ip == new_ip:
            print("当前 IP 已是最优，无需更新。")
            return "NO_CHANGE"

        update_url = f"{api_url}/{record_id}"
        payload = {
            "type": "A",
            "name": dns_name,
            "content": new_ip,
            "ttl": 60,
            "proxied": False
        }
        
        put_res = requests.put(update_url, headers=headers, json=payload)
        if put_res.status_code == 200 and put_res.json().get('success'):
            print("DNS 更新成功！")
            return True
        else:
            print(f"更新失败: {put_res.text}")
            return False
    except Exception as e:
        print(f"Cloudflare 交互异常: {e}")
        return False

# ============================================================
# Telegram 消息推送模块
# ============================================================
def push_notification(config, message):
    """将结果通过 Telegram Bot 推送给一个或多个用户"""
    token = config['telegram']['bot_token']
    chat_ids_str = str(config['telegram']['chat_id'])
    
    # 支持逗号分隔的多用户
    chat_ids = [cid.strip() for cid in chat_ids_str.split(',') if cid.strip()]
    
    for chat_id in chat_ids:
        print(f"正在向 {chat_id} 推送 Telegram 通知...")
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        try:
            requests.post(url, json=payload, timeout=10)
        except Exception as e:
            print(f"向 {chat_id} 推送通知失败: {e}")

# ============================================================
# 主执行流程
# ============================================================
def main():
    # 1. 初始化配置
    config = load_config()
    
    # 2. 先获取当前域名解析的 IP
    current_ip = get_current_dns_ip(config)
    
    # 3. 抓取 IP 库（包含当前 IP）
    if fetch_ips(config, current_ip):
        # 4. 运行测速
        best_ip, speed, region = run_speed_test(config)
        
        if best_ip:
            # 5. 更新 DNS
            update_status = update_cf_dns(config, best_ip)
            
            # 6. 通知结果
            if update_status == True:
                msg = f"✅ <b>CF 优选 IP 更新成功</b>\n域名: <code>{config['cloudflare']['dns_name']}</code>\n解析 IP: <b>{best_ip}</b>\n地区码: <b>{region}</b>\n实测速度: <b>{speed} MB/s</b>"
                push_notification(config, msg)
            elif update_status == "NO_CHANGE":
                print("状态: 当前 IP 依然是最优选择，跳过更新。")
            else:
                msg = f"❌ <b>CF 优选 IP 更新失败</b>\n最优 IP: {best_ip}\n原因: API 调用报错，请检查日志或令牌权限。"
                push_notification(config, msg)
        else:
            print("未能定位到任何有效的最优 IP。")
    else:
        print("停止运行：IP 库加载失败。")

if __name__ == "__main__":
    main()
