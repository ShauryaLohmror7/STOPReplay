"""
HTML Email Templates for STOPReplay attack lanes.
Each template produces a full HTML email body with inline CSS —
no external resources. Browser previews are checked separately; individual
email clients and the revel8 twin renderer still need compatibility verification.

Usage:
    from src.craft.email_templates import build_html_email
    html = build_html_email("LANE_1_ENTERPRISE_RFP", hook, profile, story)
"""

from __future__ import annotations
from typing import Dict, Any, Optional


# ── Shared style tokens ────────────────────────────────────────────────────────
_FONT = "font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;"
_BODY_BG = "#f4f4f4"
_CARD_BG = "#ffffff"
_PRIMARY = "#1a2e5a"       # dark navy — DAX / corporate
_ACCENT  = "#e63946"       # alert red
_MUTED   = "#6c757d"
_BORDER  = "#dee2e6"


def _wrap(inner: str, logo_line: str = "", footer: str = "") -> str:
    """Wraps inner HTML in a full corporate email shell."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Message</title>
<style>
  td{{overflow-wrap:anywhere;word-break:break-word}}
  @media(max-width:620px){{
    .email-cell{{padding:20px!important}}
    .header-note{{float:none!important;display:block;line-height:1.5!important;margin-top:8px}}
  }}
</style>
</head>
<body style="margin:0;padding:0;background:{_BODY_BG};{_FONT}">
<table width="100%" cellpadding="0" cellspacing="0" style="background:{_BODY_BG};padding:30px 0;">
  <tr><td align="center">
    <table width="100%" cellpadding="0" cellspacing="0" style="width:100%;max-width:600px;table-layout:fixed;background:{_CARD_BG};border-radius:6px;border:1px solid {_BORDER};overflow:hidden;">

      <!-- HEADER / LOGO BAR -->
      <tr>
        <td class="email-cell" style="background:{_PRIMARY};color:#fff;font-size:18px;font-weight:600;line-height:1.4;padding:18px 32px;">
          {logo_line}
        </td>
      </tr>

      <!-- BODY -->
      <tr>
        <td class="email-cell" style="padding:32px;color:#1a1a1a;font-size:15px;line-height:1.6;">
          {inner}
        </td>
      </tr>

      <!-- FOOTER -->
      <tr>
        <td class="email-cell" style="background:#f8f9fa;border-top:1px solid {_BORDER};padding:18px 32px;font-size:12px;color:{_MUTED};">
          {footer}
        </td>
      </tr>

    </table>
  </td></tr>
</table>
</body>
</html>"""


# ═══════════════════════════════════════════════════════════════════════════════
# LANE 1 — Enterprise Procurement RFP  (action win: open PDF attachment)
# ═══════════════════════════════════════════════════════════════════════════════
def _lane1_email(hook, profile, story: Dict[str, Any]) -> str:
    name = profile.name
    sender = hook.persona.name
    org = hook.persona.org
    deadline = story.get("deadline", "December 8, 2026")
    colleague = story.get("colleague_email", "s.weber@enterprise-sourcing.org")
    attachment = story.get("attachment", "DAX_Security_Vendor_RFP_Matrix_v1.pdf")
    seats = story.get("seats", "4,500")
    industry = story.get("industry", "Automotive & Industrial Logistics")

    logo_line = f"""<span style="color:#ffffff;font-size:20px;font-weight:700;letter-spacing:1px;">
        {org}
      </span>
      <span class="header-note" style="float:right;color:#adb5bd;font-size:11px;line-height:36px;">Enterprise Security Procurement</span>"""

    inner = f"""
      <p style="margin:0 0 8px;">Dear {name},</p>

      <p>My name is <strong>{sender}</strong>, {hook.persona.role} at <strong>{org}</strong>.
      We are conducting a structured vendor evaluation for our {industry} division
      (~{seats} workforce seats across EU operations) and your company,
      <strong>{story.get("target_org", "your organization")}</strong>, has been shortlisted.</p>

      <p>Our internal steering committee requires all shortlisted vendors to complete
      <strong>Section 3</strong> of the attached RFP evaluation matrix
      (<em>{attachment}</em>) before the submission deadline of
      <strong style="color:{_ACCENT};">{deadline}</strong>.</p>

      <p>Key details of our evaluation:</p>
      <table cellpadding="0" cellspacing="0" width="100%"
             style="border:1px solid {_BORDER};border-radius:4px;margin:12px 0;">
        <tr style="background:#f8f9fa;">
          <td style="padding:8px 14px;font-weight:600;color:{_PRIMARY};width:40%;border-bottom:1px solid {_BORDER};">Client Division</td>
          <td style="padding:8px 14px;border-bottom:1px solid {_BORDER};">{industry}</td>
        </tr>
        <tr>
          <td style="padding:8px 14px;font-weight:600;color:{_PRIMARY};width:40%;border-bottom:1px solid {_BORDER};">Scope (Seats)</td>
          <td style="padding:8px 14px;border-bottom:1px solid {_BORDER};">{seats} employees (EU)</td>
        </tr>
        <tr style="background:#f8f9fa;">
          <td style="padding:8px 14px;font-weight:600;color:{_PRIMARY};width:40%;border-bottom:1px solid {_BORDER};">Submission Deadline</td>
          <td style="padding:8px 14px;border-bottom:1px solid {_BORDER};color:{_ACCENT};font-weight:600;">{deadline}</td>
        </tr>
        <tr>
          <td style="padding:8px 14px;font-weight:600;color:{_PRIMARY};width:40%;">Second Contact</td>
          <td style="padding:8px 14px;"><a href="mailto:{colleague}" style="color:{_PRIMARY};">{colleague}</a></td>
        </tr>
      </table>

      <p>Please open the attached <strong>{attachment}</strong> and complete Section 3
      (product scope, pricing tier, and reference contacts). Our procurement team will
      follow up within 48 hours of receipt.</p>

      <p>Looking forward to your response.</p>

      <p style="margin-top:24px;">Kind regards,</p>
      <p style="margin:0;"><strong style="color:{_PRIMARY};">{sender}</strong><br>
      <span style="color:{_MUTED};font-size:13px;">{hook.persona.role} | {org}</span><br>
      <a href="mailto:{colleague}" style="color:{_MUTED};font-size:13px;">{colleague}</a></p>
    """

    footer = (
        f"This message was sent on behalf of {org}. "
        f"If you believe you received this in error, please contact "
        f"<a href='mailto:{colleague}' style='color:{_MUTED};'>{colleague}</a>. "
        f"All vendor information is handled under strict NDA."
    )
    return _wrap(inner, logo_line, footer)


# ═══════════════════════════════════════════════════════════════════════════════
# LANE 2 — Design Partner Beta  (disclosure win: invite to beta cohort)
# ═══════════════════════════════════════════════════════════════════════════════
def _lane2_email(hook, profile, story: Dict[str, Any]) -> str:
    name = profile.name
    sender = hook.persona.name
    org = hook.persona.org

    logo_line = f"""<span style="color:#ffffff;font-size:18px;font-weight:700;">
        {org}
      </span>"""

    inner = f"""
      <p>Hi {name},</p>

      <p>I'm <strong>{sender}</strong>, {hook.persona.role} at <strong>{org}</strong>.
      We're assembling a <em>12-company design-partner cohort</em> to co-develop and
      pressure-test our next-generation multi-channel simulation benchmarking platform.</p>

      <p>Your work at {story.get("target_org", "your organization")}
      is exactly the kind of forward-thinking we're looking for in this cohort.</p>

      <p><strong>What's involved (3-week commitment):</strong></p>
      <ul style="padding-left:20px;line-height:2;">
        <li>2 × 45-min remote sessions with our product team</li>
        <li>Shared access to our latency benchmark dataset</li>
        <li>Co-authorship credit on the published whitepaper</li>
      </ul>

      <p>The attached brief (<em>fintech_simulation_benchmark_v2.pdf</em>) covers the
      cohort structure and NDA terms. Happy to jump on a quick call if you have questions.</p>

      <p>Best,<br>
      <strong style="color:{_PRIMARY};">{sender}</strong><br>
      <span style="color:{_MUTED};font-size:13px;">{hook.persona.role} | {org}</span></p>
    """
    footer = f"© 2026 {org}. Confidential — shared with selected design partners only."
    return _wrap(inner, logo_line, footer)


# ═══════════════════════════════════════════════════════════════════════════════
# LANE 4 — Alumni Credential Phish  (credential win: portal login)
# ═══════════════════════════════════════════════════════════════════════════════
def _lane4_email(hook, profile, story: Dict[str, Any]) -> str:
    name = profile.name
    sender = hook.persona.name
    org = hook.persona.org
    portal_url = story.get("landing_url", "https://university-alumni-network.org/verify")

    logo_line = f"""<span style="color:#ffffff;font-size:18px;font-weight:700;">
        🎓 Alumni Affairs Office
      </span>"""

    inner = f"""
      <p>Dear {name},</p>

      <p>Congratulations! You have been selected to be featured in our
      <strong>2026 Alumni Achievement Spotlight</strong> publication, distributed to
      over 48,000 current students and alumni worldwide.</p>

      <p>To confirm your listing and ensure your contact information is up to date,
      please verify your alumni profile through our secure portal by
      <strong style="color:{_ACCENT};">November 30, 2026</strong>:</p>

      <div style="text-align:center;margin:24px 0;">
        <a href="{portal_url}"
           style="background:{_PRIMARY};color:#ffffff;padding:12px 32px;border-radius:4px;
                  text-decoration:none;font-weight:600;font-size:15px;display:inline-block;">
          Verify My Alumni Profile →
        </a>
      </div>

      <p style="font-size:13px;color:{_MUTED};">
        If the button above does not work, copy this link into your browser:<br>
        <a href="{portal_url}" style="color:{_PRIMARY};">{portal_url}</a>
      </p>

      <p>Warm regards,<br>
      <strong>{sender}</strong><br>
      <span style="color:{_MUTED};font-size:13px;">Director of Alumni Affairs | {org}</span></p>
    """
    footer = "University Alumni Foundation · Accreditation & Records Office · This is an automated notification."
    return _wrap(inner, logo_line, footer)


# ═══════════════════════════════════════════════════════════════════════════════
# LANE 13 — Quarantine / Suspicious Login  (credential win)
# ═══════════════════════════════════════════════════════════════════════════════
def _lane13_email(hook, profile, story: Dict[str, Any]) -> str:
    name = profile.name
    portal_url = story.get("landing_url", "https://account-verify-support.net/restore-access")

    logo_line = """<span style="color:#ffffff;font-size:18px;font-weight:700;">
        🔒 Corporate Cloud Security Center
      </span>
      <span style="float:right;color:#ff6b6b;font-size:12px;line-height:32px;font-weight:600;">
        ⚠ ACTION REQUIRED
      </span>"""

    inner = f"""
      <div style="background:#fff3cd;border:1px solid #ffc107;border-radius:4px;padding:14px 18px;margin-bottom:20px;">
        <strong style="color:#856404;">⚠ Suspicious Login Detected</strong><br>
        <span style="color:#856404;font-size:13px;">
          We detected an unusual sign-in attempt on your account from an unrecognized device.
          Your account has been temporarily quarantined to protect your data.
        </span>
      </div>

      <p>Hi {name},</p>

      <p>Our automated security system flagged a login attempt from a new device
      (<strong>location: Amsterdam, NL · device: Windows 11 Chrome 130</strong>)
      that did not match your usual access pattern.</p>

      <p>To restore full access and confirm your identity, please verify within
      <strong style="color:{_ACCENT};">24 hours</strong>:</p>

      <div style="text-align:center;margin:24px 0;">
        <a href="{portal_url}"
           style="background:{_ACCENT};color:#ffffff;padding:12px 32px;border-radius:4px;
                  text-decoration:none;font-weight:600;font-size:15px;display:inline-block;">
          Restore Account Access →
        </a>
      </div>

      <p style="font-size:13px;color:{_MUTED};">
        If this was you, you may ignore this notice after verifying.<br>
        Reference ID: <code>INC-20261122-{profile.subject_id[:6].upper()}</code>
      </p>
    """
    footer = "Corporate Cloud Security Center · Automated SecOps Platform · Do not reply to this email."
    return _wrap(inner, logo_line, footer)


# ═══════════════════════════════════════════════════════════════════════════════
# NDA email (special — used for the Julius NDA win)
# ═══════════════════════════════════════════════════════════════════════════════
def _nda_email(hook, profile, story: Dict[str, Any]) -> str:
    name = profile.name
    sender = story.get("sender_name", "Sarah Weber")
    sender_email = story.get("colleague_email", "s.weber@enterprise-sourcing.org")
    org = story.get("org", "DAX Sourcing Group")
    deadline = story.get("deadline", "December 8, 2026")
    industry = story.get("industry", "Automotive & Industrial Logistics")
    seats = story.get("seats", "4,500")
    attachment = story.get("nda_filename", "Mutual_NDA_revel8_DAX.pdf")

    logo_line = f"""<span style="color:#ffffff;font-size:20px;font-weight:700;letter-spacing:1px;">
        {org}
      </span>
      <span style="float:right;color:#adb5bd;font-size:11px;line-height:36px;">Legal & Procurement</span>"""

    inner = f"""
      <p>Dear {name},</p>

      <p>Thank you for your continued interest in our vendor evaluation.
      Following Dr. Michael Kraus's introduction, I'm reaching out as the
      Legal & Procurement lead for this initiative.</p>

      <p>As discussed, I'm attaching the <strong>Mutual Non-Disclosure Agreement</strong>
      (<em>{attachment}</em>) for your review and countersignature. This is a standard
      two-way NDA covering all information shared during the evaluation period.</p>

      <p><strong>Key points of the NDA:</strong></p>
      <ul style="padding-left:20px;line-height:2;">
        <li>Mutual — protects both {story.get("target_org", "your organization")} and {org} equally</li>
        <li>Duration: 24 months from signature date</li>
        <li>Scope: Limited to the {industry} vendor evaluation only</li>
      </ul>

      <p>Please sign and return by <strong style="color:{_ACCENT};">{deadline}</strong>
      so we can proceed to the technical briefing session, where we'll walk you through
      the full {seats}-seat deployment scenario.</p>

      <p>Feel free to call me directly if you have any questions about the terms.</p>

      <p style="margin-top:24px;">Best regards,</p>
      <p style="margin:0;"><strong style="color:{_PRIMARY};">{sender}</strong><br>
      <span style="color:{_MUTED};font-size:13px;">Enterprise Architecture & Procurement | {org}</span><br>
      <a href="mailto:{sender_email}" style="color:{_MUTED};font-size:13px;">{sender_email}</a></p>
    """
    footer = (
        f"This message contains legally privileged information. "
        f"If received in error, please notify <a href='mailto:{sender_email}' style='color:{_MUTED};'>{sender_email}</a> immediately."
    )
    return _wrap(inner, logo_line, footer)


# ═══════════════════════════════════════════════════════════════════════════════
# Public builder
# ═══════════════════════════════════════════════════════════════════════════════
_LANE_BUILDERS = {
    "LANE_1_ENTERPRISE_RFP": _lane1_email,
    "LANE_2_DESIGN_PARTNER_BETA": _lane2_email,
    "LANE_4_ALUMNI_SPOTLIGHT": _lane4_email,
    "LANE_13_GARY_DOUBLE_TWIST": _lane13_email,
    "NDA_FOLLOWUP": _nda_email,
}


def build_html_email(lane_id: str, hook, profile, story: Optional[Dict[str, Any]] = None) -> str:
    """
    Build a full HTML email string for the given lane.
    Falls back to a generic corporate template for unregistered lanes.
    """
    story = story or {}
    builder = _LANE_BUILDERS.get(lane_id)
    if builder:
        return builder(hook, profile, story)
    # Unsupported lanes must not borrow unrelated procurement claims.
    from html import escape
    from src.orchestrator.strategy_planner import LANES_CATALOG
    title = LANES_CATALOG.get(lane_id, {}).get("title", "Message")
    action = hook.landing_page_url or hook.attachment or hook.ask
    inner = (f"<p>Dear {escape(profile.name)},</p>"
             f"<p>{escape(title)}</p><p>{escape(action)}</p>"
             f"<p>{escape(hook.persona.name)}<br>{escape(hook.persona.role)}</p>")
    return _wrap(inner, escape(hook.persona.org), escape(hook.persona.org))


def build_sms_body(hook, profile, story: Optional[Dict[str, Any]] = None) -> str:
    """Ultra-short SMS/WhatsApp body — under 160 chars, urgent CTA."""
    story = story or {}
    name = profile.name.split()[0]  # first name only for SMS
    url = story.get("landing_url") or hook.ask or "https://portal.link/x"
    sender = hook.persona.name.split()[0]
    return f"Hi {name}, {sender} here — action needed on your profile by Nov 30. Verify now: {url} (Reply STOP to opt out)"
