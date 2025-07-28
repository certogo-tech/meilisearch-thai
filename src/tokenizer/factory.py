"""
Tokenizer factory with compound dictionary support.
"""

import json
import logging
from pathlib import Path
from typing import List, Optional

from .thai_segmenter import ThaiSegmenter


logger = logging.getLogger(__name__)


class TokenizerFactory:
    """Factory for creating tokenizers with compound dictionary support."""
    
    _compound_dictionary: Optional[List[str]] = None
    _dictionary_path: str = "data/dictionaries/thai_compounds.json"
    
    @classmethod
    def load_compound_dictionary(cls, dict_path: Optional[str] = None) -> List[str]:
        """Load compound words dictionary from file."""
        if dict_path:
            cls._dictionary_path = dict_path
        
        if cls._compound_dictionary is not None:
            return cls._compound_dictionary
        
        try:
            path = Path(cls._dictionary_path)
            if not path.exists():
                logger.warning(f"Compound dictionary not found: {path}")
                cls._compound_dictionary = []
                return cls._compound_dictionary
            
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract compound words from JSON structure
            compounds = []
            if isinstance(data, list):
                compounds = data
            elif isinstance(data, dict):
                for category, words in data.items():
                    if isinstance(words, list):
                        compounds.extend(words)
            
            # Remove duplicates and empty entries
            cls._compound_dictionary = list(set(word.strip() for word in compounds if word.strip()))
            
            logger.info(f"Loaded {len(cls._compound_dictionary)} compound words")
            
            # Log some examples
            if cls._compound_dictionary:
                examples = cls._compound_dictionary[:5]
                logger.info(f"Compound examples: {examples}")
            
            return cls._compound_dictionary
            
        except Exception as e:
            logger.error(f"Failed to load compound dictionary: {e}")
            cls._compound_dictionary = []
            return cls._compound_dictionary
    
    @classmethod
    def create_segmenter(
        cls,
        engine: str = "newmm",
        use_compounds: bool = True,
        custom_dict_path: Optional[str] = None,
        **kwargs
    ) -> ThaiSegmenter:
        """Create a Thai segmenter with optional compound dictionary."""
        
        custom_dict = []
        if use_compounds:
            custom_dict = cls.load_compound_dictionary(custom_dict_path)
        
        return ThaiSegmenter(
            engine=engine,
            custom_dict=custom_dict,
            **kwargs
        )
    
    @classmethod
    def create_wakame_optimized_segmenter(cls) -> ThaiSegmenter:
        """Create a segmenter specifically optimized for wakame and similar compounds."""
        
        # Ensure wakame and related compounds are in dictionary
        compounds = cls.load_compound_dictionary()
        
        # Add critical compounds if missing
        critical_compounds = [
            "วากาเมะ",
            "สาหร่ายวากาเมะ",
            "ซาชิมิ",
            "เทมปุระ",
            "ซูชิ"
        ]
        
        for compound in critical_compounds:
            if compound not in compounds:
                compounds.append(compound)
                logger.info(f"Added critical compound: {compound}")
        
        return ThaiSegmenter(
            engine="newmm",
            custom_dict=compounds,
            keep_whitespace=True
        )
    
    @classmethod
    def reload_dictionary(cls, dict_path: Optional[str] = None) -> None:
        """Reload the compound dictionary (for hot-reload functionality)."""
        cls._compound_dictionary = None
        cls.load_compound_dictionary(dict_path)
        logger.info("Compound dictionary reloaded")
    
    @classmethod
    def get_dictionary_stats(cls) -> dict:
        """Get statistics about the loaded dictionary."""
        compounds = cls.load_compound_dictionary()
        
        # Categorize compounds
        thai_japanese = [w for w in compounds if any(char in w for char in "เมะะุิ")]
        thai_english = [w for w in compounds if any(char in w for char in "์ิ์")]
        
        return {
            "total_compounds": len(compounds),
            "thai_japanese_compounds": len(thai_japanese),
            "thai_english_compounds": len(thai_english),
            "dictionary_path": cls._dictionary_path,
            "examples": compounds[:10] if compounds else []
        }
