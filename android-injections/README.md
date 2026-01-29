# Android Injections

A Python-based game automation tool for Android devices that uses X11 screen capture and computer vision to automate interactions with mobile games.

## Features

- **X11 Window Capture**: Efficient screen capture using X11 composite extension
- **Computer Vision**: Color detection, blob analysis, and target recognition
- **Automated Clicking**: Intelligent touch simulation with configurable delays
- **Real-time UI**: Live display with overlay controls and state monitoring
- **Configuration Management**: Centralized game parameter management
- **Target Management**: Create and manage detection targets for game elements
- **OCR Integration**: XP tracking using Tesseract OCR
- **Stability Detection**: Temporal stability analysis for reliable automation

## Project Structure

```
android-injections/
├── src/
│   └── android_injections/
│       ├── __init__.py
│       ├── main.py                 # Main application class
│       ├── ui/                     # User interface components
│       │   ├── keyboard_handler.py
│       │   ├── mouse_handler.py
│       │   ├── ui_renderer.py
│       │   └── ui_state.py
│       ├── vision/                 # Computer vision modules
│       │   ├── color_filter.py
│       │   └── state_eval.py
│       ├── targeting/              # Target detection and management
│       │   ├── target_loader.py
│       │   ├── target_saver.py
│       │   ├── color_analysis.py
│       │   └── exclusion_manager.py
│       ├── automation/             # Automation logic
│       │   ├── auto_target.py
│       │   ├── delay_manager.py
│       │   └── state_manager.py
│       └── config/                 # Configuration
│           └── game_config.py
├── tests/                          # Test suite
│       ├── conftest.py
│       ├── test_config.py
│       ├── test_keyboard_handler.py
│       ├── test_vision.py
│       ├── test_targeting.py
│       ├── test_automation.py
│       └── ...
├── data/                           # Data files (not in version control)
│       ├── bounds/
│       ├── targets/
│       └── exclude/
├── pyproject.toml                  # Modern Python project configuration
├── requirements.txt                # Pip dependencies
├── README.md                       # This file
├── .gitignore                      # Git ignore rules
└── main.py                         # Entry point wrapper
```

## Installation

### Prerequisites

- Python 3.8+
- Linux with X11 (required for Xlib)
- Tesseract OCR (optional, for XP tracking)
- ADB (Android Debug Bridge)

### Setup

1. **Clone and enter directory**:
   ```bash
   git clone https://github.com/yourusername/android-injections.git
   cd android-injections
   ```

2. **Create virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install package in development mode**:
   ```bash
   pip install -e .
   ```

4. **Install optional development tools**:
   ```bash
   pip install -e ".[dev]"
   ```

## Usage

### Basic Usage

```bash
# Run from project root
python main.py --window "Pixel 4a (5G)" --fps 30 --scale 0.5

# Or use the installed command
android-injections --window "Pixel 4a (5G)"
```

### Command Line Arguments

- `--window`: Target window name (default: "Pixel 4a (5G)")
- `--fps`: Target FPS for capture loop (default: 30)
- `--scale`: Display scale factor (default: auto-detect)
- `--benchmark`: Enable benchmarking mode

### Configuration

Game parameters are centralized in `config/game_config.py`:

- **Touch delays**: `touch_delay_min`, `touch_delay_max`, `touch_delay_mean`, `touch_delay_std`
- **Stability**: `stability_timer`, `passing_distance`, `pass_pause_duration`
- **Detection**: `min_blob_pixels`, `max_blobs`, `colors_per_target`
- **Plane detection**: `plane_size`, `plane_count_padding`
- **XP tracking**: `xp_brightness_threshold`, `xp_sample_interval`

Modify these values in the config class or through the UI at runtime.

### Keyboard Controls

- **Editing mode**: Click fields to enable editing, type numbers, press Enter
- **Auto mode**: Toggle automatic clicking on/off
- **Target selection**: Choose which target to click
- **Color analysis**: Run color analysis on selection
- **Save/Load**: Persist and load configurations

## Testing

### Run All Tests

```bash
pytest
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# With coverage
pytest --cov=src/android_injections tests/
```

### Test Structure

- `test_config.py` - Configuration management
- `test_keyboard_handler.py` - Input handling
- `test_vision.py` - Computer vision modules
- `test_targeting.py` - Target detection and management
- `test_automation.py` - Automation logic
- `test_ui_renderer.py` - UI rendering
- `conftest.py` - Pytest fixtures and configuration

## Development

### Code Style

This project uses:
- **Black** for code formatting
- **isort** for import sorting
- **flake8** for linting
- **mypy** for type checking

Format and check code:

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Check style
flake8 src/ tests/

# Type check
mypy src/
```

### Adding New Tests

1. Create test file in `tests/test_*.py`
2. Use pytest fixtures from `conftest.py`
3. Mark tests with appropriate markers:
   ```python
   @pytest.mark.unit
   def test_something():
       pass
   
   @pytest.mark.integration
   def test_integration():
       pass
   ```

## Architecture

### Core Components

**GameConfig** - Centralized configuration management
- All game parameters in one place
- Supports runtime modification
- Integrates with keyboard handler for live updates

**AndroidWindowMirror** - Main application class
- Handles X11 window capture
- Manages rendering loop
- Coordinates all subsystems

**Automation Pipeline**
1. **Vision** - Detect colors and state
2. **Targeting** - Recognize game elements
3. **Selection** - Choose which target to click
4. **Delay** - Calculate realistic touch delay
5. **Execution** - Send ADB touch command

### Data Flow

```
X11 Capture → Vision Analysis → Target Detection → Auto Target Selection
                                                            ↓
                                              Delay Calculation & Stability Check
                                                            ↓
                                                  ADB Touch Execution
                                                            ↓
                                                UI Rendering with Overlays
```

## Performance Considerations

- Uses numpy and OpenCV for efficient image processing
- X11 composite extension for fast window capture
- Configurable FPS to balance responsiveness vs CPU usage
- Blob detection with configurable parameters

## Troubleshooting

### Window Not Found
```bash
# List available windows
python -c "from src.android_injections.main import AndroidWindowMirror; m = AndroidWindowMirror('test'); m.list_windows()"
```

### Import Errors
Ensure virtual environment is activated and package is installed in development mode:
```bash
source venv/bin/activate
pip install -e .
```

### OCR Not Working
Install Tesseract:
```bash
sudo apt-get install tesseract-ocr
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

MIT License - See LICENSE file for details

## Acknowledgments

- Tesseract OCR team
- OpenCV project
- Python Xlib developers

## Contact

For issues, questions, or suggestions, please open an issue on GitHub.
