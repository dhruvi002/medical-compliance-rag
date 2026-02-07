# src/document_registry.py
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict

class DocumentRegistry:
    """Track document metadata and lifecycle"""
    
    def __init__(self, registry_file: str = None):
        """
        Initialize document registry
        
        Args:
            registry_file: Path to registry file
        """
        if registry_file is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            data_dir = os.path.join(script_dir, '../data/governance')
            os.makedirs(data_dir, exist_ok=True)
            registry_file = os.path.join(data_dir, 'document_registry.json')
        
        self.registry_file = registry_file
        
        # Load existing registry or create new
        if os.path.exists(self.registry_file):
            with open(self.registry_file, 'r') as f:
                self.registry = json.load(f)
        else:
            self.registry = {'documents': {}}
        
        print(f"✓ Document registry initialized: {self.registry_file}")
        print(f"  Documents tracked: {len(self.registry['documents'])}")
    
    def register_document(self,
                         document_id: str,
                         source_url: Optional[str] = None,
                         document_type: str = "compliance",
                         classification: str = "public",
                         version: str = "1.0") -> None:
        """
        Register a new document
        
        Args:
            document_id: Unique document identifier (filename)
            source_url: URL where document was obtained
            document_type: Type of document (compliance, policy, guideline)
            classification: Security level (public, internal, restricted)
            version: Document version
        """
        if document_id in self.registry['documents']:
            print(f"⚠️  Document {document_id} already registered")
            return
        
        self.registry['documents'][document_id] = {
            'document_id': document_id,
            'added_date': datetime.now().isoformat(),
            'source_url': source_url,
            'document_type': document_type,
            'classification': classification,
            'version': version,
            'last_verified': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'times_referenced': 0,
            'status': 'active',
            'retention_years': 7,  # Default for compliance docs
            'tags': []
        }
        
        self._save()
    
    def update_reference_count(self, document_id: str, increment: int = 1) -> None:
        """
        Update how many times document has been referenced
        
        Args:
            document_id: Document to update
            increment: Amount to increment by
        """
        if document_id in self.registry['documents']:
            self.registry['documents'][document_id]['times_referenced'] += increment
            self._save()
    
    def mark_verified(self, document_id: str) -> None:
        """Mark document as verified/reviewed"""
        if document_id in self.registry['documents']:
            self.registry['documents'][document_id]['last_verified'] = datetime.now().isoformat()
            self._save()
    
    def update_version(self, document_id: str, new_version: str) -> None:
        """Update document version"""
        if document_id in self.registry['documents']:
            self.registry['documents'][document_id]['version'] = new_version
            self.registry['documents'][document_id]['last_updated'] = datetime.now().isoformat()
            self._save()
    
    def archive_document(self, document_id: str) -> None:
        """Archive a document (mark as inactive)"""
        if document_id in self.registry['documents']:
            self.registry['documents'][document_id]['status'] = 'archived'
            self.registry['documents'][document_id]['archived_date'] = datetime.now().isoformat()
            self._save()
    
    def get_document_info(self, document_id: str) -> Optional[Dict]:
        """Get information about a document"""
        return self.registry['documents'].get(document_id)
    
    def get_stale_documents(self, days: int = 365) -> List[Dict]:
        """
        Get documents not verified in X days
        
        Args:
            days: Days since last verification
        
        Returns:
            List of stale documents
        """
        cutoff = datetime.now() - timedelta(days=days)
        stale = []
        
        for doc_id, doc in self.registry['documents'].items():
            if doc['status'] != 'active':
                continue
            
            last_verified = datetime.fromisoformat(doc['last_verified'])
            if last_verified < cutoff:
                days_old = (datetime.now() - last_verified).days
                stale.append({
                    'document_id': doc_id,
                    'last_verified': doc['last_verified'],
                    'days_since_verification': days_old,
                    'document_type': doc['document_type']
                })
        
        return sorted(stale, key=lambda x: x['days_since_verification'], reverse=True)
    
    def get_usage_report(self) -> Dict:
        """Generate usage report for all documents"""
        total_docs = len(self.registry['documents'])
        active_docs = sum(1 for d in self.registry['documents'].values() if d['status'] == 'active')
        archived_docs = sum(1 for d in self.registry['documents'].values() if d['status'] == 'archived')
        
        # Documents by type
        by_type = defaultdict(int)
        for doc in self.registry['documents'].values():
            by_type[doc['document_type']] += 1
        
        # Documents by classification
        by_classification = defaultdict(int)
        for doc in self.registry['documents'].values():
            by_classification[doc['classification']] += 1
        
        # Most referenced
        most_referenced = sorted(
            self.registry['documents'].items(),
            key=lambda x: x[1]['times_referenced'],
            reverse=True
        )[:10]
        
        # Never referenced
        never_referenced = [
            doc_id for doc_id, doc in self.registry['documents'].items()
            if doc['times_referenced'] == 0 and doc['status'] == 'active'
        ]
        
        return {
            'total_documents': total_docs,
            'active_documents': active_docs,
            'archived_documents': archived_docs,
            'by_type': dict(by_type),
            'by_classification': dict(by_classification),
            'most_referenced': [
                {
                    'document_id': doc_id,
                    'times_referenced': doc['times_referenced'],
                    'document_type': doc['document_type']
                }
                for doc_id, doc in most_referenced
            ],
            'never_referenced': never_referenced,
            'never_referenced_count': len(never_referenced)
        }
    
    def import_from_processed_data(self) -> None:
        """Import documents from existing processed data"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Import PDFs
        docs_file = os.path.join(script_dir, '../data/processed/documents.json')
        if os.path.exists(docs_file):
            with open(docs_file, 'r') as f:
                docs = json.load(f)
            
            print(f"\nImporting {len(docs)} PDF documents...")
            for doc in docs:
                filename = doc.get('filename', 'unknown.pdf')
                self.register_document(
                    document_id=filename,
                    source_url='https://www.osha.gov/publications',
                    document_type='compliance',
                    classification='public'
                )
        
        # Import Wikipedia articles
        wiki_file = os.path.join(script_dir, '../data/processed/wikipedia_compliance.json')
        if os.path.exists(wiki_file):
            with open(wiki_file, 'r') as f:
                articles = json.load(f)
            
            print(f"Importing {len(articles)} Wikipedia articles...")
            for article in articles:
                title = article.get('title', 'Unknown')
                source = article.get('source', '')
                self.register_document(
                    document_id=title,
                    source_url=source,
                    document_type='reference',
                    classification='public'
                )
        
        print(f"✓ Imported {len(self.registry['documents'])} documents")
    
    def sync_with_audit_logs(self, audit_log_file: str) -> None:
        """
        Update reference counts from audit logs
        
        Args:
            audit_log_file: Path to query_logs.jsonl
        """
        if not os.path.exists(audit_log_file):
            print(f"⚠️  Audit log not found: {audit_log_file}")
            return
        
        print("\nSyncing with audit logs...")
        
        # Count references per document
        reference_counts = defaultdict(int)
        
        with open(audit_log_file, 'r') as f:
            for line in f:
                if line.strip():
                    log = json.loads(line)
                    for source in log.get('sources_retrieved', []):
                        reference_counts[source] += 1
        
        # Update registry
        updated = 0
        for doc_id, count in reference_counts.items():
            if doc_id in self.registry['documents']:
                self.registry['documents'][doc_id]['times_referenced'] = count
                updated += 1
        
        self._save()
        print(f"✓ Updated {updated} documents with reference counts")
    
    def _save(self) -> None:
        """Save registry to file"""
        with open(self.registry_file, 'w') as f:
            json.dump(self.registry, f, indent=2)


def main():
    """Demo document registry"""
    print("="*60)
    print("DOCUMENT REGISTRY SYSTEM")
    print("="*60)
    
    # Initialize registry
    print("\nInitializing document registry...")
    registry = DocumentRegistry()
    
    # Import existing documents
    print("\n" + "="*60)
    print("IMPORTING DOCUMENTS")
    print("="*60)
    registry.import_from_processed_data()
    
    # Sync with audit logs
    print("\n" + "="*60)
    print("SYNCING WITH AUDIT LOGS")
    print("="*60)
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    audit_file = os.path.join(script_dir, '../data/audit/query_logs.jsonl')
    registry.sync_with_audit_logs(audit_file)
    
    # Generate usage report
    print("\n" + "="*60)
    print("USAGE REPORT")
    print("="*60)
    
    report = registry.get_usage_report()
    
    print(f"\nTotal Documents: {report['total_documents']}")
    print(f"Active: {report['active_documents']}")
    print(f"Archived: {report['archived_documents']}")
    
    print("\nDocuments by Type:")
    for doc_type, count in report['by_type'].items():
        print(f"  {doc_type}: {count}")
    
    print("\nDocuments by Classification:")
    for classification, count in report['by_classification'].items():
        print(f"  {classification}: {count}")
    
    print(f"\nTop 10 Most Referenced Documents:")
    for i, doc in enumerate(report['most_referenced'][:10], 1):
        if doc['times_referenced'] > 0:
            print(f"  {i}. {doc['document_id']}: {doc['times_referenced']} references")
    
    print(f"\nNever Referenced: {report['never_referenced_count']} documents")
    
    # Check for stale documents
    print("\n" + "="*60)
    print("STALE DOCUMENTS CHECK")
    print("="*60)
    
    stale = registry.get_stale_documents(days=365)
    
    if stale:
        print(f"\n⚠️  {len(stale)} documents not verified in 365+ days:")
        for doc in stale[:5]:
            print(f"  • {doc['document_id']}: {doc['days_since_verification']} days old")
    else:
        print("\n✓ All documents verified within last year")
    
    # Sample document info
    print("\n" + "="*60)
    print("SAMPLE DOCUMENT INFO")
    print("="*60)
    
    if report['most_referenced']:
        sample_id = report['most_referenced'][0]['document_id']
        doc_info = registry.get_document_info(sample_id)
        
        print(f"\nDocument: {doc_info['document_id']}")
        print(f"Type: {doc_info['document_type']}")
        print(f"Classification: {doc_info['classification']}")
        print(f"Version: {doc_info['version']}")
        print(f"Added: {doc_info['added_date'][:10]}")
        print(f"Last Verified: {doc_info['last_verified'][:10]}")
        print(f"Times Referenced: {doc_info['times_referenced']}")
        print(f"Status: {doc_info['status']}")
    
    print("\n" + "="*60)
    print("Document registry demo complete!")
    print("="*60)


if __name__ == '__main__':
    main()