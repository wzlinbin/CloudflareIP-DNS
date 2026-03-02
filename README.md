# CF-IP-AutoUpdate: Cloudflare 优选 IP 自动更新系统

基于 [CloudflareSpeedTest](https://github.com/XIU2/CloudflareSpeedTest) 的全自动优选 IP 抓取、测速并更新至 Cloudflare DNS 的工具。

## 🌟 核心特性

-   **多源 IP 抓取**：支持从多个主流优选 IP 提供商（如 `v2too.top`、`uouin.com`、`wetest.vip`）自动汇总并去重。
-   **智能对比更新**：自动获取当前域名的解析 IP 并加入测速。只有当新 IP 确实比现有 IP 更快时，才会触发 DNS 更新，避免频繁跳变。
-   **全自动化运行**：完美适配 `cfst.exe`，解决了测速结束需手动按回车的问题，实现真正的无人值守。
-   **多端通知推送**：支持 Telegram Bot 实时推送更新结果，可配置多个接收人 ID。
-   **编码修复**：生成的 `result.csv` 自动转换为带 BOM 的 UTF-8 编码，防止 Windows Excel 查看时出现乱码。
-   **开箱即用**：提供打包好的 `.exe` 版本，无需安装 Python。

## 🛠️ 快速上手

### 1. 准备工作
-   获取 [Cloudflare API 令牌](https://dash.cloudflare.com/profile/api-tokens) (需具备 `DNS:Edit` 权限)。
-   获取 Cloudflare 域名的 `Zone ID`。
-   准备一个 [Telegram Bot](https://t.me/BotFather) 及其 `Token` 与您的 `Chat ID`。
-   下载本仓库，并确保当前目录下存在 `cfst.exe` (CloudflareSpeedTest)。

### 2. 配置 `config.json`
在程序根目录下创建 `config.json`：

```json
{
  "cloudflare": {
    "api_token": "您的 Cloudflare Scoped Token",
    "zone_id": "对应的区域 ID",
    "dns_name": "想要更新的域名 (如 cf.yourdomain.com)"
  },
  "telegram": {
    "bot_token": "您的 TG Bot Token",
    "chat_id": "您的 Chat ID (多个 ID 用逗号分隔)"
  },
  "settings": {
    "ip_sources": [
      "https://ip.v2too.top/",
      "https://api.uouin.com/cloudflare.html",
      "https://www.wetest.vip/page/cloudflare/address_v4.ht"
    ],
    "max_ips": 100,
    "top_n": 10,
    "timeout": 15
  }
}
```

### 3. 运行程序
-   **Python 运行**：`pip install requests` 然后运行 `python main.py`。
-   **EXE 运行**：直接双击运行 `CF_AutoUpdate.exe`。

## ⏱️ 实现定时更新 (Windows)

1.  打开 **任务计划程序**。
2.  创建基本任务，触发器设为 **每小时一次** (或根据需要调整)。
3.  操作选择 **启动程序**：
    -   程序或脚本：指向 `CF_AutoUpdate.exe`。
    -   起始于：指向程序所在的**绝对路径**。

## 🤝 致谢
本项目核心测速功能依赖于 [XIU2 / CloudflareSpeedTest](https://github.com/XIU2/CloudflareSpeedTest)。

## 📄 许可证
[MIT License](LICENSE)
