import holidays
from datetime import date, timedelta
from typing import Set


def get_cote_ivoire_holidays(year: int) -> Set[date]:
    """
    Retourne l'ensemble des jours fériés en Côte d'Ivoire pour une année donnée
    Basé sur les jours fériés français (pour les fêtes chrétiennes) mais adapté
    """
    # Commencer avec les jours fériés français pour avoir les fêtes chrétiennes
    french_holidays = holidays.France(years=year)
    
    # Créer notre propre ensemble de jours fériés
    ci_holidays = set()
    
    # Ajouter les jours fériés chrétiens de France qui s'appliquent aussi en Côte d'Ivoire
    for holiday_date, name in french_holidays.items():
        # Garder seulement les fêtes chrétiennes universelles
        name_lower = name.lower()
        if any(keyword in name_lower for keyword in [
            'new year', 'nouvel an',
            'easter monday', 'lundi de pâques',
            'ascension', 
            'whit monday', 'lundi de pentecôte',
            'assumption', 'assomption',
            'all saints', 'toussaint',
            'christmas', 'noël'
        ]):
            ci_holidays.add(holiday_date)
    
    # Ajouter les jours fériés spécifiques à la Côte d'Ivoire
    
    # Jours fériés fixes spécifiques à la Côte d'Ivoire
    ci_holidays.add(date(year, 5, 1))   # Fête du Travail
    ci_holidays.add(date(year, 8, 7))   # Fête de l'Indépendance
    ci_holidays.add(date(year, 11, 15)) # Jour de la Paix
    
    # Ajouter les fêtes musulmanes (approximatives - ces dates varient selon le calendrier lunaire)
    # En production, il faudrait utiliser une API ou base de données pour ces dates exactes
    
    # Dates approximatives pour 2024
    if year == 2024:
        ci_holidays.add(date(2024, 4, 10))  # Aïd el-Fitr (Fin du Ramadan)
        ci_holidays.add(date(2024, 6, 16))  # Aïd el-Kebir (Fête du Sacrifice)
        ci_holidays.add(date(2024, 9, 15))  # Maouloud (Naissance du Prophète)
        
    # Dates approximatives pour 2025  
    elif year == 2025:
        ci_holidays.add(date(2025, 3, 30))  # Aïd el-Fitr (Fin du Ramadan)
        ci_holidays.add(date(2025, 6, 6))   # Aïd el-Kebir (Fête du Sacrifice)
        ci_holidays.add(date(2025, 9, 4))   # Maouloud (Naissance du Prophète)
        
    # Dates approximatives pour 2026
    elif year == 2026:
        ci_holidays.add(date(2026, 3, 20))  # Aïd el-Fitr (Fin du Ramadan)
        ci_holidays.add(date(2026, 5, 27))  # Aïd el-Kebir (Fête du Sacrifice)
        ci_holidays.add(date(2026, 8, 25))  # Maouloud (Naissance du Prophète)
    
    return ci_holidays


def calculate_working_days(start_date: date, end_date: date) -> int:
    """
    Calcule le nombre de jours ouvrables entre deux dates en excluant :
    - Les weekends (samedi et dimanche)
    - Les jours fériés de Côte d'Ivoire
    """
    if start_date > end_date:
        return 0
    
    # Obtenir tous les jours fériés pour les années concernées
    holidays_set = set()
    for year in range(start_date.year, end_date.year + 1):
        holidays_set.update(get_cote_ivoire_holidays(year))
    
    # Compter les jours ouvrables
    current_date = start_date
    working_days = 0
    
    while current_date <= end_date:
        # Vérifier si c'est un jour ouvrable
        # weekday(): Lundi=0, Dimanche=6
        # Weekend = samedi(5) et dimanche(6)
        if current_date.weekday() < 5 and current_date not in holidays_set:
            working_days += 1
        current_date += timedelta(days=1)
    
    return working_days


def calculate_total_days(start_date: date, end_date: date) -> int:
    """
    Calcule le nombre total de jours entre deux dates (inclus)
    """
    if start_date > end_date:
        return 0
    return (end_date - start_date).days + 1


def format_nombre_jours(working_days: int, total_days: int) -> str:
    """
    Formate le nombre de jours pour l'enregistrement
    """
    return f"{working_days} jour(s) ouvrable(s) sur {total_days} jour(s) total"


def get_holidays_for_year(year: int) -> dict:
    """
    Retourne un dictionnaire des jours fériés avec leurs noms pour une année donnée
    Utile pour le debugging et l'affichage
    """
    # Obtenir les jours fériés français pour les noms
    french_holidays = holidays.France(years=year)
    ci_holidays_set = get_cote_ivoire_holidays(year)
    
    result = {}
    for holiday_date in ci_holidays_set:
        # Essayer de trouver le nom dans les jours fériés français
        if holiday_date in french_holidays:
            result[holiday_date] = french_holidays[holiday_date]
        else:
            # Sinon, donner un nom basé sur la date
            if holiday_date.month == 5 and holiday_date.day == 1:
                result[holiday_date] = "Fête du Travail"
            elif holiday_date.month == 8 and holiday_date.day == 7:
                result[holiday_date] = "Fête de l'Indépendance"
            elif holiday_date.month == 11 and holiday_date.day == 15:
                result[holiday_date] = "Jour de la Paix"
            else:
                # Pour les fêtes musulmanes, déterminer le nom selon l'année et le mois
                if year == 2024:
                    if holiday_date.month == 4 and holiday_date.day == 10:
                        result[holiday_date] = "Aïd el-Fitr (Fin du Ramadan)"
                    elif holiday_date.month == 6 and holiday_date.day == 16:
                        result[holiday_date] = "Aïd el-Kebir (Fête du Sacrifice)"
                    elif holiday_date.month == 9 and holiday_date.day == 15:
                        result[holiday_date] = "Maouloud (Naissance du Prophète)"
                    else:
                        result[holiday_date] = "Jour férié"
                elif year == 2025:
                    if holiday_date.month == 3 and holiday_date.day == 30:
                        result[holiday_date] = "Aïd el-Fitr (Fin du Ramadan)"
                    elif holiday_date.month == 6 and holiday_date.day == 6:
                        result[holiday_date] = "Aïd el-Kebir (Fête du Sacrifice)"
                    elif holiday_date.month == 9 and holiday_date.day == 4:
                        result[holiday_date] = "Maouloud (Naissance du Prophète)"
                    else:
                        result[holiday_date] = "Jour férié"
                elif year == 2026:
                    if holiday_date.month == 3 and holiday_date.day == 20:
                        result[holiday_date] = "Aïd el-Fitr (Fin du Ramadan)"
                    elif holiday_date.month == 5 and holiday_date.day == 27:
                        result[holiday_date] = "Aïd el-Kebir (Fête du Sacrifice)"
                    elif holiday_date.month == 8 and holiday_date.day == 25:
                        result[holiday_date] = "Maouloud (Naissance du Prophète)"
                    else:
                        result[holiday_date] = "Jour férié"
                else:
                    result[holiday_date] = "Jour férié"
    
    return result 