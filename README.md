#  Automatisation de la Sauvegarde et Restauration des VMs – Projet de Fin d'Études

Ce dépôt contient l’ensemble des scripts développés dans le cadre du Projet de Fin d’Études réalisé chez **FTS**. Le projet a pour objectif d’automatiser la **sauvegarde** et la **restauration** des machines virtuelles (VMs) hébergées dans des environnements VMware Cloud Director à l’aide de **vRealize Orchestrator (vRO)** et **Veeam Backup & Replication**.

##  Structure du dépôt

```bash
📁 autobackup-vf/
│   ├── Automated VM Backup (Foreach) P1/         # Scripts utilisés dans le workflow d’ajout automatique des VMs aux jobs de sauvegarde
│   └── Automated VM Backup (Foreach) P3/     # Workflow principal de gestion des VDCs et déclenchement du P1
📁 test_connectivity/
│   ├── with-vcloud.py       # Test de connexion à VMware Cloud Director
│   ├── with-vem.py          # Test de connexion à Veeam Enterprise Manager
│   └── with-vbr.py          # Test de connexion à Veeam Backup & Replication
📁 restore_workflow/
│   ├── get-vms-from-vdc.py        # Récupération des VMs depuis les VDCs sélectionnés
│   ├── logout-vcloud.py           # Déconnexion sécurisée de vCloud Director
│   └── VMs Selected.py            # Traitement des VMs sélectionnées via l’interface utilisateur
│   └── Fetch Restore Points.py                # Récupération des points de restauration disponibles
│   └── Perform Full VM Restore.py             # Restauration complète d'une VM
│   └── Performing Instant Recovery to Vsphere.py # Restauration instantanée vers vSphere
│   └── logout-vbr.py              # Déconnexion de Veeam Backup & Replication
│   └── logout-vem.py              # Déconnexion de Veeam Enterprise Manager
│   └── Write Logs to resource.js   # Écriture des logs dans le resource element
│   └── Generate Restore Report.js  # Génération automatique du rapport final
│   └── send mail.js                # Envoi du rapport par mail (si activé)
```
# Technologies utilisées
```
VMware vRealize Orchestrator (vRO)
Veeam Backup & Replication / Enterprise Manager
VMware Cloud Director 
Python
javascript
```
