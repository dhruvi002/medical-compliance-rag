# src/personalized_learning.py
import json
import os
from typing import List, Dict
from vector_store import VectorStore
from rag_system import RAGSystem
from skill_gap_analyzer import SkillGapAnalyzer

class PersonalizedLearningSystem:
    """Generate personalized learning content based on skill gaps"""
    
    def __init__(self, 
                 rag_system: RAGSystem,
                 analyzer: SkillGapAnalyzer):
        """
        Initialize personalized learning system
        
        Args:
            rag_system: Initialized RAG system
            analyzer: Skill gap analyzer
        """
        self.rag = rag_system
        self.analyzer = analyzer
        
        print("✓ Personalized Learning System initialized")
    
    def generate_learning_path(self, employee_analysis: Dict) -> Dict:
        """
        Generate personalized learning path for an employee
        
        Args:
            employee_analysis: Analysis dict from SkillGapAnalyzer
        
        Returns:
            Dict with learning modules and content
        """
        employee_id = employee_analysis['employee_id']
        gaps = employee_analysis['gaps']
        
        if not gaps:
            return {
                'employee_id': employee_id,
                'status': 'No gaps identified',
                'modules': []
            }
        
        # Generate learning modules for each gap
        modules = []
        
        for i, gap in enumerate(gaps[:3], 1):  # Focus on top 3 gaps
            category = gap['category']
            severity = gap['severity']
            current_score = gap['score']
            
            # Generate questions for this category
            questions = self._generate_category_questions(category, severity)
            
            # Get learning content from RAG system
            learning_content = self._fetch_learning_content(category)
            
            module = {
                'module_number': i,
                'category': category,
                'severity': severity,
                'current_proficiency': current_score,
                'target_proficiency': 0.8,
                'improvement_needed': round(0.8 - current_score, 2),
                'estimated_time_minutes': 30 if severity == 'critical' else 20,
                'questions': questions,
                'learning_content': learning_content
            }
            
            modules.append(module)
        
        return {
            'employee_id': employee_id,
            'role': employee_analysis['role'],
            'overall_score': employee_analysis['overall_score'],
            'status': 'Learning path generated',
            'total_modules': len(modules),
            'estimated_total_time_minutes': sum(m['estimated_time_minutes'] for m in modules),
            'modules': modules
        }
    
    def _generate_category_questions(self, category: str, severity: str) -> List[str]:
        """
        Generate practice questions for a category
        
        Args:
            category: Compliance category
            severity: 'critical' or 'moderate'
        
        Returns:
            List of question strings
        """
        # Load synthetic Q&As
        script_dir = os.path.dirname(os.path.abspath(__file__))
        qa_file = os.path.join(script_dir, '../data/processed/synthetic_qa_combined.json')
        
        with open(qa_file, 'r') as f:
            all_qas = json.load(f)
        
        # Filter by category
        category_qas = [qa for qa in all_qas if qa.get('category') == category]
        
        # For critical gaps, include more questions
        num_questions = 5 if severity == 'critical' else 3
        
        # Return questions (limit to available)
        questions = [qa['question'] for qa in category_qas[:num_questions]]
        
        return questions
    
    def _fetch_learning_content(self, category: str) -> List[Dict]:
        """
        Fetch relevant learning content from RAG system
        
        Args:
            category: Compliance category
        
        Returns:
            List of content chunks with sources
        """
        # Create a query to fetch educational content
        query = f"What are the key requirements and best practices for {category}?"
        
        # Use RAG system to get relevant content
        result = self.rag.query(query, verbose=False)
        
        # Extract relevant chunks
        content_chunks = []
        for i, source in enumerate(result['sources'][:3], 1):  # Top 3 sources
            content_chunks.append({
                'chunk_number': i,
                'source_file': source['file'],
                'preview': source['preview']
            })
        
        return content_chunks
    
    def generate_quiz(self, employee_analysis: Dict, category: str = None) -> Dict:
        """
        Generate a practice quiz for an employee
        
        Args:
            employee_analysis: Employee's analysis
            category: Specific category to quiz on (None = all gaps)
        
        Returns:
            Quiz dict with questions and answer key
        """
        employee_id = employee_analysis['employee_id']
        
        # Load all Q&As
        script_dir = os.path.dirname(os.path.abspath(__file__))
        qa_file = os.path.join(script_dir, '../data/processed/synthetic_qa_combined.json')
        
        with open(qa_file, 'r') as f:
            all_qas = json.load(f)
        
        # Filter questions
        if category:
            # Specific category
            quiz_qas = [qa for qa in all_qas if qa.get('category') == category][:5]
        else:
            # Mix from all gap categories
            quiz_qas = []
            for gap in employee_analysis['gaps'][:3]:
                gap_category = gap['category']
                category_qas = [qa for qa in all_qas if qa.get('category') == gap_category]
                quiz_qas.extend(category_qas[:2])  # 2 questions per gap category
        
        # Format quiz
        questions = []
        for i, qa in enumerate(quiz_qas, 1):
            questions.append({
                'question_number': i,
                'category': qa.get('category'),
                'difficulty': qa.get('difficulty'),
                'question': qa['question'],
                'answer': qa['answer']  # For answer key
            })
        
        return {
            'employee_id': employee_id,
            'quiz_category': category or 'Mixed (Gap Areas)',
            'total_questions': len(questions),
            'questions': questions
        }


def main():
    """Demo personalized learning system"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("="*60)
    print("PERSONALIZED LEARNING SYSTEM")
    print("="*60)
    
    # Initialize components
    print("\n[1/4] Loading RAG system...")
    persist_dir = os.path.join(script_dir, '../chroma_db')
    vector_store = VectorStore(persist_directory=persist_dir)
    rag = RAGSystem(vector_store, model_name="llama3.1:8b", n_results=3)
    
    print("\n[2/4] Loading skill gap analyzer...")
    employees_file = os.path.join(script_dir, '../data/processed/employee_profiles.json')
    analyzer = SkillGapAnalyzer(employees_file)
    
    print("\n[3/4] Analyzing employees...")
    analyses = analyzer.analyze_all_employees()
    
    print("\n[4/4] Initializing personalized learning system...")
    learning_system = PersonalizedLearningSystem(rag, analyzer)
    
    # Find an employee with gaps for demo
    sample_employee = next((a for a in analyses if len(a['gaps']) >= 2), analyses[0])
    
    print("\n" + "="*60)
    print("GENERATING PERSONALIZED LEARNING PATH")
    print("="*60)
    
    print(f"\nEmployee: {sample_employee['employee_id']}")
    print(f"Role: {sample_employee['role']}")
    print(f"Current Score: {sample_employee['overall_score']:.0%}")
    print(f"Gaps Identified: {len(sample_employee['gaps'])}")
    
    # Generate learning path
    print("\nGenerating learning path...")
    learning_path = learning_system.generate_learning_path(sample_employee)
    
    # Save learning path
    output_dir = os.path.join(script_dir, '../data/processed')
    learning_path_file = os.path.join(output_dir, 'sample_learning_path.json')
    
    with open(learning_path_file, 'w', encoding='utf-8') as f:
        json.dump(learning_path, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Learning path saved to: {learning_path_file}")
    
    # Display learning path
    print("\n" + "="*60)
    print("LEARNING PATH SUMMARY")
    print("="*60)
    
    print(f"\nTotal Modules: {learning_path['total_modules']}")
    print(f"Estimated Time: {learning_path['estimated_total_time_minutes']} minutes")
    
    for module in learning_path['modules']:
        print(f"\n{'─'*60}")
        print(f"MODULE {module['module_number']}: {module['category']}")
        print(f"{'─'*60}")
        print(f"Severity: {module['severity'].upper()}")
        print(f"Current: {module['current_proficiency']:.0%} → Target: {module['target_proficiency']:.0%}")
        print(f"Improvement Needed: {module['improvement_needed']:.0%}")
        print(f"Estimated Time: {module['estimated_time_minutes']} minutes")
        
        print(f"\nPractice Questions ({len(module['questions'])}):")
        for i, q in enumerate(module['questions'][:2], 1):  # Show first 2
            print(f"  {i}. {q[:80]}...")
        
        print(f"\nLearning Resources ({len(module['learning_content'])} sources):")
        for content in module['learning_content']:
            print(f"  • {content['source_file']}")
    
    # Generate a quiz
    print("\n" + "="*60)
    print("SAMPLE PRACTICE QUIZ")
    print("="*60)
    
    gap_category = sample_employee['gaps'][0]['category']
    print(f"\nGenerating quiz for: {gap_category}")
    
    quiz = learning_system.generate_quiz(sample_employee, category=gap_category)
    
    # Save quiz
    quiz_file = os.path.join(output_dir, 'sample_quiz.json')
    with open(quiz_file, 'w', encoding='utf-8') as f:
        json.dump(quiz, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Quiz saved to: {quiz_file}")
    
    print(f"\nQuiz: {quiz['quiz_category']}")
    print(f"Questions: {quiz['total_questions']}")
    
    for q in quiz['questions'][:3]:  # Show first 3
        print(f"\nQ{q['question_number']}. [{q['category']} - {q['difficulty']}]")
        print(f"{q['question']}")
    
    print("\n" + "="*60)
    print("Personalized learning system demo complete!")
    print("="*60)


if __name__ == '__main__':
    main()