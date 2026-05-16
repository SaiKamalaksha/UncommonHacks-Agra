import signal
import sys

from agent.alerter import Alerter
from agent.agent import FileWatcher
from agent.config import AgentConfig
from agent.llm_analyst import LLMAnalyst
from agent.scorer import Scorer


def main():
    print("=" * 60)
    print("  AGRA EDR Agent")
    print("=" * 60)

    config = AgentConfig()

    print("\n[1/4] Loading ML models ...")
    scorer = Scorer(config.model_dir)

    llm = None
    if config.use_llm:
        print("\n[2/4] Connecting to Ollama LLM ...")
        llm = LLMAnalyst(config.ollama_model, config.ollama_url)
        if llm.available:
            print(f"  Ollama connected — model: {config.ollama_model}")
        else:
            print("  Ollama not available — running ML-only mode.")
    else:
        print("\n[2/4] LLM disabled in config — ML-only mode.")

    print("\n[3/4] Initializing alerter ...")
    alerter = Alerter(config)
    print(f"  Backend: {config.backend_url}")

    print("\n[4/4] Starting file watcher ...")
    watcher = FileWatcher(config, scorer, llm, alerter)
    watcher.start()

    print("\n" + "=" * 60)
    print("  Agent is running. Press Ctrl+C to stop.")
    print("=" * 60 + "\n")

    def shutdown(signum, frame):
        print("\n  Shutting down ...")
        watcher.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    signal.pause()


if __name__ == "__main__":
    main()
