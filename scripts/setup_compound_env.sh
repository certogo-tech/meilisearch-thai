#!/bin/bash
# Setup script for Thai compound tokenization

echo "🚀 Setting up Thai Compound Tokenization"

# Set environment variables
export THAI_TOKENIZER_CUSTOM_DICTIONARY_PATH="data/dictionaries/thai_compounds.json"
export THAI_TOKENIZER_TOKENIZER_HANDLE_COMPOUNDS="true"
export THAI_TOKENIZER_TOKENIZER_ENGINE="newmm"
export THAI_TOKENIZER_DEBUG="true"

echo "✅ Environment variables set:"
echo "  - Custom dictionary: $THAI_TOKENIZER_CUSTOM_DICTIONARY_PATH"
echo "  - Compound handling: $THAI_TOKENIZER_TOKENIZER_HANDLE_COMPOUNDS"
echo "  - Engine: $THAI_TOKENIZER_TOKENIZER_ENGINE"

# Check if dictionary file exists
if [ -f "$THAI_TOKENIZER_CUSTOM_DICTIONARY_PATH" ]; then
    echo "✅ Compound dictionary found"
    echo "  - Dictionary entries: $(cat $THAI_TOKENIZER_CUSTOM_DICTIONARY_PATH | jq '[.[]] | flatten | length')"
else
    echo "❌ Compound dictionary not found at: $THAI_TOKENIZER_CUSTOM_DICTIONARY_PATH"
fi

echo ""
echo "🔧 To use these settings in your current shell:"
echo "  source scripts/setup_compound_env.sh"
echo ""
echo "🧪 To test the integration:"
echo "  python3 examples/compound_tokenization.py"
