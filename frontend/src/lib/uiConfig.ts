/**
 * UI presentation flags.
 *
 * These control what the interface EXPOSES, never what the backend does. All
 * functionality behind them remains fully operational.
 */

/**
 * Show the names and health of the backing services (PostgreSQL, Neo4j,
 * ChromaDB, Ollama) in the sidebar and on the Analytics page.
 *
 * Hidden for the hackathon demo: naming internal infrastructure makes the
 * product read as a technical prototype rather than a finished tool, and it is
 * not information a plant engineer would act on.
 *
 * Set to `true` to restore both surfaces. Nothing else needs changing — the
 * health data is still fetched and still drives the degraded-service warning
 * below, so operators are told when something is limited without being shown
 * which database caused it.
 */
export const SHOW_INFRASTRUCTURE_DETAILS = false;
