# Repository Restructuring - Migration Guide

## What Changed

This document explains the reorganization of the Android Injections repository to follow Python best practices (PEP 517/518).

### Before
```
android-injections/
├── main.py
├── ui/
├── vision/
├── targeting/
├── automation/
├── config/
├── bounds/
├── targets/
├── exclude/
└── tests/
```

### After
```
android-injections/
├── src/
│   └── android_injections/
│       ├── __init__.py
│       ├── main.py
│       ├── ui/
│       ├── vision/
│       ├── targeting/
│       ├── automation/
│       └── config/
├── tests/                    # Enhanced test suite
├── data/
│   ├── bounds/
│   ├── targets/
│   └── exclude/
├── pyproject.toml           # New - Modern project config
├── requirements.txt         # New - Dependencies
├── README.md               # Enhanced documentation
├── .gitignore              # New - Git ignore rules
└── main.py                 # Wrapper script
```

## Key Improvements

### 1. **PEP 517/518 Compliance**
- Added `pyproject.toml` with full project metadata
- Proper package discovery and installation configuration
- Supports `pip install -e .` for development mode

### 2. **Proper Python Packaging**
- All code now in `src/android_injections/` package
- Proper `__init__.py` files for all modules
- Installable as a standard Python package
- Clear separation of source code from data

### 3. **Enhanced Testing**
- Comprehensive test suite in `tests/` directory
- 43 new integration and import tests
- Pytest fixtures and configuration in `conftest.py`
- Test categories: unit, integration, slow

### 4. **Data Organization**
- Game data now in dedicated `data/` folder
- Separate subdirectories: `bounds/`, `targets/`, `exclude/`
- Data files are not in version control (see `.gitignore`)

### 5. **Documentation**
- Comprehensive README.md with:
  - Feature overview
  - Installation instructions
  - Usage examples
  - Architecture documentation
  - Contributing guidelines
- Project metadata in pyproject.toml

### 6. **Dependency Management**
- `requirements.txt` for pip installations
- Optional development dependencies
- Clear version specifications

## Migration for Users

### If You Were Cloning the Repo

**Before:**
```bash
cd android-injections
python3 main.py --window "Pixel 4a (5G)"
```

**After:**
```bash
cd android-injections
pip install -e .
python3 main.py --window "Pixel 4a (5G)"
```

Or directly:
```bash
python3 -m pytest              # Run tests
python3 main.py                # Run application
```

### If You Had Custom Imports

**Before:**
```python
from ui.keyboard_handler import process_keyboard_event
from config.game_config import GameConfig
```

**After:**
```python
from android_injections.ui.keyboard_handler import process_keyboard_event
from android_injections.config.game_config import GameConfig
```

### If You Stored Data Files

Your data files have moved:
- `bounds/*.json` → `data/bounds/*.json`
- `targets/*.json` → `data/targets/*.json`
- `exclude/*.json` → `data/exclude/*.json`

The application automatically looks for these in the new location.

## Development Workflow

### Setup
```bash
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

### Run Tests
```bash
pytest                          # Run all tests
pytest -m unit                  # Run unit tests only
pytest --cov=src/android_injections  # With coverage
```

### Code Quality
```bash
black src/ tests/              # Format code
isort src/ tests/              # Sort imports
flake8 src/ tests/             # Lint
mypy src/                       # Type check
```

## Backward Compatibility

The wrapper `main.py` at the root ensures the application can still be run the same way:
```bash
python3 main.py --window "Pixel 4a (5G)"
```

## File Locations

| Type | Old Location | New Location |
|------|------|------|
| Source Code | `ui/`, `config/`, etc. | `src/android_injections/ui/`, etc. |
| Data Files | `bounds/`, `targets/`, `exclude/` | `data/bounds/`, `data/targets/`, `data/exclude/` |
| Tests | `tests/` | `tests/` (expanded) |
| Config | None | `pyproject.toml` |
| Dependencies | None | `requirements.txt` |

## Testing

The restructuring includes comprehensive tests to ensure everything still works:

### Import Tests (14 tests)
- Verify all modules can be imported
- Check for circular imports
- Validate package structure

### Config Integration Tests (29 tests)
- GameConfig initialization
- Parameter modification
- Bounds checking
- Update field from input
- Integration with keyboard handler

**All 43 tests pass! ✅**

## Next Steps

1. **If you're a user**: Just use the application normally with the new structure
2. **If you're a developer**: Run `pip install -e ".[dev]"` and use the new test suite
3. **If you're contributing**: Follow the development workflow above

## Questions?

See:
- `README.md` for full documentation
- `pyproject.toml` for configuration details
- `tests/` directory for test examples

