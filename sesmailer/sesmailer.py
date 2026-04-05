import os
import mimetypes
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

import boto3


class SESMailer:
    def __init__(self, ses_client=None) -> None:
        self.charset = "UTF-8"
        self._isHTML = False
        self.Subject = None
        self.Body = None
        self.AltBody = None
        self._ToAddresses = []
        self._From = None
        self._Cc = []
        self._Bcc = []
        self._ReplyTo = []
        self._attachments = {}

        self._ses_client = ses_client or boto3.client("ses")

    def set_from(self, from_email: str, from_name: str = None):
        if from_name:
            self._From = f"{from_name} <{from_email}>"
        else:
            self._From = from_email
        return self

    def add_address(self, mail_address: str, address_name: str = None):
        if address_name:
            self._ToAddresses.append(f"{address_name} <{mail_address}>")
        else:
            self._ToAddresses.append(mail_address)
        return self

    def add_cc(self, mail_address: str, address_name: str = None):
        if address_name:
            self._Cc.append(f"{address_name} <{mail_address}>")
        else:
            self._Cc.append(mail_address)
        return self

    def add_bcc(self, mail_address: str, address_name: str = None):
        if address_name:
            self._Bcc.append(f"{address_name} <{mail_address}>")
        else:
            self._Bcc.append(mail_address)
        return self

    def add_reply_to(self, mail_address: str, address_name: str = None):
        if address_name:
            self._ReplyTo.append(f"{address_name} <{mail_address}>")
        else:
            self._ReplyTo.append(mail_address)
        return self

    def add_attachment(self, file_path: str, filename: str = None):
        self._attachments[file_path] = filename
        return self

    def is_html(self, is_html: bool):
        self._isHTML = is_html
        return self

    def send(self):
        if self._attachments:
            return self._send_mail_with_attachments()

        return self._send_mail()

    def _send_mail(self):
        mail_body = {}
        if self._isHTML:
            mail_body["Html"] = {"Data": self.Body, "Charset": self.charset}
            if self.AltBody:
                mail_body["Text"] = {"Data": self.AltBody, "Charset": self.charset}
        else:
            mail_body["Text"] = {"Data": self.Body, "Charset": self.charset}

        destination = {"ToAddresses": self._ToAddresses}
        if self._Cc:
            destination["CcAddresses"] = self._Cc
        if self._Bcc:
            destination["BccAddresses"] = self._Bcc

        kwargs = {
            "Source": self._From,
            "Destination": destination,
            "Message": {
                "Subject": {"Data": self.Subject, "Charset": self.charset},
                "Body": mail_body,
            },
        }
        if self._ReplyTo:
            kwargs["ReplyToAddresses"] = self._ReplyTo

        self._ses_client.send_email(**kwargs)

    def _send_mail_with_attachments(self):
        msg = MIMEMultipart()
        msg["Subject"] = self.Subject
        msg["From"] = self._From
        msg["To"] = ", ".join(self._ToAddresses)
        if self._Cc:
            msg["Cc"] = ", ".join(self._Cc)
        if self._Bcc:
            msg["Bcc"] = ", ".join(self._Bcc)
        if self._ReplyTo:
            msg["Reply-To"] = ", ".join(self._ReplyTo)
        subtype = "html" if self._isHTML else "plain"
        msg.attach(MIMEText(self.Body, subtype))

        self._prepare_attachments(msg)

        destinations = self._ToAddresses + self._Cc + self._Bcc
        self._ses_client.send_raw_email(
            Source=self._From,
            Destinations=destinations,
            RawMessage={"Data": msg.as_string()},
        )

    def _prepare_attachments(self, raw_message):
        for path, name in self._attachments.items():
            _, ext = os.path.splitext(name)
            if not ext:
                _, ext = os.path.splitext(path)
                name = f"{name}{ext}"

            content_type, _ = mimetypes.guess_type(name)
            if content_type is None:
                content_type = "application/octet-stream"
            _, subtype = content_type.split("/", 1)

            with open(path, "rb") as f:
                attachment = MIMEApplication(f.read(), _subtype=subtype)
                attachment.add_header("Content-Disposition", "attachment", filename=name)
                raw_message.attach(attachment)
