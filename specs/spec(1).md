# 📄 Spécification Technique du Système — Version 2.0 (Test Léger)

> **Version :** 2.0  
> **Statut :** Validation du Pipeline  
> **Auteur :** Équipe Technique  
> **Changelog v2.0 :** Test de versionnage court après réinitialisation des verrous BDD.

---

## 1. Présentation Générale

Ce document constitue le test de mise à jour pour valider le passage de la version `v1.0` à la version `v2.0` dans la base de données PostgreSQL et la génération du PDF `spec(1)_v2.0.pdf`.

---

## 2. Exigences Fonctionnelles

* **REQ-V2-01 (Incrémentation Automatique) :** Le système doit détecter la modification du fichier source et enregistrer la version `2.0` dans la table `doc_versions`.
* **REQ-V2-02 (Rendu Rapide) :** Génération optimisée du document sans latence sur les agents d'enrichissement.

---

## 3. Architecture Simplifiée
[Fichier Source v2.0] --> [FastAPI Pipeline] --> [BDD PostgreSQL (doc_versions v2.0)]


---

## 4. Glossaire Léger

| Terme | Définition |
| :--- | :--- |
| **Pipeline v2** | Deuxième cycle d'exécution du graphe d'agents. |
| **Validation Hash** | Vérification de la modification SHA-256 pour déclencher la mise à jour. |