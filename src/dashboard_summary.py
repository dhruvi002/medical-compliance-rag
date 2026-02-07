# src/dashboard_summary.py
import json
import os
from datetime import datetime

def load_json(filepath):
    """Load JSON file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def generate_dashboard():
    """Generate comprehensive dashboard summary"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, '../data/processed')
    
    print("="*70)
    print(" "*20 + "COMPLIANCE TRAINING DASHBOARD")
    print("="*70)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    # Load data
    print("\nLoading data...")
    
    try:
        org_insights = load_json(os.path.join(data_dir, 'organizational_insights.json'))
        employee_analyses = load_json(os.path.join(data_dir, 'employee_analyses.json'))
        
        print("✓ Data loaded successfully\n")
        
        # Section 1: Organization Overview
        print("┌" + "─"*68 + "┐")
        print("│" + " "*20 + "ORGANIZATION OVERVIEW" + " "*27 + "│")
        print("├" + "─"*68 + "┤")
        print(f"│ Total Employees:                    {org_insights['total_employees']:>3}                      │")
        print(f"│ Average Compliance Score:            {org_insights['avg_overall_score']:.0%}                      │")
        print(f"│ Employees Needing Training:          {org_insights['employees_needing_training']:>3}                      │")
        print(f"│ Urgent Training Required:            {org_insights['urgent_training_needed']:>3}                      │")
        print("└" + "─"*68 + "┘")
        
        # Section 2: Training Priority Breakdown
        print("\n┌" + "─"*68 + "┐")
        print("│" + " "*18 + "TRAINING PRIORITY BREAKDOWN" + " "*23 + "│")
        print("├" + "─"*68 + "┤")
        
        for priority in ['high', 'medium', 'low']:
            count = org_insights['training_priority_breakdown'].get(priority, 0)
            percentage = (count / org_insights['total_employees']) * 100
            bar_length = int(percentage / 2)  # Scale to 50 chars max
            bar = "█" * bar_length + "░" * (50 - bar_length)
            print(f"│ {priority.upper():8s} │ {bar} {count:>3} ({percentage:>5.1f}%) │")
        
        print("└" + "─"*68 + "┘")
        
        # Section 3: Top Organizational Gaps
        print("\n┌" + "─"*68 + "┐")
        print("│" + " "*20 + "TOP 5 SKILL GAPS" + " "*32 + "│")
        print("├" + "─"*68 + "┤")
        
        for i, gap in enumerate(org_insights['top_organizational_gaps'][:5], 1):
            category = gap['category'][:35]  # Truncate long names
            count = gap['employees_affected']
            pct = gap['percentage']
            print(f"│ {i}. {category:35s} {count:>3} employees ({pct:>5.1f}%) │")
        
        print("└" + "─"*68 + "┘")
        
        # Section 4: Performance by Experience Level
        print("\n┌" + "─"*68 + "┐")
        print("│" + " "*17 + "PERFORMANCE BY EXPERIENCE" + " "*26 + "│")
        print("├" + "─"*68 + "┤")
        
        for level in ['entry', 'junior', 'mid', 'senior']:
            if level in org_insights['experience_level_performance']:
                score = org_insights['experience_level_performance'][level]
                bar_length = int(score * 50)
                bar = "█" * bar_length + "░" * (50 - bar_length)
                print(f"│ {level.capitalize():8s} │ {bar} {score:.0%}      │")
        
        print("└" + "─"*68 + "┘")
        
        # Section 5: Performance by Role (Top 5)
        print("\n┌" + "─"*68 + "┐")
        print("│" + " "*21 + "TOP 5 ROLES BY SCORE" + " "*27 + "│")
        print("├" + "─"*68 + "┤")
        
        sorted_roles = sorted(
            org_insights['role_performance'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        for i, (role, score) in enumerate(sorted_roles, 1):
            role_display = role[:35]
            bar_length = int(score * 40)
            bar = "█" * bar_length
            print(f"│ {i}. {role_display:35s} {bar:40s} {score:.0%} │")
        
        print("└" + "─"*68 + "┘")
        
        # Section 6: High Priority Employees
        high_priority = [e for e in employee_analyses if e['training_priority'] == 'high']
        
        print("\n┌" + "─"*68 + "┐")
        print("│" + " "*16 + "HIGH PRIORITY EMPLOYEES (Sample)" + " "*20 + "│")
        print("├" + "─"*68 + "┤")
        print("│ ID       Role                    Score  Gaps  Recommendations  │")
        print("├" + "─"*68 + "┤")
        
        for emp in high_priority[:5]:
            emp_id = emp['employee_id']
            role = emp['role'][:20]
            score = emp['overall_score']
            gaps = len(emp['gaps'])
            print(f"│ {emp_id:8s} {role:20s}    {score:>3.0%}   {gaps:>2}      Urgent        │")
        
        print("└" + "─"*68 + "┘")
        
        # Section 7: System Statistics
        print("\n┌" + "─"*68 + "┐")
        print("│" + " "*22 + "SYSTEM STATISTICS" + " "*29 + "│")
        print("├" + "─"*68 + "┤")
        
        # Count files
        total_docs = 0
        chunks_file = os.path.join(data_dir, 'chunks.json')
        if os.path.exists(chunks_file):
            with open(chunks_file, 'r') as f:
                chunks = json.load(f)
                total_docs = len(chunks)
        
        print(f"│ Knowledge Base Chunks:              {total_docs:>5}                      │")
        print(f"│ Employee Profiles:                  {org_insights['total_employees']:>5}                      │")
        print(f"│ Unique Compliance Categories:        {len(org_insights['top_organizational_gaps']):>5}                      │")
        print("└" + "─"*68 + "┘")
        
        # Recommendations
        print("\n" + "="*70)
        print("RECOMMENDED ACTIONS")
        print("="*70)
        
        print("\n1. 🔴 URGENT: Schedule training for", org_insights['urgent_training_needed'], "high-priority employees")
        print(f"2. 📚 Focus organizational training on: {org_insights['top_organizational_gaps'][0]['category']}")
        print(f"3. ⚡ Target entry-level employees (lowest average score: {org_insights['experience_level_performance']['entry']:.0%})")
        print(f"4. ✅ Recognize {sorted_roles[0][0]} for highest compliance ({sorted_roles[0][1]:.0%})")
        
        print("\n" + "="*70)
        
    except FileNotFoundError as e:
        print(f"\n❌ Error: Required data file not found")
        print(f"   {e}")
        print("\n   Please run the following scripts first:")
        print("   1. python src/employee_profiles.py")
        print("   2. python src/skill_gap_analyzer.py")

def main():
    generate_dashboard()

if __name__ == '__main__':
    main()