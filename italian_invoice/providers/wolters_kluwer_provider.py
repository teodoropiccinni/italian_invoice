"""
Provider Wolters Kluwer per integrazione SDI
Integrazione con il servizio di intermediazione SDI di Wolters Kluwer
utilizzando OpenID Connect per l'autenticazione
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional

import frappe
import requests

from italian_invoice.providers.base import SDIProvider

# Configurazione logger
logger = logging.getLogger("italian_invoice.wolters_kluwer_provider")


class WoltersKluwerProvider(SDIProvider):
	"""Provider per servizi SDI di Wolters Kluwer"""

	# Configurazione OpenID Connect di Wolters Kluwer
	OPENID_CONFIG_URL = "https://login.wolterskluwer.eu/auth/core/.well-known/openid-configuration"
	
	# Default timeout per le richieste
	REQUEST_TIMEOUT = 30
	
	def __init__(self):
		self.logger = logger
		self.openid_config = None
		self.access_token = None
		self.token_expiry = None
		self._load_openid_config()
	
	def _load_openid_config(self):
		"""Carica la configurazione OpenID Connect dalla URL di Wolters Kluwer"""
		try:
			response = requests.get(self.OPENID_CONFIG_URL, timeout=self.REQUEST_TIMEOUT)
			response.raise_for_status()
			self.openid_config = response.json()
			self.logger.info("Configurazione OpenID Connect caricata con successo")
		except Exception as e:
			self.logger.error(f"Errore nel caricamento configurazione OpenID: {str(e)}")
			raise Exception(
				f"Impossibile caricare configurazione Wolters Kluwer: {str(e)}"
			)
	
	def _get_oauth_credentials(self, company):
		"""Recupera le credenziali OAuth dalla configurazione della company"""
		if not hasattr(company, "custom_wolters_kluwer_client_id"):
			raise ValueError(
				"Client ID Wolters Kluwer non configurato per la company"
			)
		if not hasattr(company, "custom_wolters_kluwer_client_secret"):
			raise ValueError(
				"Client Secret Wolters Kluwer non configurato per la company"
			)
		
		return {
			"client_id": company.custom_wolters_kluwer_client_id,
			"client_secret": company.custom_wolters_kluwer_client_secret,
			"redirect_uri": company.get(
				"custom_wolters_kluwer_redirect_uri",
				"http://localhost:8000/api/method/italian_invoice.api.sdi_provider.wolters_kluwer_callback"
			),
		}
	
	def _get_access_token(self, company) -> str:
		"""
		Ottiene un token di accesso OAuth valido
		Utilizza la cache se il token non è scaduto
		
		Args:
		    company: Documento Company
		
		Returns:
		    str: Token di accesso OAuth
		"""
		# Se il token è in cache e non scaduto, lo restituisce
		if self.access_token and self.token_expiry:
			if datetime.now() < self.token_expiry:
				return self.access_token
		
		# Altrimenti richiede un nuovo token
		try:
			credentials = self._get_oauth_credentials(company)
			
			token_endpoint = self.openid_config.get("token_endpoint")
			if not token_endpoint:
				raise ValueError("Token endpoint non trovato nella configurazione OpenID")
			
			payload = {
				"grant_type": "client_credentials",
				"client_id": credentials["client_id"],
				"client_secret": credentials["client_secret"],
				"scope": "sdi_api",
			}
			
			response = requests.post(
				token_endpoint,
				data=payload,
				timeout=self.REQUEST_TIMEOUT
			)
			response.raise_for_status()
			
			token_data = response.json()
			self.access_token = token_data["access_token"]
			
			# Imposta la scadenza del token (con buffer di 60 secondi)
			expires_in = token_data.get("expires_in", 3600)
			self.token_expiry = datetime.now() + timedelta(seconds=expires_in - 60)
			
			self.logger.info("Token di accesso ottenuto con successo")
			return self.access_token
			
		except Exception as e:
			self.logger.error(f"Errore nell'ottenimento del token: {str(e)}")
			raise Exception(f"Impossibile ottenere token di accesso: {str(e)}")
	
	def _get_api_url(self, endpoint: str) -> str:
		"""
		Costruisce l'URL per un endpoint dell'API di Wolters Kluwer
		
		Args:
		    endpoint: Nome dell'endpoint
		
		Returns:
		    str: URL completo dell'endpoint
		"""
		base_url = self.openid_config.get("sdi_api_url", "https://api.wolterskluwer.eu/sdi")
		return f"{base_url}/{endpoint}"
	
	def send_invoice(self, xml_content: str, doc, company) -> dict:
		"""
		Invia fattura al SDI tramite Wolters Kluwer
		
		Args:
		    xml_content: XML della fattura
		    doc: Documento fattura (Sales/Purchase Invoice)
		    company: Documento Company
		
		Returns:
		    dict: Risultato invio con uuid e stato
		"""
		try:
			token = self._get_access_token(company)
			
			url = self._get_api_url("invoices/send")
			
			headers = {
				"Authorization": f"Bearer {token}",
				"Content-Type": "application/xml",
			}
			
			response = requests.post(
				url,
				headers=headers,
				data=xml_content,
				timeout=self.REQUEST_TIMEOUT
			)
			
			if response.status_code in [200, 201]:
				response_data = response.json()
				uuid = response_data.get("uuid") or response_data.get("id")
				
				# Crea transazione SDI
				transazione_sdi = frappe.new_doc("Transazione SDI")
				transazione_sdi.tipo_fattura = doc.doctype
				transazione_sdi.fattura = doc.name
				transazione_sdi.stato_invio = "Inviata"
				transazione_sdi.uuid = uuid
				transazione_sdi.provider = "Wolters Kluwer"
				transazione_sdi.insert()
				
				# Aggiorna documento con riferimento transazione
				doc.custom_transazione_sdi = transazione_sdi.name
				doc.save()
				
				return {
					"success": True,
					"uuid": uuid,
					"message": f"Fattura inviata a Wolters Kluwer",
					"data": response_data,
				}
			else:
				error_msg = response.text
				try:
					error_msg = response.json().get("message", error_msg)
				except:
					pass
				
				return {
					"success": False,
					"message": f"Errore nell'invio: {error_msg}",
					"status_code": response.status_code,
				}
		
		except Exception as e:
			self.logger.exception(f"Errore invio fattura a Wolters Kluwer: {str(e)}")
			return {
				"success": False,
				"message": f"Errore invio fattura: {str(e)}",
			}
	
	def download_invoice(self, uuid: str, format: str, company) -> bytes:
		"""
		Scarica fattura dal SDI di Wolters Kluwer
		
		Args:
		    uuid: Identificativo fattura
		    format: Formato richiesto (xml, pdf, etc)
		    company: Documento Company
		
		Returns:
		    bytes: Contenuto del file
		"""
		try:
			token = self._get_access_token(company)
			
			format_lower = format.lower()
			url = self._get_api_url(f"invoices/{uuid}/download?format={format_lower}")
			
			headers = {
				"Authorization": f"Bearer {token}",
			}
			
			response = requests.get(
				url,
				headers=headers,
				timeout=self.REQUEST_TIMEOUT
			)
			response.raise_for_status()
			
			return response.content
		
		except Exception as e:
			self.logger.error(f"Errore download fattura: {str(e)}")
			raise Exception(f"Impossibile scaricare fattura: {str(e)}")
	
	def get_invoice_status(self, uuid: str, company) -> dict:
		"""
		Ottiene lo stato di una fattura
		
		Args:
		    uuid: Identificativo fattura
		    company: Documento Company
		
		Returns:
		    dict: Stato fattura con dettagli
		"""
		try:
			token = self._get_access_token(company)
			
			url = self._get_api_url(f"invoices/{uuid}/status")
			
			headers = {
				"Authorization": f"Bearer {token}",
			}
			
			response = requests.get(
				url,
				headers=headers,
				timeout=self.REQUEST_TIMEOUT
			)
			response.raise_for_status()
			
			status_data = response.json()
			
			return {
				"success": True,
				"status": status_data.get("status"),
				"data": status_data,
			}
		
		except Exception as e:
			self.logger.error(f"Errore recupero stato fattura: {str(e)}")
			return {
				"success": False,
				"message": f"Errore recupero stato: {str(e)}",
			}
	
	def handle_notification(self, notification_data: dict) -> dict:
		"""
		Gestisce notifiche SDI da Wolters Kluwer
		
		Args:
		    notification_data: Dati notifica ricevuti
		
		Returns:
		    dict: Risultato elaborazione
		"""
		try:
			uuid = notification_data.get("uuid") or notification_data.get("id")
			status = notification_data.get("status")
			
			if not uuid or not status:
				return {
					"success": False,
					"message": "Dati notifica incompleti",
				}
			
			# Aggiorna la transazione SDI
			transazioni = frappe.get_list(
				"Transazione SDI",
				filters={"uuid": uuid},
				fields=["name"]
			)
			
			if transazioni:
				transazione = frappe.get_doc("Transazione SDI", transazioni[0]["name"])
				transazione.stato_invio = status
				transazione.data_aggiornamento = datetime.now()
				transazione.risposta_provider = json.dumps(notification_data)
				transazione.save()
				
				return {
					"success": True,
					"message": f"Transazione aggiornata: {status}",
					"uuid": uuid,
				}
			else:
				self.logger.warning(f"Transazione non trovata per UUID: {uuid}")
				return {
					"success": False,
					"message": f"Transazione non trovata per UUID: {uuid}",
				}
		
		except Exception as e:
			self.logger.exception(f"Errore elaborazione notifica: {str(e)}")
			return {
				"success": False,
				"message": f"Errore elaborazione notifica: {str(e)}",
			}
	
	def configure_webhooks(self, company) -> dict:
		"""
		Configura webhook per notifiche SDI presso Wolters Kluwer
		
		Args:
		    company: Documento Company
		
		Returns:
		    dict: Risultato configurazione
		"""
		try:
			token = self._get_access_token(company)
			
			# URL del webhook nel nostro sistema
			webhook_url = frappe.utils.get_url(
				"/api/method/italian_invoice.api.sdi_provider.wolters_kluwer_webhook"
			)
			
			url = self._get_api_url("webhooks/configure")
			
			headers = {
				"Authorization": f"Bearer {token}",
				"Content-Type": "application/json",
			}
			
			payload = {
				"webhook_url": webhook_url,
				"events": [
					"invoice.sent",
					"invoice.accepted",
					"invoice.rejected",
					"invoice.delivered",
					"invoice.failed",
				],
				"company_piva": company.tax_id,
			}
			
			response = requests.post(
				url,
				headers=headers,
				json=payload,
				timeout=self.REQUEST_TIMEOUT
			)
			response.raise_for_status()
			
			webhook_data = response.json()
			
			# Salva la configurazione webhook nella company
			company.custom_wolters_kluwer_webhook_id = webhook_data.get("webhook_id")
			company.save()
			
			return {
				"success": True,
				"message": "Webhook configurato con successo",
				"webhook_id": webhook_data.get("webhook_id"),
			}
		
		except Exception as e:
			self.logger.error(f"Errore configurazione webhook: {str(e)}")
			return {
				"success": False,
				"message": f"Errore configurazione webhook: {str(e)}",
			}
	
	def handle_webhook(self, endpoint: str, data: dict) -> dict:
		"""
		Gestisce chiamate webhook in arrivo da Wolters Kluwer
		
		Args:
		    endpoint: Nome endpoint webhook
		    data: Dati ricevuti dal webhook
		
		Returns:
		    dict: Risultato elaborazione
		"""
		try:
			if endpoint == "invoice_notification":
				return self.handle_notification(data)
			else:
				self.logger.warning(f"Endpoint webhook sconosciuto: {endpoint}")
				return {
					"success": False,
					"message": f"Endpoint non riconosciuto: {endpoint}",
				}
		
		except Exception as e:
			self.logger.exception(f"Errore gestione webhook: {str(e)}")
			return {
				"success": False,
				"message": f"Errore gestione webhook: {str(e)}",
			}
	
	def setup_business_register(self, company, config: dict) -> dict:
		"""
		Registra il business presso Wolters Kluwer
		
		Args:
		    company: Documento Company
		    config: Configurazione con dati aziendali
		
		Returns:
		    dict: Risultato registrazione
		"""
		try:
			token = self._get_access_token(company)
			
			url = self._get_api_url("business/register")
			
			headers = {
				"Authorization": f"Bearer {token}",
				"Content-Type": "application/json",
			}
			
			payload = {
				"company_name": company.company_name,
				"piva": company.tax_id,
				"codice_fiscale": company.get("custom_codice_fiscale"),
				"email": company.email,
				"phone": company.phone_no,
				"address": f"{company.address_line1}, {company.city}",
			}
			payload.update(config)
			
			response = requests.post(
				url,
				headers=headers,
				json=payload,
				timeout=self.REQUEST_TIMEOUT
			)
			response.raise_for_status()
			
			return {
				"success": True,
				"message": "Business registrato con successo presso Wolters Kluwer",
				"data": response.json(),
			}
		
		except Exception as e:
			self.logger.error(f"Errore registrazione business: {str(e)}")
			return {
				"success": False,
				"message": f"Errore registrazione: {str(e)}",
			}
