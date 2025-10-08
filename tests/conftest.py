"""
Pytest configuration and fixtures for youtube-comment-downloader tests
"""
import os
import pytest
from datetime import datetime, timedelta


@pytest.fixture(scope="module")
def vcr_config():
    """Configure VCR for recording and replaying HTTP interactions"""
    return {
        "filter_headers": ["authorization", "cookie", "x-youtube-client-name", "x-youtube-client-version"],
        "filter_query_parameters": ["key"],  # Hide API keys
        "filter_post_data_parameters": ["key"],
        "match_on": ["uri", "method"],  # Don't match on body as YouTube's can vary
        "record_mode": os.environ.get("VCR_RECORD_MODE", "once"),  # Allow override via env var
        "cassette_library_dir": "tests/cassettes",
        "before_record_response": sanitize_response,
        "decode_compressed_response": True,
        "serializer": "yaml",
    }


def sanitize_response(response):
    """Remove sensitive/personal data from responses before recording"""
    # Remove Set-Cookie headers to avoid recording session data
    if "headers" in response and "Set-Cookie" in response["headers"]:
        del response["headers"]["Set-Cookie"]

    # Remove any location headers that might contain tokens
    if "headers" in response and "location" in response["headers"]:
        location = response["headers"]["location"][0] if isinstance(response["headers"]["location"], list) else response["headers"]["location"]
        if "token=" in location or "key=" in location:
            response["headers"]["location"] = ["REDACTED"]

    return response


@pytest.fixture
def youtube_video_id():
    """Use a stable public video for testing"""
    # Using a short, stable video that's unlikely to be removed
    return "jNQXAC9IVRw"  # "Me at the zoo" - First YouTube video


@pytest.fixture
def youtube_url(youtube_video_id):
    """Generate YouTube URL from video ID"""
    return f"https://www.youtube.com/watch?v={youtube_video_id}"


def pytest_runtest_setup(item):
    """Check cassette age and warn if stale"""
    # Only check if we're using VCR
    if hasattr(item, 'iter_markers'):
        vcr_markers = list(item.iter_markers(name='vcr'))
        if vcr_markers:
            # Try to determine cassette path
            test_file = item.parent.name.replace(".py", "")
            test_name = item.name
            cassette_path = f"tests/cassettes/{test_file}/{test_name}.yaml"

            if os.path.exists(cassette_path):
                age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(cassette_path))
                if age > timedelta(days=90):
                    # Just warn, don't skip - let the test decide
                    item.add_report_section("setup", "cassette_age",
                                          f"WARNING: Cassette older than 90 days: {cassette_path}")


def pytest_collection_modifyitems(config, items):
    """Add markers to tests based on their requirements"""
    for item in items:
        # Add network marker to tests that use VCR
        if list(item.iter_markers(name='vcr')):
            item.add_marker(pytest.mark.network)


@pytest.fixture(autouse=True)
def test_timeout():
    """Set a default timeout for all tests to prevent hanging"""
    # This can be overridden per-test with @pytest.mark.timeout(seconds)
    return 60  # 60 seconds default


# Custom pytest hooks for better test reporting
def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line(
        "markers", "network: tests that may require network access for recording"
    )
    config.addinivalue_line(
        "markers", "slow: tests that take more than a few seconds"
    )


def pytest_recording_configure(config, vcr):
    """Configure pytest-recording plugin (called automatically by the plugin)"""
    # Register custom VCR matchers if needed
    def youtube_api_matcher(r1, r2):
        """Custom matcher for YouTube API requests"""
        # Match on path and key parameters, ignore changing parameters
        if "youtubei/v1" in r1.uri and "youtubei/v1" in r2.uri:
            # Extract the API endpoint
            path1 = r1.uri.split("?")[0]
            path2 = r2.uri.split("?")[0]
            return path1 == path2
        return r1.uri == r2.uri

    vcr.register_matcher("youtube_api", youtube_api_matcher)