# src/access_control.py
import json
import os
from typing import Dict, List, Optional
from datetime import datetime
import hashlib

class AccessControlSystem:
    """Manage user roles and permissions"""
    
    def __init__(self, users_file: str = None):
        """
        Initialize access control system
        
        Args:
            users_file: Path to users database file
        """
        if users_file is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            data_dir = os.path.join(script_dir, '../data/governance')
            os.makedirs(data_dir, exist_ok=True)
            users_file = os.path.join(data_dir, 'users.json')
        
        self.users_file = users_file
        
        # Load existing users or create new
        if os.path.exists(self.users_file):
            with open(self.users_file, 'r') as f:
                self.users = json.load(f)
        else:
            self.users = {'users': {}}
        
        # Define role permissions
        self.role_permissions = {
            'employee': {
                'can_query_rag': True,
                'can_view_own_analytics': True,
                'can_view_org_analytics': False,
                'can_modify_knowledge_base': False,
                'can_manage_users': False,
                'can_view_audit_logs': False,
                'access_level': 'standard'
            },
            'trainer': {
                'can_query_rag': True,
                'can_view_own_analytics': True,
                'can_view_org_analytics': True,
                'can_modify_knowledge_base': False,
                'can_manage_users': False,
                'can_view_audit_logs': True,
                'access_level': 'elevated'
            },
            'admin': {
                'can_query_rag': True,
                'can_view_own_analytics': True,
                'can_view_org_analytics': True,
                'can_modify_knowledge_base': True,
                'can_manage_users': True,
                'can_view_audit_logs': True,
                'access_level': 'full'
            }
        }
        
        print(f"✓ Access control system initialized: {self.users_file}")
        print(f"  Users registered: {len(self.users['users'])}")
    
    def create_user(self,
                   user_id: str,
                   name: str,
                   email: str,
                   role: str = 'employee',
                   department: Optional[str] = None) -> None:
        """
        Create a new user
        
        Args:
            user_id: Unique user identifier (e.g., EMP0001)
            name: Full name
            email: Email address
            role: User role (employee, trainer, admin)
            department: Department/team
        """
        if user_id in self.users['users']:
            print(f"⚠️  User {user_id} already exists")
            return
        
        if role not in self.role_permissions:
            print(f"❌ Invalid role: {role}")
            return
        
        self.users['users'][user_id] = {
            'user_id': user_id,
            'name': name,
            'email': email,
            'role': role,
            'department': department,
            'permissions': self.role_permissions[role],
            'created_date': datetime.now().isoformat(),
            'last_active': None,
            'status': 'active',
            'query_count': 0
        }
        
        self._save()
        print(f"✓ Created user: {user_id} ({role})")
    
    def update_last_active(self, user_id: str) -> None:
        """Update user's last active timestamp"""
        if user_id in self.users['users']:
            self.users['users'][user_id]['last_active'] = datetime.now().isoformat()
            self.users['users'][user_id]['query_count'] += 1
            self._save()
    
    def change_role(self, user_id: str, new_role: str) -> bool:
        """
        Change user's role
        
        Args:
            user_id: User to modify
            new_role: New role (employee, trainer, admin)
        
        Returns:
            Success boolean
        """
        if user_id not in self.users['users']:
            print(f"❌ User {user_id} not found")
            return False
        
        if new_role not in self.role_permissions:
            print(f"❌ Invalid role: {new_role}")
            return False
        
        old_role = self.users['users'][user_id]['role']
        self.users['users'][user_id]['role'] = new_role
        self.users['users'][user_id]['permissions'] = self.role_permissions[new_role]
        self._save()
        
        print(f"✓ Changed {user_id} role: {old_role} → {new_role}")
        return True
    
    def deactivate_user(self, user_id: str) -> None:
        """Deactivate a user account"""
        if user_id in self.users['users']:
            self.users['users'][user_id]['status'] = 'inactive'
            self.users['users'][user_id]['deactivated_date'] = datetime.now().isoformat()
            self._save()
            print(f"✓ Deactivated user: {user_id}")
    
    def check_permission(self, user_id: str, permission: str) -> bool:
        """
        Check if user has a specific permission
        
        Args:
            user_id: User to check
            permission: Permission name (e.g., 'can_query_rag')
        
        Returns:
            True if user has permission
        """
        if user_id not in self.users['users']:
            return False
        
        user = self.users['users'][user_id]
        
        # Check if active
        if user['status'] != 'active':
            return False
        
        # Check permission
        return user['permissions'].get(permission, False)
    
    def get_user_info(self, user_id: str) -> Optional[Dict]:
        """Get user information"""
        return self.users['users'].get(user_id)
    
    def get_users_by_role(self, role: str) -> List[Dict]:
        """Get all users with a specific role"""
        return [
            user for user in self.users['users'].values()
            if user['role'] == role and user['status'] == 'active'
        ]
    
    def get_all_users(self, include_inactive: bool = False) -> List[Dict]:
        """Get all users"""
        if include_inactive:
            return list(self.users['users'].values())
        else:
            return [
                user for user in self.users['users'].values()
                if user['status'] == 'active'
            ]
    
    def import_from_employee_profiles(self) -> None:
        """Import users from employee profiles"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        profiles_file = os.path.join(script_dir, '../data/processed/employee_profiles.json')
        
        if not os.path.exists(profiles_file):
            print("⚠️  Employee profiles not found")
            return
        
        with open(profiles_file, 'r') as f:
            employees = json.load(f)
        
        print(f"\nImporting {len(employees)} employees as users...")
        
        imported = 0
        for emp in employees:
            emp_id = emp['employee_id']
            
            # Skip if already exists
            if emp_id in self.users['users']:
                continue
            
            # Determine role based on experience
            if emp['experience_level'] == 'senior':
                role = 'trainer'
            else:
                role = 'employee'
            
            # Create user
            email = f"{emp_id.lower()}@healthcare.example.com"
            self.create_user(
                user_id=emp_id,
                name=f"{emp['role']} {emp_id}",
                email=email,
                role=role,
                department=emp['role']
            )
            imported += 1
        
        print(f"✓ Imported {imported} new users")
    
    def sync_with_audit_logs(self, audit_log_file: str) -> None:
        """
        Update user activity from audit logs
        
        Args:
            audit_log_file: Path to query_logs.jsonl
        """
        if not os.path.exists(audit_log_file):
            print(f"⚠️  Audit log not found: {audit_log_file}")
            return
        
        print("\nSyncing user activity with audit logs...")
        
        # Count queries per user
        from collections import defaultdict
        user_activity = defaultdict(lambda: {'count': 0, 'last_active': None})
        
        with open(audit_log_file, 'r') as f:
            for line in f:
                if line.strip():
                    log = json.loads(line)
                    user_id = log.get('user_id', 'anonymous')
                    timestamp = log.get('timestamp')
                    
                    user_activity[user_id]['count'] += 1
                    if timestamp:
                        user_activity[user_id]['last_active'] = timestamp
        
        # Update users
        updated = 0
        for user_id, activity in user_activity.items():
            if user_id in self.users['users']:
                self.users['users'][user_id]['query_count'] = activity['count']
                if activity['last_active']:
                    self.users['users'][user_id]['last_active'] = activity['last_active']
                updated += 1
        
        self._save()
        print(f"✓ Updated activity for {updated} users")
    
    def get_usage_report(self) -> Dict:
        """Generate user usage report"""
        total_users = len(self.users['users'])
        active_users = sum(1 for u in self.users['users'].values() if u['status'] == 'active')
        
        # Users by role
        by_role = {}
        for role in self.role_permissions.keys():
            by_role[role] = len(self.get_users_by_role(role))
        
        # Most active users
        most_active = sorted(
            self.users['users'].values(),
            key=lambda x: x.get('query_count', 0),
            reverse=True
        )[:10]
        
        # Inactive users (never queried)
        inactive = [
            u for u in self.users['users'].values()
            if u.get('query_count', 0) == 0 and u['status'] == 'active'
        ]
        
        return {
            'total_users': total_users,
            'active_users': active_users,
            'by_role': by_role,
            'most_active_users': [
                {
                    'user_id': u['user_id'],
                    'name': u['name'],
                    'role': u['role'],
                    'query_count': u.get('query_count', 0)
                }
                for u in most_active if u.get('query_count', 0) > 0
            ],
            'never_queried': len(inactive)
        }
    
    def _save(self) -> None:
        """Save users to file"""
        with open(self.users_file, 'w') as f:
            json.dump(self.users, f, indent=2)


def main():
    """Demo access control system"""
    print("="*60)
    print("ACCESS CONTROL SYSTEM")
    print("="*60)
    
    # Initialize access control
    print("\nInitializing access control...")
    ac = AccessControlSystem()
    
    # Import employees
    print("\n" + "="*60)
    print("IMPORTING EMPLOYEES AS USERS")
    print("="*60)
    ac.import_from_employee_profiles()
    
    # Add some admin users manually
    print("\nCreating admin users...")
    ac.create_user(
        user_id='ADMIN001',
        name='System Administrator',
        email='admin@healthcare.example.com',
        role='admin',
        department='IT'
    )
    
    # Sync with audit logs
    print("\n" + "="*60)
    print("SYNCING WITH AUDIT LOGS")
    print("="*60)
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    audit_file = os.path.join(script_dir, '../data/audit/query_logs.jsonl')
    ac.sync_with_audit_logs(audit_file)
    
    # Usage report
    print("\n" + "="*60)
    print("USER USAGE REPORT")
    print("="*60)
    
    report = ac.get_usage_report()
    
    print(f"\nTotal Users: {report['total_users']}")
    print(f"Active Users: {report['active_users']}")
    
    print("\nUsers by Role:")
    for role, count in report['by_role'].items():
        print(f"  {role}: {count}")
    
    if report['most_active_users']:
        print(f"\nTop 10 Most Active Users:")
        for i, user in enumerate(report['most_active_users'][:10], 1):
            print(f"  {i}. {user['user_id']} ({user['role']}): {user['query_count']} queries")
    
    print(f"\nNever Queried: {report['never_queried']} users")
    
    # Permission checks
    print("\n" + "="*60)
    print("PERMISSION CHECKS")
    print("="*60)
    
    test_user = 'EMP0001'
    print(f"\nChecking permissions for {test_user}:")
    
    user_info = ac.get_user_info(test_user)
    if user_info:
        print(f"Name: {user_info['name']}")
        print(f"Role: {user_info['role']}")
        print(f"Status: {user_info['status']}")
        
        print("\nPermissions:")
        for perm, value in user_info['permissions'].items():
            if perm != 'access_level':
                status = "✓" if value else "✗"
                print(f"  {status} {perm}")
    
    # Test permission check
    print("\n" + "="*60)
    print("TESTING PERMISSION CHECKS")
    print("="*60)
    
    can_query = ac.check_permission(test_user, 'can_query_rag')
    can_manage = ac.check_permission(test_user, 'can_manage_users')
    
    print(f"\n{test_user} can query RAG: {can_query}")
    print(f"{test_user} can manage users: {can_manage}")
    
    # Test admin
    admin_user = 'ADMIN001'
    can_admin_manage = ac.check_permission(admin_user, 'can_manage_users')
    print(f"\n{admin_user} can manage users: {can_admin_manage}")
    
    print("\n" + "="*60)
    print("Access control demo complete!")
    print("="*60)


if __name__ == '__main__':
    main()