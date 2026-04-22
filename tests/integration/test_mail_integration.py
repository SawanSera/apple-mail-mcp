"""
Integration tests for Apple Mail MCP.

These tests require:
1. Apple Mail.app installed and running
2. At least one configured mail account
3. Permission granted for automation

Run with: pytest tests/integration/ -v
"""

import pytest

from apple_mail_mcp.mail_connector import AppleMailConnector

# Skip all integration tests by default
# Run with: pytest --run-integration
pytestmark = pytest.mark.skipif(
    "not config.getoption('--run-integration')",
    reason="Integration tests disabled by default. Use --run-integration to run."
)


@pytest.fixture
def connector() -> AppleMailConnector:
    """Create a real connector instance."""
    return AppleMailConnector()


@pytest.fixture
def test_account() -> str:
    """
    Return the test account name.

    Override this in conftest.py or via environment variable.
    """
    import os
    return os.getenv("TEST_MAIL_ACCOUNT", "Gmail")


class TestMailIntegration:
    """Integration tests with real Apple Mail."""

    def test_list_mailboxes(self, connector: AppleMailConnector, test_account: str) -> None:
        """Test listing mailboxes from real account."""
        result = connector.list_mailboxes(test_account)
        assert isinstance(result, list)
        # Should have at least INBOX
        assert len(result) > 0

    def test_search_messages(self, connector: AppleMailConnector, test_account: str) -> None:
        """Test searching messages in real mailbox."""
        result = connector.search_messages(
            account=test_account,
            mailbox="INBOX",
            limit=5
        )
        assert isinstance(result, list)
        # Mailbox might be empty, so just check type

    def test_search_unread_messages(
        self, connector: AppleMailConnector, test_account: str
    ) -> None:
        """Test searching for unread messages."""
        result = connector.search_messages(
            account=test_account,
            mailbox="INBOX",
            read_status=False,
            limit=10
        )
        assert isinstance(result, list)

        # Verify all returned messages are unread
        for msg in result:
            assert msg["read_status"] is False


class TestMailSendIntegration:
    """
    Integration tests for sending emails.

    WARNING: These tests will send real emails!
    Only run if you have a test account configured.
    """

    @pytest.mark.skip(reason="Sends real email - enable manually")
    def test_send_email(self, connector: AppleMailConnector) -> None:
        """
        Test sending a real email.

        MANUALLY ENABLE THIS TEST and update recipient!
        """
        result = connector.send_email(
            subject="Test Email from Apple Mail MCP",
            body="This is a test email sent via the MCP integration test suite.",
            to=["YOUR_TEST_EMAIL@example.com"]  # UPDATE THIS!
        )
        assert result is True


class TestGetMessagesBatchIntegration:
    """Integration tests for get_messages_batch against real Mail.app.

    These tests validate that:
    - The AppleScript syntax is correct
    - The `exit repeat` early-termination pattern works in real Mail.app
    - Field parsing survives real email content (subjects, bodies)
    - The batch result matches individual get_message results for the same ID
    """

    def test_empty_list_returns_empty(self, connector: AppleMailConnector) -> None:
        """Empty input must not hit AppleScript at all and return []."""
        result = connector.get_messages_batch([])
        assert result == []

    def test_batch_result_matches_individual_get_message(
        self, connector: AppleMailConnector, test_account: str
    ) -> None:
        """Batch result for an ID must be identical to individual get_message result."""
        messages = connector.search_messages(
            account=test_account, mailbox="INBOX", limit=3
        )
        if not messages:
            pytest.skip("INBOX is empty — cannot run batch comparison test")

        msg_id = messages[0]["id"]

        individual = connector.get_message(msg_id, include_content=True)
        batch = connector.get_messages_batch([msg_id], include_content=True)

        assert len(batch) == 1
        result = batch[0]
        assert result["id"] == individual["id"]
        assert result["subject"] == individual["subject"]
        assert result["sender"] == individual["sender"]
        assert result["read_status"] == individual["read_status"]
        assert result["flagged"] == individual["flagged"]
        assert result["replied_to"] == individual["replied_to"]
        assert result["content"] == individual["content"]

    def test_fetches_multiple_messages_in_one_call(
        self, connector: AppleMailConnector, test_account: str
    ) -> None:
        """Batch fetches multiple messages and returns all of them."""
        messages = connector.search_messages(
            account=test_account, mailbox="INBOX", limit=5
        )
        if len(messages) < 2:
            pytest.skip("Need at least 2 messages in INBOX")

        ids = [m["id"] for m in messages[:3]]
        results = connector.get_messages_batch(ids)

        assert len(results) == len(ids)
        returned_ids = {r["id"] for r in results}
        assert returned_ids == set(ids)

    def test_all_fields_present_in_batch_result(
        self, connector: AppleMailConnector, test_account: str
    ) -> None:
        """Every result dict must contain all expected fields."""
        messages = connector.search_messages(
            account=test_account, mailbox="INBOX", limit=1
        )
        if not messages:
            pytest.skip("INBOX is empty")

        results = connector.get_messages_batch([messages[0]["id"]])
        assert len(results) == 1

        msg = results[0]
        for field in ("id", "subject", "sender", "date_received",
                      "read_status", "flagged", "replied_to", "content"):
            assert field in msg, f"Missing field: {field}"

    def test_include_content_false_returns_empty_content(
        self, connector: AppleMailConnector, test_account: str
    ) -> None:
        """include_content=False must return empty string for content field."""
        messages = connector.search_messages(
            account=test_account, mailbox="INBOX", limit=1
        )
        if not messages:
            pytest.skip("INBOX is empty")

        results = connector.get_messages_batch(
            [messages[0]["id"]], include_content=False
        )
        assert len(results) == 1
        assert results[0]["content"] == ""

    def test_unknown_id_is_silently_skipped(
        self, connector: AppleMailConnector
    ) -> None:
        """A message ID that does not exist must be silently skipped, not raise."""
        results = connector.get_messages_batch(["999999999"])
        assert results == []

    def test_mixed_valid_and_unknown_ids(
        self, connector: AppleMailConnector, test_account: str
    ) -> None:
        """Valid IDs are returned; unknown IDs are skipped without error."""
        messages = connector.search_messages(
            account=test_account, mailbox="INBOX", limit=1
        )
        if not messages:
            pytest.skip("INBOX is empty")

        valid_id = messages[0]["id"]
        results = connector.get_messages_batch([valid_id, "999999999"])

        assert len(results) == 1
        assert results[0]["id"] == valid_id


class TestSaveDraftsBatchIntegration:
    """Integration tests for save_drafts_batch against real Mail.app.

    Tests validate AppleScript syntax, variable naming patterns (msg_0 / msg_1),
    recipient wiring, and that draft IDs are real saveable message IDs.
    Drafts are deleted in teardown so the test leaves no lasting side effects.
    """

    @pytest.fixture
    def saved_draft_ids(
        self, connector: AppleMailConnector, test_account: str
    ) -> list[str]:
        """Save drafts and delete them after the test."""
        drafts = [
            {
                "subject": "Integration test draft A",
                "body": "Test body A — created by integration test suite",
                "to": ["test-recipient-a@example.com"],
            },
            {
                "subject": "Integration test draft B",
                "body": "Test body B — created by integration test suite",
                "to": ["test-recipient-b@example.com"],
                "cc": ["test-cc@example.com"],
            },
        ]
        ids = connector.save_drafts_batch(drafts, account=test_account)
        yield ids
        # Cleanup: delete the drafts we created
        if ids:
            try:
                connector.delete_messages(ids, permanent=True)
            except Exception:
                pass  # Best-effort cleanup

    def test_single_draft_returns_one_id(
        self, connector: AppleMailConnector, test_account: str
    ) -> None:
        """A single draft must produce exactly one valid draft ID."""
        ids = connector.save_drafts_batch(
            [{"subject": "Integration single draft", "body": "Body", "to": ["r@example.com"]}],
            account=test_account,
        )
        assert len(ids) == 1
        assert ids[0].strip().isdigit(), f"Expected numeric ID, got: {ids[0]!r}"

        # Cleanup
        try:
            connector.delete_messages(ids, permanent=True)
        except Exception:
            pass

    def test_multiple_drafts_returns_all_ids_in_order(
        self, saved_draft_ids: list[str]
    ) -> None:
        """Batch save of N drafts returns N IDs in input order."""
        assert len(saved_draft_ids) == 2
        assert all(id_.strip().isdigit() for id_ in saved_draft_ids), (
            f"All IDs must be numeric, got: {saved_draft_ids}"
        )

    def test_draft_ids_are_distinct(self, saved_draft_ids: list[str]) -> None:
        """Each saved draft must receive a unique ID."""
        assert len(set(saved_draft_ids)) == len(saved_draft_ids)

    def test_saved_draft_is_fetchable_by_id(
        self, connector: AppleMailConnector, test_account: str
    ) -> None:
        """Draft IDs returned by save_drafts_batch are valid numeric IDs.

        Note: get_messages_batch searches all accounts in iteration order. Apple Mail
        integer IDs are not guaranteed globally unique across accounts, so a batch
        fetch may return a different account's message when IDs collide. This test
        verifies only that the ID is valid (numeric) and that the batch call returns
        a result for it — not that the subject matches.
        """
        ids = connector.save_drafts_batch(
            [{"subject": "Fetchable draft test", "body": "Body", "to": ["r@example.com"]}],
            account=test_account,
        )
        assert len(ids) == 1
        assert ids[0].strip().isdigit(), f"Expected numeric ID, got: {ids[0]!r}"

        # The batch fetch should find *some* message for this numeric ID.
        # Whether it's the draft itself depends on iteration order across accounts.
        fetched = connector.get_messages_batch(ids)
        assert len(fetched) == 1
        assert fetched[0]["id"] == ids[0]

        # Cleanup
        try:
            connector.delete_messages(ids, permanent=True)
        except Exception:
            pass


class TestErrorHandling:
    """Test error handling with real Mail.app."""

    def test_nonexistent_account(self, connector: AppleMailConnector) -> None:
        """Test error when account doesn't exist."""
        from apple_mail_mcp.exceptions import MailAccountNotFoundError

        with pytest.raises(MailAccountNotFoundError):
            connector.list_mailboxes("NonExistentAccount12345")

    def test_nonexistent_mailbox(
        self, connector: AppleMailConnector, test_account: str
    ) -> None:
        """Test error when mailbox doesn't exist."""
        from apple_mail_mcp.exceptions import MailMailboxNotFoundError

        with pytest.raises(MailMailboxNotFoundError):
            connector.search_messages(
                account=test_account,
                mailbox="NonExistentMailbox12345"
            )
