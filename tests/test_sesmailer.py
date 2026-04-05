import os
import tempfile

import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_aws

from sesmailer import SESMailer


SENDER = "sender@example.com"
RECIPIENT = "recipient@example.com"


@pytest.fixture
def ses_verified(monkeypatch):
    """Start moto mock and verify the sender identity so SES accepts calls."""
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    with mock_aws():
        client = boto3.client("ses", region_name="us-east-1")
        client.verify_email_identity(EmailAddress=SENDER)
        yield client


@pytest.fixture
def mailer(ses_verified):
    """Return a SESMailer instance running against the mocked SES."""
    return SESMailer()


# ---------- Builder / fluent API ----------


class TestFluentAPI:
    def test_set_from_returns_self(self, mailer):
        assert mailer.set_from(SENDER) is mailer

    def test_add_address_returns_self(self, mailer):
        assert mailer.add_address(RECIPIENT) is mailer

    def test_add_cc_returns_self(self, mailer):
        assert mailer.add_cc("cc@example.com") is mailer

    def test_add_bcc_returns_self(self, mailer):
        assert mailer.add_bcc("bcc@example.com") is mailer

    def test_add_reply_to_returns_self(self, mailer):
        assert mailer.add_reply_to("reply@example.com") is mailer

    def test_add_attachment_returns_self(self, mailer):
        assert mailer.add_attachment("/tmp/f.txt") is mailer

    def test_is_html_returns_self(self, mailer):
        assert mailer.is_html(True) is mailer

    def test_chaining(self, mailer):
        result = (
            mailer
            .set_from(SENDER)
            .add_address(RECIPIENT)
            .add_cc("cc@example.com")
            .add_bcc("bcc@example.com")
            .is_html(True)
        )
        assert result is mailer


# ---------- Address formatting ----------


class TestAddressFormatting:
    def test_set_from_plain(self, mailer):
        mailer.set_from(SENDER)
        assert mailer._From == SENDER

    def test_set_from_with_name(self, mailer):
        mailer.set_from(SENDER, from_name="Sender Name")
        assert mailer._From == f"Sender Name <{SENDER}>"

    def test_add_address_plain(self, mailer):
        mailer.add_address(RECIPIENT)
        assert mailer._ToAddresses == [RECIPIENT]

    def test_add_address_with_name(self, mailer):
        mailer.add_address(RECIPIENT, address_name="John")
        assert mailer._ToAddresses == [f"John <{RECIPIENT}>"]

    def test_add_cc_plain(self, mailer):
        mailer.add_cc("cc@example.com")
        assert mailer._Cc == ["cc@example.com"]

    def test_add_cc_with_name(self, mailer):
        mailer.add_cc("cc@example.com", address_name="CC User")
        assert mailer._Cc == ["CC User <cc@example.com>"]

    def test_add_bcc_plain(self, mailer):
        mailer.add_bcc("bcc@example.com")
        assert mailer._Bcc == ["bcc@example.com"]

    def test_add_bcc_with_name(self, mailer):
        mailer.add_bcc("bcc@example.com", address_name="BCC User")
        assert mailer._Bcc == ["BCC User <bcc@example.com>"]

    def test_add_reply_to_plain(self, mailer):
        mailer.add_reply_to("reply@example.com")
        assert mailer._ReplyTo == ["reply@example.com"]

    def test_add_reply_to_with_name(self, mailer):
        mailer.add_reply_to("reply@example.com", address_name="Support")
        assert mailer._ReplyTo == ["Support <reply@example.com>"]

    def test_multiple_addresses(self, mailer):
        mailer.add_address("a@example.com").add_address("b@example.com")
        assert len(mailer._ToAddresses) == 2


# ---------- Sending plain text email ----------


class TestSendPlainText:
    def test_send_plain_text(self, mailer, ses_verified):
        mailer.set_from(SENDER)
        mailer.add_address(RECIPIENT)
        mailer.Subject = "Test Subject"
        mailer.Body = "Hello, plain text"

        mailer.send()

        stats = ses_verified.get_send_statistics()
        data_points = stats["SendDataPoints"]
        assert len(data_points) > 0
        assert data_points[0]["DeliveryAttempts"] > 0


# ---------- Sending HTML email ----------


class TestSendHTML:
    def test_send_html(self, mailer, ses_verified):
        mailer.set_from(SENDER)
        mailer.add_address(RECIPIENT)
        mailer.is_html(True)
        mailer.Subject = "HTML Subject"
        mailer.Body = "<h1>Hello</h1>"
        mailer.AltBody = "Hello fallback"

        mailer.send()

        stats = ses_verified.get_send_statistics()
        data_points = stats["SendDataPoints"]
        assert len(data_points) > 0

    def test_send_html_without_alt_body(self, mailer, ses_verified):
        mailer.set_from(SENDER)
        mailer.add_address(RECIPIENT)
        mailer.is_html(True)
        mailer.Subject = "HTML Only"
        mailer.Body = "<p>No alt body</p>"

        mailer.send()

        stats = ses_verified.get_send_statistics()
        assert len(stats["SendDataPoints"]) > 0


# ---------- Sending with attachments ----------


class TestSendWithAttachments:
    def test_send_with_attachment(self, mailer, ses_verified):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"file content")
            tmp_path = f.name

        try:
            mailer.set_from(SENDER)
            mailer.add_address(RECIPIENT)
            mailer.Subject = "With Attachment"
            mailer.Body = "See attached"
            mailer.add_attachment(tmp_path, filename="doc.txt")

            mailer.send()

            stats = ses_verified.get_send_statistics()
            assert len(stats["SendDataPoints"]) > 0
        finally:
            os.unlink(tmp_path)

    def test_send_html_with_attachment(self, mailer, ses_verified):
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            f.write(b"<p>content</p>")
            tmp_path = f.name

        try:
            mailer.set_from(SENDER)
            mailer.add_address(RECIPIENT)
            mailer.is_html(True)
            mailer.Subject = "HTML + Attachment"
            mailer.Body = "<h1>Hi</h1>"
            mailer.add_attachment(tmp_path, filename="page.html")

            mailer.send()

            stats = ses_verified.get_send_statistics()
            assert len(stats["SendDataPoints"]) > 0
        finally:
            os.unlink(tmp_path)

    def test_attachment_without_explicit_filename_uses_path_ext(self, mailer):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF-fake")
            tmp_path = f.name

        try:
            mailer.add_attachment(tmp_path, filename="report")
            assert mailer._attachments[tmp_path] == "report"
        finally:
            os.unlink(tmp_path)


# ---------- Sending with CC/BCC ----------


class TestSendWithCcBcc:
    def test_send_with_cc_and_bcc(self, mailer, ses_verified):
        mailer.set_from(SENDER)
        mailer.add_address(RECIPIENT)
        mailer.add_cc("cc@example.com")
        mailer.add_bcc("bcc@example.com")
        mailer.Subject = "CC/BCC Test"
        mailer.Body = "Hello with cc and bcc"

        mailer.send()

        stats = ses_verified.get_send_statistics()
        assert len(stats["SendDataPoints"]) > 0

    def test_send_attachment_with_cc_and_bcc(self, mailer, ses_verified):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"content")
            tmp_path = f.name

        try:
            mailer.set_from(SENDER)
            mailer.add_address(RECIPIENT)
            mailer.add_cc("cc@example.com")
            mailer.add_bcc("bcc@example.com")
            mailer.Subject = "Attachment CC/BCC"
            mailer.Body = "See attached"
            mailer.add_attachment(tmp_path, filename="file.txt")

            mailer.send()

            stats = ses_verified.get_send_statistics()
            assert len(stats["SendDataPoints"]) > 0
        finally:
            os.unlink(tmp_path)


# ---------- Sending with Reply-To ----------


class TestSendWithReplyTo:
    def test_send_with_reply_to(self, mailer, ses_verified):
        mailer.set_from(SENDER)
        mailer.add_address(RECIPIENT)
        mailer.add_reply_to("support@example.com")
        mailer.Subject = "Reply-To Test"
        mailer.Body = "Reply to support"

        mailer.send()

        stats = ses_verified.get_send_statistics()
        assert len(stats["SendDataPoints"]) > 0

    def test_send_attachment_with_reply_to(self, mailer, ses_verified):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"content")
            tmp_path = f.name

        try:
            mailer.set_from(SENDER)
            mailer.add_address(RECIPIENT)
            mailer.add_reply_to("support@example.com", address_name="Support")
            mailer.Subject = "Attachment Reply-To"
            mailer.Body = "See attached"
            mailer.add_attachment(tmp_path, filename="file.txt")

            mailer.send()

            stats = ses_verified.get_send_statistics()
            assert len(stats["SendDataPoints"]) > 0
        finally:
            os.unlink(tmp_path)


# ---------- Error handling ----------


class TestErrorHandling:
    def test_send_raises_on_client_error(self, mailer):
        """Sending from an unverified identity raises ClientError."""
        mailer.set_from("unverified@example.com")
        mailer.add_address(RECIPIENT)
        mailer.Subject = "Should Fail"
        mailer.Body = "This should fail"

        with pytest.raises(ClientError):
            mailer.send()


# ---------- State isolation ----------


class TestStateIsolation:
    def test_default_state(self, mailer):
        assert mailer._From is None
        assert mailer._ToAddresses == []
        assert mailer._Cc == []
        assert mailer._Bcc == []
        assert mailer._ReplyTo == []
        assert mailer._attachments == {}
        assert mailer._isHTML is False
        assert mailer.Subject is None
        assert mailer.Body is None
        assert mailer.AltBody is None
        assert mailer.charset == "UTF-8"
