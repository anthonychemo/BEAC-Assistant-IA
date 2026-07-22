# Documentation de projet — BEAC-Assistant-IA

Ces trois cahiers servent de base à la rédaction du rapport de projet. Chacun est autoportant et peut être lu indépendamment.

| Document | Contenu |
|---|---|
| [Cahier des charges](cahier-des-charges/README.md) | Contexte, problématique, objectifs, périmètre, besoins fonctionnels et non fonctionnels, contraintes, livrables, planning |
| [Cahier d'analyse](cahier-analyse/README.md) | Étude de l'existant, justification de la solution RAG, acteurs, cas d'utilisation, analyse des risques, méthodologie, glossaire |
| [Cahier de conception](cahier-conception/README.md) | Architecture technique, choix technologiques, modèle de données, conception du moteur RAG/API/interface, sécurité, déploiement, limites et évolutions |

Ces documents s'appuient sur une analyse approfondie du code réel du projet (backend `beac-rag-backend/`, frontend `Frontend/`) et non sur une description générique — ils reflètent l'architecture et les décisions effectivement en place.

## Notes techniques complémentaires

| Document | Contenu |
|---|---|
| [Recherche et filtration](recherche-et-filtration.md) | Explication complète des deux systèmes de recherche (chat sémantique vs bibliothèque hybride), des filtres, du cache, des index de performance et du bug de proxy corrigé |
| [Mise en production](mise-en-production.md) | État des lieux réel, enjeu du LLM gratuit à l'échelle, souveraineté des données, technologies idéales et coûts (sourcés), deux scénarios chiffrés (DIY vs managé), plan d'action priorisé |
