"""
Tests for CLI interface with VCR.py recording
"""
import os
import sys
import json
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from youtube_comment_downloader import main, to_json


class TestCLI:
    """Test suite for command-line interface"""

    def test_main_no_args(self, capsys):
        """Test main function with no arguments shows usage"""
        with pytest.raises(SystemExit) as exc_info:
            main([])

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error:" in captured.out or "usage:" in captured.out

    def test_main_help(self, capsys):
        """Test help output"""
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])

        # Help exits with 0
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "Download Youtube comments" in captured.out

    @pytest.mark.vcr
    @pytest.mark.network
    def test_main_with_youtube_id(self, tmp_path, youtube_video_id):
        """Test downloading with YouTube ID"""
        output_file = tmp_path / "comments.json"

        # Run with limited comments for speed
        with pytest.raises(SystemExit) as exc_info:
            main([
                "-y", youtube_video_id,
                "-o", str(output_file),
                "-l", "5"  # Limit to 5 comments
            ])

        assert exc_info.value.code == 0
        assert output_file.exists()

        # Verify output file contains valid JSON lines
        with open(output_file, 'r', encoding='utf8') as f:
            lines = f.readlines()
            assert len(lines) == 5
            for line in lines:
                comment = json.loads(line)
                assert 'text' in comment
                assert 'author' in comment

    @pytest.mark.vcr
    @pytest.mark.network
    def test_main_with_url(self, tmp_path, youtube_url):
        """Test downloading with YouTube URL"""
        output_file = tmp_path / "comments_url.json"

        with pytest.raises(SystemExit) as exc_info:
            main([
                "-u", youtube_url,
                "-o", str(output_file),
                "-l", "3"
            ])

        assert exc_info.value.code == 0
        assert output_file.exists()

        with open(output_file, 'r', encoding='utf8') as f:
            comments = [json.loads(line) for line in f]
            assert len(comments) == 3

    @pytest.mark.vcr
    @pytest.mark.network
    def test_main_pretty_output(self, tmp_path, youtube_video_id):
        """Test pretty JSON output format"""
        output_file = tmp_path / "pretty_comments.json"

        with pytest.raises(SystemExit) as exc_info:
            main([
                "-y", youtube_video_id,
                "-o", str(output_file),
                "-p",  # Pretty output
                "-l", "2"
            ])

        assert exc_info.value.code == 0
        assert output_file.exists()

        # Pretty output should be valid JSON object
        with open(output_file, 'r', encoding='utf8') as f:
            data = json.load(f)
            assert 'comments' in data
            assert len(data['comments']) == 2
            # Check it's properly formatted
            assert isinstance(data['comments'], list)

    @pytest.mark.vcr
    @pytest.mark.network
    def test_main_with_sort_popular(self, tmp_path, youtube_video_id):
        """Test downloading with popular sort"""
        output_file = tmp_path / "popular_comments.json"

        with pytest.raises(SystemExit) as exc_info:
            main([
                "-y", youtube_video_id,
                "-o", str(output_file),
                "-s", "0",  # Sort by popular
                "-l", "5"
            ])

        assert exc_info.value.code == 0
        assert output_file.exists()

        with open(output_file, 'r', encoding='utf8') as f:
            comments = [json.loads(line) for line in f]
            assert len(comments) == 5

    @pytest.mark.vcr
    @pytest.mark.network
    def test_main_with_sort_recent(self, tmp_path, youtube_video_id):
        """Test downloading with recent sort"""
        output_file = tmp_path / "recent_comments.json"

        with pytest.raises(SystemExit) as exc_info:
            main([
                "-y", youtube_video_id,
                "-o", str(output_file),
                "-s", "1",  # Sort by recent (default)
                "-l", "5"
            ])

        assert exc_info.value.code == 0
        assert output_file.exists()

    @pytest.mark.vcr
    @pytest.mark.network
    def test_main_with_language(self, tmp_path, youtube_video_id):
        """Test downloading with language parameter"""
        output_file = tmp_path / "lang_comments.json"

        with pytest.raises(SystemExit) as exc_info:
            main([
                "-y", youtube_video_id,
                "-o", str(output_file),
                "-a", "en",  # English language
                "-l", "3"
            ])

        assert exc_info.value.code == 0
        assert output_file.exists()

    def test_main_with_proxy(self, tmp_path):
        """Test proxy parameter is passed to downloader"""
        output_file = tmp_path / "proxy_test.json"
        proxy_url = "https://proxy.example.com:8080"

        with patch('youtube_comment_downloader.YoutubeCommentDownloader') as mock_downloader:
            # Mock the downloader to avoid network calls
            mock_instance = MagicMock()
            mock_instance.get_comments.return_value = iter([
                {'text': 'test', 'author': 'tester', 'cid': '1'}
            ])
            mock_downloader.return_value = mock_instance

            with pytest.raises(SystemExit) as exc_info:
                main([
                    "-y", "test_id",
                    "-o", str(output_file),
                    "-x", proxy_url,
                    "-l", "1"
                ])

            # Check proxy was passed to constructor
            mock_downloader.assert_called_once_with(https_proxy=proxy_url)

    def test_main_creates_output_directory(self, tmp_path):
        """Test that output directory is created if it doesn't exist"""
        output_dir = tmp_path / "new_dir"
        output_file = output_dir / "comments.json"

        assert not output_dir.exists()

        with patch('youtube_comment_downloader.YoutubeCommentDownloader') as mock_downloader:
            mock_instance = MagicMock()
            mock_instance.get_comments.return_value = iter([
                {'text': 'test', 'author': 'tester', 'cid': '1'}
            ])
            mock_downloader.return_value = mock_instance

            with pytest.raises(SystemExit) as exc_info:
                main([
                    "-y", "test_id",
                    "-o", str(output_file),
                    "-l", "1"
                ])

            assert exc_info.value.code == 0
            assert output_dir.exists()
            assert output_file.exists()

    def test_main_missing_required_args(self, capsys):
        """Test error when required arguments are missing"""
        # Missing output
        with pytest.raises(SystemExit) as exc_info:
            main(["-y", "test_id"])

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error:" in captured.out

        # Missing youtube id or url
        with pytest.raises(SystemExit) as exc_info:
            main(["-o", "output.json"])

        assert exc_info.value.code == 1

    def test_main_both_id_and_url(self, tmp_path):
        """Test that both ID and URL can't be specified"""
        output_file = tmp_path / "test.json"

        # This should work - preferring ID over URL
        with patch('youtube_comment_downloader.YoutubeCommentDownloader') as mock_downloader:
            mock_instance = MagicMock()
            mock_instance.get_comments.return_value = iter([])
            mock_downloader.return_value = mock_instance

            with pytest.raises(SystemExit) as exc_info:
                main([
                    "-y", "test_id",
                    "-u", "https://youtube.com/watch?v=test",
                    "-o", str(output_file)
                ])

            # Should use get_comments (ID) not get_comments_from_url
            mock_instance.get_comments.assert_called_once()
            mock_instance.get_comments_from_url.assert_not_called()

    def test_to_json_function(self):
        """Test the to_json helper function"""
        comment = {
            'text': 'Test comment',
            'author': 'Test Author',
            'votes': '42'
        }

        # Test without indent
        result = to_json(comment)
        assert json.loads(result) == comment

        # Test with indent
        result = to_json(comment, indent=2)
        assert 'Test comment' in result
        # Should have indentation
        assert '  ' in result

    def test_to_json_unicode_handling(self):
        """Test to_json handles Unicode properly"""
        comment = {
            'text': '测试评论 🎉',
            'author': 'ユーザー'
        }

        result = to_json(comment)
        # Should not escape Unicode
        assert '测试评论' in result
        assert 'ユーザー' in result

    @pytest.mark.vcr
    @pytest.mark.network
    def test_main_invalid_video_id(self, tmp_path):
        """Test handling of invalid video ID"""
        output_file = tmp_path / "invalid.json"

        with pytest.raises(SystemExit) as exc_info:
            main([
                "-y", "definitely_invalid_id_xyz",
                "-o", str(output_file),
                "-l", "1"
            ])

        # Should complete but with no comments
        assert exc_info.value.code == 0
        assert output_file.exists()

        with open(output_file, 'r', encoding='utf8') as f:
            content = f.read()
            # File should be empty or have no comments
            assert content == "" or json.loads(content) == []

    @pytest.mark.vcr
    @pytest.mark.network
    @pytest.mark.slow
    def test_subprocess_cli_invocation(self, tmp_path, youtube_video_id):
        """Test invoking CLI as subprocess (like users would)"""
        output_file = tmp_path / "subprocess_test.json"

        result = subprocess.run([
            sys.executable, "-m", "youtube_comment_downloader",
            "-y", youtube_video_id,
            "-o", str(output_file),
            "-l", "2"
        ], capture_output=True, text=True)

        assert result.returncode == 0
        assert output_file.exists()
        assert "Downloaded" in result.stdout
        assert "Done!" in result.stdout