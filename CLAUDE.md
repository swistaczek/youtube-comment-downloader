# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

youtube-comment-downloader is a Python library and command-line tool for downloading YouTube comments without using the YouTube API. It outputs comments in line-delimited JSON format and can be used both as a CLI tool and as a Python library.

## Development Environment Setup

The project uses `mise` for environment management. Key commands:

```bash
# Install project dependencies
mise run install

# Install development dependencies (includes testing dependencies and editable install)
mise run install-dev

# Run tests
mise run test

# Run linting checks
mise run lint

# Clean build artifacts
mise run clean
```

## Testing

The project uses **pytest with VCR.py** for testing, which records and replays HTTP interactions to enable fast, reliable, offline testing.

### Test Infrastructure

- **VCR.py with pytest-recording**: Records real YouTube API responses to YAML cassettes
- **pytest-cov**: Code coverage reporting
- **pytest-timeout**: Prevents hanging tests
- **freezegun**: Mock datetime for consistent timestamps

### Running Tests

```bash
# Run all tests using existing cassettes (default)
pytest

# Run tests with coverage
pytest --cov=youtube_comment_downloader --cov-report=html

# Run specific test file
pytest tests/test_downloader.py

# Run tests in strict mode (no network access)
pytest --record-mode=none --block-network

# Run benchmarks only
pytest tests/test_search_dict.py --benchmark-only
```

### VCR Recording Modes

```bash
# Use existing cassettes, record new ones if missing (default)
pytest --record-mode=once

# Never record, fail if cassette missing (CI mode)
pytest --record-mode=none --block-network

# Always create new cassettes (refresh mode)
pytest --record-mode=rewrite

# Record new interactions only
pytest --record-mode=new_episodes
```

### Cassette Management

```bash
# Check cassette age
python tests/scripts/refresh_cassettes.py --check-age

# Refresh ALL cassettes
python tests/scripts/refresh_cassettes.py --all

# Refresh specific test cassettes
python tests/scripts/refresh_cassettes.py --test test_get_comments_basic

# Verify cassettes work in strict mode
python tests/scripts/refresh_cassettes.py --verify
```

### Test Markers

- `@pytest.mark.vcr`: Test uses VCR for HTTP recording
- `@pytest.mark.network`: Test may require network for recording
- `@pytest.mark.slow`: Test takes more than a few seconds
- `@pytest.mark.block_network`: Ensures no network access

### Cassette Storage

Cassettes are stored in `tests/cassettes/` organized by test module:
```
tests/cassettes/
├── test_downloader/
│   ├── test_get_comments_basic.yaml
│   └── test_comment_sorting_popular.yaml
└── test_cli/
    └── test_main_with_youtube_id.yaml
```

### CI/CD Integration

- **GitHub Actions** runs tests in strict mode (no network access)
- Monthly workflow refreshes cassettes automatically
- Coverage reports uploaded to Codecov
- Test matrix: Python 3.8-3.11 on Ubuntu, Windows, macOS

## Architecture

### Core Components

1. **YoutubeCommentDownloader class** (`youtube_comment_downloader/downloader.py`):
   - Main class handling YouTube interaction
   - Key methods:
     - `get_comments(youtube_id, ...)` - Download comments using video ID
     - `get_comments_from_url(youtube_url, ...)` - Download comments using URL
     - `ajax_request()` - Handle YouTube API requests with retries
     - `search_dict()` - Recursive dictionary search utility
   - Manages session, cookies, and proxy configuration
   - Handles YouTube consent flow automatically

2. **CLI Interface** (`youtube_comment_downloader/__init__.py`):
   - Implements `main()` function for command-line usage
   - Handles argument parsing, output formatting (JSON/pretty JSON)
   - Progress reporting during download
   - Creates output directories if needed

3. **Data Flow**:
   - Initial page request extracts `ytcfg` (YouTube configuration) and `ytInitialData`
   - Comments are fetched via continuation tokens through AJAX requests
   - Each response may contain multiple comment payloads and continuation tokens
   - Comments are yielded as they're processed (generator pattern)

### Key Implementation Details

- **Cookie Consent**: Automatically handles YouTube's cookie consent page
- **Proxy Support**: HTTPS proxy configuration via session object
- **Retry Logic**: Built-in retry mechanism with configurable sleep intervals
- **Comment Sorting**: Supports both popular (0) and recent (1) comment sorting
- **Language Support**: Can specify language for YouTube-generated text
- **Payment Detection**: Identifies and includes paid comment information
- **Heart/Reply Status**: Tracks creator hearts and reply status

## Building and Distribution

```bash
# Build package
python -m build

# Install in editable mode for development
pip install -e .

# Run the CLI directly
python -m youtube_comment_downloader --help
```

## Entry Points

- CLI: `youtube-comment-downloader` command (registered via setup.cfg)
- Module: `python -m youtube_comment_downloader`
- Library: `from youtube_comment_downloader import YoutubeCommentDownloader`

## Dependencies

Production:
- `dateparser` - For parsing YouTube timestamp strings
- `requests` - HTTP client for YouTube requests

Development:
- `pytest` - Test framework
- `pytest-benchmark` - Performance testing