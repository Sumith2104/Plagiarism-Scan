import os
import smtplib
import logging
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from typing import Optional, Tuple
from app.core.config import settings

logger = logging.getLogger(__name__)

# Candidate file paths for the official PlagiaScan logo
LOGO_SEARCH_PATHS = [
    # Dedicated email-optimized logo
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../images/logo_email.png")),
    # Original image provided in images folder
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../images/Gemini_Generated_Image_wzo73vwzo73vwzo7.png")),
    # Web public assets
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../frontend/public/logo.png")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../frontend/public/logo-icon.png")),
    # Direct fallback paths
    r"c:\Users\hariv\Downloads\Plagiarism-Scan-main\Plagiarism-Scan-main\images\logo_email.png",
    r"c:\Users\hariv\Downloads\Plagiarism-Scan-main\Plagiarism-Scan-main\images\Gemini_Generated_Image_wzo73vwzo73vwzo7.png",
]

def get_logo_data() -> Tuple[Optional[bytes], Optional[str]]:
    """
    Locates and reads the official PlagiaScan logo from the project files.
    Returns a tuple of (raw_bytes, base64_data_uri).
    """
    for path in LOGO_SEARCH_PATHS:
        if os.path.exists(path):
            try:
                with open(path, "rb") as f:
                    raw_bytes = f.read()
                    b64_str = base64.b64encode(raw_bytes).decode("utf-8")
                    data_uri = f"data:image/png;base64,{b64_str}"
                    return raw_bytes, data_uri
            except Exception as e:
                logger.warning(f"Failed reading logo from {path}: {e}")
    return None, None


def _get_email_styles() -> str:
    """Returns responsive CSS styles optimized for modern email clients including Gmail."""
    return """
        body {
            margin: 0;
            padding: 0;
            background-color: #f1f5f9;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            color: #1e293b;
            -webkit-font-smoothing: antialiased;
        }
        .wrapper {
            width: 100%;
            background-color: #f1f5f9;
            padding: 32px 16px;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            background-color: #ffffff;
            border-radius: 16px;
            overflow: hidden;
            border: 1px solid #e2e8f0;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.02);
        }
        .header {
            background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #312e81 100%);
            padding: 36px 24px;
            text-align: center;
        }
        .logo-img {
            max-width: 190px;
            height: auto;
            display: block;
            margin: 0 auto 12px auto;
            border: none;
            outline: none;
        }
        .header-subtext {
            color: #c7d2fe;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            margin: 0;
        }
        .content {
            padding: 36px 32px;
            line-height: 1.65;
            color: #334155;
            font-size: 15px;
        }
        .greeting {
            font-size: 18px;
            font-weight: 700;
            color: #0f172a;
            margin-top: 0;
            margin-bottom: 16px;
        }
        .lead-text {
            font-size: 15px;
            color: #334155;
            margin-bottom: 20px;
        }
        .info-card {
            background-color: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 20px 24px;
            margin: 24px 0;
        }
        .metric-row {
            display: table;
            width: 100%;
            margin-bottom: 10px;
            border-bottom: 1px dashed #e2e8f0;
            padding-bottom: 8px;
        }
        .metric-label {
            display: table-cell;
            font-weight: 600;
            color: #64748b;
            font-size: 13px;
        }
        .metric-value {
            display: table-cell;
            text-align: right;
            font-weight: 700;
            font-size: 14px;
            color: #0f172a;
        }
        .btn-wrapper {
            text-align: center;
            margin: 32px 0 16px 0;
        }
        .btn {
            display: inline-block;
            background: linear-gradient(135deg, #4f46e5 0%, #6366f1 100%);
            color: #ffffff !important;
            text-decoration: none;
            font-weight: 700;
            font-size: 14px;
            padding: 14px 32px;
            border-radius: 10px;
            box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
            text-align: center;
        }
        .btn-text {
            color: #ffffff !important;
        }
        .footer {
            background-color: #f8fafc;
            border-top: 1px solid #e2e8f0;
            padding: 24px 32px;
            text-align: center;
            font-size: 12px;
            color: #64748b;
            line-height: 1.5;
        }
        .footer a {
            color: #4f46e5;
            text-decoration: none;
        }
        .tag-badge {
            display: inline-block;
            padding: 3px 10px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 700;
        }
        .tag-safe {
            background-color: #ecfdf5;
            color: #047857;
            border: 1px solid #a7f3d0;
        }
        .tag-warning {
            background-color: #fffbeb;
            color: #b45309;
            border: 1px solid #fde68a;
        }
        .tag-danger {
            background-color: #fff1f2;
            color: #be123c;
            border: 1px solid #fecdd3;
        }
    """


def build_welcome_email(to_email: str, full_name: Optional[str] = None) -> Tuple[MIMEMultipart, str, str]:
    """
    Constructs a professionally phrased, branded welcome email with the PlagiaScan logo.
    """
    sender_email = settings.EMAIL_ADDRESS or "noreply@plagiascan.com"
    recipient_name = full_name.strip() if full_name and full_name.strip() else to_email.split("@")[0]
    subject = "Welcome to PlagiaScan - Your Academic & Forensic Integrity Workspace"

    raw_logo_bytes, b64_logo_uri = get_logo_data()

    # In Gmail, 'cid:plagiascan_logo' is the gold standard for displaying embedded images
    logo_src = "cid:plagiascan_logo" if raw_logo_bytes else (b64_logo_uri or "https://via.placeholder.com/200x80?text=PlagiaScan")

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{subject}</title>
    <style>{_get_email_styles()}</style>
</head>
<body>
    <div class="wrapper">
        <div class="container">
            <!-- Header with Official Logo -->
            <div class="header">
                <img src="{logo_src}" alt="PlagiaScan Logo" class="logo-img" />
                <p class="header-subtext">Academic &amp; Forensic Integrity Platform</p>
            </div>

            <!-- Email Body Content -->
            <div class="content">
                <h1 class="greeting">Dear {recipient_name},</h1>

                <p class="lead-text">
                    Thank you for choosing PlagiaScan. We are pleased to inform you that your account has been successfully registered and your personal workspace is now active.
                </p>

                <p>
                    PlagiaScan delivers state-of-the-art academic plagiarism detection and content forensics. With your new account, you can take full advantage of our hybrid scanning architecture, which combines:
                </p>

                <div class="info-card">
                    <div class="metric-row">
                        <span class="metric-label">Registered Account</span>
                        <span class="metric-value">{to_email}</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Account Security</span>
                        <span class="metric-value">Bcrypt Multi-Round Encryption</span>
                    </div>
                    <div class="metric-row" style="border-bottom: none; padding-bottom: 0;">
                        <span class="metric-label">Verification Engine</span>
                        <span class="metric-value">Active &amp; Ready</span>
                    </div>
                </div>

                <p>
                    <strong>What you can do next:</strong>
                </p>
                <ul style="padding-left: 20px; color: #475569; font-size: 14px; line-height: 1.7;">
                    <li><strong>Upload and Analyze Documents:</strong> Submit research manuscripts, student essays, or technical documents in PDF, DOCX, or TXT format.</li>
                    <li><strong>Dual Plagiarism Detection:</strong> Cross-check submissions against web sources and internal repository collections with sequence-aligned line attribution.</li>
                    <li><strong>AI Generation Analysis:</strong> Inspect linguistic cadence, burstiness, and stylistic hallmarks using our calibrated 5-signal ensemble.</li>
                    <li><strong>Cryptographic Proof of Authenticity:</strong> Generate public verification badges to validate originality with universities and academic peers.</li>
                </ul>

                <div class="btn-wrapper">
                    <a href="http://localhost:5173/dashboard" class="btn">
                        <span class="btn-text">Access Your PlagiaScan Workspace &rarr;</span>
                    </a>
                </div>

                <p style="margin-top: 28px; font-size: 13px; color: #64748b;">
                    If you did not initiate this registration or have questions regarding your account security, please contact our integrity team immediately.
                </p>

                <p style="margin-top: 24px; margin-bottom: 0;">
                    Warm regards,<br>
                    <strong>The PlagiaScan Integrity Team</strong><br>
                    <span style="font-size: 12px; color: #64748b;">Academic &amp; Forensic Research Systems</span>
                </p>
            </div>

            <!-- Footer -->
            <div class="footer">
                <p style="margin: 0 0 6px 0;">
                    This official notification was transmitted by PlagiaScan to <strong>{to_email}</strong>.
                </p>
                <p style="margin: 0; font-size: 11px; color: #94a3b8;">
                    &copy; 2026 PlagiaScan Inc. All rights reserved. &bull; Protecting Academic Originality Worldwide
                </p>
            </div>
        </div>
    </div>
</body>
</html>
"""

    plain_text = f"""Dear {recipient_name},

Thank you for choosing PlagiaScan. We are pleased to inform you that your account ({to_email}) has been successfully registered and your personal workspace is now active.

PlagiaScan provides forensic-level academic plagiarism detection, multi-signal AI text analysis, and cryptographic authenticity verification.

You can now sign in to your workspace at http://localhost:5173 to upload documents and perform comprehensive originality scans.

Warm regards,
The PlagiaScan Integrity Team
Academic & Forensic Research Systems
"""

    # Build MIMEMultipart related message
    msg = MIMEMultipart("related")
    msg["From"] = f"PlagiaScan <{sender_email}>"
    msg["To"] = to_email
    msg["Subject"] = subject

    alt_part = MIMEMultipart("alternative")
    alt_part.attach(MIMEText(plain_text, "plain"))
    alt_part.attach(MIMEText(html_content, "html"))
    msg.attach(alt_part)

    # Attach the logo as inline image with Content-ID
    if raw_logo_bytes:
        img_part = MIMEImage(raw_logo_bytes, _subtype="png")
        img_part.add_header("Content-ID", "<plagiascan_logo>")
        img_part.add_header("Content-Disposition", "inline", filename="plagiascan_logo.png")
        msg.attach(img_part)

    return msg, html_content, plain_text


def build_scan_completed_email(
    to_email: str,
    full_name: Optional[str],
    document_title: str,
    scan_id: int,
    overall_score: float,
    ai_probability: float,
    ai_label: str,
    web_matches_count: int,
    scan_mode: str = "standard"
) -> Tuple[MIMEMultipart, str, str]:
    """
    Constructs a professionally formatted scan completion notification with the PlagiaScan logo and metrics.
    """
    sender_email = settings.EMAIL_ADDRESS or "noreply@plagiascan.com"
    recipient_name = full_name.strip() if full_name and full_name.strip() else to_email.split("@")[0]
    subject = f"PlagiaScan Report Complete: \"{document_title}\""

    raw_logo_bytes, b64_logo_uri = get_logo_data()
    logo_src = "cid:plagiascan_logo" if raw_logo_bytes else (b64_logo_uri or "https://via.placeholder.com/200x80?text=PlagiaScan")

    # Determine badge color based on score
    if overall_score < 15:
        score_badge = f'<span class="tag-badge tag-safe">{overall_score:.1f}% Similarity &bull; High Originality</span>'
    elif overall_score < 40:
        score_badge = f'<span class="tag-badge tag-warning">{overall_score:.1f}% Similarity &bull; Moderate Overlap</span>'
    else:
        score_badge = f'<span class="tag-badge tag-danger">{overall_score:.1f}% Similarity &bull; High Overlap</span>'

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{subject}</title>
    <style>{_get_email_styles()}</style>
</head>
<body>
    <div class="wrapper">
        <div class="container">
            <!-- Header with Official Logo -->
            <div class="header">
                <img src="{logo_src}" alt="PlagiaScan Logo" class="logo-img" />
                <p class="header-subtext">Academic &amp; Forensic Integrity Platform</p>
            </div>

            <!-- Email Body Content -->
            <div class="content">
                <h1 class="greeting">Dear {recipient_name},</h1>

                <p class="lead-text">
                    We are pleased to notify you that the plagiarism and forensic content scan for your document, <strong>&ldquo;{document_title}&rdquo;</strong>, has finished processing successfully.
                </p>

                <p>
                    Our multi-signal detection engine has analyzed your submission across multiple layers of scrutiny, including vector semantic indexing, web corpus alignment, and statistical linguistic analysis. A summary of the key findings is detailed below:
                </p>

                <div class="info-card">
                    <div class="metric-row">
                        <span class="metric-label">Document Title</span>
                        <span class="metric-value">{document_title}</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Plagiarism Index</span>
                        <span class="metric-value">{score_badge}</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">AI Generation Probability</span>
                        <span class="metric-value">{ai_probability:.1f}% ({ai_label})</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">External Web Matches</span>
                        <span class="metric-value">{web_matches_count} Source(s) Detected</span>
                    </div>
                    <div class="metric-row" style="border-bottom: none; padding-bottom: 0;">
                        <span class="metric-label">Analysis Mode</span>
                        <span class="metric-value">{scan_mode.capitalize()} Analysis</span>
                    </div>
                </div>

                <p>
                    You can access the comprehensive forensic report to view sentence-by-sentence highlights, source attributions, sequence alignment diffs, and cryptographic authenticity verification.
                </p>

                <div class="btn-wrapper">
                    <a href="http://localhost:5173/report/{scan_id}" class="btn">
                        <span class="btn-text">View Complete Forensic Report &rarr;</span>
                    </a>
                </div>

                <p style="margin-top: 24px; margin-bottom: 0;">
                    Sincerely,<br>
                    <strong>The PlagiaScan Integrity Team</strong><br>
                    <span style="font-size: 12px; color: #64748b;">Academic &amp; Forensic Research Systems</span>
                </p>
            </div>

            <!-- Footer -->
            <div class="footer">
                <p style="margin: 0 0 6px 0;">
                    This forensic notification was automatically generated by PlagiaScan for <strong>{to_email}</strong>.
                </p>
                <p style="margin: 0; font-size: 11px; color: #94a3b8;">
                    &copy; 2026 PlagiaScan Inc. All rights reserved. &bull; Protecting Academic Originality Worldwide
                </p>
            </div>
        </div>
    </div>
</body>
</html>
"""

    plain_text = f"""Dear {recipient_name},

The forensic plagiarism scan for your submitted document, "{document_title}", has completed successfully.

Scan Results Summary:
- Plagiarism Index: {overall_score:.1f}%
- AI Generation Probability: {ai_probability:.1f}% ({ai_label})
- External Web Matches: {web_matches_count} source(s) detected
- Scan Mode: {scan_mode.capitalize()}

To view the complete line-by-line report, please visit:
http://localhost:5173/report/{scan_id}

Sincerely,
The PlagiaScan Integrity Team
"""

    msg = MIMEMultipart("related")
    msg["From"] = f"PlagiaScan <{sender_email}>"
    msg["To"] = to_email
    msg["Subject"] = subject

    alt_part = MIMEMultipart("alternative")
    alt_part.attach(MIMEText(plain_text, "plain"))
    alt_part.attach(MIMEText(html_content, "html"))
    msg.attach(alt_part)

    if raw_logo_bytes:
        img_part = MIMEImage(raw_logo_bytes, _subtype="png")
        img_part.add_header("Content-ID", "<plagiascan_logo>")
        img_part.add_header("Content-Disposition", "inline", filename="plagiascan_logo.png")
        msg.attach(img_part)

    return msg, html_content, plain_text


def get_smtp_connection() -> smtplib.SMTP:
    """
    Creates, secures, and authenticates an SMTP connection using project configuration.
    Supports STARTTLS (port 587) and direct SSL (port 465), while sanitizing Google App Passwords.
    """
    sender_email = (settings.EMAIL_ADDRESS or "").strip()
    sender_password = (settings.EMAIL_PASSWORD or "").strip().replace(" ", "")

    if not sender_email or not sender_password:
        raise ValueError("EMAIL_ADDRESS or EMAIL_PASSWORD is not configured in .env")

    host = getattr(settings, "SMTP_SERVER", "smtp.gmail.com") or "smtp.gmail.com"
    port = int(getattr(settings, "SMTP_PORT", 587) or 587)
    use_ssl = bool(getattr(settings, "SMTP_USE_SSL", False)) or port == 465

    if use_ssl:
        server = smtplib.SMTP_SSL(host, port, timeout=12)
    else:
        server = smtplib.SMTP(host, port, timeout=12)
        server.starttls()

    server.login(sender_email, sender_password)
    return server


def send_welcome_email(to_email: str, full_name: Optional[str] = None) -> bool:
    """
    Sends the branded welcome email to the user asynchronously using configured SMTP credentials.
    Always saves a local HTML preview for audit and development inspection.
    """
    try:
        msg, html_content, _ = build_welcome_email(to_email, full_name)

        # Save email preview locally with embedded logo for immediate visual verification
        preview_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../email_previews"))
        os.makedirs(preview_dir, exist_ok=True)
        preview_path = os.path.join(preview_dir, "welcome_email_preview.html")
        _, b64_logo_uri = get_logo_data()
        preview_html = html_content.replace('src="cid:plagiascan_logo"', f'src="{b64_logo_uri or "/images/logo_email.png"}"')
        with open(preview_path, "w", encoding="utf-8") as f:
            f.write(preview_html)
        logger.info(f"Welcome email preview written to {preview_path}")

        if not settings.EMAIL_ADDRESS or not settings.EMAIL_PASSWORD:
            logger.warning("Email credentials not configured. Skipping live SMTP transmission.")
            return False

        server = get_smtp_connection()
        server.send_message(msg)
        server.quit()
        logger.info(f"Professional welcome email successfully sent to {to_email}")
        return True
    except smtplib.SMTPAuthenticationError as auth_err:
        logger.error(
            f"Gmail SMTP Authentication Failed: {auth_err}. "
            "Please generate an App Password at https://myaccount.google.com/apppasswords "
            "and set it as EMAIL_PASSWORD in backend/.env"
        )
        return False
    except Exception as e:
        logger.error(f"Failed to dispatch welcome email to {to_email}: {e}")
        return False


def send_scan_completed_email(
    to_email: str,
    full_name: Optional[str],
    document_title: str,
    scan_id: int,
    overall_score: float,
    ai_probability: float,
    ai_label: str,
    web_matches_count: int,
    scan_mode: str = "standard"
) -> bool:
    """
    Sends the branded scan completion notification to the user asynchronously using configured SMTP credentials.
    Always saves a local HTML preview for audit and development inspection.
    """
    try:
        msg, html_content, _ = build_scan_completed_email(
            to_email=to_email,
            full_name=full_name,
            document_title=document_title,
            scan_id=scan_id,
            overall_score=overall_score,
            ai_probability=ai_probability,
            ai_label=ai_label,
            web_matches_count=web_matches_count,
            scan_mode=scan_mode
        )

        preview_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../email_previews"))
        os.makedirs(preview_dir, exist_ok=True)
        preview_path = os.path.join(preview_dir, "scan_completed_email_preview.html")
        _, b64_logo_uri = get_logo_data()
        preview_html = html_content.replace('src="cid:plagiascan_logo"', f'src="{b64_logo_uri or "/images/logo_email.png"}"')
        with open(preview_path, "w", encoding="utf-8") as f:
            f.write(preview_html)
        logger.info(f"Scan completed email preview written to {preview_path}")

        if not settings.EMAIL_ADDRESS or not settings.EMAIL_PASSWORD:
            logger.warning("Email credentials not configured. Skipping live SMTP transmission.")
            return False

        server = get_smtp_connection()
        server.send_message(msg)
        server.quit()
        logger.info(f"Professional scan completed email sent to {to_email}")
        return True
    except smtplib.SMTPAuthenticationError as auth_err:
        logger.error(
            f"Gmail SMTP Authentication Failed: {auth_err}. "
            "Please generate an App Password at https://myaccount.google.com/apppasswords "
            "and set it as EMAIL_PASSWORD in backend/.env"
        )
        return False
    except Exception as e:
        logger.error(f"Failed to dispatch scan completed email to {to_email}: {e}")
        return False
