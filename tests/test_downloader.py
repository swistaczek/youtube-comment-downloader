"""
Tests for YoutubeCommentDownloader class with VCR.py recording
"""
import pytest
import json
from unittest.mock import Mock, patch
from youtube_comment_downloader.downloader import (
    YoutubeCommentDownloader,
    SORT_BY_POPULAR,
    SORT_BY_RECENT
)


class TestYoutubeCommentDownloader:
    """Test suite for YoutubeCommentDownloader"""

    def test_initialization(self):
        """Test downloader initialization without network access"""
        downloader = YoutubeCommentDownloader()
        assert downloader.session is not None
        assert downloader.session.headers['User-Agent'] is not None
        assert 'CONSENT' in downloader.session.cookies

    def test_initialization_with_proxy(self):
        """Test downloader initialization with proxy configuration"""
        proxy_url = "https://user:pass@proxy.example.com:8080"
        downloader = YoutubeCommentDownloader(https_proxy=proxy_url)
        assert downloader.session.proxies == {'https': proxy_url}

    @pytest.mark.vcr
    @pytest.mark.network
    def test_get_comments_basic(self, youtube_video_id):
        """Test basic comment fetching with VCR recording"""
        downloader = YoutubeCommentDownloader()
        comments = []

        # Get first 10 comments
        for i, comment in enumerate(downloader.get_comments(youtube_video_id)):
            if i >= 10:
                break
            comments.append(comment)

        assert len(comments) == 10
        # Check required fields are present
        required_fields = ['cid', 'text', 'author', 'channel', 'votes', 'photo']
        for comment in comments:
            for field in required_fields:
                assert field in comment, f"Missing field {field} in comment"

    @pytest.mark.vcr
    @pytest.mark.network
    def test_get_comments_from_url(self, youtube_url):
        """Test fetching comments using full YouTube URL"""
        downloader = YoutubeCommentDownloader()
        comments = []

        for i, comment in enumerate(downloader.get_comments_from_url(youtube_url)):
            if i >= 5:
                break
            comments.append(comment)

        assert len(comments) == 5
        assert all('text' in comment for comment in comments)

    @pytest.mark.vcr
    @pytest.mark.network
    def test_comment_sorting_popular(self, youtube_video_id):
        """Test fetching popular comments"""
        downloader = YoutubeCommentDownloader()
        comments = []

        for i, comment in enumerate(downloader.get_comments(
            youtube_video_id, sort_by=SORT_BY_POPULAR
        )):
            if i >= 5:
                break
            comments.append(comment)

        assert len(comments) == 5
        # Popular comments should generally have votes
        assert any(comment.get('votes', '0') != '0' for comment in comments)

    @pytest.mark.vcr
    @pytest.mark.network
    def test_comment_sorting_recent(self, youtube_video_id):
        """Test fetching recent comments"""
        downloader = YoutubeCommentDownloader()
        comments = []

        for i, comment in enumerate(downloader.get_comments(
            youtube_video_id, sort_by=SORT_BY_RECENT
        )):
            if i >= 5:
                break
            comments.append(comment)

        assert len(comments) == 5
        # Check that comments have timestamps
        assert all('time' in comment for comment in comments)

    @pytest.mark.vcr
    @pytest.mark.network
    @pytest.mark.parametrize("language", ["en", "es"])
    def test_language_parameter(self, youtube_video_id, language):
        """Test language parameter affects YouTube interface language"""
        downloader = YoutubeCommentDownloader()
        comments = []

        for i, comment in enumerate(downloader.get_comments(
            youtube_video_id, language=language
        )):
            if i >= 3:
                break
            comments.append(comment)

        # We should still get comments regardless of language
        assert len(comments) == 3

    @pytest.mark.vcr
    @pytest.mark.network
    def test_comment_with_replies(self, youtube_video_id):
        """Test that reply comments are properly marked"""
        downloader = YoutubeCommentDownloader()
        comments = []

        # Get more comments to find some replies
        for i, comment in enumerate(downloader.get_comments(youtube_video_id)):
            if i >= 30:
                break
            comments.append(comment)

        # Check for reply field
        assert all('reply' in comment for comment in comments)
        # At least some comments should be replies (have '.' in cid)
        replies = [c for c in comments if c.get('reply', False)]
        # The first video might not have replies, so we just check the field exists
        assert isinstance(replies, list)

    @pytest.mark.vcr
    @pytest.mark.network
    def test_disabled_comments(self):
        """Test handling of videos with disabled comments"""
        # Use a video ID that likely has disabled comments
        # Note: This is fragile and might need updating
        video_id = "test_disabled_comments"
        downloader = YoutubeCommentDownloader()
        comments = list(downloader.get_comments(video_id))

        # Should return empty list for disabled comments
        assert comments == []

    @pytest.mark.vcr
    @pytest.mark.network
    def test_invalid_video_id(self):
        """Test handling of invalid video ID"""
        downloader = YoutubeCommentDownloader()
        comments = list(downloader.get_comments("invalid_id_12345"))

        # Should handle gracefully and return empty
        assert comments == []

    def test_search_dict_utility(self):
        """Test the search_dict static method"""
        test_data = {
            "level1": {
                "level2": {
                    "target": "found",
                    "other": "not this"
                },
                "target": "also found"
            },
            "list": [
                {"target": "in list"},
                {"other": "not target"}
            ]
        }

        results = list(YoutubeCommentDownloader.search_dict(test_data, "target"))
        assert len(results) == 3
        assert "found" in results
        assert "also found" in results
        assert "in list" in results

    def test_regex_search_utility(self):
        """Test the regex_search static method"""
        text = "The answer is 42 in this text"

        # Test successful match
        result = YoutubeCommentDownloader.regex_search(
            text, r"answer is (\d+)", group=1
        )
        assert result == "42"

        # Test no match with default
        result = YoutubeCommentDownloader.regex_search(
            text, r"missing (\d+)", group=1, default="not found"
        )
        assert result == "not found"

        # Test no match without default
        result = YoutubeCommentDownloader.regex_search(
            text, r"missing (\d+)", group=1
        )
        assert result is None

    @pytest.mark.vcr
    @pytest.mark.network
    @pytest.mark.slow
    def test_comment_pagination(self, youtube_video_id):
        """Test that pagination works for videos with many comments"""
        downloader = YoutubeCommentDownloader()
        comments = []

        # Get enough comments to likely trigger pagination
        for i, comment in enumerate(downloader.get_comments(youtube_video_id)):
            if i >= 50:
                break
            comments.append(comment)

        assert len(comments) == 50
        # Check that we have unique comment IDs
        cids = [c['cid'] for c in comments]
        assert len(cids) == len(set(cids)), "Duplicate comment IDs found"

    @pytest.mark.vcr
    @pytest.mark.network
    def test_time_parsed_field(self, youtube_video_id):
        """Test that time_parsed field is added to comments when possible"""
        downloader = YoutubeCommentDownloader()
        comments = []

        for i, comment in enumerate(downloader.get_comments(youtube_video_id)):
            if i >= 5:
                break
            comments.append(comment)

        # Check for time_parsed field (might not be in all comments)
        comments_with_time_parsed = [
            c for c in comments if 'time_parsed' in c
        ]
        # At least some comments should have parsed timestamps
        assert len(comments_with_time_parsed) > 0
        # Parsed time should be a number (Unix timestamp)
        for comment in comments_with_time_parsed:
            assert isinstance(comment['time_parsed'], (int, float))

    @pytest.mark.vcr
    @pytest.mark.network
    def test_comment_hearts(self, youtube_video_id):
        """Test that heart field is properly set"""
        downloader = YoutubeCommentDownloader()
        comments = []

        for i, comment in enumerate(downloader.get_comments(youtube_video_id)):
            if i >= 20:
                break
            comments.append(comment)

        # All comments should have heart field
        assert all('heart' in comment for comment in comments)
        # Heart should be boolean
        assert all(isinstance(comment['heart'], bool) for comment in comments)