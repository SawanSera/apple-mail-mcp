"""Unit tests for mail connector."""

from unittest.mock import MagicMock, patch

import pytest

from apple_mail_mcp.exceptions import (
    MailAccountNotFoundError,
    MailAppleScriptError,
    MailMailboxNotFoundError,
)
from apple_mail_mcp.mail_connector import AppleMailConnector


class TestAppleMailConnector:
    """Tests for AppleMailConnector."""

    @pytest.fixture
    def connector(self) -> AppleMailConnector:
        """Create a connector instance."""
        return AppleMailConnector(timeout=30)

    @patch("subprocess.run")
    def test_run_applescript_success(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        """Test successful AppleScript execution."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="result",
            stderr=""
        )

        result = connector._run_applescript("test script")
        assert result == "result"

        mock_run.assert_called_once()
        args = mock_run.call_args
        assert args[0][0] == ["/usr/bin/osascript", "-"]

    @patch("subprocess.run")
    def test_run_applescript_account_not_found(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        """Test account not found error."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Can't get account \"NonExistent\""
        )

        with pytest.raises(MailAccountNotFoundError):
            connector._run_applescript("test script")

    @patch("subprocess.run")
    def test_run_applescript_mailbox_not_found(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        """Test mailbox not found error."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Can't get mailbox \"NonExistent\""
        )

        with pytest.raises(MailMailboxNotFoundError):
            connector._run_applescript("test script")

    @patch("subprocess.run")
    def test_run_applescript_timeout(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        """Test timeout handling."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 30)

        with pytest.raises(MailAppleScriptError, match="timeout"):
            connector._run_applescript("test script")

    @patch.object(AppleMailConnector, "_run_applescript")
    def test_list_mailboxes(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        """Test listing mailboxes."""
        mock_run.return_value = "mailbox data"

        result = connector.list_mailboxes("Gmail")
        assert len(result) > 0

    @patch.object(AppleMailConnector, "_run_applescript")
    def test_search_messages_basic(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        """Test basic message search."""
        sep = "\x1f"
        mock_run.return_value = f"12345{sep}Test Subject{sep}sender@example.com{sep}Mon Jan 1 2024{sep}false"

        result = connector.search_messages("Gmail", "INBOX")

        assert len(result) == 1
        assert result[0]["id"] == "12345"
        assert result[0]["subject"] == "Test Subject"
        assert result[0]["sender"] == "sender@example.com"
        assert result[0]["read_status"] is False

    @patch.object(AppleMailConnector, "_run_applescript")
    def test_search_messages_with_filters(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        """Test message search with filters."""
        mock_run.return_value = ""

        connector.search_messages(
            "Gmail",
            "INBOX",
            sender_contains="john@example.com",
            subject_contains="meeting",
            read_status=False,
            limit=10
        )

        # Verify the script includes filter conditions
        call_args = mock_run.call_args[0][0]
        assert 'sender contains "john@example.com"' in call_args
        assert 'subject contains "meeting"' in call_args
        assert "read status is false" in call_args
        assert "msgCount >= 10" in call_args

    @patch.object(AppleMailConnector, "_run_applescript")
    def test_get_message(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        """Test getting a message."""
        sep = "\x1f"
        mock_run.return_value = f"12345{sep}Subject{sep}sender@example.com{sep}Mon Jan 1 2024{sep}true{sep}false{sep}false{sep}Message body"

        result = connector.get_message("12345", include_content=True)

        assert result["id"] == "12345"
        assert result["subject"] == "Subject"
        assert result["content"] == "Message body"
        assert result["read_status"] is True
        assert result["flagged"] is False
        assert result["replied_to"] is False

    @patch.object(AppleMailConnector, "_run_applescript")
    def test_send_email_basic(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        """Test sending a basic email."""
        mock_run.return_value = "sent"

        result = connector.send_email(
            subject="Test",
            body="Test body",
            to=["recipient@example.com"]
        )

        assert result is True

    @patch.object(AppleMailConnector, "_run_applescript")
    def test_send_email_with_cc_bcc(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        """Test sending email with CC and BCC."""
        mock_run.return_value = "sent"

        result = connector.send_email(
            subject="Test",
            body="Test body",
            to=["recipient@example.com"],
            cc=["cc@example.com"],
            bcc=["bcc@example.com"]
        )

        assert result is True

        # Verify script includes recipients
        call_args = mock_run.call_args[0][0]
        assert "recipient@example.com" in call_args
        assert "cc@example.com" in call_args
        assert "bcc@example.com" in call_args

    @patch.object(AppleMailConnector, "_run_applescript")
    def test_mark_as_read(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        """Test marking messages as read."""
        mock_run.return_value = "2"

        result = connector.mark_as_read(["12345", "12346"], read=True)

        assert result == 2

    @patch.object(AppleMailConnector, "_run_applescript")
    def test_mark_as_unread(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        """Test marking messages as unread."""
        mock_run.return_value = "1"

        result = connector.mark_as_read(["12345"], read=False)

        assert result == 1

        # Verify script sets read status to false
        call_args = mock_run.call_args[0][0]
        assert "set read status of msg to false" in call_args

    def test_mark_as_read_empty_list(self, connector: AppleMailConnector) -> None:
        """Test marking with empty list."""
        result = connector.mark_as_read([])
        assert result == 0

    @patch.object(AppleMailConnector, "_run_applescript")
    def test_search_messages_pipe_in_subject_parses_correctly(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        """Issue 11: subject containing '|' must not corrupt field parsing."""
        sep = "\x1f"
        # Subject contains a literal pipe — should not split subject field
        mock_run.return_value = (
            f"12345{sep}Subject with | pipe{sep}sender@example.com{sep}Mon Jan 1 2024{sep}false"
        )

        result = connector.search_messages("Gmail", "INBOX")

        assert len(result) == 1
        assert result[0]["subject"] == "Subject with | pipe"
        assert result[0]["sender"] == "sender@example.com"

    @patch.object(AppleMailConnector, "_run_applescript")
    def test_get_message_pipe_in_body_parses_correctly(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        """Issue 11: message body containing '|' must not corrupt field parsing."""
        sep = "\x1f"
        mock_run.return_value = (
            f"12345{sep}Subject{sep}sender@example.com{sep}Mon Jan 1 2024{sep}true{sep}false{sep}true{sep}Body with | pipes | here"
        )

        result = connector.get_message("12345")

        assert result["subject"] == "Subject"
        assert result["content"] == "Body with | pipes | here"

    @patch.object(AppleMailConnector, "_run_applescript")
    def test_search_uses_unit_separator_in_script(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        """Issue 11: AppleScript must use ASCII 31 (unit separator) not pipe."""
        mock_run.return_value = ""
        connector.search_messages("Gmail", "INBOX")
        script = mock_run.call_args[0][0]
        assert "ASCII character 31" in script
        # Must NOT use plain pipe as field delimiter
        assert '& "|" &' not in script
