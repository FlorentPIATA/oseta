# OSETA — Lessons Learned

## Format : [date] | contexte | cause racine | règle généralisable

[2026-05-06] | services/collector.py | Fichier dépasse 200 lignes (237) car fonctions de fetch incluses dans le même module que l'orchestration | Règle : séparer les clients HTTP (fetch functions) dans un sous-module `_sources.py` dès le début pour respecter la limite de 200 lignes.

[2026-05-06] | tests/conftest.py | pytest-asyncio 0.24 avec `asyncio_default_fixture_loop_scope = "session"` crée un loop de session pour les fixtures mais un loop de fonction pour les tests — asyncpg crée des Futures pendant le test sur le loop de fonction, alors que le teardown de la fixture tourne sur le loop de session → RuntimeError "Future attached to a different loop" | Règle : utiliser `asyncio_default_fixture_loop_scope = "function"` pour que fixtures et tests partagent le même loop. Créer/détruire le schéma via `asyncio.run()` dans `pytest_sessionstart`/`pytest_sessionfinish` (hors de tout loop pytest-asyncio). Créer un engine NullPool par test dans la fixture `session` (pas session-scoped).

[2026-05-06] | tests/conftest.py | `pool_pre_ping=True` avec asyncpg en contexte de test async force asyncpg à pinger les connexions poolées au checkout — les Futures internes du ping sont attachées au loop courant et génèrent "different loop" si le loop a changé entre les tests | Règle : toujours utiliser `poolclass=NullPool` dans les engines de test async. NullPool crée une connexion fraîche à chaque checkout — aucune Future stale possible.

[2026-05-06] | tests/conftest.py | TRUNCATE en teardown de fixture async échoue si le teardown tourne via `run_until_complete` alors que les connexions asyncpg ont des Futures du contexte principal | Règle : faire le TRUNCATE en setup (début de test) plutôt qu'en teardown — le setup tourne dans le bon contexte async. Le dernier test laisse la DB sale, c'est acceptable.

[2026-05-06] | models/schemas.py + routes/predictions.py | `realized_at` existait sur le modèle DB (Prediction) mais était absent du schéma Pydantic PredictionRead — le test `test_realize_success` échouait avec KeyError | Règle : à chaque nouveau champ nullable ajouté au modèle DB, vérifier immédiatement le schéma Read correspondant dans models/schemas.py.

[2026-05-06] | config.py + docker-compose | pydantic-settings charge `.env.local` via `env_file=(".env", ".env.local")` — mais le process uvicorn charge les settings au démarrage. Changer `.env.local` ne recharge PAS les settings dans le container en cours d'exécution (uvicorn --reload ne surveille que les .py) | Règle : après tout changement de clé API dans `.env.local`, faire `docker compose restart api` pour que le nouveau token soit pris en compte.
