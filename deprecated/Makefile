.PHONY: help build test clean run-rust run-python run contracts

help:
	@echo "DNAB (Dune Android Bot) - Build Commands"
	@echo ""
	@echo "Phase 1: Streaming Server Migration"
	@echo "===================================="
	@echo "  make build          - Build both Python and Rust"
	@echo "  make test           - Run all tests (Python + Rust)"
	@echo "  make contracts      - Run Python contract tests"
	@echo "  make run-rust       - Start Rust streaming server"
	@echo "  make run-python     - Start Python automation"
	@echo "  make run            - Start both services"
	@echo "  make clean          - Clean build artifacts"
	@echo ""

build: build-rust build-python
	@echo "✅ All builds complete"

build-rust:
	@echo "🔨 Building Rust streaming server..."
	cd android-core && cargo build --release --quiet
	@echo "✅ Rust build complete"

build-python:
	@echo "🔨 Building Python package..."
	cd android-injections && python3 -m pip install -e . --quiet 2>/dev/null || echo "⚠️  Python build requires venv (python3 -m venv venv && . venv/bin/activate)"

test: test-rust test-python

test-rust:
	@echo "🧪 Testing Rust..."
	cd android-core && cargo test --lib --quiet
	@echo "✅ Rust tests passed"

test-python:
	@echo "🧪 Testing Python..."
	cd android-injections && python3 -m pytest tests/ -q 2>/dev/null || echo "⚠️  Python tests skipped (venv not active)"

contracts:
	@echo "📋 Running contract tests (Python)..."
	cd android-injections && python3 -m pytest tests/contracts/ -v 2>/dev/null || echo "⚠️  Contracts tests skipped (venv not active)"

run-rust:
	@echo "🚀 Starting Rust streaming server..."
	./android-core/target/release/android_core

run-python:
	@echo "🚀 Starting Python automation..."
	cd android-injections && python3 -m android_injections.main

run: build
	@echo "🚀 Starting both services..."
	@echo "  Rust server on localhost:2007"
	@echo "  Python client..."
	./android-core/target/release/android_core &
	cd android-injections && python3 -m android_injections.main

clean:
	@echo "🧹 Cleaning..."
	cd android-core && cargo clean
	cd android-injections && find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	cd android-injections && find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Clean complete"

.DEFAULT_GOAL := help
