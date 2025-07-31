# 📁 Scripts Directory

This directory is reserved for future utility scripts and tools for the Thai Tokenizer project.

## 📂 Current Structure

```
scripts/
└── README.md                    # This file
```

## 🎯 Design Philosophy

This directory follows the principle of organized project structure:

- ✅ **Reserved for utilities**: Future scripts and tools will go here
- ✅ **Keeps root clean**: Main functionality accessed via simple root wrappers
- ✅ **Logical organization**: Scripts grouped by function when added
- ✅ **Easy maintenance**: Clear location for project utilities

## 🚀 Current Usage

The main functionality is accessed via simple wrapper scripts in the project root:

```bash
# From project root
./setup_existing_meilisearch.sh        # Calls deployment/scripts/setup_existing_meilisearch.sh
python3 start_api_with_compounds.py    # Calls deployment/scripts/start_api_with_compounds.py
```

## 📚 Related Documentation

- **Quick Start**: `../QUICK_START.md`
- **Existing MeiliSearch Guide**: `../deployment/scripts/README_EXISTING_MEILISEARCH.md`
- **Project Structure**: `../docs/project/FILE_STRUCTURE.md`

## 🔮 Future Plans

This directory may contain:
- Development utilities
- Testing helpers
- Maintenance scripts
- Build tools