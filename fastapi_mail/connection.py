import logging
import smtplib
import certifi
from ssl import SSLContext, CERT_REQUIRED

from pydantic import BaseSettings as Settings

from fastapi_mail.config import ConnectionConfig
from fastapi_mail.errors import ConnectionErrors, PydanticClassRequired

logger = logging.getLogger(__name__)


class Connection:
    """
    Manages Connection to provided email service with its credentials
    """

    def __init__(self, settings: ConnectionConfig):

        if not issubclass(settings.__class__, Settings):
            raise PydanticClassRequired(
                """\
Email configuration should be provided from ConnectionConfig class, \
check example below:

from fastmail import ConnectionConfig
conf = Connection(
    MAIL_USERNAME="your_username",
    MAIL_PASSWORD="your_pass",
    MAIL_FROM="your_from_email",
    MAIL_PORT=587,
    MAIL_SERVER="email_service",
    MAIL_TLS=True,
    MAIL_SSL=False
)
"""
            )

        self.settings = settings.dict()

    async def __aenter__(self):  # setting up a connection
        await self._configure_connection()
        return self

    async def __aexit__(self, exc_type, exc, tb):  # closing the connection
        if not self.settings.get('SUPPRESS_SEND'):   # for test environ
            self.session.quit()

    async def _configure_connection(self):
        try:
            validate_certs = self.settings.get('VALIDATE_CERTS')
            ssl_context = SSLContext()
            if validate_certs:
                logger.debug("'VALIDATE_CERTS' set, configuring SSL-Context.")
                ssl_context.check_hostname = bool(validate_certs)
                ssl_context.verify_mode = CERT_REQUIRED
                ssl_context.load_verify_locations(cafile=certifi.where())
            if self.settings.get('MAIL_SSL'):
                logger.debug("'MAIL_SSL' set, configuring SMTP-Client with implicit TLS.")
                self.session = smtplib.SMTP_SSL(
                    self.settings.get('MAIL_SERVER'),
                    port=self.settings.get('MAIL_PORT')
                )
            else:
                logger.debug("'MAIL_SSL' unset, configuring SMTP-Client.")
                self.session = smtplib.SMTP(
                    self.settings.get('MAIL_SERVER'),
                    port=self.settings.get('MAIL_PORT')
                )
            if self.settings.get('MAIL_TLS'):
                logger.debug("'MAIL_TLS' set, beginning STARTTLS.")
                self.session.starttls(context=ssl_context)
                logger.debug("STARTTLS accepted.")

            if not self.settings.get('SUPPRESS_SEND'):
                logger.debug("Attempting Connection...")
                self.session.connect()
                logger.debug("Connection successful!")

                if self.settings.get('USE_CREDENTIALS'):
                    logger.debug("'USE_CREDENTIALS' set, logging in using credentials.")
                    self.session.login(
                        self.settings.get('MAIL_USERNAME'), self.settings.get('MAIL_PASSWORD')
                    )

        except Exception as error:
            raise ConnectionErrors(
                f'Exception raised {error}, check your credentials or email service configuration'
            )
