"""
templates/email_template.py
----------------------------
Builds a beautiful, responsive HTML email + a plain-text fallback.
"""

from datetime import date


# Colour palette
PRIMARY = "#1a1a2e"
ACCENT  = "#e94560"
BG      = "#f5f7fa"
CARD_BG = "#ffffff"
TAG_BG  = "#eef2ff"
TAG_FG  = "#4f46e5"
MUTED   = "#6b7280"
GREEN   = "#10b981"

SOURCE_COLOURS = {
    "RemoteOK":       "#ff4500",
    "Remotive":       "#0891b2",
    "WeWorkRemotely": "#7c3aed",
    "Jobicy":         "#059669",
    "Arbeitnow":      "#d97706",
}


def _source_badge(source: str) -> str:
    colour = SOURCE_COLOURS.get(source, "#6b7280")
    return (
        f'<span style="background:{colour};color:#fff;padding:2px 8px;'
        f'border-radius:12px;font-size:11px;font-weight:600;">{source}</span>'
    )


def _tag_pill(tag: str) -> str:
    return (
        f'<span style="background:{TAG_BG};color:{TAG_FG};padding:2px 8px;'
        f'border-radius:12px;font-size:11px;margin-right:4px;">{tag.strip()}</span>'
    )


def _job_card(job: dict, rank: int) -> str:
    title    = job.get("title", "N/A")
    company  = job.get("company", "Unknown")
    location = job.get("location", "Remote")
    url      = job.get("url", "#")
    source   = job.get("source", "")
    tags_raw = job.get("tags", "")
    summary  = job.get("ai_summary", "")
    date_str = job.get("date", "")

    tags_html = ""
    if tags_raw:
        tag_list = [t for t in tags_raw.split(",") if t.strip()][:5]
        tags_html = "".join(_tag_pill(t) for t in tag_list)

    summary_html = (
        f'<p style="color:{MUTED};font-size:13px;margin:6px 0 0 0;font-style:italic;">'
        f'🤖 {summary}</p>'
    ) if summary else ""

    date_html = (
        f'<span style="color:{MUTED};font-size:11px;"> · {date_str}</span>'
    ) if date_str else ""

    return f"""
    <tr>
      <td style="padding:16px 24px;">
        <table width="100%" cellpadding="0" cellspacing="0" style="
          background:{CARD_BG};
          border-radius:12px;
          border:1px solid #e5e7eb;
          overflow:hidden;
        ">
          <tr>
            <td style="padding:20px 24px;">
              <!-- Rank + Source row -->
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td>
                    <span style="
                      background:{ACCENT};color:#fff;
                      padding:2px 10px;border-radius:20px;
                      font-size:12px;font-weight:700;
                    ">#{rank}</span>
                    &nbsp;{_source_badge(source)}{date_html}
                  </td>
                </tr>
              </table>
              <!-- Title -->
              <h3 style="margin:10px 0 4px 0;font-size:17px;color:{PRIMARY};font-family:Georgia,serif;">
                <a href="{url}" style="color:{PRIMARY};text-decoration:none;">{title}</a>
              </h3>
              <!-- Company / location -->
              <p style="margin:0;font-size:14px;color:{MUTED};">
                🏢 <strong>{company}</strong> &nbsp;·&nbsp; 📍 {location}
              </p>
              {summary_html}
              <!-- Tags -->
              {"<div style='margin-top:10px;'>" + tags_html + "</div>" if tags_html else ""}
              <!-- Apply button -->
              <table cellpadding="0" cellspacing="0" style="margin-top:14px;">
                <tr>
                  <td style="
                    background:{ACCENT};border-radius:8px;
                  ">
                    <a href="{url}" style="
                      display:inline-block;padding:8px 20px;
                      color:#fff;font-size:13px;font-weight:700;
                      text-decoration:none;
                    ">Apply Now →</a>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
      </td>
    </tr>"""


def build_html_email(jobs: list[dict], intro: str) -> str:
    today = date.today().strftime("%B %d, %Y")
    job_cards = "\n".join(_job_card(j, i + 1) for i, j in enumerate(jobs))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Tech Job Digest – {today}</title>
</head>
<body style="margin:0;padding:0;background:{BG};font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">

  <!-- Wrapper -->
  <table width="100%" cellpadding="0" cellspacing="0" style="background:{BG};padding:32px 0;">
    <tr>
      <td align="center">
        <table width="640" cellpadding="0" cellspacing="0" style="max-width:640px;width:100%;">

          <!-- Header -->
          <tr>
            <td style="
              background:linear-gradient(135deg,{PRIMARY} 0%,#16213e 100%);
              border-radius:16px 16px 0 0;
              padding:36px 40px;
              text-align:center;
            ">
              <p style="margin:0;color:{ACCENT};font-size:12px;letter-spacing:3px;font-weight:700;text-transform:uppercase;">
                Daily Digest
              </p>
              <h1 style="margin:8px 0 4px 0;color:#fff;font-size:28px;font-family:Georgia,serif;">
                Tech Job Openings
              </h1>
              <p style="margin:0;color:#94a3b8;font-size:14px;">{today}</p>
              <div style="margin:20px auto 0;width:48px;height:3px;background:{ACCENT};border-radius:2px;"></div>
            </td>
          </tr>

          <!-- Intro -->
          <tr>
            <td style="
              background:#fff;
              padding:24px 40px;
              border-left:1px solid #e5e7eb;
              border-right:1px solid #e5e7eb;
            ">
              <p style="
                margin:0;color:#374151;font-size:15px;line-height:1.7;
                border-left:4px solid {ACCENT};padding-left:16px;
              ">{intro}</p>
            </td>
          </tr>

          <!-- Stats bar -->
          <tr>
            <td style="
              background:{PRIMARY};
              padding:14px 40px;
            ">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td align="center" style="color:#94a3b8;font-size:13px;">
                    <span style="color:#fff;font-weight:700;font-size:18px;">{len(jobs)}</span>
                    &nbsp;curated jobs &nbsp;·&nbsp;
                    <span style="color:{GREEN};font-weight:600;">AI-ranked</span>
                    &nbsp;·&nbsp; multiple sources
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Job Cards -->
          <tr>
            <td style="
              background:{BG};
              border-left:1px solid #e5e7eb;
              border-right:1px solid #e5e7eb;
              padding:8px 0;
            ">
              <table width="100%" cellpadding="0" cellspacing="0">
                {job_cards}
              </table>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="
              background:{PRIMARY};
              border-radius:0 0 16px 16px;
              padding:24px 40px;
              text-align:center;
            ">
              <p style="margin:0 0 8px 0;color:#94a3b8;font-size:12px;">
                Jobs sourced from RemoteOK · Remotive · WeWorkRemotely · Jobicy · Arbeitnow
              </p>
              <p style="margin:0;color:#4b5563;font-size:11px;">
                This digest is AI-curated and sent automatically. Links go directly to job boards.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>

</body>
</html>"""


def build_plain_email(jobs: list[dict], intro: str) -> str:
    today = date.today().strftime("%B %d, %Y")
    lines = [
        f"TECH JOB DIGEST – {today}",
        "=" * 50,
        "",
        intro,
        "",
        f"{len(jobs)} curated openings (AI-ranked):",
        "-" * 50,
    ]
    for i, job in enumerate(jobs, 1):
        lines.append(f"\n#{i}  {job.get('title','N/A')}  [{job.get('source','')}]")
        lines.append(f"    Company : {job.get('company','Unknown')}")
        lines.append(f"    Location: {job.get('location','Remote')}")
        if job.get("ai_summary"):
            lines.append(f"    AI Note : {job['ai_summary']}")
        lines.append(f"    Apply   : {job.get('url','')}")
        lines.append("")
    lines += [
        "-" * 50,
        "Sources: RemoteOK, Remotive, WeWorkRemotely, Jobicy, Arbeitnow",
    ]
    return "\n".join(lines)