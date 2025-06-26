#!/usr/bin/env python3
"""
Script d'initialisation de la base de données
Usage: python init_db.py
"""

if __name__ == "__main__":
    import subprocess
    import sys
    import os
    
    # Changer vers le répertoire backend
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(backend_dir)
    
    # Exécuter le script d'initialisation avec python -m
    try:
        result = subprocess.run([
            sys.executable, "-m", "utils.create_admin"
        ], check=True, capture_output=True, text=True)
        
        print("✅ Initialisation réussie!")
        print(result.stdout)
        
    except subprocess.CalledProcessError as e:
        print("❌ Erreur lors de l'initialisation:")
        print(e.stderr)
        sys.exit(1) 