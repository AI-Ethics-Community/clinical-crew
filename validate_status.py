#!/usr/bin/env python3
"""
Validation script to check status consistency between backend and frontend.
"""
import re
from pathlib import Path

def check_file_for_spanish_status(file_path: Path, patterns: list) -> list:
    """Check a file for Spanish status values."""
    issues = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            for line_num, line in enumerate(content.split('\n'), 1):
                for pattern in patterns:
                    if re.search(pattern, line):
                        issues.append({
                            'file': str(file_path),
                            'line': line_num,
                            'content': line.strip(),
                            'pattern': pattern
                        })
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    return issues

def main():
    """Main validation function."""
    print("🔍 Validating status consistency...\n")
    
    # Patterns to check (Spanish status values in code)
    status_patterns = [
        r'["\']interrogando["\']',
        r'["\']completado["\']',
        r'["\']evaluando["\']',
        r'["\']integrando["\']',
    ]
    
    # Field name patterns (Spanish fields that should be English)
    field_patterns = [
        r'\.evaluacion[^a-zA-Z]',
        r'\.respuesta[^a-zA-Z]',
        r'\.recomendaciones[^a-zA-Z]',
        r'interconsulta_id',
    ]
    
    # Files to check
    backend_files = list(Path('app').rglob('*.py'))
    
    all_issues = []
    
    # Check for Spanish status values in Python files
    print("📋 Checking Python files for Spanish status values...")
    for file_path in backend_files:
        if 'test' in str(file_path):  # Skip test files
            continue
        issues = check_file_for_spanish_status(file_path, status_patterns)
        all_issues.extend(issues)
    
    # Check for Spanish field names in Python files
    print("📋 Checking Python files for Spanish field names...")
    for file_path in backend_files:
        if 'test' in str(file_path):  # Skip test files
            continue
        issues = check_file_for_spanish_status(file_path, field_patterns)
        all_issues.extend(issues)
    
    if all_issues:
        print(f"\n⚠️  Found {len(all_issues)} potential issues:\n")
        for issue in all_issues:
            print(f"  {issue['file']}:{issue['line']}")
            print(f"    Pattern: {issue['pattern']}")
            print(f"    Content: {issue['content']}\n")
    else:
        print("\n✅ No Spanish status values or field names found in code!")
    
    # Check database model methods
    print("\n📋 Checking database methods...")
    db_model_path = Path('app/models/database.py')
    if db_model_path.exists():
        with open(db_model_path, 'r') as f:
            content = f.read()
            if 'def update_status(' in content:
                print("  ✅ update_status() method found")
            if 'def add_interconsultation(' in content:
                print("  ✅ add_interconsultation() method found")
            if 'def add_counter_referral(' in content:
                print("  ✅ add_counter_referral() method found")
    
    # Check workflow state
    print("\n📋 Checking workflow state definition...")
    graph_path = Path('app/agents/graph.py')
    if graph_path.exists():
        with open(graph_path, 'r') as f:
            content = f.read()
            if 'status: str' in content and 'estado: str' not in content:
                print("  ✅ Workflow uses 'status' field (not 'estado')")
            elif 'estado: str' in content:
                print("  ⚠️  Workflow still uses 'estado' field")
    
    print("\n✅ Validation complete!")
    
    return len(all_issues) == 0

if __name__ == '__main__':
    import sys
    success = main()
    sys.exit(0 if success else 1)
