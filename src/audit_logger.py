# src/audit_logger.py
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import hashlib

class AuditLogger:
    """Track all RAG system queries for compliance auditing"""
    
    def __init__(self, log_file: str = None):
        """
        Initialize audit logger
        
        Args:
            log_file: Path to audit log file (default: data/audit/query_logs.jsonl)
        """
        if log_file is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            log_dir = os.path.join(script_dir, '../data/audit')
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, 'query_logs.jsonl')
        
        self.log_file = log_file
        
        # Ensure log file exists
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w') as f:
                pass
        
        print(f"✓ Audit logger initialized: {self.log_file}")
    
    def log_query(self,
                  user_id: str,
                  query: str,
                  sources_retrieved: List[str],
                  answer_generated: bool,
                  response_time_seconds: float,
                  model_used: str,
                  num_sources: int = 0,
                  error: Optional[str] = None) -> str:
        """
        Log a RAG query
        
        Args:
            user_id: Employee ID or username
            query: The question asked
            sources_retrieved: List of source files used
            answer_generated: Whether answer was successfully generated
            response_time_seconds: Time taken to respond
            model_used: LLM model name
            num_sources: Number of sources retrieved
            error: Error message if query failed
        
        Returns:
            query_id: Unique identifier for this query
        """
        timestamp = datetime.now().isoformat()
        
        # Generate unique query ID
        query_id = hashlib.md5(
            f"{user_id}{timestamp}{query}".encode()
        ).hexdigest()[:12]
        
        log_entry = {
            'query_id': query_id,
            'timestamp': timestamp,
            'user_id': user_id,
            'query': query,
            'query_length': len(query),
            'sources_retrieved': sources_retrieved,
            'num_sources': num_sources,
            'answer_generated': answer_generated,
            'response_time_seconds': round(response_time_seconds, 2),
            'model_used': model_used,
            'error': error,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'hour': datetime.now().hour
        }
        
        # Append to JSONL file (one JSON object per line)
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
        
        return query_id
    
    def get_logs(self, 
                 user_id: Optional[str] = None,
                 start_date: Optional[str] = None,
                 end_date: Optional[str] = None,
                 limit: Optional[int] = None) -> List[Dict]:
        """
        Retrieve audit logs with filters
        
        Args:
            user_id: Filter by specific user
            start_date: Filter from date (YYYY-MM-DD)
            end_date: Filter to date (YYYY-MM-DD)
            limit: Max number of logs to return
        
        Returns:
            List of log entries
        """
        logs = []
        
        with open(self.log_file, 'r') as f:
            for line in f:
                if line.strip():
                    log = json.loads(line)
                    
                    # Apply filters
                    if user_id and log['user_id'] != user_id:
                        continue
                    
                    if start_date and log['date'] < start_date:
                        continue
                    
                    if end_date and log['date'] > end_date:
                        continue
                    
                    logs.append(log)
        
        # Apply limit
        if limit:
            logs = logs[-limit:]  # Most recent N logs
        
        return logs
    
    def get_statistics(self, days: int = 30) -> Dict:
        """
        Generate usage statistics
        
        Args:
            days: Number of days to analyze
        
        Returns:
            Statistics dict
        """
        from datetime import timedelta
        from collections import defaultdict
        
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        logs = self.get_logs(start_date=cutoff_date)
        
        if not logs:
            return {
                'total_queries': 0,
                'period_days': days,
                'message': 'No queries in this period'
            }
        
        # Calculate statistics
        total_queries = len(logs)
        unique_users = len(set(log['user_id'] for log in logs))
        avg_response_time = sum(log['response_time_seconds'] for log in logs) / total_queries
        
        # Success rate
        successful = sum(1 for log in logs if log['answer_generated'])
        success_rate = successful / total_queries if total_queries > 0 else 0
        
        # Most common sources
        source_counts = defaultdict(int)
        for log in logs:
            for source in log['sources_retrieved']:
                source_counts[source] += 1
        
        top_sources = sorted(source_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Queries by day
        queries_by_day = defaultdict(int)
        for log in logs:
            queries_by_day[log['date']] += 1
        
        # Peak hour
        queries_by_hour = defaultdict(int)
        for log in logs:
            queries_by_hour[log['hour']] += 1
        
        peak_hour = max(queries_by_hour.items(), key=lambda x: x[1])[0] if queries_by_hour else 0
        
        return {
            'period_days': days,
            'total_queries': total_queries,
            'unique_users': unique_users,
            'avg_response_time_seconds': round(avg_response_time, 2),
            'success_rate': round(success_rate, 2),
            'queries_per_day': round(total_queries / days, 1),
            'top_5_sources': [
                {'source': source, 'times_referenced': count}
                for source, count in top_sources
            ],
            'peak_hour': peak_hour,
            'queries_by_date': dict(queries_by_day)
        }
    
    def search_queries(self, keyword: str, limit: int = 20) -> List[Dict]:
        """
        Search queries containing keyword
        
        Args:
            keyword: Search term
            limit: Max results
        
        Returns:
            Matching log entries
        """
        matches = []
        
        with open(self.log_file, 'r') as f:
            for line in f:
                if line.strip():
                    log = json.loads(line)
                    if keyword.lower() in log['query'].lower():
                        matches.append(log)
                        
                        if len(matches) >= limit:
                            break
        
        return matches


def main():
    """Demo audit logging"""
    import time
    
    print("="*60)
    print("AUDIT LOGGING SYSTEM DEMO")
    print("="*60)
    
    # Initialize logger
    print("\nInitializing audit logger...")
    logger = AuditLogger()
    
    # Simulate some queries
    print("\nLogging sample queries...")
    
    sample_queries = [
        {
            'user_id': 'EMP0001',
            'query': 'What are HIPAA privacy requirements?',
            'sources': ['hipaa_privacy_rule.pdf', 'HIPAA'],
            'time': 12.3,
            'success': True
        },
        {
            'user_id': 'EMP0042',
            'query': 'How do I dispose of sharps?',
            'sources': ['osha_bloodborne_pathogens.pdf', 'Sharps_waste'],
            'time': 10.5,
            'success': True
        },
        {
            'user_id': 'EMP0001',
            'query': 'Hand hygiene protocol?',
            'sources': ['Guideline_for_Hand_Hygiene.pdf'],
            'time': 9.8,
            'success': True
        },
        {
            'user_id': 'EMP0099',
            'query': 'What is the capital of France?',
            'sources': [],
            'time': 5.2,
            'success': False
        }
    ]
    
    for i, query_data in enumerate(sample_queries, 1):
        query_id = logger.log_query(
            user_id=query_data['user_id'],
            query=query_data['query'],
            sources_retrieved=query_data['sources'],
            answer_generated=query_data['success'],
            response_time_seconds=query_data['time'],
            model_used='llama3.1:8b',
            num_sources=len(query_data['sources'])
        )
        print(f"  [{i}/{len(sample_queries)}] Logged query {query_id}")
        time.sleep(0.1)
    
    print(f"\n✓ Logged {len(sample_queries)} sample queries")
    
    # Retrieve logs
    print("\n" + "="*60)
    print("RETRIEVING LOGS")
    print("="*60)
    
    # All logs
    all_logs = logger.get_logs()
    print(f"\nTotal logs in system: {len(all_logs)}")
    
    # Filter by user
    user_logs = logger.get_logs(user_id='EMP0001')
    print(f"Logs for EMP0001: {len(user_logs)}")
    
    # Search
    print("\n" + "="*60)
    print("SEARCHING LOGS")
    print("="*60)
    
    search_results = logger.search_queries('HIPAA', limit=10)
    print(f"\nQueries containing 'HIPAA': {len(search_results)}")
    
    if search_results:
        print("\nSample result:")
        result = search_results[0]
        print(f"  Query ID: {result['query_id']}")
        print(f"  User: {result['user_id']}")
        print(f"  Query: {result['query']}")
        print(f"  Timestamp: {result['timestamp']}")
    
    # Statistics
    print("\n" + "="*60)
    print("USAGE STATISTICS (Last 30 Days)")
    print("="*60)
    
    stats = logger.get_statistics(days=30)
    
    print(f"\nTotal Queries: {stats['total_queries']}")
    print(f"Unique Users: {stats['unique_users']}")
    print(f"Avg Response Time: {stats['avg_response_time_seconds']}s")
    print(f"Success Rate: {stats['success_rate']:.0%}")
    print(f"Queries/Day: {stats['queries_per_day']}")
    print(f"Peak Hour: {stats['peak_hour']}:00")
    
    print("\nTop 5 Referenced Sources:")
    for i, source_stat in enumerate(stats['top_5_sources'], 1):
        print(f"  {i}. {source_stat['source']}: {source_stat['times_referenced']} times")
    
    print("\n" + "="*60)
    print("Audit logging demo complete!")
    print("="*60)


if __name__ == '__main__':
    main()