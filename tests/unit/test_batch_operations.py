"""Unit tests for batch message and draft operations."""

from unittest.mock import MagicMock, patch

import pytest

from apple_mail_mcp.mail_connector import AppleMailConnector


@pytest.fixture
def connector() -> AppleMailConnector:
    return AppleMailConnector()


SEP = "\x1f"
REC = "\x1e"  # ASCII Record Separator — used between message records in batch output


# ---------------------------------------------------------------------------
# get_messages_batch
# ---------------------------------------------------------------------------


class TestGetMessagesBatch:
    @patch.object(AppleMailConnector, "_run_applescript")
    def test_empty_list_returns_empty(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        result = connector.get_messages_batch([])
        assert result == []
        mock_run.assert_not_called()

    @patch.object(AppleMailConnector, "_run_applescript")
    def test_single_id_returns_one_message(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        mock_run.return_value = f"12345{SEP}Subject{SEP}sender@example.com{SEP}Mon Jan 1 2024{SEP}true{SEP}false{SEP}false{SEP}Body content"

        result = connector.get_messages_batch(["12345"])

        assert len(result) == 1
        assert result[0]["id"] == "12345"
        assert result[0]["subject"] == "Subject"
        assert result[0]["sender"] == "sender@example.com"
        assert result[0]["read_status"] is True
        assert result[0]["flagged"] is False
        assert result[0]["replied_to"] is False
        assert result[0]["content"] == "Body content"

    @patch.object(AppleMailConnector, "_run_applescript")
    def test_multiple_ids_returns_all_messages(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        line1 = f"111{SEP}Subj A{SEP}a@example.com{SEP}Mon Jan 1 2024{SEP}true{SEP}false{SEP}false{SEP}Body A"
        line2 = f"222{SEP}Subj B{SEP}b@example.com{SEP}Tue Jan 2 2024{SEP}false{SEP}true{SEP}true{SEP}Body B"
        mock_run.return_value = f"{line1}{REC}{line2}"

        result = connector.get_messages_batch(["111", "222"])

        assert len(result) == 2
        assert result[0]["id"] == "111"
        assert result[0]["flagged"] is False
        assert result[1]["id"] == "222"
        assert result[1]["flagged"] is True
        assert result[1]["replied_to"] is True

    @patch.object(AppleMailConnector, "_run_applescript")
    def test_uses_single_applescript_call(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        mock_run.return_value = ""
        connector.get_messages_batch(["111", "222", "333"])
        assert mock_run.call_count == 1

    @patch.object(AppleMailConnector, "_run_applescript")
    def test_all_ids_embedded_in_script(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        mock_run.return_value = ""
        connector.get_messages_batch(["111", "222", "333"])
        script = mock_run.call_args[0][0]
        assert "111" in script
        assert "222" in script
        assert "333" in script

    @patch.object(AppleMailConnector, "_run_applescript")
    def test_uses_unit_separator_not_pipe(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        mock_run.return_value = ""
        connector.get_messages_batch(["12345"])
        script = mock_run.call_args[0][0]
        assert "ASCII character 31" in script
        assert '& "|" &' not in script

    @patch.object(AppleMailConnector, "_run_applescript")
    def test_no_content_when_include_content_false(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        mock_run.return_value = f"12345{SEP}Subject{SEP}sender@example.com{SEP}Mon Jan 1 2024{SEP}true{SEP}false{SEP}false{SEP}"

        result = connector.get_messages_batch(["12345"], include_content=False)

        script = mock_run.call_args[0][0]
        assert "content of msg" not in script
        assert result[0]["content"] == ""

    @patch.object(AppleMailConnector, "_run_applescript")
    def test_empty_applescript_result_returns_empty_list(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        mock_run.return_value = ""
        result = connector.get_messages_batch(["99999"])
        assert result == []

    def test_exceeds_max_raises_value_error(
        self, connector: AppleMailConnector
    ) -> None:
        ids = [str(i) for i in range(101)]
        with pytest.raises(ValueError, match="100"):
            connector.get_messages_batch(ids)

    def test_invalid_id_raises_value_error(
        self, connector: AppleMailConnector
    ) -> None:
        with pytest.raises(ValueError):
            connector.get_messages_batch(['12345" end tell'])

    @patch.object(AppleMailConnector, "_run_applescript")
    def test_pipe_in_content_does_not_corrupt_parsing(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        mock_run.return_value = f"12345{SEP}Subject{SEP}sender@example.com{SEP}Mon Jan 1 2024{SEP}true{SEP}false{SEP}false{SEP}Body with | pipes | here"

        result = connector.get_messages_batch(["12345"])

        assert result[0]["subject"] == "Subject"
        assert result[0]["content"] == "Body with | pipes | here"

    @patch.object(AppleMailConnector, "_run_applescript")
    def test_script_exits_inner_repeat_on_found(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        """Script must exit inner loops once a message is found to avoid redundant searches."""
        mock_run.return_value = ""
        connector.get_messages_batch(["12345"])
        script = mock_run.call_args[0][0]
        assert "exit repeat" in script


# ---------------------------------------------------------------------------
# save_drafts_batch
# ---------------------------------------------------------------------------


class TestSaveDraftsBatch:
    @patch.object(AppleMailConnector, "_run_applescript")
    def test_empty_list_returns_empty_no_calls(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        result = connector.save_drafts_batch([], account="Test Account")
        assert result == []
        mock_run.assert_not_called()

    @patch.object(AppleMailConnector, "_run_applescript")
    def test_single_draft_returns_one_id(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        # Call 1: get sender email; Call 2: create drafts
        mock_run.side_effect = ["sender@example.com", "100"]

        result = connector.save_drafts_batch(
            [{"subject": "Re: Test", "body": "Hello", "to": ["to@example.com"]}],
            account="Test Account",
        )

        assert result == ["100"]

    @patch.object(AppleMailConnector, "_run_applescript")
    def test_multiple_drafts_returns_all_ids(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        mock_run.side_effect = ["sender@example.com", "100\n101\n102"]

        result = connector.save_drafts_batch(
            [
                {"subject": "Re: A", "body": "Body A", "to": ["a@example.com"]},
                {"subject": "Re: B", "body": "Body B", "to": ["b@example.com"]},
                {"subject": "Re: C", "body": "Body C", "to": ["c@example.com"]},
            ],
            account="Test Account",
        )

        assert result == ["100", "101", "102"]

    @patch.object(AppleMailConnector, "_run_applescript")
    def test_exactly_two_applescript_calls_regardless_of_count(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        mock_run.side_effect = ["sender@example.com", "100\n101\n102\n103\n104"]

        connector.save_drafts_batch(
            [
                {"subject": f"Re: {i}", "body": f"Body {i}", "to": [f"r{i}@example.com"]}
                for i in range(5)
            ],
            account="Test Account",
        )

        assert mock_run.call_count == 2

    @patch.object(AppleMailConnector, "_run_applescript")
    def test_subjects_and_bodies_escaped_in_script(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        mock_run.side_effect = ["sender@example.com", "100"]

        connector.save_drafts_batch(
            [{"subject": 'Subject with "quotes"', "body": 'Body with "quotes"', "to": ["r@example.com"]}],
            account="Test Account",
        )

        draft_script = mock_run.call_args_list[1][0][0]
        # Escaped form of the double quotes must appear in script
        assert '\\"quotes\\"' in draft_script

    @patch.object(AppleMailConnector, "_run_applescript")
    def test_cc_recipients_included_in_script(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        mock_run.side_effect = ["sender@example.com", "100"]

        connector.save_drafts_batch(
            [{"subject": "Re: Test", "body": "Hello", "to": ["to@example.com"], "cc": ["cc@example.com"]}],
            account="Test Account",
        )

        draft_script = mock_run.call_args_list[1][0][0]
        assert "cc@example.com" in draft_script

    @patch.object(AppleMailConnector, "_run_applescript")
    def test_bcc_recipients_included_in_script(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        mock_run.side_effect = ["sender@example.com", "100"]

        connector.save_drafts_batch(
            [{"subject": "Re: Test", "body": "Hello", "to": ["to@example.com"], "bcc": ["bcc@example.com"]}],
            account="Test Account",
        )

        draft_script = mock_run.call_args_list[1][0][0]
        assert "bcc@example.com" in draft_script

    @patch.object(AppleMailConnector, "_run_applescript")
    def test_all_recipient_addresses_in_script(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        mock_run.side_effect = ["sender@example.com", "100\n101"]

        connector.save_drafts_batch(
            [
                {"subject": "Re: A", "body": "Body A", "to": ["a@example.com"]},
                {"subject": "Re: B", "body": "Body B", "to": ["b@example.com"]},
            ],
            account="Test Account",
        )

        draft_script = mock_run.call_args_list[1][0][0]
        assert "a@example.com" in draft_script
        assert "b@example.com" in draft_script

    @patch.object(AppleMailConnector, "_run_applescript")
    def test_account_name_escaped_in_sender_lookup(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        mock_run.side_effect = ["sender@example.com", "100"]

        connector.save_drafts_batch(
            [{"subject": "Re: Test", "body": "Hello", "to": ["r@example.com"]}],
            account='Account with "quotes"',
        )

        sender_script = mock_run.call_args_list[0][0][0]
        assert '\\"quotes\\"' in sender_script

    def test_exceeds_max_raises_value_error(
        self, connector: AppleMailConnector
    ) -> None:
        drafts = [{"subject": "s", "body": "b", "to": ["r@example.com"]} for _ in range(51)]
        with pytest.raises(ValueError, match="50"):
            connector.save_drafts_batch(drafts, account="Test")

    @patch.object(AppleMailConnector, "_run_applescript")
    def test_returns_ids_in_same_order_as_input(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        mock_run.side_effect = ["sender@example.com", "200\n201"]

        result = connector.save_drafts_batch(
            [
                {"subject": "Re: First", "body": "Body 1", "to": ["a@example.com"]},
                {"subject": "Re: Second", "body": "Body 2", "to": ["b@example.com"]},
            ],
            account="Test Account",
        )

        assert result[0] == "200"
        assert result[1] == "201"
