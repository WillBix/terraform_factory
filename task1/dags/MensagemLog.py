import logging

class MensagemLog:

	logger = logging.getLogger("MensagemLog")
	logger.setLevel(logging.INFO)
	handler = logging.StreamHandler()
	formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
	handler.setFormatter(formatter)
	logger.addHandler(handler)

	@staticmethod
	def exibir_mensagem(level, message):
		if level == "INFO":
			MensagemLog.logger.info(message)
		elif level == "WARNING":
			MensagemLog.logger.warning(message)
		elif level == "ERROR":
			MensagemLog.logger.error(message)
		else:
			MensagemLog.logger.debug(message)