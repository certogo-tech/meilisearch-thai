# Thai Search Proxy Quality Tuning Guide

This guide helps optimize search quality for Thai language content.

## Table of Contents
- [Understanding Search Quality](#understanding-search-quality)
- [Tokenization Tuning](#tokenization-tuning)
- [Ranking Configuration](#ranking-configuration)
- [Custom Dictionary Management](#custom-dictionary-management)
- [Query Optimization](#query-optimization)
- [Result Analysis](#result-analysis)
- [A/B Testing](#ab-testing)

## Understanding Search Quality

### Key Metrics

1. **Precision**: Percentage of relevant results in returned set
2. **Recall**: Percentage of all relevant documents found
3. **F1 Score**: Harmonic mean of precision and recall
4. **MRR (Mean Reciprocal Rank)**: Average of reciprocal ranks of first relevant result
5. **NDCG (Normalized Discounted Cumulative Gain)**: Measures ranking quality

### Quality Indicators

```python
# Calculate search quality metrics
def calculate_metrics(search_results, relevant_docs):
    # Precision
    relevant_found = set(r['id'] for r in search_results) & set(relevant_docs)
    precision = len(relevant_found) / len(search_results) if search_results else 0
    
    # Recall
    recall = len(relevant_found) / len(relevant_docs) if relevant_docs else 0
    
    # F1 Score
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    return {
        "precision": precision,
        "recall": recall,
        "f1_score": f1
    }
```

## Tokenization Tuning

### 1. Choosing the Right Tokenizer

```yaml
# config/tokenizer.yaml
engines:
  newmm:
    enabled: true
    priority: 1
    use_cases:
      - general_text
      - mixed_content
    
  attacut:
    enabled: true
    priority: 2
    use_cases:
      - formal_documents
      - academic_papers
    
  deepcut:
    enabled: true
    priority: 3
    use_cases:
      - social_media
      - informal_text

# Domain-specific selection
domain_engines:
  academic: attacut
  social: deepcut
  general: newmm
```

### 2. Tokenizer Performance Comparison

```bash
# Test tokenizer accuracy
curl -X POST http://localhost:8000/api/v1/tokenize/compare \
  -H "Content-Type: application/json" \
  -d '{
    "text": "การเกษตรแบบยั่งยืนและเทคโนโลยีสมัยใหม่",
    "engines": ["newmm", "attacut", "deepcut"]
  }'
```

Expected output:
```json
{
  "results": {
    "newmm": {
      "tokens": ["การ", "เกษตร", "แบบ", "ยั่งยืน", "และ", "เทคโนโลยี", "สมัยใหม่"],
      "time_ms": 2.3
    },
    "attacut": {
      "tokens": ["การเกษตร", "แบบ", "ยั่งยืน", "และ", "เทคโนโลยี", "สมัยใหม่"],
      "time_ms": 15.7
    },
    "deepcut": {
      "tokens": ["การ", "เกษตร", "แบบ", "ยั่งยืน", "และ", "เทคโนโลยี", "สมัย", "ใหม่"],
      "time_ms": 45.2
    }
  }
}
```

### 3. Custom Tokenization Rules

```python
# src/tokenizer/custom_rules.py
class CustomTokenizationRules:
    def __init__(self):
        self.compound_patterns = [
            # Keep English acronyms together
            (r'[A-Z]{2,}', 'keep'),
            
            # Keep URLs intact
            (r'https?://[^\s]+', 'keep'),
            
            # Keep email addresses
            (r'[\w\.-]+@[\w\.-]+\.\w+', 'keep'),
            
            # Keep product codes
            (r'[A-Z0-9]{2,}-\d+', 'keep')
        ]
    
    def apply_pre_tokenization(self, text: str) -> str:
        """Apply rules before tokenization."""
        # Protect special patterns
        for pattern, action in self.compound_patterns:
            if action == 'keep':
                text = self._protect_pattern(text, pattern)
        
        return text
```

## Ranking Configuration

### 1. Base Ranking Weights

```yaml
# config/ranking.yaml
ranking_weights:
  # Field importance
  field_weights:
    title: 2.0
    abstract: 1.5
    content: 1.0
    keywords: 1.8
    authors: 0.8
  
  # Match type boosts
  match_type_boosts:
    exact_match: 2.0
    phrase_match: 1.5
    tokenized_match: 1.2
    fuzzy_match: 0.8
  
  # Position boosts
  position_boosts:
    title_start: 1.5
    sentence_start: 1.2
    paragraph_start: 1.1
```

### 2. Content-Type Specific Ranking

```python
# src/search_proxy/ranking/content_ranker.py
class ContentTypeRanker:
    def __init__(self):
        self.content_type_configs = {
            "research_paper": {
                "boost_recent": True,
                "recency_weight": 1.2,
                "citation_weight": 1.5,
                "author_reputation": 1.3
            },
            "news_article": {
                "boost_recent": True,
                "recency_weight": 2.0,
                "view_count_weight": 1.2,
                "engagement_weight": 1.1
            },
            "tutorial": {
                "boost_recent": False,
                "completeness_weight": 1.5,
                "rating_weight": 1.8,
                "update_frequency": 1.2
            }
        }
    
    def calculate_content_boost(self, document: Dict, content_type: str) -> float:
        config = self.content_type_configs.get(content_type, {})
        boost = 1.0
        
        if config.get("boost_recent") and self._is_recent(document):
            boost *= config.get("recency_weight", 1.0)
        
        # Apply other content-specific boosts
        return boost
```

### 3. Dynamic Ranking Adjustment

```bash
# Update ranking configuration via API
curl -X POST http://localhost:8000/api/v1/admin/ranking/update \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: admin-key" \
  -d '{
    "field_weights": {
      "title": 2.5,
      "abstract": 1.8
    },
    "boost_exact_matches": 2.2
  }'
```

## Custom Dictionary Management

### 1. Dictionary Structure

```json
{
  "version": "1.0",
  "language": "th",
  "domains": {
    "general": {
      "compounds": [
        "คอมพิวเตอร์",
        "อินเทอร์เน็ต",
        "สมาร์ทโฟน"
      ],
      "abbreviations": {
        "กทม.": "กรุงเทพมหานคร",
        "มทส.": "มหาวิทยาลัยเทคโนโลยีสุรนารี"
      }
    },
    "agriculture": {
      "compounds": [
        "สาหร่ายวากาเมะ",
        "เกษตรอินทรีย์",
        "ปุ๋ยชีวภาพ"
      ],
      "synonyms": {
        "ข้าว": ["ข้าวเปลือก", "ข้าวสาร", "ข้าวกล้อง"],
        "มะพร้าว": ["หัวมะพร้าว", "ผลมะพร้าว", "ลูกมะพร้าว"]
      }
    }
  }
}
```

### 2. Dictionary Validation

```python
# scripts/validate_dictionary.py
import json
import re
from typing import Dict, List

def validate_dictionary(dict_path: str) -> List[str]:
    """Validate custom dictionary format and content."""
    errors = []
    
    with open(dict_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Check required fields
    if 'version' not in data:
        errors.append("Missing 'version' field")
    
    # Validate compounds
    for domain, content in data.get('domains', {}).items():
        for compound in content.get('compounds', []):
            # Check for invalid characters
            if re.search(r'[^\u0E00-\u0E7F\w\s\-.]', compound):
                errors.append(f"Invalid characters in compound: {compound}")
            
            # Check minimum length
            if len(compound) < 2:
                errors.append(f"Compound too short: {compound}")
    
    return errors

# Run validation
errors = validate_dictionary('data/dictionaries/thai_compounds.json')
if errors:
    print("Dictionary validation failed:")
    for error in errors:
        print(f"  - {error}")
else:
    print("Dictionary validation passed!")
```

### 3. Dynamic Dictionary Updates

```bash
# Add new compound word
curl -X POST http://localhost:8000/api/v1/admin/dictionary/compound \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: admin-key" \
  -d '{
    "word": "โซลาร์เซลล์",
    "domain": "technology",
    "variations": ["โซล่าเซลล์", "แผงโซลาร์"]
  }'

# Add synonym group
curl -X POST http://localhost:8000/api/v1/admin/dictionary/synonym \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: admin-key" \
  -d '{
    "primary": "คอมพิวเตอร์",
    "synonyms": ["คอม", "พีซี", "เครื่องคอมพิวเตอร์"],
    "domain": "technology"
  }'
```

## Query Optimization

### 1. Query Expansion

```python
# src/search_proxy/query/expander.py
class QueryExpander:
    def __init__(self, synonym_dict: Dict):
        self.synonym_dict = synonym_dict
    
    def expand_query(self, query: str) -> List[str]:
        """Expand query with synonyms and variations."""
        tokens = self.tokenize(query)
        expanded_queries = [query]  # Original query
        
        # Add synonym variations
        for token in tokens:
            if token in self.synonym_dict:
                for synonym in self.synonym_dict[token]:
                    variant = query.replace(token, synonym)
                    expanded_queries.append(variant)
        
        # Add common variations
        expanded_queries.extend(self._generate_variations(query))
        
        return list(set(expanded_queries))
    
    def _generate_variations(self, query: str) -> List[str]:
        variations = []
        
        # Handle tone marks
        variations.append(self._remove_tone_marks(query))
        
        # Handle common misspellings
        variations.extend(self._common_misspellings(query))
        
        return variations
```

### 2. Query Intent Detection

```python
# src/search_proxy/query/intent.py
class QueryIntentDetector:
    def detect_intent(self, query: str) -> Dict[str, Any]:
        """Detect user's search intent."""
        
        intent = {
            "type": "unknown",
            "confidence": 0.0,
            "modifiers": []
        }
        
        # Question patterns
        question_patterns = {
            "how_to": r"(วิธี|อย่างไร|ยังไง|ทำอะไร)",
            "what_is": r"(คืออะไร|หมายถึง|หมายความว่า)",
            "why": r"(ทำไม|เพราะอะไร|สาเหตุ)",
            "when": r"(เมื่อไหร่|เมื่อไร|เวลาไหน)"
        }
        
        for intent_type, pattern in question_patterns.items():
            if re.search(pattern, query):
                intent["type"] = intent_type
                intent["confidence"] = 0.8
                break
        
        # Detect modifiers
        if "ล่าสุด" in query or "ใหม่" in query:
            intent["modifiers"].append("recent")
        
        if "ดีที่สุด" in query or "ยอดนิยม" in query:
            intent["modifiers"].append("popular")
        
        return intent
```

### 3. Query Rewriting

```python
# src/search_proxy/query/rewriter.py
class QueryRewriter:
    def rewrite_query(self, query: str, context: Dict = None) -> str:
        """Rewrite query for better search results."""
        
        # Remove stop words
        query = self._remove_stop_words(query)
        
        # Fix common typos
        query = self._fix_typos(query)
        
        # Apply domain-specific rules
        if context and context.get("domain"):
            query = self._apply_domain_rules(query, context["domain"])
        
        # Normalize spacing
        query = self._normalize_spacing(query)
        
        return query
    
    def _remove_stop_words(self, query: str) -> str:
        stop_words = {"ที่", "ของ", "และ", "หรือ", "แต่", "กับ"}
        tokens = query.split()
        return " ".join(t for t in tokens if t not in stop_words)
```

## Result Analysis

### 1. Search Quality Metrics Collection

```python
# src/analytics/quality_metrics.py
class SearchQualityAnalyzer:
    def analyze_search_session(self, session_data: Dict) -> Dict:
        """Analyze search quality from user session."""
        
        metrics = {
            "query": session_data["query"],
            "total_results": session_data["total_results"],
            "clicks": [],
            "dwell_times": [],
            "reformulations": []
        }
        
        # Analyze click-through rate
        if session_data["results_shown"] > 0:
            metrics["ctr"] = len(session_data["clicks"]) / session_data["results_shown"]
        
        # Analyze position of clicks
        for click in session_data["clicks"]:
            metrics["clicks"].append({
                "position": click["position"],
                "dwell_time": click["dwell_time"],
                "action": click["action"]  # view, download, share
            })
        
        # Calculate average reciprocal rank
        if metrics["clicks"]:
            first_click_position = metrics["clicks"][0]["position"]
            metrics["reciprocal_rank"] = 1.0 / first_click_position
        
        return metrics
```

### 2. Result Relevance Feedback

```bash
# Submit relevance feedback
curl -X POST http://localhost:8000/api/v1/feedback/relevance \
  -H "Content-Type: application/json" \
  -d '{
    "search_id": "550e8400-e29b-41d4-a716-446655440000",
    "query": "สาหร่ายวากาเมะ",
    "feedback": [
      {
        "document_id": "doc-123",
        "position": 1,
        "relevant": true,
        "rating": 5
      },
      {
        "document_id": "doc-456",
        "position": 2,
        "relevant": false,
        "rating": 2,
        "reason": "not_related"
      }
    ]
  }'
```

### 3. Quality Dashboard

```python
# Generate quality report
import pandas as pd
import matplotlib.pyplot as plt

def generate_quality_report(analytics_data: List[Dict]):
    """Generate search quality report."""
    
    df = pd.DataFrame(analytics_data)
    
    # Calculate metrics
    avg_ctr = df['ctr'].mean()
    avg_position = df['first_click_position'].mean()
    zero_result_rate = len(df[df['total_results'] == 0]) / len(df)
    
    # Popular failed queries
    failed_queries = df[df['total_results'] == 0]['query'].value_counts().head(10)
    
    # Create visualizations
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    # CTR distribution
    axes[0, 0].hist(df['ctr'], bins=20)
    axes[0, 0].set_title('Click-Through Rate Distribution')
    
    # Position of first click
    axes[0, 1].bar(range(1, 11), df['first_click_position'].value_counts().sort_index()[:10])
    axes[0, 1].set_title('First Click Position')
    
    # Query reformulation rate
    axes[1, 0].pie([df['reformulated'].sum(), len(df) - df['reformulated'].sum()],
                   labels=['Reformulated', 'Not Reformulated'])
    axes[1, 0].set_title('Query Reformulation Rate')
    
    # Top failed queries
    axes[1, 1].barh(failed_queries.index[:5], failed_queries.values[:5])
    axes[1, 1].set_title('Top Failed Queries')
    
    plt.tight_layout()
    plt.savefig('search_quality_report.png')
    
    return {
        "average_ctr": avg_ctr,
        "average_first_click_position": avg_position,
        "zero_result_rate": zero_result_rate,
        "top_failed_queries": failed_queries.to_dict()
    }
```

## A/B Testing

### 1. Configuration Setup

```yaml
# config/ab_testing.yaml
experiments:
  tokenizer_comparison:
    name: "Tokenizer Engine Comparison"
    status: "active"
    start_date: "2024-01-01"
    end_date: "2024-02-01"
    traffic_split:
      control: 0.5
      variant_a: 0.25  # AttaCut
      variant_b: 0.25  # DeepCut
    metrics:
      - click_through_rate
      - average_position_clicked
      - query_reformulation_rate
  
  ranking_boost_test:
    name: "Title Boost Optimization"
    status: "active"
    variants:
      control:
        title_boost: 2.0
      variant_a:
        title_boost: 2.5
      variant_b:
        title_boost: 3.0
```

### 2. Experiment Implementation

```python
# src/search_proxy/experiments/ab_test.py
class ABTestManager:
    def __init__(self, config_path: str):
        self.experiments = self._load_experiments(config_path)
        self.assignment_cache = {}
    
    def get_variant(self, user_id: str, experiment_name: str) -> str:
        """Assign user to experiment variant."""
        
        # Check cache
        cache_key = f"{user_id}:{experiment_name}"
        if cache_key in self.assignment_cache:
            return self.assignment_cache[cache_key]
        
        # Get experiment config
        experiment = self.experiments.get(experiment_name)
        if not experiment or experiment["status"] != "active":
            return "control"
        
        # Deterministic assignment based on user ID
        hash_value = int(hashlib.md5(cache_key.encode()).hexdigest(), 16)
        normalized = (hash_value % 100) / 100.0
        
        # Assign to variant
        cumulative = 0.0
        for variant, split in experiment["traffic_split"].items():
            cumulative += split
            if normalized <= cumulative:
                self.assignment_cache[cache_key] = variant
                return variant
        
        return "control"
    
    def apply_variant_config(self, base_config: Dict, variant: str, experiment: str) -> Dict:
        """Apply variant-specific configuration."""
        
        variant_config = self.experiments[experiment]["variants"].get(variant, {})
        
        # Merge configurations
        updated_config = base_config.copy()
        updated_config.update(variant_config)
        
        return updated_config
```

### 3. Results Analysis

```python
# Analyze A/B test results
from scipy import stats

def analyze_ab_test(control_data: List[float], variant_data: List[float]) -> Dict:
    """Analyze A/B test results for statistical significance."""
    
    # Calculate basic statistics
    control_mean = np.mean(control_data)
    variant_mean = np.mean(variant_data)
    
    # Perform t-test
    t_stat, p_value = stats.ttest_ind(control_data, variant_data)
    
    # Calculate confidence interval
    diff_mean = variant_mean - control_mean
    diff_std = np.sqrt(np.var(control_data)/len(control_data) + 
                       np.var(variant_data)/len(variant_data))
    ci_lower = diff_mean - 1.96 * diff_std
    ci_upper = diff_mean + 1.96 * diff_std
    
    # Calculate lift
    lift = (variant_mean - control_mean) / control_mean * 100
    
    return {
        "control_mean": control_mean,
        "variant_mean": variant_mean,
        "lift_percentage": lift,
        "p_value": p_value,
        "significant": p_value < 0.05,
        "confidence_interval": (ci_lower, ci_upper)
    }

# Example usage
results = analyze_ab_test(
    control_data=[0.12, 0.15, 0.11, ...],  # CTR data
    variant_data=[0.18, 0.20, 0.16, ...]
)

print(f"Lift: {results['lift_percentage']:.1f}%")
print(f"Significant: {results['significant']}")
```

## Best Practices

### 1. Continuous Monitoring

```bash
# Set up monitoring script
#!/bin/bash
# monitor_quality.sh

while true; do
    # Get current metrics
    metrics=$(curl -s http://localhost:8000/api/v1/metrics/quality)
    
    # Check thresholds
    ctr=$(echo $metrics | jq -r '.average_ctr')
    if (( $(echo "$ctr < 0.1" | bc -l) )); then
        echo "ALERT: Low CTR detected: $ctr"
        # Send alert
    fi
    
    sleep 300  # Check every 5 minutes
done
```

### 2. Regular Dictionary Updates

```python
# Weekly dictionary update script
import requests
from datetime import datetime

def update_dictionary_weekly():
    """Update dictionary with new terms from search logs."""
    
    # Get frequently searched but no-result queries
    response = requests.get(
        "http://localhost:8000/api/v1/analytics/no-result-queries",
        params={"days": 7, "min_count": 5}
    )
    
    candidates = response.json()["queries"]
    
    # Review and add to dictionary
    for query in candidates:
        if is_valid_compound(query):
            add_to_dictionary(query)
    
    print(f"Dictionary updated on {datetime.now()}")
```

### 3. Quality Checklist

- [ ] Monitor CTR weekly (target: >15%)
- [ ] Review zero-result queries weekly
- [ ] Update custom dictionary monthly
- [ ] A/B test ranking changes
- [ ] Collect user feedback regularly
- [ ] Analyze query reformulation patterns
- [ ] Check tokenization accuracy quarterly
- [ ] Review and adjust boost factors
- [ ] Validate synonym mappings
- [ ] Performance test after changes

## Troubleshooting Poor Results

### Common Issues and Solutions

1. **Too Many Irrelevant Results**
   - Increase minimum score threshold
   - Adjust fuzzy match penalties
   - Review and update stop words

2. **Missing Obvious Results**
   - Check tokenization of query
   - Verify compound words in dictionary
   - Review synonym mappings

3. **Poor Ranking of Results**
   - Analyze click positions
   - Adjust field weights
   - Review content type boosts

4. **Slow Search Performance**
   - Enable query caching
   - Optimize tokenizer selection
   - Reduce max results limit