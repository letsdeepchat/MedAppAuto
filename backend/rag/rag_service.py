"""
RAG (Retrieval-Augmented Generation) Service
Provides FAQ knowledge base functionality using vector search
"""

import json
import logging
import os
from typing import Dict, Any, List, Optional
from pathlib import Path

try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    from config import settings
except ImportError:
    # Mock settings for testing
    class MockSettings:
        pass
    settings = MockSettings()


class RAGService:
    """Service for RAG-based FAQ retrieval and answering"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.collection = None
        self.model = None
        self.chroma_client = None
        self.data_dir = Path(__file__).parent.parent.parent / "data"
        self.clinic_data = {}
        self.doctor_data = {}

    async def initialize(self):
        """Initialize the RAG service with data and vector database"""
        try:
            # Load data files
            await self._load_data_files()

            # Initialize vector database if available
            if CHROMA_AVAILABLE and SENTENCE_TRANSFORMERS_AVAILABLE:
                await self._initialize_vector_db()
                await self._populate_knowledge_base()
                self.logger.info("RAG service initialized with vector search")
            else:
                self.logger.warning("Vector search dependencies not available, using fallback search")

        except Exception as e:
            self.logger.error(f"Error initializing RAG service: {e}")
            # Continue with basic functionality even if vector search fails

    async def _load_data_files(self):
        """Load clinic and doctor data from JSON files"""
        try:
            # Load clinic info
            clinic_file = self.data_dir / "clinic_info.json"
            if clinic_file.exists():
                with open(clinic_file, 'r', encoding='utf-8') as f:
                    self.clinic_data = json.load(f)
                self.logger.info("Clinic data loaded successfully")

            # Load doctor schedule
            doctor_file = self.data_dir / "doctor_schedule.json"
            if doctor_file.exists():
                with open(doctor_file, 'r', encoding='utf-8') as f:
                    self.doctor_data = json.load(f)
                self.logger.info("Doctor data loaded successfully")

        except Exception as e:
            self.logger.error(f"Error loading data files: {e}")

    async def _initialize_vector_db(self):
        """Initialize ChromaDB vector database"""
        try:
            # Create data directory if it doesn't exist
            chroma_dir = self.data_dir / "chroma_db"
            chroma_dir.mkdir(exist_ok=True)

            # Initialize ChromaDB client
            self.chroma_client = chromadb.PersistentClient(
                path=str(chroma_dir),
                settings=Settings(anonymized_telemetry=False)
            )

            # Initialize sentence transformer model
            self.model = SentenceTransformer('all-MiniLM-L6-v2')

            # Get or create collection
            self.collection = self.chroma_client.get_or_create_collection(
                name="medical_faq",
                metadata={"description": "Medical clinic FAQ knowledge base"}
            )

        except Exception as e:
            self.logger.error(f"Error initializing vector database: {e}")
            self.chroma_client = None
            self.model = None

    async def _populate_knowledge_base(self):
        """Populate the knowledge base with FAQ data"""
        if not self.collection or not self.clinic_data:
            return

        try:
            # Extract FAQ data from clinic info
            faq_entries = []

            # Clinic policies and information
            policies = self.clinic_data.get("clinic", {}).get("policies", {})
            for policy_key, policy_value in policies.items():
                faq_entries.append({
                    "content": f"{policy_key.replace('_', ' ').title()}: {policy_value}",
                    "metadata": {"type": "policy", "category": policy_key}
                })

            # Services
            services = self.clinic_data.get("clinic", {}).get("services", [])
            for service in services:
                faq_entries.append({
                    "content": f"Service: {service} - We offer {service.lower()} at our medical center.",
                    "metadata": {"type": "service", "category": "services"}
                })

            # Operating hours
            hours = self.clinic_data.get("clinic", {}).get("operating_hours", {})
            for day, time_range in hours.items():
                faq_entries.append({
                    "content": f"Operating hours for {day}: {time_range}",
                    "metadata": {"type": "hours", "category": "operating_hours"}
                })

            # Insurance
            insurance = self.clinic_data.get("clinic", {}).get("insurance_accepted", [])
            for provider in insurance:
                faq_entries.append({
                    "content": f"We accept insurance from {provider}",
                    "metadata": {"type": "insurance", "category": "insurance_accepted"}
                })

            # Languages
            languages = self.clinic_data.get("clinic", {}).get("languages_spoken", [])
            for language in languages:
                faq_entries.append({
                    "content": f"We provide services in {language}",
                    "metadata": {"type": "language", "category": "languages_spoken"}
                })

            # Doctor information
            doctors = self.doctor_data.get("doctors", [])
            for doctor in doctors:
                specialties = ", ".join(doctor.get("appointment_types", []))
                languages = ", ".join(doctor.get("languages", []))
                faq_entries.append({
                    "content": f"Dr. {doctor['name']} specializes in {doctor['specialty']} and offers: {specialties}. Languages: {languages}",
                    "metadata": {"type": "doctor", "category": "doctor_info", "doctor_id": doctor["id"]}
                })

            # Add entries to vector database
            if faq_entries:
                documents = [entry["content"] for entry in faq_entries]
                metadatas = [entry["metadata"] for entry in faq_entries]
                ids = [f"faq_{i}" for i in range(len(faq_entries))]

                # Generate embeddings
                embeddings = self.model.encode(documents).tolist()

                # Add to collection
                self.collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    embeddings=embeddings,
                    ids=ids
                )

                self.logger.info(f"Added {len(faq_entries)} FAQ entries to knowledge base")

        except Exception as e:
            self.logger.error(f"Error populating knowledge base: {e}")

    async def query_faqs(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Query the FAQ knowledge base

        Args:
            query: User's question
            top_k: Number of top results to return

        Returns:
            Dict containing answer and sources
        """
        try:
            # Try vector search first
            if self.collection and self.model:
                return await self._vector_search(query, top_k)
            else:
                # Fallback to keyword search
                return await self._keyword_search(query)

        except Exception as e:
            self.logger.error(f"Error querying FAQs: {e}")
            return {
                "answer": "I'm sorry, I encountered an error while searching our knowledge base. Please try rephrasing your question or contact our clinic directly.",
                "sources": []
            }

    async def _vector_search(self, query: str, top_k: int) -> Dict[str, Any]:
        """Perform vector similarity search"""
        try:
            # Generate query embedding
            query_embedding = self.model.encode([query]).tolist()[0]

            # Search collection
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=['documents', 'metadatas', 'distances']
            )

            # Format results
            sources = []
            relevant_docs = []

            if results['documents']:
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                    distance = results['distances'][0][i] if results['distances'] else 0

                    sources.append({
                        "content": doc,
                        "metadata": metadata,
                        "relevance_score": 1 - distance  # Convert distance to similarity score
                    })

                    relevant_docs.append(doc)

            # Generate answer from relevant documents
            answer = self._generate_answer(query, relevant_docs)

            return {
                "answer": answer,
                "sources": sources
            }

        except Exception as e:
            self.logger.error(f"Vector search error: {e}")
            return await self._keyword_search(query)

    async def _keyword_search(self, query: str) -> Dict[str, Any]:
        """Fallback keyword-based search"""
        try:
            query_lower = query.lower()
            relevant_info = []

            # Search clinic data
            if self.clinic_data:
                clinic = self.clinic_data.get("clinic", {})

                # Search policies
                policies = clinic.get("policies", {})
                for policy_key, policy_value in policies.items():
                    if any(keyword in policy_value.lower() or keyword in policy_key.lower()
                          for keyword in query_lower.split()):
                        relevant_info.append(f"{policy_key.replace('_', ' ').title()}: {policy_value}")

                # Search services
                services = clinic.get("services", [])
                for service in services:
                    if any(keyword in service.lower() for keyword in query_lower.split()):
                        relevant_info.append(f"We offer {service} services.")

                # Search operating hours
                hours = clinic.get("operating_hours", {})
                if any(word in query_lower for word in ['hour', 'time', 'open', 'close']):
                    for day, time_range in hours.items():
                        relevant_info.append(f"{day.title()}: {time_range}")

            # Search doctor data
            if self.doctor_data:
                doctors = self.doctor_data.get("doctors", [])
                for doctor in doctors:
                    if any(keyword in doctor.get('name', '').lower() or
                          keyword in doctor.get('specialty', '').lower()
                          for keyword in query_lower.split()):
                        specialties = ", ".join(doctor.get("appointment_types", []))
                        relevant_info.append(f"Dr. {doctor['name']} ({doctor['specialty']}): {specialties}")

            # Generate answer
            if relevant_info:
                answer = "Here's what I found:\n\n" + "\n".join(f"• {info}" for info in relevant_info[:5])
            else:
                answer = "I couldn't find specific information about your question. Please try rephrasing or contact our clinic directly for assistance."

            return {
                "answer": answer,
                "sources": [{"content": info, "metadata": {"type": "keyword_match"}} for info in relevant_info]
            }

        except Exception as e:
            self.logger.error(f"Keyword search error: {e}")
            return {
                "answer": "I'm having trouble accessing our knowledge base right now. Please contact our clinic directly for assistance.",
                "sources": []
            }

    def _generate_answer(self, query: str, relevant_docs: List[str]) -> str:
        """Generate a natural language answer from relevant documents"""
        if not relevant_docs:
            return "I couldn't find specific information about your question. Please try rephrasing or contact our clinic directly."

        # Simple answer generation - combine relevant information
        combined_info = "\n".join(relevant_docs[:3])  # Use top 3 results

        # For now, return the most relevant document as the answer
        # In a production system, this could use an LLM to generate a more natural response
        if len(combined_info) > 500:
            # Truncate if too long
            combined_info = combined_info[:500] + "..."

        return f"Based on our clinic information:\n\n{combined_info}"

    async def add_faq_entry(self, question: str, answer: str, metadata: Optional[Dict[str, Any]] = None):
        """Add a new FAQ entry to the knowledge base"""
        if not self.collection or not self.model:
            self.logger.warning("Vector database not available, cannot add FAQ entry")
            return

        try:
            # Generate embedding
            embedding = self.model.encode([answer]).tolist()[0]

            # Add to collection
            faq_id = f"faq_custom_{len(self.collection.get()['ids']) + 1}"
            self.collection.add(
                documents=[answer],
                metadatas=[metadata or {"type": "custom_faq"}],
                embeddings=[embedding],
                ids=[faq_id]
            )

            self.logger.info(f"Added custom FAQ entry: {faq_id}")

        except Exception as e:
            self.logger.error(f"Error adding FAQ entry: {e}")

    async def close(self):
        """Close the service and cleanup resources"""
        if self.chroma_client:
            # ChromaDB handles cleanup automatically
            pass