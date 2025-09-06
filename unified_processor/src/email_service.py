"""Email notification service"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, Any

from .config import Config


class EmailService:
    """Handles email notifications for processing updates"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.enabled = config.email.enabled
    
    async def send_email(self, subject: str, body: str, html_body: str = None):
        """Send email notification"""
        if not self.enabled:
            return
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.config.email.sender_email
            msg['To'] = self.config.email.recipient_email
            msg['Subject'] = subject
            
            # Add text body
            msg.attach(MIMEText(body, 'plain'))
            
            # Add HTML body if provided
            if html_body:
                msg.attach(MIMEText(html_body, 'html'))
            
            # Send email
            with smtplib.SMTP(self.config.email.smtp_server, self.config.email.smtp_port) as server:
                server.starttls()
                server.login(self.config.email.sender_email, self.config.email.sender_password)
                server.send_message(msg)
            
            self.logger.info(f"Email sent: {subject}")
            
        except Exception as e:
            self.logger.error(f"Failed to send email: {e}")
    
    async def send_progress_report(self, stats: Dict[str, Any], processing_time: float):
        """Send progress report"""
        if not self.enabled or not self.config.email.daily_report:
            return
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Calculate percentages
        total = stats.get('total', 0)
        completed = stats.get('completed', 0)
        failed = stats.get('failed_permanently', 0)
        in_progress = stats.get('processing', 0)
        pending = stats.get('pending', 0)
        
        completion_pct = (completed / total * 100) if total > 0 else 0
        
        # Estimate time remaining
        if completed > 0 and pending > 0 and processing_time > 0:
            avg_time_per_norm = processing_time / completed
            estimated_remaining = (pending * avg_time_per_norm) / 3600  # hours
            eta_text = f"Estimated remaining: {estimated_remaining:.1f} hours"
        else:
            eta_text = "ETA: Unknown"
        
        subject = f"Norm Processing Progress Report - {completion_pct:.1f}% Complete"
        
        body = f"""
Norm Processing Progress Report
Generated: {timestamp}

OVERALL PROGRESS:
- Total norms: {total:,}
- Completed: {completed:,} ({completion_pct:.1f}%)
- Failed permanently: {failed:,}
- Currently processing: {in_progress:,}
- Pending: {pending:,}

PERFORMANCE:
- Total processing time: {processing_time/3600:.1f} hours
- Average per norm: {(processing_time/completed):.2f if completed > 0 else 'N/A'} seconds
- {eta_text}

STATUS BREAKDOWN:
"""
        
        for status, count in stats.items():
            if status not in ['total']:
                percentage = (count / total * 100) if total > 0 else 0
                body += f"- {status.replace('_', ' ').title()}: {count:,} ({percentage:.1f}%)\n"
        
        # HTML version
        html_body = f"""
<html>
<head></head>
<body>
<h2>Norm Processing Progress Report</h2>
<p><strong>Generated:</strong> {timestamp}</p>

<h3>Overall Progress</h3>
<table border="1" cellpadding="5" cellspacing="0">
<tr><td><strong>Total norms</strong></td><td>{total:,}</td></tr>
<tr style="background-color: #d4edda;"><td><strong>Completed</strong></td><td>{completed:,} ({completion_pct:.1f}%)</td></tr>
<tr style="background-color: #f8d7da;"><td><strong>Failed permanently</strong></td><td>{failed:,}</td></tr>
<tr style="background-color: #fff3cd;"><td><strong>Currently processing</strong></td><td>{in_progress:,}</td></tr>
<tr><td><strong>Pending</strong></td><td>{pending:,}</td></tr>
</table>

<h3>Performance</h3>
<ul>
<li>Total processing time: {processing_time/3600:.1f} hours</li>
<li>Average per norm: {(processing_time/completed):.2f if completed > 0 else 'N/A'} seconds</li>
<li>{eta_text}</li>
</ul>

<h3>Progress Bar</h3>
<div style="background-color: #e0e0e0; border-radius: 10px; padding: 3px;">
    <div style="background-color: #4CAF50; width: {completion_pct:.1f}%; height: 20px; border-radius: 10px; text-align: center; line-height: 20px; color: white;">
        {completion_pct:.1f}%
    </div>
</div>

</body>
</html>
"""
        
        await self.send_email(subject, body, html_body)
    
    async def send_error_notification(self, error_message: str, norm_id: str = None):
        """Send error notification"""
        if not self.enabled or not self.config.email.error_notifications:
            return
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        subject = f"Norm Processing Error{' - ID: ' + norm_id if norm_id else ''}"
        
        body = f"""
Processing Error Notification
Time: {timestamp}
Norm ID: {norm_id or 'Unknown'}

Error Details:
{error_message}

This is an automated notification from the Norm Processing System.
"""
        
        await self.send_email(subject, body)
    
    async def send_completion_notification(self, stats: Dict[str, Any], total_time: float):
        """Send notification when processing is complete"""
        if not self.enabled:
            return
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        total = stats.get('total', 0)
        completed = stats.get('completed', 0)
        failed = stats.get('failed_permanently', 0)
        
        subject = "Norm Processing Complete!"
        
        body = f"""
Norm Processing Completed Successfully!
Completion Time: {timestamp}

FINAL RESULTS:
- Total norms processed: {total:,}
- Successfully completed: {completed:,} ({completed/total*100:.1f}%)
- Permanently failed: {failed:,} ({failed/total*100:.1f}%)
- Total processing time: {total_time/3600:.1f} hours
- Average time per norm: {total_time/total:.2f} seconds

Congratulations! The processing job has finished.
"""
        
        await self.send_email(subject, body)