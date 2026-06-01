import os
from typing import Dict, List


def run_generation_eval(
    rag_system,
    eval_set: List[Dict],
    settings,
) -> Dict:
    """
    Run RAGAS faithfulness, answer_relevancy, context_precision, context_recall
    over the labeled eval set.

    Requires GROQ_API_KEY env var or a running Ollama instance. Returns a dict
    with metric scores plus n_queries. Returns zeros with an error key if the
    LLM judge cannot be configured.
    """
    try:
        from ragas import EvaluationDataset, SingleTurnSample, evaluate
        from ragas.metrics import (
            AnswerRelevancy,
            ContextPrecision,
            ContextRecall,
            Faithfulness,
        )
    except ImportError as e:
        return {"error": f"ragas not installed: {e}", "n_queries": len(eval_set)}

    llm = _build_judge_llm(settings)
    if llm is None:
        return {
            "error": "No LLM judge available. Set GROQ_API_KEY or start Ollama.",
            "n_queries": len(eval_set),
        }

    samples = []
    for entry in eval_set:
        result = rag_system.query(
            entry["query"],
            user_id="eval_runner",
            role="admin",
        )
        samples.append(
            SingleTurnSample(
                user_input=entry["query"],
                response=result["answer"],
                retrieved_contexts=[
                    c for c in result.get("contexts", [result["answer"]])
                ],
                reference=entry["reference_answer"],
            )
        )

    dataset = EvaluationDataset(samples=samples)
    metrics = [Faithfulness(), AnswerRelevancy(), ContextPrecision(), ContextRecall()]
    result = evaluate(dataset=dataset, metrics=metrics, llm=llm)

    return {
        "faithfulness": float(result["faithfulness"]),
        "answer_relevancy": float(result["answer_relevancy"]),
        "context_precision": float(result["context_precision"]),
        "context_recall": float(result["context_recall"]),
        "n_queries": len(eval_set),
    }


def _build_judge_llm(settings):
    """Return a RAGAS-compatible LLM wrapper, preferring Groq then Ollama."""
    groq_key = os.environ.get("GROQ_API_KEY", "")
    if groq_key:
        try:
            from langchain_groq import ChatGroq
            from ragas.llms import LangchainLLMWrapper

            return LangchainLLMWrapper(
                ChatGroq(model=settings.groq_model, api_key=groq_key)
            )
        except ImportError:
            pass

    # Fallback: Ollama via LangChain community (optional dep)
    try:
        from langchain_community.chat_models import ChatOllama
        from ragas.llms import LangchainLLMWrapper

        return LangchainLLMWrapper(ChatOllama(model=settings.ollama_model))
    except ImportError:
        pass

    return None
