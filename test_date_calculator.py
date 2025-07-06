#!/usr/bin/env python3
"""
Script de test pour les fonctions de calcul de dates
"""
from datetime import date
from utils.date_calculator import (
    calculate_working_days,
    calculate_total_days,
    format_nombre_jours,
    get_holidays_for_year,
    get_cote_ivoire_holidays
)

def test_basic_calculations():
    """Test des calculs de base"""
    print("=== Tests de calculs de base ===")
    
    # Test 1: Semaine complète du lundi au vendredi
    start_date = date(2024, 1, 15)  # Lundi
    end_date = date(2024, 1, 19)    # Vendredi
    working_days = calculate_working_days(start_date, end_date)
    total_days = calculate_total_days(start_date, end_date)
    
    print(f"Du {start_date} au {end_date}:")
    print(f"  Jours ouvrables: {working_days}")
    print(f"  Jours total: {total_days}")
    print(f"  Formaté: {format_nombre_jours(working_days, total_days)}")
    print()
    
    # Test 2: Avec weekend
    start_date = date(2024, 1, 15)  # Lundi
    end_date = date(2024, 1, 21)    # Dimanche
    working_days = calculate_working_days(start_date, end_date)
    total_days = calculate_total_days(start_date, end_date)
    
    print(f"Du {start_date} au {end_date} (avec weekend):")
    print(f"  Jours ouvrables: {working_days}")
    print(f"  Jours total: {total_days}")
    print(f"  Formaté: {format_nombre_jours(working_days, total_days)}")
    print()

def test_holidays():
    """Test avec les jours fériés"""
    print("=== Tests avec jours fériés ===")
    
    # Test 3: Période incluant le Nouvel An
    start_date = date(2024, 12, 30)  # Lundi
    end_date = date(2024, 1, 2)      # Mardi
    working_days = calculate_working_days(start_date, end_date)
    total_days = calculate_total_days(start_date, end_date)
    
    print(f"Du {start_date} au {end_date} (Nouvel An):")
    print(f"  Jours ouvrables: {working_days}")
    print(f"  Jours total: {total_days}")
    print(f"  Formaté: {format_nombre_jours(working_days, total_days)}")
    print()
    
    # Test 4: Période incluant Noël
    start_date = date(2024, 12, 23)  # Lundi
    end_date = date(2024, 12, 27)    # Vendredi
    working_days = calculate_working_days(start_date, end_date)
    total_days = calculate_total_days(start_date, end_date)
    
    print(f"Du {start_date} au {end_date} (Noël):")
    print(f"  Jours ouvrables: {working_days}")
    print(f"  Jours total: {total_days}")
    print(f"  Formaté: {format_nombre_jours(working_days, total_days)}")
    print()

def test_edge_cases():
    """Test des cas limites"""
    print("=== Tests des cas limites ===")
    
    # Test 5: Date identique
    start_date = date(2024, 1, 15)  # Lundi
    end_date = date(2024, 1, 15)    # Même jour
    working_days = calculate_working_days(start_date, end_date)
    total_days = calculate_total_days(start_date, end_date)
    
    print(f"Même jour {start_date}:")
    print(f"  Jours ouvrables: {working_days}")
    print(f"  Jours total: {total_days}")
    print(f"  Formaté: {format_nombre_jours(working_days, total_days)}")
    print()
    
    # Test 6: Date de fin antérieure
    start_date = date(2024, 1, 15)
    end_date = date(2024, 1, 10)
    working_days = calculate_working_days(start_date, end_date)
    total_days = calculate_total_days(start_date, end_date)
    
    print(f"Date de fin antérieure {start_date} -> {end_date}:")
    print(f"  Jours ouvrables: {working_days}")
    print(f"  Jours total: {total_days}")
    print(f"  Formaté: {format_nombre_jours(working_days, total_days)}")
    print()

def display_holidays():
    """Afficher les jours fériés"""
    print("=== Jours fériés de Côte d'Ivoire ===")
    
    for year in [2024, 2025, 2026]:
        print(f"\n--- {year} ---")
        holidays_dict = get_holidays_for_year(year)
        
        for holiday_date, name in sorted(holidays_dict.items()):
            weekday = holiday_date.strftime("%A")
            print(f"  {holiday_date.strftime('%d/%m/%Y')} - {weekday}: {name}")

def test_specific_cote_ivoire_holidays():
    """Test des jours fériés spécifiques à la Côte d'Ivoire"""
    print("\n=== Test des jours fériés spécifiques ===")
    
    # Test avec Fête de l'Indépendance (7 août)
    start_date = date(2024, 8, 5)   # Lundi
    end_date = date(2024, 8, 9)     # Vendredi
    working_days = calculate_working_days(start_date, end_date)
    total_days = calculate_total_days(start_date, end_date)
    
    print(f"Du {start_date} au {end_date} (Fête de l'Indépendance 7 août):")
    print(f"  Jours ouvrables: {working_days}")
    print(f"  Jours total: {total_days}")
    print(f"  Formaté: {format_nombre_jours(working_days, total_days)}")
    print()
    
    # Test avec Jour de la Paix (15 novembre)
    start_date = date(2024, 11, 13)  # Mercredi
    end_date = date(2024, 11, 17)    # Dimanche
    working_days = calculate_working_days(start_date, end_date)
    total_days = calculate_total_days(start_date, end_date)
    
    print(f"Du {start_date} au {end_date} (Jour de la Paix 15 novembre):")
    print(f"  Jours ouvrables: {working_days}")
    print(f"  Jours total: {total_days}")
    print(f"  Formaté: {format_nombre_jours(working_days, total_days)}")
    print()

if __name__ == "__main__":
    print("Testing Date Calculator with holidays package")
    print("=" * 50)
    
    test_basic_calculations()
    test_holidays()
    test_edge_cases()
    test_specific_cote_ivoire_holidays()
    display_holidays()
    
    print("\n" + "=" * 50)
    print("Tests terminés!") 