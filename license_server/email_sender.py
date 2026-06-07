"""
邮件发送模块 — 购买确认、License Key 交付
支持 SMTP（QQ邮箱/Gmail/自定义）
"""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

SMTP_CONFIG = {
    "host": os.environ.get("SMTP_HOST", "smtp.qq.com"),
    "port": int(os.environ.get("SMTP_PORT", "587")),
    "user": os.environ.get("SMTP_USER", ""),
    "password": os.environ.get("SMTP_PASSWORD", ""),
    "from_name": os.environ.get("SMTP_FROM_NAME", "AI Privacy Gateway"),
    "from_email": os.environ.get("SMTP_FROM_EMAIL", ""),
}

PRO_EMAIL_TEMPLATE = """\
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
             max-width: 600px; margin: 0 auto; padding: 20px; color: #e0e0e0;
             background: #0f0f1a;">
  <div style="text-align: center; padding: 30px 0;">
    <h1 style="color: #22c55e; font-size: 28px; margin: 0;">AI Privacy Gateway</h1>
    <p style="color: #888; font-size: 14px;">你的 AI 数据安全防火墙</p>
  </div>

  <div style="background: #1a1a2e; border-radius: 12px; padding: 30px; margin: 20px 0;
              border: 1px solid #333;">
    <h2 style="color: #22c55e; font-size: 20px; margin-top: 0;">
      感谢购买 Pro 版！
    </h2>

    <p>你的 License Key 已生成：</p>

    <div style="background: #0f0f1a; border: 1px solid #22c55e; border-radius: 8px;
                padding: 15px; text-align: center; margin: 20px 0;">
      <code style="font-size: 20px; font-weight: bold; color: #22c55e;
                   letter-spacing: 2px; font-family: 'Courier New', monospace;">
        {license_key}
      </code>
    </div>

    <p style="color: #888; font-size: 13px;">
      有效期至：<strong style="color: #e0e0e0;">{expires_at}</strong><br>
      最大并发：<strong style="color: #e0e0e0;">{max_concurrent} 人</strong>
    </p>
  </div>

  <div style="background: #1a1a2e; border-radius: 12px; padding: 25px; margin: 20px 0;
              border: 1px solid #333;">
    <h3 style="color: #e0e0e0; margin-top: 0;">快速开始</h3>
    <p style="color: #888; font-size: 14px;">一行命令启动服务：</p>
    <pre style="background: #0f0f1a; color: #22c55e; padding: 15px; border-radius: 8px;
                font-size: 13px; overflow-x: auto; border: 1px solid #333;">
{docker_command}</pre>
  </div>

  <div style="color: #666; font-size: 12px; text-align: center; margin-top: 30px;
              padding-top: 20px; border-top: 1px solid #333;">
    <p>AI Privacy Gateway — MIT License</p>
    <p>如有问题，回复此邮件或联系 support@privacygw.com</p>
  </div>
</body>
</html>"""

ENTERPRISE_EMAIL_TEMPLATE = """\
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
             max-width: 600px; margin: 0 auto; padding: 20px; color: #e0e0e0;
             background: #0f0f1a;">
  <div style="text-align: center; padding: 30px 0;">
    <h1 style="color: #22c55e; font-size: 28px; margin: 0;">AI Privacy Gateway</h1>
    <p style="color: #888; font-size: 14px;">Enterprise 企业版</p>
  </div>

  <div style="background: #1a1a2e; border-radius: 12px; padding: 30px; margin: 20px 0;
              border: 2px solid #22c55e;">
    <h2 style="color: #22c55e; font-size: 20px; margin-top: 0;">
      Enterprise 版本已就绪
    </h2>

    <p>你的企业 License Key：</p>

    <div style="background: #0f0f1a; border: 2px solid #22c55e; border-radius: 8px;
                padding: 15px; text-align: center; margin: 20px 0;">
      <code style="font-size: 20px; font-weight: bold; color: #22c55e;
                   letter-spacing: 2px; font-family: 'Courier New', monospace;">
        {license_key}
      </code>
    </div>

    <p style="color: #888; font-size: 13px;">
      有效期至：<strong style="color: #e0e0e0;">{expires_at}</strong><br>
      最大并发：<strong style="color: #e0e0e0;">{max_concurrent} 人</strong>
    </p>

    <p style="color: #888; font-size: 14px; margin-top: 20px;">
      支持 Redis 集群、AC 自动机万级词库、RBAC、审计日志等全部企业功能。<br>
      我们将在 1 个工作日内联系你安排驻场支持。
    </p>
  </div>

  <div style="color: #666; font-size: 12px; text-align: center; margin-top: 30px;
              padding-top: 20px; border-top: 1px solid #333;">
    <p>AI Privacy Gateway Enterprise — 企业级 AI 数据安全</p>
    <p>如有问题，联系 contact@privacygw.com</p>
  </div>
</body>
</html>"""


def _send_email(to_email: str, subject: str, html_body: str) -> bool:
    """通过 SMTP 发送邮件"""
    if not SMTP_CONFIG["user"] or not SMTP_CONFIG["password"]:
        print(f"[EMAIL] SMTP 未配置，跳过发送。主题: {subject}, 收件人: {to_email}")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{SMTP_CONFIG['from_name']} <{SMTP_CONFIG['from_email']}>"
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        server = smtplib.SMTP(SMTP_CONFIG["host"], SMTP_CONFIG["port"], timeout=15)
        server.starttls()
        server.login(SMTP_CONFIG["user"], SMTP_CONFIG["password"])
        server.sendmail(SMTP_CONFIG["from_email"], to_email, msg.as_string())
        server.quit()
        print(f"[EMAIL] 发送成功: {to_email}")
        return True
    except Exception as e:
        print(f"[EMAIL] 发送失败: {e}")
        return False


def send_pro_license_email(
    to_email: str,
    license_key: str,
    expires_at: str,
    max_concurrent: int = 20
) -> bool:
    """发送 Pro 版购买确认邮件"""
    docker_cmd = (
        "docker run -d --name privacy-gateway \\\n"
        "  -p 9999:9999 \\\n"
        "  -e PRIVACYGW_LICENSE_KEY=" + license_key + " \\\n"
        "  ghcr.io/gunxueqiu6/ai-privacy-gateway:pro"
    )
    html = PRO_EMAIL_TEMPLATE.format(
        license_key=license_key,
        expires_at=expires_at,
        max_concurrent=max_concurrent,
        docker_command=docker_cmd
    )
    return _send_email(
        to_email,
        f"你的 AI Privacy Gateway Pro License — {license_key}",
        html
    )


def send_enterprise_license_email(
    to_email: str,
    license_key: str,
    expires_at: str,
    max_concurrent: int = 100
) -> bool:
    """发送 Enterprise 版购买确认邮件"""
    html = ENTERPRISE_EMAIL_TEMPLATE.format(
        license_key=license_key,
        expires_at=expires_at,
        max_concurrent=max_concurrent
    )
    return _send_email(
        to_email,
        f"AI Privacy Gateway Enterprise License — {license_key}",
        html
    )


def send_license_email(
    to_email: str,
    license_key: str,
    tier: str,
    expires_at: str,
    max_concurrent: int = 20
) -> bool:
    """根据 tier 发送对应的购买确认邮件"""
    if tier == "enterprise":
        return send_enterprise_license_email(to_email, license_key, expires_at, max_concurrent)
    return send_pro_license_email(to_email, license_key, expires_at, max_concurrent)
