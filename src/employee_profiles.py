# src/employee_profiles.py
import json
import random
import os
from datetime import datetime, timedelta
from typing import List, Dict

class EmployeeProfileGenerator:
    """Generate synthetic employee profiles for training analysis"""
    
    def __init__(self):
        self.roles = [
            "Registered Nurse",
            "Medical Assistant", 
            "Phlebotomist",
            "Lab Technician",
            "Emergency Room Nurse",
            "Surgery Technician",
            "Clinic Administrator",
            "Home Health Aide"
        ]
        
        self.experience_levels = {
            "entry": (0, 2),      # 0-2 years
            "junior": (2, 5),     # 2-5 years
            "mid": (5, 10),       # 5-10 years
            "senior": (10, 20)    # 10-20 years
        }
        
        self.compliance_categories = [
            "HIPAA",
            "OSHA",
            "Infection Control",
            "Medical Waste",
            "Documentation & Training",
            "PPE Requirements",
            "Bloodborne Pathogens",
            "Hand Hygiene",
            "Emergency Procedures"
        ]
    
    def generate_employee(self, employee_id: int) -> Dict:
        """Generate a single employee profile"""
        
        # Random attributes
        role = random.choice(self.roles)
        experience_level = random.choice(list(self.experience_levels.keys()))
        years_exp = random.uniform(*self.experience_levels[experience_level])
        
        # Training completion (senior employees have more training)
        if experience_level == "entry":
            training_completion = random.uniform(0.3, 0.6)
        elif experience_level == "junior":
            training_completion = random.uniform(0.5, 0.75)
        elif experience_level == "mid":
            training_completion = random.uniform(0.7, 0.9)
        else:  # senior
            training_completion = random.uniform(0.85, 1.0)
        
        # Assign strengths and weaknesses
        num_strengths = random.randint(2, 4)
        num_weaknesses = random.randint(1, 3)
        
        all_categories = self.compliance_categories.copy()
        random.shuffle(all_categories)
        
        strengths = all_categories[:num_strengths]
        weaknesses = all_categories[num_strengths:num_strengths + num_weaknesses]
        
        # Last training date (more recent for senior employees)
        if experience_level in ["senior", "mid"]:
            days_ago = random.randint(30, 180)
        else:
            days_ago = random.randint(180, 365)
        
        last_training = datetime.now() - timedelta(days=days_ago)
        
        return {
            "employee_id": f"EMP{employee_id:04d}",
            "role": role,
            "experience_level": experience_level,
            "years_experience": round(years_exp, 1),
            "training_completion_rate": round(training_completion, 2),
            "last_training_date": last_training.strftime("%Y-%m-%d"),
            "strong_areas": strengths,
            "weak_areas": weaknesses,
            "compliance_categories": self.compliance_categories
        }
    
    def generate_employees(self, n: int = 100) -> List[Dict]:
        """Generate multiple employee profiles"""
        employees = []
        
        for i in range(1, n + 1):
            employee = self.generate_employee(i)
            employees.append(employee)
            
            if i % 20 == 0:
                print(f"Generated {i}/{n} employee profiles...")
        
        return employees
    
    def generate_training_history(self, employee: Dict, n_questions: int = 20) -> List[Dict]:
        """
        Generate simulated training quiz history for an employee
        
        Based on their strengths/weaknesses, simulate performance
        """
        history = []
        
        # Load Q&A pairs to sample from
        script_dir = os.path.dirname(os.path.abspath(__file__))
        qa_file = os.path.join(script_dir, '../data/processed/synthetic_qa_combined.json')
        
        with open(qa_file, 'r') as f:
            all_questions = json.load(f)
        
        # Sample questions
        sampled_questions = random.sample(all_questions, min(n_questions, len(all_questions)))
        
        for q in sampled_questions:
            category = q.get('category', 'Unknown')
            difficulty = q.get('difficulty', 'medium')
            
            # Determine if employee got it right based on their profile
            if category in employee['strong_areas']:
                # High probability of correct answer
                if difficulty == 'easy':
                    correct_prob = 0.95
                elif difficulty == 'medium':
                    correct_prob = 0.85
                else:  # hard
                    correct_prob = 0.70
            elif category in employee['weak_areas']:
                # Low probability of correct answer
                if difficulty == 'easy':
                    correct_prob = 0.60
                elif difficulty == 'medium':
                    correct_prob = 0.40
                else:  # hard
                    correct_prob = 0.20
            else:
                # Average probability
                if difficulty == 'easy':
                    correct_prob = 0.80
                elif difficulty == 'medium':
                    correct_prob = 0.60
                else:  # hard
                    correct_prob = 0.40
            
            # Apply experience modifier
            if employee['experience_level'] == 'senior':
                correct_prob = min(1.0, correct_prob + 0.1)
            elif employee['experience_level'] == 'entry':
                correct_prob = max(0.0, correct_prob - 0.1)
            
            is_correct = random.random() < correct_prob
            
            # Simulate confidence score (0-100)
            if is_correct:
                confidence = random.randint(70, 100)
            else:
                confidence = random.randint(30, 70)
            
            history.append({
                "question": q['question'],
                "category": category,
                "difficulty": difficulty,
                "correct": is_correct,
                "confidence": confidence,
                "timestamp": (datetime.now() - timedelta(days=random.randint(1, 90))).isoformat()
            })
        
        return history


def main():
    """Generate employee profiles and save"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, '../data/processed')
    
    print("="*60)
    print("EMPLOYEE PROFILE GENERATION")
    print("="*60)
    
    # Generate employees
    generator = EmployeeProfileGenerator()
    
    print("\nGenerating 100 employee profiles...")
    employees = generator.generate_employees(100)
    
    print(f"\n✓ Generated {len(employees)} employees")
    
    # Generate training history for each
    print("\nGenerating training history for each employee...")
    for i, emp in enumerate(employees, 1):
        emp['training_history'] = generator.generate_training_history(emp, n_questions=20)
        
        if i % 20 == 0:
            print(f"  Generated history for {i}/{len(employees)} employees...")
    
    # Save employees
    employees_file = os.path.join(output_dir, 'employee_profiles.json')
    with open(employees_file, 'w', encoding='utf-8') as f:
        json.dump(employees, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Saved to: {employees_file}")
    
    # Statistics
    print("\n" + "="*60)
    print("EMPLOYEE STATISTICS")
    print("="*60)
    
    # By role
    roles = {}
    for emp in employees:
        role = emp['role']
        roles[role] = roles.get(role, 0) + 1
    
    print("\nEmployees by Role:")
    for role, count in sorted(roles.items()):
        print(f"  {role}: {count}")
    
    # By experience
    experience = {}
    for emp in employees:
        level = emp['experience_level']
        experience[level] = experience.get(level, 0) + 1
    
    print("\nEmployees by Experience Level:")
    for level in ['entry', 'junior', 'mid', 'senior']:
        count = experience.get(level, 0)
        print(f"  {level}: {count}")
    
    # Average training completion
    avg_completion = sum(e['training_completion_rate'] for e in employees) / len(employees)
    print(f"\nAverage Training Completion: {avg_completion:.1%}")
    
    # Sample employee
    print("\n" + "="*60)
    print("SAMPLE EMPLOYEE PROFILE")
    print("="*60)
    sample = employees[0]
    print(f"ID: {sample['employee_id']}")
    print(f"Role: {sample['role']}")
    print(f"Experience: {sample['years_experience']} years ({sample['experience_level']})")
    print(f"Training Completion: {sample['training_completion_rate']:.0%}")
    print(f"Last Training: {sample['last_training_date']}")
    print(f"Strong Areas: {', '.join(sample['strong_areas'])}")
    print(f"Weak Areas: {', '.join(sample['weak_areas'])}")
    print(f"Training History: {len(sample['training_history'])} questions answered")
    
    # Performance stats for sample
    correct = sum(1 for q in sample['training_history'] if q['correct'])
    print(f"Overall Score: {correct}/{len(sample['training_history'])} ({correct/len(sample['training_history']):.0%})")


if __name__ == '__main__':
    main()