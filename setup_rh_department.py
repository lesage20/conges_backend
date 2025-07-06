"""
Script pour configurer le département Ressources Humaines et assigner le DRH comme chef.
"""
import asyncio
import uuid
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import select, and_
from models.database import get_database_url
from models.user import User, RoleEnum
from models.departement import Departement

async def setup_rh_department():
    """Configure le département RH et assigne le DRH comme chef"""
    # Créer le moteur async pour ce script
    engine = create_async_engine(get_database_url(), echo=True)
    
    async with AsyncSession(engine) as db:
        print("🔧 Configuration du département Ressources Humaines...")
        
        try:
            # 1. Chercher s'il existe déjà un département RH
            result = await db.execute(
                select(Departement).where(
                    Departement.nom.in_(["Ressources Humaines", "RH", "DRH"])
                )
            )
            dept_rh = result.scalar_one_or_none()
            
            if not dept_rh:
                # Créer le département RH
                dept_rh = Departement(
                    nom="Ressources Humaines",
                    description="Département de gestion des ressources humaines",
                    budget_conges="0"
                )
                db.add(dept_rh)
                await db.flush()  # Pour obtenir l'ID
                print(f"✅ Département 'Ressources Humaines' créé avec l'ID: {dept_rh.id}")
            else:
                print(f"✅ Département RH existant trouvé: {dept_rh.nom} (ID: {dept_rh.id})")
            
            # 2. Chercher le DRH
            result = await db.execute(
                select(User).where(User.role == RoleEnum.DRH)
            )
            drh = result.scalar_one_or_none()
            
            if not drh:
                print("❌ Aucun utilisateur avec le rôle DRH trouvé. Veuillez d'abord créer un utilisateur DRH.")
                return
            
            print(f"✅ DRH trouvé: {drh.prenom} {drh.nom} (ID: {drh.id})")
            
            # 3. Assigner le DRH au département RH s'il n'y est pas déjà
            if drh.departement_id != dept_rh.id:
                drh.departement_id = dept_rh.id
                print(f"✅ DRH assigné au département Ressources Humaines")
            
            # 4. Assigner le DRH comme chef du département RH
            if dept_rh.chef_departement_id != drh.id:
                dept_rh.chef_departement_id = drh.id
                print(f"✅ DRH défini comme chef du département Ressources Humaines")
            
            await db.commit()
            
            # 5. Vérifier les autres employés du département RH
            result = await db.execute(
                select(User).where(
                    and_(
                        User.departement_id == dept_rh.id,
                        User.role == RoleEnum.EMPLOYE
                    )
                )
            )
            employes_rh = result.scalars().all()
            
            if employes_rh:
                print(f"✅ {len(employes_rh)} employé(s) trouvé(s) dans le département RH:")
                for emp in employes_rh:
                    print(f"   - {emp.prenom} {emp.nom}")
            else:
                print("ℹ️  Aucun employé actuellement assigné au département RH")
            
            print("\n🎉 Configuration terminée avec succès !")
            print("📋 Résumé de la hiérarchie:")
            print(f"   • DRH: {drh.prenom} {drh.nom}")
            print(f"   • Chef du département RH: {drh.prenom} {drh.nom}")
            print(f"   • Règles d'approbation:")
            print(f"     - Demandes DRH: Auto-approuvées")
            print(f"     - Demandes chefs de service: Validées par le DRH")
            print(f"     - Demandes employés RH: Validées par le DRH")
            print(f"     - Demandes employés autres départements: Validées par leur chef de service")
            
        except Exception as e:
            print(f"❌ Erreur lors de la configuration: {e}")
            await db.rollback()
            raise
        finally:
            await engine.dispose()

async def main():
    await setup_rh_department()

if __name__ == "__main__":
    asyncio.run(main()) 