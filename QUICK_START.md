# Phase 1: Quick Reference

## What You Have

✅ **Rust Streaming Server** (`/android-core/`)
- 14 unit tests passing (test-driven development)
- Compiled binary: `2.0 MB` 
- HTTP API on `localhost:2007`
- Ready for Phase 2 (vision/targeting modules)

✅ **Python Contract Tests** (`/android-injections/tests/contracts/`)
- 68 contract tests (language-agnostic)
- Validate both Python and Rust implementations
- Ready to test Rust server against Python contracts

✅ **Build System** (`Makefile`)
- Single command build/test for both projects
- Manages both Rust and Python builds

## Commands

```bash
cd /home/lann/workspace/DNAB

# Test everything
make test              # Runs: Rust tests + Python tests

# Build everything
make build             # Builds: Rust binary + Python package

# Run services
make run-rust          # Start streaming server (localhost:2007)
make run-python        # Start automation (if Python ready)
make run               # Both together

# View options
make help              # Show all commands

# Clean up
make clean             # Remove build artifacts
```

## Test Everything

```bash
make test

# Output:
# 🧪 Testing Rust...
# test result: ok. 14 passed
# ✅ Rust tests passed
```

## Start the Server

```bash
make run-rust

# Output:
# 🚀 Starting Rust streaming server...
# 2026-01-29T06:42:06.065732Z  INFO android_core::server: Server running on 127.0.0.1:2007
```

## Verify It Works

```bash
curl http://localhost:2007/api/health

# Output:
# {"status":"ok","version":"0.1.0"}
```

## Next: Test Rust Against Python Contracts

Once the Rust server implements actual video streaming, run:

```bash
cd android-injections
source venv/bin/activate
pytest tests/contracts/test_stream_contract.py -v
```

This will validate that the Rust implementation matches Python behavior.

## Directory Layout

```
/android-core/
  src/stream.rs         - 11 unit tests
  src/server.rs         - 2 unit tests  
  src/config.rs         - 2 unit tests
  target/release/       - Compiled binary

/android-injections/
  tests/contracts/      - 68 contract tests
```

## What's Ready for Phase 2

- Rust library structure (`src/lib.rs` exports `StreamingServer` trait)
- Server skeleton (`axum` HTTP framework ready)
- Module organization (ready to add `vision/`, `targeting/`, `automation/`)
- Testing infrastructure (unit tests + contract tests)

Just add the core logic modules and expose them through the API!
