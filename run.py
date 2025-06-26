#!/usr/bin/env python3
"""
Script de lancement de l'API
Usage: python run.py
"""

if __name__ == "__main__":
    import subprocess
    import sys
    import os
    
    # Changer vers le répertoire backend
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(backend_dir)
    
    # Lancer l'API avec uvicorn
    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn", "main:app", 
            "--host", "0.0.0.0", 
            "--port", "8000", 
            "--reload"
        ], check=True)
        
    except KeyboardInterrupt:
        print("\n🛑 Arrêt de l'API")
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur lors du lancement: {e}")
        sys.exit(1) 