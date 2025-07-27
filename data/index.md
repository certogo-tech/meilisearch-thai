# Data Directory

This directory contains sample data, test fixtures, and data-related resources for the Thai Tokenizer MeiliSearch integration system.

## 📁 Directory Structure

```
data/
├── samples/           # Sample Thai documents and test data
│   ├── README.md     # Sample data documentation
│   ├── thai_documents.json
│   ├── formal_documents.json
│   ├── informal_documents.json
│   └── test_queries.json
├── meilisearch/      # MeiliSearch data directory (created at runtime)
├── snapshots/        # MeiliSearch snapshots (created at runtime)
└── dumps/           # MeiliSearch dumps (created at runtime)
```

## 📊 Sample Data

### [Thai Text Samples](samples/)
The `samples/` directory contains carefully curated Thai text data for testing and demonstration:

- **[thai_documents.json](samples/thai_documents.json)** - General Thai documents covering various topics
- **[formal_documents.json](samples/formal_documents.json)** - Formal Thai text (news, academic, official)
- **[informal_documents.json](samples/informal_documents.json)** - Informal Thai text (social media, chat, casual)
- **[test_queries.json](samples/test_queries.json)** - Search queries for testing and validation

### Sample Data Features
- **Diverse Content**: Covers technology, education, health, automotive, and general topics
- **Mixed Languages**: Includes Thai-English mixed content for real-world scenarios
- **Compound Words**: Focuses on Thai compound words that are challenging for tokenization
- **Difficulty Levels**: Ranges from simple to complex Thai text patterns
- **Metadata Rich**: Includes categories, tags, difficulty levels, and content analysis

## 🚀 Usage

### For Development
```bash
# Load sample data into MeiliSearch
python deployment/scripts/setup_demo.py

# Run search comparisons with sample data
python deployment/scripts/compare_results.py

# Benchmark performance with sample data
python deployment/scripts/benchmark.py
```

### For Testing
```bash
# Run tests with sample data
pytest tests/ -v

# Test specific scenarios
pytest tests/integration/test_sample_data.py -v
```

### For API Testing
```bash
# Test tokenization with sample text
curl -X POST http://localhost:8000/api/v1/tokenize \
  -H "Content-Type: application/json" \
  -d '{"text": "เทคโนโลยีสารสนเทศและการสื่อสาร"}'

# Test document processing
curl -X POST http://localhost:8000/api/v1/documents/process \
  -H "Content-Type: application/json" \
  -d @data/samples/thai_documents.json
```

## 🔧 Runtime Data Directories

### MeiliSearch Data
- **meilisearch/**: Main MeiliSearch data directory (auto-created)
- **snapshots/**: MeiliSearch snapshots for backup/restore
- **dumps/**: MeiliSearch data dumps for migration

These directories are created automatically when the system runs and are managed by MeiliSearch and Docker volumes.

## 📝 Adding New Sample Data

To add new sample data:

1. **Create JSON files** following the existing schema:
   ```json
   [
     {
       "id": "unique_id",
       "title": "Document Title",
       "content": "Thai text content...",
       "category": "technology",
       "tags": ["tag1", "tag2"],
       "metadata": {
         "difficulty": "medium",
         "mixed_content": true
       }
     }
   ]
   ```

2. **Update test queries** in `test_queries.json`:
   ```json
   [
     {
       "query": "search term",
       "description": "What this query tests",
       "expected_results": ["doc_id1", "doc_id2"]
     }
   ]
   ```

3. **Run validation**:
   ```bash
   python deployment/scripts/setup_demo.py
   python deployment/scripts/compare_results.py
   ```

4. **Update documentation** to reflect new data

## 🎯 Data Guidelines

### Content Quality
- Use authentic Thai text from diverse sources
- Include proper Thai grammar and vocabulary
- Cover various domains and topics
- Test edge cases and challenging scenarios

### Metadata Standards
- **Categories**: technology, education, health, automotive, general
- **Difficulty**: easy, medium, hard, expert
- **Content Types**: formal, informal, mixed, technical
- **Language Mix**: thai_only, mixed_thai_english, multilingual

### File Organization
- Keep files focused on specific content types
- Use descriptive filenames
- Maintain consistent JSON schema
- Include comprehensive metadata

## 📚 Related Documentation

- **[Sample Data Guide](samples/README.md)** - Detailed sample data documentation
- **[Development Guide](../docs/development/README.md)** - Using sample data in development
- **[API Documentation](../docs/api/index.md)** - API endpoints for data processing
- **[Deployment Scripts](../deployment/scripts/README.md)** - Scripts that use sample data

## 🤝 Contributing Sample Data

We welcome contributions of high-quality Thai text samples:

1. Follow the data guidelines above
2. Ensure content is appropriate and copyright-free
3. Include proper metadata and categorization
4. Test with the existing system
5. Submit a pull request with documentation updates

---

**Ready to work with the data?** Check out the [Sample Data Guide](samples/README.md) for detailed usage instructions!