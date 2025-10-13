import os
import asyncio
from typing import List, Dict, Any

from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy, # This is correct
    context_recall,
    context_precision,
)

from ragas.llms import LangchainLLMWrapper          
from ragas.embeddings import LangchainEmbeddingsWrapper 

from langchain_community import ChatLiteLLM as LangChainLiteLLM 
from langchain_community import LiteLLMEmbeddings as LangChainLiteLLMEmbedding 

from app.services.rag_service import rag_search

# --- 1. Ragas LiteLLM/Groq/TEI Configuration ---

# The litellm proxy is available at http://litellm:4000
# from the perspective of the backend container.
LITELLM_PROXY_URL = settings.PROXY_URL # e.g., "http://litellm:4000"
LITELLM_PROXY_KEY = settings.PROXY_KEY # Your PROXY_KEY

# Configure the LLM for Ragas metrics (Faithfulness, Answer Relevance)
# We use the Ragas LiteLLM wrapper directly
litellm_llm = LangchainLLMWrapper(
    model_name=settings.LITELMM_MODEL,
    api_base=settings.LITELMM_URL,
    # other params...
)

ragas_llm = LLM(llm=litellm_llm)

# Configure the Embeddings for Ragas metrics (Answer Relevance, Context Precision)
# We use the Ragas LiteLLMEmbedding wrapper directly
litellm_embedding = LangChainLiteLLMEmbedding(
    model_name=settings.EMBEDDING_MODEL_NAME,
    api_base=settings.TEI_EMBEDDINGS_URL,
    # other params...
)

# 2. Wrap the LangChain object with Ragas's generic wrapper
ragas_embeddings = LangchainEmbeddingsWrapper(embeddings=litellm_embedding)


# --- 2. Evaluation Logic ---

async def run_evaluation(testset: List[Dict[str, Any]]):
    """
    Runs the Ragas evaluation on a provided testset.

    Args:
        testset: A list of dicts, each containing 'question' and 'ground_truth'.
    """
    logger.info("Starting Ragas evaluation...")

    # Step 1: Execute RAG for all questions
    results = []
    for item in testset:
        question = item['question']
        logger.info(f"Processing question: {question}")
        try:
            # Call your main RAG function
            rag_output = await rag_search(
                query=question, 
                k=3, # Max 3 chunks is a good default for Ragas
                use_embeddings=True
            )
            
            # Extract required fields for Ragas Dataset
            contexts = [c['content'] for c in rag_output['chunks']]
            
            results.append({
                'question': question,
                'answer': rag_output['answer'],
                'contexts': contexts, # List of retrieved text chunks
                'ground_truth': item['ground_truth'] # The expected correct answer
            })

        except Exception as e:
            logger.error(f"RAG execution failed for question '{question}': {e}")
            results.append({
                'question': question,
                'answer': "Error during RAG execution.",
                'contexts': [],
                'ground_truth': item['ground_truth']
            })
            continue

    # Step 2: Convert to Ragas Dataset
    data = {k: [r[k] for r in results] for k in results[0].keys()}
    dataset = Dataset.from_dict(data)
    
    # Step 3: Run Ragas Metrics
    
    # Override Ragas defaults with your LiteLLM/Groq/TEI setup
    for metric in [faithfulness, answer_relevancy, context_recall, context_precision]:
        metric.llm = ragas_llm
        metric.embeddings = ragas_embeddings
    
    score = evaluate(
        dataset,
        metrics=[
            faithfulness,         # Checks if the answer is grounded in the context
            answer_relevancy,     # Checks if the answer is relevant to the question
            context_recall,       # Checks if the retrieved context covers the ground truth
            context_precision,    # Checks if the retrieved context is relevant to the question
        ],
        raise_on_error=False # Don't stop on a single failure
    )

    logger.info("Ragas Evaluation Complete.")
    print(score)
    return score.to_dict()

# --- 3. Example Execution (for testing/manual profile) ---

if __name__ == "__main__":
    # A small synthetic testset (you would load a real one in production)
    example_testset = [
        {
            "question": "Define autoencoders", 
            "ground_truth": "Autoencoders are a type of neural network used for learning efficient data codings in an unsupervised manner."
        },
        {
            "question": "What is the primary goal of linear factor models?", 
            "ground_truth": "The primary goal of linear factor models, such as PCA, is to model the covariance structure among variables by a few latent factors."
        }
        # Add more questions relevant to autoencoders.pdf, linear_algebra.pdf, etc.
    ]
    
    # Run the async function
    asyncio.run(run_evaluation(example_testset))