# src/skill_gap_analyzer.py
import json
import os
from typing import List, Dict, Tuple
from collections import defaultdict
import statistics

class SkillGapAnalyzer:
    """Analyze employee performance and identify skill gaps"""
    
    def __init__(self, employees_file: str):
        """
        Initialize analyzer with employee data
        
        Args:
            employees_file: Path to employee_profiles.json
        """
        with open(employees_file, 'r', encoding='utf-8') as f:
            self.employees = json.load(f)
        
        print(f"✓ Loaded {len(self.employees)} employee profiles")
    
    def analyze_employee(self, employee: Dict) -> Dict:
        """
        Analyze a single employee's performance
        
        Returns:
            Dict with performance metrics and gap analysis
        """
        history = employee['training_history']
        
        if not history:
            return {
                'employee_id': employee['employee_id'],
                'overall_score': 0,
                'gaps': [],
                'strengths': [],
                'needs_training': True
            }
        
        # Overall performance
        total_questions = len(history)
        correct_answers = sum(1 for q in history if q['correct'])
        overall_score = correct_answers / total_questions if total_questions > 0 else 0
        
        # Performance by category
        category_performance = defaultdict(lambda: {'correct': 0, 'total': 0})
        
        for question in history:
            category = question['category']
            category_performance[category]['total'] += 1
            if question['correct']:
                category_performance[category]['correct'] += 1
        
        # Calculate scores by category
        category_scores = {}
        for category, stats in category_performance.items():
            category_scores[category] = stats['correct'] / stats['total']
        
        # Performance by difficulty
        difficulty_performance = defaultdict(lambda: {'correct': 0, 'total': 0})
        
        for question in history:
            difficulty = question['difficulty']
            difficulty_performance[difficulty]['total'] += 1
            if question['correct']:
                difficulty_performance[difficulty]['correct'] += 1
        
        difficulty_scores = {}
        for difficulty, stats in difficulty_performance.items():
            difficulty_scores[difficulty] = stats['correct'] / stats['total']
        
        # Identify gaps (categories with <60% accuracy)
        gaps = []
        for category, score in category_scores.items():
            if score < 0.6:
                gaps.append({
                    'category': category,
                    'score': round(score, 2),
                    'questions_attempted': category_performance[category]['total'],
                    'severity': 'critical' if score < 0.4 else 'moderate'
                })
        
        # Identify strengths (categories with >80% accuracy)
        strengths = []
        for category, score in category_scores.items():
            if score > 0.8:
                strengths.append({
                    'category': category,
                    'score': round(score, 2),
                    'questions_attempted': category_performance[category]['total']
                })
        
        # Sort gaps by severity (lowest score first)
        gaps.sort(key=lambda x: x['score'])
        strengths.sort(key=lambda x: x['score'], reverse=True)
        
        # Training recommendation
        needs_training = overall_score < 0.7 or len(gaps) > 2
        
        # Confidence analysis
        avg_confidence = statistics.mean(q['confidence'] for q in history)
        
        # Incorrect but confident (overconfident errors)
        overconfident_errors = [
            q for q in history 
            if not q['correct'] and q['confidence'] > 70
        ]
        
        return {
            'employee_id': employee['employee_id'],
            'role': employee['role'],
            'experience_level': employee['experience_level'],
            'years_experience': employee['years_experience'],
            'overall_score': round(overall_score, 2),
            'total_questions': total_questions,
            'correct_answers': correct_answers,
            'category_scores': {k: round(v, 2) for k, v in category_scores.items()},
            'difficulty_scores': {k: round(v, 2) for k, v in difficulty_scores.items()},
            'gaps': gaps,
            'strengths': strengths,
            'needs_training': needs_training,
            'avg_confidence': round(avg_confidence, 1),
            'overconfident_errors': len(overconfident_errors),
            'training_priority': 'high' if overall_score < 0.6 else 'medium' if overall_score < 0.75 else 'low'
        }
    
    def analyze_all_employees(self) -> List[Dict]:
        """Analyze all employees"""
        analyses = []
        
        for i, employee in enumerate(self.employees, 1):
            analysis = self.analyze_employee(employee)
            analyses.append(analysis)
            
            if i % 20 == 0:
                print(f"Analyzed {i}/{len(self.employees)} employees...")
        
        return analyses
    
    def aggregate_insights(self, analyses: List[Dict]) -> Dict:
        """
        Generate organization-wide insights
        
        Args:
            analyses: List of individual employee analyses
        
        Returns:
            Aggregate statistics and insights
        """
        # Overall statistics
        total_employees = len(analyses)
        avg_score = statistics.mean(a['overall_score'] for a in analyses)
        
        # Training priority breakdown
        priority_counts = defaultdict(int)
        for analysis in analyses:
            priority_counts[analysis['training_priority']] += 1
        
        # Most common gaps
        all_gaps = []
        for analysis in analyses:
            all_gaps.extend([g['category'] for g in analysis['gaps']])
        
        gap_frequency = defaultdict(int)
        for gap in all_gaps:
            gap_frequency[gap] += 1
        
        # Sort by frequency
        top_gaps = sorted(gap_frequency.items(), key=lambda x: x[1], reverse=True)
        
        # Performance by role
        role_performance = defaultdict(list)
        for analysis in analyses:
            role_performance[analysis['role']].append(analysis['overall_score'])
        
        role_avg_scores = {
            role: round(statistics.mean(scores), 2)
            for role, scores in role_performance.items()
        }
        
        # Performance by experience level
        exp_performance = defaultdict(list)
        for analysis in analyses:
            exp_performance[analysis['experience_level']].append(analysis['overall_score'])
        
        exp_avg_scores = {
            level: round(statistics.mean(scores), 2)
            for level, scores in exp_performance.items()
        }
        
        # Employees needing urgent training
        urgent_training = [
            a for a in analyses 
            if a['training_priority'] == 'high'
        ]
        
        return {
            'total_employees': total_employees,
            'avg_overall_score': round(avg_score, 2),
            'training_priority_breakdown': dict(priority_counts),
            'employees_needing_training': sum(1 for a in analyses if a['needs_training']),
            'top_organizational_gaps': [
                {'category': cat, 'employees_affected': count, 'percentage': round(count/total_employees*100, 1)}
                for cat, count in top_gaps[:5]
            ],
            'role_performance': role_avg_scores,
            'experience_level_performance': exp_avg_scores,
            'urgent_training_needed': len(urgent_training),
            'avg_confidence': round(statistics.mean(a['avg_confidence'] for a in analyses), 1)
        }
    
    def generate_recommendations(self, employee_analysis: Dict) -> List[str]:
        """
        Generate personalized training recommendations
        
        Args:
            employee_analysis: Analysis dict for single employee
        
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        # Priority based on gaps
        if employee_analysis['gaps']:
            critical_gaps = [g for g in employee_analysis['gaps'] if g['severity'] == 'critical']
            moderate_gaps = [g for g in employee_analysis['gaps'] if g['severity'] == 'moderate']
            
            if critical_gaps:
                recommendations.append(
                    f"🔴 URGENT: Complete training modules for {', '.join(g['category'] for g in critical_gaps[:2])} "
                    f"(current proficiency: {critical_gaps[0]['score']:.0%})"
                )
            
            if moderate_gaps:
                recommendations.append(
                    f"⚠️ Review materials on {', '.join(g['category'] for g in moderate_gaps[:2])} "
                    f"to improve from {moderate_gaps[0]['score']:.0%} proficiency"
                )
        
        # Difficulty-based recommendations
        if employee_analysis['difficulty_scores']:
            if 'hard' in employee_analysis['difficulty_scores']:
                hard_score = employee_analysis['difficulty_scores']['hard']
                if hard_score < 0.5:
                    recommendations.append(
                        f"📚 Practice complex scenarios and case studies (hard questions: {hard_score:.0%} accuracy)"
                    )
        
        # Overconfidence warning
        if employee_analysis['overconfident_errors'] > 3:
            recommendations.append(
                f"⚡ Review {employee_analysis['overconfident_errors']} questions where you were confident but incorrect"
            )
        
        # Experience-based
        if employee_analysis['experience_level'] == 'entry':
            recommendations.append(
                "📖 Consider shadowing senior staff during compliance procedures"
            )
        
        # General recommendation
        if employee_analysis['overall_score'] < 0.7:
            recommendations.append(
                f"🎯 Schedule 1-on-1 compliance coaching session (current score: {employee_analysis['overall_score']:.0%})"
            )
        elif employee_analysis['overall_score'] > 0.9:
            recommendations.append(
                f"⭐ Excellent performance! Consider becoming a peer trainer for {employee_analysis['strengths'][0]['category']}"
            )
        
        # If no specific gaps but could improve
        if not recommendations and employee_analysis['overall_score'] < 0.85:
            recommendations.append(
                "✅ Maintain current training schedule and review quarterly updates"
            )
        
        return recommendations


def main():
    """Analyze all employees and generate report"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    employees_file = os.path.join(script_dir, '../data/processed/employee_profiles.json')
    
    print("="*60)
    print("SKILL GAP ANALYSIS")
    print("="*60)
    
    # Initialize analyzer
    print("\nInitializing analyzer...")
    analyzer = SkillGapAnalyzer(employees_file)
    
    # Analyze all employees
    print("\nAnalyzing employee performance...")
    analyses = analyzer.analyze_all_employees()
    print(f"✓ Analyzed {len(analyses)} employees")
    
    # Generate aggregate insights
    print("\nGenerating organizational insights...")
    insights = analyzer.aggregate_insights(analyses)
    
    # Save individual analyses
    output_dir = os.path.join(script_dir, '../data/processed')
    analyses_file = os.path.join(output_dir, 'employee_analyses.json')
    
    with open(analyses_file, 'w', encoding='utf-8') as f:
        json.dump(analyses, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Saved individual analyses to: {analyses_file}")
    
    # Save organizational insights
    insights_file = os.path.join(output_dir, 'organizational_insights.json')
    
    with open(insights_file, 'w', encoding='utf-8') as f:
        json.dump(insights, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Saved organizational insights to: {insights_file}")
    
    # Print summary report
    print("\n" + "="*60)
    print("ORGANIZATIONAL INSIGHTS")
    print("="*60)
    
    print(f"\nTotal Employees: {insights['total_employees']}")
    print(f"Average Compliance Score: {insights['avg_overall_score']:.0%}")
    print(f"Employees Needing Training: {insights['employees_needing_training']}")
    print(f"Urgent Training Required: {insights['urgent_training_needed']}")
    
    print("\nTraining Priority Breakdown:")
    for priority, count in insights['training_priority_breakdown'].items():
        percentage = count / insights['total_employees'] * 100
        print(f"  {priority.upper()}: {count} employees ({percentage:.1f}%)")
    
    print("\nTop 5 Organizational Skill Gaps:")
    for i, gap in enumerate(insights['top_organizational_gaps'], 1):
        print(f"  {i}. {gap['category']}: {gap['employees_affected']} employees ({gap['percentage']:.1f}%)")
    
    print("\nPerformance by Role:")
    for role, score in sorted(insights['role_performance'].items(), key=lambda x: x[1]):
        print(f"  {role}: {score:.0%}")
    
    print("\nPerformance by Experience Level:")
    for level in ['entry', 'junior', 'mid', 'senior']:
        if level in insights['experience_level_performance']:
            score = insights['experience_level_performance'][level]
            print(f"  {level.capitalize()}: {score:.0%}")
    
    # Sample employee report
    print("\n" + "="*60)
    print("SAMPLE EMPLOYEE REPORT")
    print("="*60)
    
    # Find an employee with gaps for interesting example
    sample = next((a for a in analyses if a['gaps']), analyses[0])
    
    print(f"\nEmployee ID: {sample['employee_id']}")
    print(f"Role: {sample['role']}")
    print(f"Experience: {sample['years_experience']} years ({sample['experience_level']})")
    print(f"Overall Score: {sample['overall_score']:.0%} ({sample['correct_answers']}/{sample['total_questions']} correct)")
    print(f"Training Priority: {sample['training_priority'].upper()}")
    
    if sample['strengths']:
        print("\n✅ Strengths:")
        for strength in sample['strengths'][:3]:
            print(f"   • {strength['category']}: {strength['score']:.0%}")
    
    if sample['gaps']:
        print("\n❌ Skill Gaps:")
        for gap in sample['gaps'][:3]:
            print(f"   • {gap['category']}: {gap['score']:.0%} ({gap['severity']})")
    
    print("\n📋 Recommendations:")
    recommendations = analyzer.generate_recommendations(sample)
    for rec in recommendations:
        print(f"   {rec}")
    
    print("\n" + "="*60)
    print("Analysis complete!")
    print("="*60)


if __name__ == '__main__':
    main()