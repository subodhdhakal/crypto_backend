import logging

class Logger:
    """
    Configures and provides a reusable logger instance.
    """
    def __init__(self, log_file: str = "app.log"):
        # Set up logging configuration
        logging.basicConfig(
            level=logging.INFO,  # Default log level
            format="%(asctime)s [%(levelname)s]: %(message)s",
            handlers=[
                logging.StreamHandler(),      # Log to console
                logging.FileHandler(log_file, encoding='utf-8')  # Log to file
            ]
        )
        # Get the logger instance
        self.logger = logging.getLogger("CryptoVolumeTracker")

        # Suppress Twilio library logs by setting their level to WARNING
        logging.getLogger("twilio").setLevel(logging.WARNING)

        # Supress Flask/Werkzeug logging level to WARNING
        logging.getLogger('werkzeug').setLevel(logging.WARNING)

    def get_logger(self):
        return self.logger

# Initialize a global logger instance
log = Logger().get_logger()
