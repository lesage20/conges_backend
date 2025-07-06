def arithmetic_arranger(problems, show_answers=False):

    if len(problems) > 5:
        return "Error: Too many problems."
    
    first_line = []    
    second_line = []   
    dashes_line = []   
    answers_line = []  
    
    for problem in problems:
        parts = problem.split()
        
        if len(parts) != 3:
            return "Error: Operator must be '+' or '-'."
        
        first_operand, operator, second_operand = parts
        
        if operator not in ['+', '-']:
            return "Error: Operator must be '+' or '-'."
        
        if not first_operand.isdigit() or not second_operand.isdigit():
            return "Error: Numbers must only contain digits."
        
        if len(first_operand) > 4 or len(second_operand) > 4:
            return "Error: Numbers cannot be more than four digits."
        
        width = max(len(first_operand), len(operator) + 1 + len(second_operand)) + 2
        
        first_line.append(first_operand.rjust(width))
        
        second_line.append(operator + second_operand.rjust(width - 1))
        
        dashes_line.append('-' * width)
        
        if show_answers:
            if operator == '+':
                answer = int(first_operand) + int(second_operand)
            else:  # operator == '-'
                answer = int(first_operand) - int(second_operand)
            answers_line.append(str(answer).rjust(width))
    
    result_lines = []
    result_lines.append('    '.join(first_line))
    result_lines.append('    '.join(second_line))
    result_lines.append('    '.join(dashes_line))
    
    if show_answers:
        result_lines.append('    '.join(answers_line))
    
    return '\n'.join(result_lines)


# Tests pour vérifier le fonctionnement
if __name__ == "__main__":
    # Test de base
    print("Test 1:")
    print(arithmetic_arranger(["32 + 698", "3801 - 2", "45 + 43", "123 + 49"]))
    print()
    
    # Test avec réponses
    print("Test 2 (avec réponses):")
    print(arithmetic_arranger(["32 + 8", "1 - 3801", "9999 + 9999", "523 - 49"], True))
    print()
    
    # Test d'erreur - trop de problèmes
    print("Test 3 (trop de problèmes):")
    print(arithmetic_arranger(["3 + 855", "3801 - 2", "45 + 43", "123 + 49"]))
    print()
    
    # Test d'erreur - opérateur invalide
    print("Test 4 (opérateur invalide):")
    print(arithmetic_arranger(["11 + 4", "3801 - 2999", "1 + 2", "123 + 49", "1 - 9380"]))
    print()
    
    # Test d'erreur - nombre trop long
    print("Test 5 (nombre trop long):")
    print(arithmetic_arranger(["44 + 815", "909 - 2", "45 + 43", "123 + 49", "888 + 40", "653 + 87"]))
    print()
    
    # Test d'erreur - caractères non numériques
    print("Test 6 (caractères non numériques):")
    print(arithmetic_arranger(["3 / 855", "3801 - 2", "45 + 43", "123 + 49"]))
    print()
    
    print("Test 7:")
    print(arithmetic_arranger(["3801 - 2", "123 + 49"]))
    
