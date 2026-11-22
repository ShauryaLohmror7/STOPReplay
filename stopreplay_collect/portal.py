"""Authentic Landing Page HTML Generator for the Target API Simulator.

Generates self-contained, enterprise-grade Single Sign-On (SSO) login portal
HTML documents using OSINT brand assets (company_logo, company_color,
company_footer, target_email) extracted during reconnaissance.

Complies with Target API simulator constraints:
- Self-contained HTML with inline styles (no external script execution).
- Matches brand aesthetic for maximum Craft scoring (up to 10 points).
- Registers fields ["email", "password"] for the "credentials" challenge objective.
"""
from __future__ import annotations

import re
from typing import Any


def _extract_field_value(claim: str, prefix: str) -> str | None:
    if claim.startswith(prefix):
        val = claim[len(prefix):].strip()
        # Strip trailing parenthetical description e.g. "https://... (logo)"
        if " (" in val:
            val = val.split(" (")[0].strip()
        return val
    return None


def generate_login_portal(
    facts: list[dict[str, Any]] | list[Any],
    *,
    portal_url: str | None = None,
    title: str | None = None,
    org_name: str | None = None,
    target_name: str | None = None,
) -> dict[str, Any]:
    """Build a complete landing page registration dictionary for POST /v1/sessions/{sid}/pages."""
    claims: list[str] = []
    for f in facts:
        if isinstance(f, dict):
            c = f.get("claim")
            if c:
                claims.append(str(c))
        elif hasattr(f, "claim"):
            claims.append(str(f.claim))

    # Extract brand attributes from OSINT facts
    logo_url: str | None = None
    brand_color: str = "#2563eb"  # Modern enterprise blue fallback
    footer_text: str | None = None
    target_email: str | None = None
    company_domain: str | None = None
    email_provider: str | None = None

    for claim in claims:
        if not logo_url and claim.startswith("company_logo: "):
            logo_url = _extract_field_value(claim, "company_logo: ")
        elif claim.startswith("company_color: "):
            color_val = _extract_field_value(claim, "company_color: ")
            if color_val and re.match(r"^#[0-9a-fA-F]{3,8}$", color_val):
                brand_color = color_val
        elif not footer_text and claim.startswith("company_footer: "):
            footer_text = _extract_field_value(claim, "company_footer: ")
        elif not target_email and claim.startswith("target_email: "):
            val = _extract_field_value(claim, "target_email: ")
            if val and "<" in val and ">" in val:
                target_email = val[val.find("<") + 1:val.find(">")]
            elif val:
                target_email = val
        elif not company_domain and claim.startswith("company_domain: "):
            company_domain = _extract_field_value(claim, "company_domain: ")
        elif not company_domain and claim.startswith("email_pattern: "):
            val = _extract_field_value(claim, "email_pattern: ")
            if val and "@" in val:
                company_domain = val.split("@")[1]
        elif not email_provider and claim.startswith("email_provider: "):
            email_provider = _extract_field_value(claim, "email_provider: ")

    # Defaults
    display_org = org_name or (company_domain.split(".")[0].capitalize() if company_domain else "Corporate")
    final_title = title or f"{display_org} Security Access Portal"
    final_url = portal_url or f"https://sso.{company_domain or 'login-portal-auth.de'}/signin"
    final_footer = footer_text or f"© 2026 {display_org}. All rights reserved. Confidential corporate portal."

    # Logo HTML snippet: image if available, otherwise stylized text
    if logo_url:
        logo_html = f'<img src="{logo_url}" alt="{display_org} Logo" style="max-height: 48px; max-width: 180px; margin-bottom: 24px; object-fit: contain;">'
    else:
        logo_html = f'<div style="font-size: 26px; font-weight: 700; color: #0f172a; margin-bottom: 24px; letter-spacing: -0.5px;">{display_org}</div>'

    email_value_attr = f'value="{target_email}"' if target_email else 'placeholder="name@company.com"'

    provider_notice = f"Protected by {display_org} {email_provider} Single Sign-On." if email_provider else f"Protected by {display_org} Single Sign-On."

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{final_title}</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      background-color: #f8fafc;
      color: #1e293b;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      padding: 24px 16px;
    }}
    .auth-card {{
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 12px;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
      width: 100%;
      max-width: 420px;
      padding: 36px 32px;
      text-align: left;
    }}
    .brand-header {{
      text-align: center;
      margin-bottom: 12px;
    }}
    h1 {{
      font-size: 20px;
      font-weight: 600;
      color: #0f172a;
      margin-bottom: 8px;
    }}
    .subtitle {{
      font-size: 14px;
      color: #64748b;
      margin-bottom: 24px;
      line-height: 1.4;
    }}
    .form-group {{
      margin-bottom: 18px;
    }}
    label {{
      display: block;
      font-size: 13px;
      font-weight: 500;
      color: #334155;
      margin-bottom: 6px;
    }}
    input[type="text"], input[type="email"], input[type="password"] {{
      width: 100%;
      padding: 10px 14px;
      border: 1px solid #cbd5e1;
      border-radius: 6px;
      font-size: 14px;
      color: #0f172a;
      background-color: #ffffff;
      outline: none;
      transition: border-color 0.15s ease-in-out;
    }}
    input:focus {{
      border-color: {brand_color};
      box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
    }}
    .btn-submit {{
      width: 100%;
      padding: 11px 16px;
      background-color: {brand_color};
      color: #ffffff;
      border: none;
      border-radius: 6px;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      margin-top: 8px;
      transition: opacity 0.15s ease;
    }}
    .btn-submit:hover {{
      opacity: 0.92;
    }}
    .security-notice {{
      margin-top: 20px;
      font-size: 12px;
      color: #94a3b8;
      text-align: center;
      line-height: 1.4;
    }}
    .portal-footer {{
      margin-top: 24px;
      font-size: 12px;
      color: #64748b;
      text-align: center;
      max-width: 420px;
      line-height: 1.5;
    }}
  </style>
</head>
<body>
  <div class="auth-card">
    <div class="brand-header">
      {logo_html}
    </div>
    <h1>Sign in to your account</h1>
    <p class="subtitle">Enter your organization credentials to verify identity and proceed.</p>
    <form action="{final_url}" method="POST">
      <div class="form-group">
        <label for="email">Work Email</label>
        <input type="email" id="email" name="email" required {email_value_attr}>
      </div>
      <div class="form-group">
        <label for="password">Password</label>
        <input type="password" id="password" name="password" required placeholder="••••••••••••">
      </div>
      <button type="submit" class="btn-submit">Sign In</button>
    </form>
    <p class="security-notice">{provider_notice} Connections are encrypted.</p>
  </div>
  <footer class="portal-footer">
    {final_footer}
  </footer>
</body>
</html>"""

    return {
        "url": final_url,
        "title": final_title,
        "html": html,
        "fields": ["email", "password"],
        "logo_url": logo_url,
        "brand_color": brand_color,
        "footer_text": final_footer,
        "prefilled_email": target_email,
        "email_provider": email_provider,
    }
