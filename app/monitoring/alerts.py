"""
Alerting system for FixGenie monitoring
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
import aiohttp
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import structlog

logger = structlog.get_logger()


class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert status"""
    ACTIVE = "active"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"
    SUPPRESSED = "suppressed"


@dataclass
class Alert:
    """Alert data structure"""
    id: str
    title: str
    description: str
    severity: AlertSeverity
    status: AlertStatus
    source: str
    timestamp: datetime
    labels: Dict[str, str]
    annotations: Dict[str, str]
    resolved_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary"""
        data = asdict(self)
        data['severity'] = self.severity.value
        data['status'] = self.status.value
        data['timestamp'] = self.timestamp.isoformat()
        if self.resolved_at:
            data['resolved_at'] = self.resolved_at.isoformat()
        if self.acknowledged_at:
            data['acknowledged_at'] = self.acknowledged_at.isoformat()
        return data


class AlertChannel(ABC):
    """Abstract base class for alert channels"""
    
    @abstractmethod
    async def send_alert(self, alert: Alert) -> bool:
        """Send alert through this channel"""
        pass
    
    @abstractmethod
    async def send_resolution(self, alert: Alert) -> bool:
        """Send alert resolution through this channel"""
        pass


class SlackChannel(AlertChannel):
    """Slack alert channel"""
    
    def __init__(self, webhook_url: str, channel: str = "#alerts"):
        self.webhook_url = webhook_url
        self.channel = channel
        
    async def send_alert(self, alert: Alert) -> bool:
        """Send alert to Slack"""
        try:
            color = self._get_color(alert.severity)
            
            payload = {
                "channel": self.channel,
                "username": "FixGenie Alerts",
                "icon_emoji": ":warning:",
                "attachments": [
                    {
                        "color": color,
                        "title": f"🚨 {alert.title}",
                        "text": alert.description,
                        "fields": [
                            {
                                "title": "Severity",
                                "value": alert.severity.value.upper(),
                                "short": True
                            },
                            {
                                "title": "Source",
                                "value": alert.source,
                                "short": True
                            },
                            {
                                "title": "Time",
                                "value": alert.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
                                "short": True
                            }
                        ],
                        "footer": "FixGenie Monitoring",
                        "ts": int(alert.timestamp.timestamp())
                    }
                ]
            }
            
            # Add labels as fields
            if alert.labels:
                for key, value in alert.labels.items():
                    payload["attachments"][0]["fields"].append({
                        "title": key.title(),
                        "value": value,
                        "short": True
                    })
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status == 200:
                        logger.info("Alert sent to Slack", alert_id=alert.id)
                        return True
                    else:
                        logger.error("Failed to send alert to Slack", 
                                   alert_id=alert.id, status=response.status)
                        return False
                        
        except Exception as e:
            logger.error("Error sending alert to Slack", alert_id=alert.id, error=str(e))
            return False
    
    async def send_resolution(self, alert: Alert) -> bool:
        """Send alert resolution to Slack"""
        try:
            payload = {
                "channel": self.channel,
                "username": "FixGenie Alerts",
                "icon_emoji": ":white_check_mark:",
                "attachments": [
                    {
                        "color": "good",
                        "title": f"✅ RESOLVED: {alert.title}",
                        "text": f"Alert has been resolved",
                        "fields": [
                            {
                                "title": "Resolution Time",
                                "value": alert.resolved_at.strftime("%Y-%m-%d %H:%M:%S UTC") if alert.resolved_at else "Unknown",
                                "short": True
                            },
                            {
                                "title": "Duration",
                                "value": self._calculate_duration(alert),
                                "short": True
                            }
                        ],
                        "footer": "FixGenie Monitoring",
                        "ts": int(alert.resolved_at.timestamp()) if alert.resolved_at else int(datetime.utcnow().timestamp())
                    }
                ]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status == 200:
                        logger.info("Alert resolution sent to Slack", alert_id=alert.id)
                        return True
                    else:
                        logger.error("Failed to send alert resolution to Slack", 
                                   alert_id=alert.id, status=response.status)
                        return False
                        
        except Exception as e:
            logger.error("Error sending alert resolution to Slack", alert_id=alert.id, error=str(e))
            return False
    
    def _get_color(self, severity: AlertSeverity) -> str:
        """Get color for alert severity"""
        colors = {
            AlertSeverity.LOW: "#36a64f",      # Green
            AlertSeverity.MEDIUM: "#ff9500",   # Orange
            AlertSeverity.HIGH: "#ff0000",     # Red
            AlertSeverity.CRITICAL: "#8b0000"  # Dark Red
        }
        return colors.get(severity, "#808080")
    
    def _calculate_duration(self, alert: Alert) -> str:
        """Calculate alert duration"""
        if not alert.resolved_at:
            return "Unknown"
        
        duration = alert.resolved_at - alert.timestamp
        total_seconds = int(duration.total_seconds())
        
        if total_seconds < 60:
            return f"{total_seconds}s"
        elif total_seconds < 3600:
            return f"{total_seconds // 60}m {total_seconds % 60}s"
        else:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}h {minutes}m"


class EmailChannel(AlertChannel):
    """Email alert channel"""
    
    def __init__(self, smtp_host: str, smtp_port: int, username: str, password: str, 
                 from_email: str, to_emails: List[str]):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_email = from_email
        self.to_emails = to_emails
        
    async def send_alert(self, alert: Alert) -> bool:
        """Send alert via email"""
        try:
            subject = f"[FixGenie Alert] {alert.severity.value.upper()}: {alert.title}"
            
            # Create HTML email body
            html_body = self._create_alert_html(alert)
            
            # Create email message
            msg = MimeMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to_emails)
            
            # Add HTML part
            html_part = MimeText(html_body, 'html')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            logger.info("Alert sent via email", alert_id=alert.id)
            return True
            
        except Exception as e:
            logger.error("Error sending alert via email", alert_id=alert.id, error=str(e))
            return False
    
    async def send_resolution(self, alert: Alert) -> bool:
        """Send alert resolution via email"""
        try:
            subject = f"[FixGenie Alert] RESOLVED: {alert.title}"
            
            # Create HTML email body
            html_body = self._create_resolution_html(alert)
            
            # Create email message
            msg = MimeMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to_emails)
            
            # Add HTML part
            html_part = MimeText(html_body, 'html')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            logger.info("Alert resolution sent via email", alert_id=alert.id)
            return True
            
        except Exception as e:
            logger.error("Error sending alert resolution via email", alert_id=alert.id, error=str(e))
            return False
    
    def _create_alert_html(self, alert: Alert) -> str:
        """Create HTML email body for alert"""
        severity_color = {
            AlertSeverity.LOW: "#28a745",
            AlertSeverity.MEDIUM: "#ffc107", 
            AlertSeverity.HIGH: "#fd7e14",
            AlertSeverity.CRITICAL: "#dc3545"
        }.get(alert.severity, "#6c757d")
        
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f8f9fa;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <div style="background-color: {severity_color}; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
                    <h1 style="margin: 0; font-size: 24px;">🚨 FixGenie Alert</h1>
                    <p style="margin: 5px 0 0 0; font-size: 16px; opacity: 0.9;">{alert.severity.value.upper()} Severity</p>
                </div>
                
                <div style="padding: 20px;">
                    <h2 style="color: #333; margin-top: 0;">{alert.title}</h2>
                    <p style="color: #666; font-size: 16px; line-height: 1.5;">{alert.description}</p>
                    
                    <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold; color: #333;">Source:</td>
                            <td style="padding: 8px; border-bottom: 1px solid #eee; color: #666;">{alert.source}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold; color: #333;">Time:</td>
                            <td style="padding: 8px; border-bottom: 1px solid #eee; color: #666;">{alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold; color: #333;">Alert ID:</td>
                            <td style="padding: 8px; border-bottom: 1px solid #eee; color: #666;">{alert.id}</td>
                        </tr>
        """
        
        # Add labels
        for key, value in alert.labels.items():
            html += f"""
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold; color: #333;">{key.title()}:</td>
                            <td style="padding: 8px; border-bottom: 1px solid #eee; color: #666;">{value}</td>
                        </tr>
            """
        
        html += """
                    </table>
                </div>
                
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 0 0 8px 8px; text-align: center;">
                    <p style="margin: 0; color: #666; font-size: 14px;">FixGenie Monitoring System</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _create_resolution_html(self, alert: Alert) -> str:
        """Create HTML email body for alert resolution"""
        duration = ""
        if alert.resolved_at:
            delta = alert.resolved_at - alert.timestamp
            total_seconds = int(delta.total_seconds())
            if total_seconds < 60:
                duration = f"{total_seconds}s"
            elif total_seconds < 3600:
                duration = f"{total_seconds // 60}m {total_seconds % 60}s"
            else:
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                duration = f"{hours}h {minutes}m"
        
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f8f9fa;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <div style="background-color: #28a745; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
                    <h1 style="margin: 0; font-size: 24px;">✅ Alert Resolved</h1>
                    <p style="margin: 5px 0 0 0; font-size: 16px; opacity: 0.9;">FixGenie Alert System</p>
                </div>
                
                <div style="padding: 20px;">
                    <h2 style="color: #333; margin-top: 0;">{alert.title}</h2>
                    <p style="color: #666; font-size: 16px;">This alert has been automatically resolved.</p>
                    
                    <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold; color: #333;">Alert ID:</td>
                            <td style="padding: 8px; border-bottom: 1px solid #eee; color: #666;">{alert.id}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold; color: #333;">Resolved At:</td>
                            <td style="padding: 8px; border-bottom: 1px solid #eee; color: #666;">{alert.resolved_at.strftime('%Y-%m-%d %H:%M:%S UTC') if alert.resolved_at else 'Unknown'}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold; color: #333;">Duration:</td>
                            <td style="padding: 8px; border-bottom: 1px solid #eee; color: #666;">{duration}</td>
                        </tr>
                    </table>
                </div>
                
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 0 0 8px 8px; text-align: center;">
                    <p style="margin: 0; color: #666; font-size: 14px;">FixGenie Monitoring System</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html


class AlertRule:
    """Alert rule definition"""
    
    def __init__(self, name: str, condition: Callable[[Dict[str, Any]], bool], 
                 severity: AlertSeverity, description: str, labels: Dict[str, str] = None):
        self.name = name
        self.condition = condition
        self.severity = severity
        self.description = description
        self.labels = labels or {}
        self.last_triggered = None
        self.cooldown_period = timedelta(minutes=5)  # Prevent spam
        
    def should_trigger(self, metrics: Dict[str, Any]) -> bool:
        """Check if alert should trigger"""
        # Check cooldown
        if self.last_triggered and datetime.utcnow() - self.last_triggered < self.cooldown_period:
            return False
            
        # Check condition
        if self.condition(metrics):
            self.last_triggered = datetime.utcnow()
            return True
            
        return False


class AlertManager:
    """Central alert management system"""
    
    def __init__(self):
        self.channels: List[AlertChannel] = []
        self.rules: List[AlertRule] = []
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        
    def add_channel(self, channel: AlertChannel):
        """Add alert channel"""
        self.channels.append(channel)
        logger.info("Alert channel added", channel_type=type(channel).__name__)
        
    def add_rule(self, rule: AlertRule):
        """Add alert rule"""
        self.rules.append(rule)
        logger.info("Alert rule added", rule_name=rule.name)
        
    async def check_rules(self, metrics: Dict[str, Any]):
        """Check all alert rules against current metrics"""
        for rule in self.rules:
            try:
                if rule.should_trigger(metrics):
                    await self._trigger_alert(rule, metrics)
            except Exception as e:
                logger.error("Error checking alert rule", rule_name=rule.name, error=str(e))
                
    async def _trigger_alert(self, rule: AlertRule, metrics: Dict[str, Any]):
        """Trigger an alert"""
        alert_id = f"{rule.name}_{int(datetime.utcnow().timestamp())}"
        
        alert = Alert(
            id=alert_id,
            title=rule.name,
            description=rule.description,
            severity=rule.severity,
            status=AlertStatus.ACTIVE,
            source="FixGenie Monitoring",
            timestamp=datetime.utcnow(),
            labels=rule.labels.copy(),
            annotations={"metrics": json.dumps(metrics, default=str)}
        )
        
        # Store active alert
        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)
        
        # Send to all channels
        for channel in self.channels:
            try:
                await channel.send_alert(alert)
            except Exception as e:
                logger.error("Error sending alert", alert_id=alert_id, 
                           channel_type=type(channel).__name__, error=str(e))
        
        logger.warning("Alert triggered", alert_id=alert_id, rule_name=rule.name)
        
    async def resolve_alert(self, alert_id: str):
        """Resolve an active alert"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.utcnow()
            
            # Send resolution to all channels
            for channel in self.channels:
                try:
                    await channel.send_resolution(alert)
                except Exception as e:
                    logger.error("Error sending alert resolution", alert_id=alert_id,
                               channel_type=type(channel).__name__, error=str(e))
            
            # Remove from active alerts
            del self.active_alerts[alert_id]
            
            logger.info("Alert resolved", alert_id=alert_id)
            
    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts"""
        return list(self.active_alerts.values())
        
    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """Get alert history"""
        return self.alert_history[-limit:]


# Pre-defined alert rules for FixGenie
def create_default_alert_rules() -> List[AlertRule]:
    """Create default alert rules for FixGenie"""
    rules = []
    
    # High error rate
    rules.append(AlertRule(
        name="High Error Rate",
        condition=lambda m: m.get("error_rate", 0) > 0.05,  # 5% error rate
        severity=AlertSeverity.HIGH,
        description="Error rate is above 5%",
        labels={"component": "api", "type": "error_rate"}
    ))
    
    # Slow response time
    rules.append(AlertRule(
        name="Slow Response Time",
        condition=lambda m: m.get("avg_response_time", 0) > 5.0,  # 5 seconds
        severity=AlertSeverity.MEDIUM,
        description="Average response time is above 5 seconds",
        labels={"component": "api", "type": "performance"}
    ))
    
    # High memory usage
    rules.append(AlertRule(
        name="High Memory Usage",
        condition=lambda m: m.get("memory_percent", 0) > 85,  # 85% memory usage
        severity=AlertSeverity.HIGH,
        description="Memory usage is above 85%",
        labels={"component": "system", "type": "resource"}
    ))
    
    # AI service failures
    rules.append(AlertRule(
        name="AI Service Failures",
        condition=lambda m: m.get("ai_error_rate", 0) > 0.1,  # 10% AI error rate
        severity=AlertSeverity.CRITICAL,
        description="AI service error rate is above 10%",
        labels={"component": "ai", "type": "service_failure"}
    ))
    
    # Database connection issues
    rules.append(AlertRule(
        name="Database Connection Issues",
        condition=lambda m: m.get("db_connection_errors", 0) > 5,  # 5 connection errors
        severity=AlertSeverity.CRITICAL,
        description="Multiple database connection errors detected",
        labels={"component": "database", "type": "connection"}
    ))
    
    return rules


# Export alert system components
__all__ = [
    "Alert",
    "AlertSeverity",
    "AlertStatus", 
    "AlertChannel",
    "SlackChannel",
    "EmailChannel",
    "AlertRule",
    "AlertManager",
    "create_default_alert_rules"
]
