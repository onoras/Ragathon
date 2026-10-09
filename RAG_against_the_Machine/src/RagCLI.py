class RagCLI:
    """RAG pipeline CLI for  the vLLM knowledge base"""

    def index(self, max_chunk_size: int = 2000) -> None:
        """Ingest data/raw/ and build the index under data/processed/."""
        raise NotImplementedError

    def search(self, query: str,  k: int) -> None:
        """Return the top-k sources for a single query."""
        raise NotImplementedError

    def search_dataset(self, dataset_path: str, k: int,
                       save_directory: str) -> None:
        """
        Run search over a whole dataset and write a StudentSearchResults
        JSON file.
        """
        raise NotImplementedError

    def answer(self, query: str, k: int) -> None:
        """Answer a single query using the retrieved context."""
        raise NotImplementedError

    def answer_dataset(self, student_search_results_path: str,
                       save_directory:
                       str = "data/output/search_results_and_answer") -> None:
        """
        Generate answers for a dataset, producing a
        StudentSearchResultsAndAnswer JSON file.
        """
        raise NotImplementedError

    def evaluate(self, student_search_results_path: str,
                 dataset_path: str) -> None:
        """
        Report your own recall@k against a ground-truth dataset,
        for your own testing.
        """
        raise NotImplementedError
