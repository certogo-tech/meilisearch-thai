# Thai Tokenizer Sample Dataset

This directory contains comprehensive Thai text samples designed to test and demonstrate the Thai compound word tokenization capabilities of the MeiliSearch integration.

## Dataset Overview

### Files Structure
```
data/samples/
├── thai_documents.json      # General Thai documents (10 docs)
├── formal_documents.json    # Formal/official documents (5 docs)  
├── informal_documents.json  # Casual/social media style (5 docs)
├── test_queries.json        # Search test queries (25 queries)
├── combined_dataset.json    # Dataset metadata and statistics
└── README.md               # This documentation
```

## Document Categories

### 1. General Documents (`thai_documents.json`)
- **Technology**: AI, machine learning, digital transformation
- **Culture**: Thai food, traditions, cultural practices
- **Business**: Stock market, investment, startups
- **Travel**: Tourism, destinations, cultural sites
- **Health**: Digital health, wellness, medical technology
- **Education**: Online learning, educational technology
- **Environment**: Climate change, renewable energy
- **Sports**: Thai sports, athletes, competitions
- **Lifestyle**: Urban life, daily activities, mixed content

### 2. Formal Documents (`formal_documents.json`)
- **Legal**: Data protection law, regulations
- **Academic**: Research papers, scientific studies
- **Government**: National development plans, policies
- **Medical**: Clinical guidelines, treatment protocols
- **Technical**: Cybersecurity standards, technical specifications

### 3. Informal Documents (`informal_documents.json`)
- **Reviews**: Restaurant reviews, product reviews
- **Social**: Travel experiences, personal stories
- **Lifestyle**: Shopping, work-from-home experiences
- **Health**: Food trends, wellness practices

## Compound Word Patterns

### Types of Compound Words Tested
1. **Technical Terms**: `ปัญญาประดิษฐ์`, `การเรียนรู้ของเครื่อง`
2. **Cultural Terms**: `ต้มยำกุ้ง`, `วัฒนธรรมล้านนา`
3. **Business Terms**: `ตลาดหุ้น`, `การลงทุน`
4. **Location Names**: `เชียงใหม่`, `กรุงเทพฯ`
5. **Health Terms**: `การดูแลสุขภาพ`, `แอปพลิเคชันสุขภาพ`
6. **Mixed Content**: `Startup ไทย`, `Digital marketing`

### Difficulty Levels
- **Basic**: Simple compound words, common terms
- **Intermediate**: Complex compounds, cultural terms
- **Advanced**: Technical jargon, formal language, mixed content

## Test Queries (`test_queries.json`)

### Query Types
1. **Exact Compound**: Search for complete compound words
2. **Partial Compound**: Search for parts of compound words
3. **Mixed Language**: Thai-English mixed queries
4. **Technical Terms**: Specialized vocabulary
5. **Cultural Terms**: Thai-specific cultural concepts
6. **Fuzzy Search**: Approximate matching tests

### Search Scenarios
- Single compound word matching
- Multi-document relevance ranking
- Partial word matching
- Brand name recognition
- Abbreviation handling
- Cross-category searching

## Usage Examples

### 1. Loading Documents for Indexing
```python
import json

# Load general documents
with open('data/samples/thai_documents.json', 'r', encoding='utf-8') as f:
    general_docs = json.load(f)

# Load formal documents  
with open('data/samples/formal_documents.json', 'r', encoding='utf-8') as f:
    formal_docs = json.load(f)

# Combine all documents
all_documents = general_docs + formal_docs + informal_docs
```

### 2. Running Search Tests
```python
# Load test queries
with open('data/samples/test_queries.json', 'r', encoding='utf-8') as f:
    test_queries = json.load(f)

# Test compound word search
for query in test_queries:
    if query['search_type'] == 'exact_compound':
        # Test exact compound word matching
        results = search_engine.search(query['query'])
        # Validate against expected_results
```

### 3. Analyzing Compound Words
```python
# Extract compound words for analysis
compound_words = []
for doc in all_documents:
    if 'compound_words' in doc['metadata']:
        compound_words.extend(doc['metadata']['compound_words'])

# Analyze tokenization patterns
unique_compounds = list(set(compound_words))
print(f"Total unique compound words: {len(unique_compounds)}")
```

## Testing Scenarios

### 1. Basic Functionality Tests
- Document indexing with Thai content
- Simple compound word searches
- Result relevance validation

### 2. Advanced Feature Tests
- Mixed Thai-English content handling
- Partial compound word matching
- Cross-document relevance ranking
- Technical term recognition

### 3. Performance Tests
- Indexing speed with Thai documents
- Search response times
- Memory usage with large datasets
- Concurrent search handling

## Expected Outcomes

### Tokenization Accuracy
- Compound words should be properly segmented
- Word boundaries should be correctly identified
- Mixed content should be handled appropriately

### Search Relevance
- Exact matches should rank highest
- Partial matches should be relevant
- Cross-category searches should work
- Cultural terms should be recognized

### Performance Benchmarks
- Indexing: < 100ms per document
- Search: < 50ms per query
- Memory: < 256MB for full dataset
- Accuracy: > 90% for compound word recognition

## Troubleshooting

### Common Issues
1. **Encoding Problems**: Ensure UTF-8 encoding for all files
2. **Missing Compounds**: Check tokenizer configuration
3. **Poor Relevance**: Verify MeiliSearch settings
4. **Mixed Content Issues**: Validate language detection

### Validation Steps
1. Load and parse all JSON files successfully
2. Verify compound word metadata is complete
3. Test basic search functionality
4. Validate expected search results
5. Check performance benchmarks

## Contributing

To add new test cases:
1. Follow the existing JSON structure
2. Include comprehensive metadata
3. Add corresponding test queries
4. Update statistics in `combined_dataset.json`
5. Document any new compound word patterns

## License

This dataset is provided for testing and demonstration purposes as part of the Thai Tokenizer for MeiliSearch project.