# 📁 Scripts Directory

This directory contains utility scripts and wrappers for the Thai Tokenizer project.

## 📂 Current Structure

```
scripts/
├── README.md                           # This file
├── setup_existing_meilisearch.sh       # Setup wrapper for existing MeiliSearch
└── start_api_with_compounds.py         # Development API wrapper
```

## 🎯 Design Philosophy

This directory follows the principle of organized project structure:

- ✅ **Centralized scripts**: All user-facing scripts in one location
- ✅ **Clean root**: Keeps root directory minimal
- ✅ **Easy access**: Available via Make commands or direct calls
- ✅ **Logical organization**: Scripts grouped by function

## 🚀 Usage

### Via Make Commands (Recommended)
```bash
make setup-existing    # Setup with existing MeiliSearch
make start-dev         # Start development API
make help             # Show all available commands
```

### Direct Script Calls
```bash
bash scripts/setup_existing_meilisearch.sh     # Setup existing MeiliSearch
python3 scripts/start_api_with_compounds.py    # Start development API
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