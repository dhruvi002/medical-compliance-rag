# src/compliance_dashboard.py
import json
import os
from datetime import datetime, timedelta
from typing import Dict
from audit_logger import AuditLogger
from document_registry import DocumentRegistry
from access_control import AccessControlSystem

class ComplianceDashboard:
    """Comprehensive governance and compliance dashboard"""
    
    def __init__(self):
        """Initialize dashboard with all governance components"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Initialize components
        print("Initializing compliance dashboard components...")
        
        self.audit_logger = AuditLogger()
        self.doc_registry = DocumentRegistry()
        self.access_control = AccessControlSystem()
        
        print("✓ All components initialized\n")
    
    def generate_executive_summary(self, days: int = 30) -> Dict:
        """
        Generate executive summary for leadership
        
        Args:
            days: Period to analyze
        
        Returns:
            Executive summary dict
        """
        # Audit statistics
        audit_stats = self.audit_logger.get_statistics(days=days)
        
        # Document usage
        doc_report = self.doc_registry.get_usage_report()
        
        # User activity
        user_report = self.access_control.get_usage_report()
        
        # Data freshness
        stale_docs = self.doc_registry.get_stale_documents(days=365)
        
        return {
            'period_days': days,
            'generated_at': datetime.now().isoformat(),
            'system_health': {
                'total_queries': audit_stats.get('total_queries', 0),
                'active_users': user_report['active_users'],
                'avg_response_time': audit_stats.get('avg_response_time_seconds', 0),
                'success_rate': audit_stats.get('success_rate', 0),
                'queries_per_day': audit_stats.get('queries_per_day', 0)
            },
            'knowledge_base': {
                'total_documents': doc_report['total_documents'],
                'active_documents': doc_report['active_documents'],
                'stale_documents': len(stale_docs),
                'never_referenced': doc_report['never_referenced_count']
            },
            'user_engagement': {
                'total_users': user_report['total_users'],
                'active_users': user_report['active_users'],
                'never_queried': user_report['never_queried'],
                'engagement_rate': round((user_report['active_users'] - user_report['never_queried']) / user_report['active_users'] * 100, 1) if user_report['active_users'] > 0 else 0
            },
            'top_sources': audit_stats.get('top_5_sources', [])[:5],
            'alerts': self._generate_alerts(audit_stats, doc_report, user_report, stale_docs)
        }
    
    def _generate_alerts(self, audit_stats, doc_report, user_report, stale_docs) -> list:
        """Generate system alerts"""
        alerts = []
        
        # Slow response times
        if audit_stats.get('avg_response_time_seconds', 0) > 30:
            alerts.append({
                'severity': 'warning',
                'message': f"Avg response time high: {audit_stats['avg_response_time_seconds']:.1f}s (target: <20s)"
            })
        
        # Low success rate
        if audit_stats.get('success_rate', 1) < 0.9:
            alerts.append({
                'severity': 'critical',
                'message': f"Low success rate: {audit_stats['success_rate']:.0%} (target: >90%)"
            })
        
        # Stale documents
        if len(stale_docs) > 10:
            alerts.append({
                'severity': 'warning',
                'message': f"{len(stale_docs)} documents need verification (>1 year old)"
            })
        
        # Unused documents
        if doc_report['never_referenced_count'] > 20:
            alerts.append({
                'severity': 'info',
                'message': f"{doc_report['never_referenced_count']} documents never referenced"
            })
        
        # Low user engagement
        engagement = (user_report['active_users'] - user_report['never_queried']) / user_report['active_users'] if user_report['active_users'] > 0 else 0
        if engagement < 0.5:
            alerts.append({
                'severity': 'warning',
                'message': f"Low user engagement: {engagement:.0%} of users have queried system"
            })
        
        return alerts
    
    def display_dashboard(self, days: int = 30):
        """Display comprehensive dashboard"""
        summary = self.generate_executive_summary(days=days)
        
        # Header
        print("=" * 80)
        print(" " * 25 + "COMPLIANCE GOVERNANCE DASHBOARD")
        print("=" * 80)
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Period: Last {days} days")
        print("=" * 80)
        
        # System Health
        print("\n┌" + "─" * 78 + "┐")
        print("│" + " " * 30 + "SYSTEM HEALTH" + " " * 35 + "│")
        print("├" + "─" * 78 + "┤")
        
        health = summary['system_health']
        print(f"│ Total Queries (30d):              {health['total_queries']:>6}                             │")
        print(f"│ Active Users:                      {health['active_users']:>6}                             │")
        print(f"│ Avg Response Time:              {health['avg_response_time']:>6.1f}s                            │")
        print(f"│ Success Rate:                      {health['success_rate']:>5.0%}                             │")
        print(f"│ Queries/Day:                       {health['queries_per_day']:>6.1f}                             │")
        
        print("└" + "─" * 78 + "┘")
        
        # Knowledge Base
        print("\n┌" + "─" * 78 + "┐")
        print("│" + " " * 29 + "KNOWLEDGE BASE" + " " * 34 + "│")
        print("├" + "─" * 78 + "┤")
        
        kb = summary['knowledge_base']
        print(f"│ Total Documents:                   {kb['total_documents']:>6}                             │")
        print(f"│ Active Documents:                  {kb['active_documents']:>6}                             │")
        print(f"│ Stale (>1 year):                   {kb['stale_documents']:>6}                             │")
        print(f"│ Never Referenced:                  {kb['never_referenced']:>6}                             │")
        
        # Calculate freshness percentage
        freshness = ((kb['active_documents'] - kb['stale_documents']) / kb['active_documents'] * 100) if kb['active_documents'] > 0 else 0
        bar_length = int(freshness / 2)
        bar = "█" * bar_length + "░" * (50 - bar_length)
        print(f"│ Freshness: {bar} {freshness:>5.1f}% │")
        
        print("└" + "─" * 78 + "┘")
        
        # User Engagement
        print("\n┌" + "─" * 78 + "┐")
        print("│" + " " * 28 + "USER ENGAGEMENT" + " " * 34 + "│")
        print("├" + "─" * 78 + "┤")
        
        users = summary['user_engagement']
        print(f"│ Total Users:                       {users['total_users']:>6}                             │")
        print(f"│ Active Users:                      {users['active_users']:>6}                             │")
        print(f"│ Never Queried:                     {users['never_queried']:>6}                             │")
        
        engagement = users['engagement_rate']
        bar_length = int(engagement / 2)
        bar = "█" * bar_length + "░" * (50 - bar_length)
        print(f"│ Engagement: {bar} {engagement:>5.1f}% │")
        
        print("└" + "─" * 78 + "┘")
        
        # Top Sources
        print("\n┌" + "─" * 78 + "┐")
        print("│" + " " * 26 + "TOP 5 REFERENCED SOURCES" + " " * 27 + "│")
        print("├" + "─" * 78 + "┤")
        
        if summary['top_sources']:
            for i, source in enumerate(summary['top_sources'][:5], 1):
                source_name = source['source'][:50]
                count = source['times_referenced']
                print(f"│ {i}. {source_name:50s} {count:>4} refs │")
        else:
            print("│" + " " * 30 + "No data available" + " " * 30 + "│")
        
        print("└" + "─" * 78 + "┘")
        
        # Alerts
        if summary['alerts']:
            print("\n┌" + "─" * 78 + "┐")
            print("│" + " " * 32 + "ALERTS" + " " * 39 + "│")
            print("├" + "─" * 78 + "┤")
            
            for alert in summary['alerts']:
                severity = alert['severity'].upper()
                icon = "🔴" if severity == "CRITICAL" else "⚠️" if severity == "WARNING" else "ℹ️"
                message = alert['message'][:65]
                print(f"│ {icon} {severity:8s} {message:65s} │")
            
            print("└" + "─" * 78 + "┘")
        
        # Recommendations
        print("\n" + "=" * 80)
        print("RECOMMENDED ACTIONS")
        print("=" * 80)
        
        recommendations = self._generate_recommendations(summary)
        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. {rec}")
        
        print("\n" + "=" * 80)
    
    def _generate_recommendations(self, summary: Dict) -> list:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Based on stale documents
        if summary['knowledge_base']['stale_documents'] > 5:
            recommendations.append(
                f"📚 Review and verify {summary['knowledge_base']['stale_documents']} stale documents"
            )
        
        # Based on unused documents
        if summary['knowledge_base']['never_referenced'] > 10:
            recommendations.append(
                f"🗑️  Archive or promote {summary['knowledge_base']['never_referenced']} unused documents"
            )
        
        # Based on user engagement
        if summary['user_engagement']['never_queried'] > 20:
            recommendations.append(
                f"📢 Send onboarding materials to {summary['user_engagement']['never_queried']} inactive users"
            )
        
        # Based on response time
        if summary['system_health']['avg_response_time'] > 20:
            recommendations.append(
                f"⚡ Optimize system - avg response time is {summary['system_health']['avg_response_time']:.1f}s"
            )
        
        # Based on success rate
        if summary['system_health']['success_rate'] < 0.9:
            recommendations.append(
                f"🔧 Investigate query failures - success rate is {summary['system_health']['success_rate']:.0%}"
            )
        
        # If no issues
        if not recommendations:
            recommendations.append("✅ System performing well - maintain current operations")
        
        return recommendations
    
    def export_report(self, filename: str = None, days: int = 30):
        """Export dashboard report as JSON"""
        if filename is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            output_dir = os.path.join(script_dir, '../data/governance')
            os.makedirs(output_dir, exist_ok=True)
            filename = os.path.join(output_dir, f'compliance_report_{datetime.now().strftime("%Y%m%d")}.json')
        
        summary = self.generate_executive_summary(days=days)
        
        with open(filename, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n📄 Report exported to: {filename}")
        return filename


def main():
    """Generate and display compliance dashboard"""
    print("=" * 80)
    print(" " * 25 + "INITIALIZING DASHBOARD")
    print("=" * 80)
    print()
    
    # Initialize dashboard
    dashboard = ComplianceDashboard()
    
    # Display dashboard
    dashboard.display_dashboard(days=30)
    
    # Export report
    print("\n" + "=" * 80)
    print("EXPORTING REPORT")
    print("=" * 80)
    
    dashboard.export_report(days=30)
    
    print("\n" + "=" * 80)
    print("Dashboard generation complete!")
    print("=" * 80)


if __name__ == '__main__':
    main()