# Command boundary reference archive

Captured on 12 November 2026 before replacing the active command interpreter.
`manifest.json` records SHA-256 hashes of the exact working-tree bytes, including
changes that had not been committed. Nothing in this directory is imported by
the application. Treat it as reference material, not a fallback implementation.

The snapshot includes:

- `ai_client.py`: provider clients and the old command-routing entry point.
- `atc_llm.py`, `kb_oaci.py`, `04_ner_extraction.py`: prompts, French knowledge
  cards, regex hints, permissive JSON recovery and postprocessing.
- `03_bluesky_connector.py`: the old four-action translator and range checks.
- `graph_secteur.py`, `secteur_graphe.json`, `atc_callsign.py`: referenced helpers/data.
- `approach_radio.py`: the former keyword-selected procedure prompts.
- `simple_demo.py`, `atc_app.py`: pre-migration execution policies and orchestration.
- Corresponding client, application, voice and procedure tests.

Some original modules remain under `src` because scenario generation, historical
CLI scripts or shared functionality still use them. Archiving this boundary is
not a repository-wide removal or a statement about ownership of the whole app.

See [the new boundary design](../../docs/COMMAND_BOUNDARY.md) for the replacement,
intentional behavior changes, retained dependencies and extension points.
