"""Stub for FAISS-backed vector store integration."""
import numpy as np

try:
    import faiss
except ImportError:
    faiss = None


class FaissVectorStore:
    def __init__(self, dimension=768, index_path=None):
        self.dimension = dimension
        self.index_path = index_path
        if faiss is None:
            self.index = None
        else:
            self.index = faiss.IndexFlatL2(dimension)

    def add_vectors(self, embeddings, metadata=None):
        if self.index is None:
            raise RuntimeError('FAISS is not installed.')
        array = np.asarray(embeddings, dtype='float32')
        self.index.add(array)

    def query(self, embedding, top_k=5):
        if self.index is None:
            raise RuntimeError('FAISS is not installed.')
        query_vec = np.asarray([embedding], dtype='float32')
        distances, indices = self.index.search(query_vec, top_k)
        return distances[0], indices[0]

    def save(self, path):
        if self.index is None:
            raise RuntimeError('FAISS is not installed.')
        faiss.write_index(self.index, path)

    def load(self, path):
        if self.index is None:
            raise RuntimeError('FAISS is not installed.')
        self.index = faiss.read_index(path)
