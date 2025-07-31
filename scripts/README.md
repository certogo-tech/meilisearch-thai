# 📁 Scripts Directory

This directory contains utility scripts and wrappers for the Thai Tokenizer project.

## 📂 Directory Structure

```
scripts/
├── README.md                    # This file
└── wrappers/                    # Wrapper scripts (called from root)
    ├── setup_existing_meilisearch.sh    # Setup for existing MeiliSearch
    └── start_api_with_compounds.py      # API startup with compounds
```

## 🔧 Wrapper Scripts

### `wrappers/setup_existing_meilisearch.sh`
Sets up Thai Tokenizer integration with existing MeiliSearch instances.

**Called from root via**: `./setup_existing_meilisearch.sh`

**What it does**:
- Verifies compound dictionary (32 entries)
- Creates environment configuration
- Tests MeiliSearch connectivity
- Starts Thai Tokenizer service
- Validates compound word tokenization

### `wrappers/start_api_with_compounds.py`
Starts the Thai Tokenizer API with compound word support for development.

**Called from root via**: `python3 start_api_with_compounds.py`

**What it does**:
- Loads compound dictionary
- Starts FastAPI server
- Enables compound word tokenization
- Provides development-friendly logging

## 🎯 Design Philosophy

The wrapper scripts in this directory are called by simple wrapper scripts in the project root. This design:

- ✅ **Keeps root clean**: Only essential files in root directory
- ✅ **Maintains compatibility**: Existing commands still work
- ✅ **Organizes logically**: Scripts grouped by function
- ✅ **Enables maintenance**: Easy to find and update scripts

## 🚀 Usage

All scripts are designed to be called from the project root directory:

```bash
# From project root
./setup_existing_meilisearch.sh        # Calls scripts/wrappers/setup_existing_meilisearch.sh
python3 start_api_with_compounds.py    # Calls scripts/wrappers/start_api_with_compounds.py
```

## 📚 Related Documentation

- **Quick Start**: `../QUICK_START.md`
- **Existing MeiliSearch Guide**: `../deployment/scripts/README_EXISTING_MEILISEARCH.md`
- **Project Structure**: `../docs/project/FILE_STRUCTURE.md`