"""
API endpoints per integrazione Wolters Kluwer
Gestisce callback OAuth e webhook di notifiche
"""

import json
import logging

import frappe
from frappe import whitelist
from frappe.exceptions import Forbidden

from italian_invoice.utilities.fatture import get_sdi_provider

logger = logging.getLogger("italian_invoice.api.sdi_provider.wolters_kluwer")


@whitelist(allow_guest=True)
def wolters_kluwer_callback():
	"""
	Callback OAuth di Wolters Kluwer
	Riceve il codice di autorizzazione e lo scambia con un token
	"""
	try:
		import frappe
		from frappe.auth import get_current_user
		from urllib.parse import parse_qs, urlparse
		
		# Ottieni parametri dalla query string
		code = frappe.request.args.get("code")
		state = frappe.request.args.get("state")
		error = frappe.request.args.get("error")
		
		if error:
			frappe.respond_as_json(
				{
					"success": False,
					"error": error,
					"error_description": frappe.request.args.get("error_description"),
				},
				status_code=400,
			)
			return
		
		if not code or not state:
			frappe.respond_as_json(
				{
					"success": False,
					"message": "Missing authorization code or state",
				},
				status_code=400,
			)
			return
		
		# Verifica lo state per CSRF protection
		session_state = frappe.session.get("wolterskluwer_oauth_state")
		if not session_state or session_state != state:
			frappe.respond_as_json(
				{
					"success": False,
					"message": "Invalid state parameter",
				},
				status_code=403,
			)
			return
		
		company_name = frappe.session.get("wolterskluwer_oauth_company")
		if not company_name:
			frappe.respond_as_json(
				{
					"success": False,
					"message": "Company not found in session",
				},
				status_code=400,
			)
			return
		
		# Scambia il codice con un token
		provider = get_sdi_provider(company_name)
		
		try:
			token_endpoint = provider.openid_config.get("token_endpoint")
			company = frappe.get_doc("Company", company_name)
			credentials = provider._get_oauth_credentials(company)
			
			payload = {
				"grant_type": "authorization_code",
				"code": code,
				"client_id": credentials["client_id"],
				"client_secret": credentials["client_secret"],
				"redirect_uri": credentials["redirect_uri"],
			}
			
			import requests
			response = requests.post(token_endpoint, data=payload, timeout=30)
			response.raise_for_status()
			
			token_data = response.json()
			
			# Salva il token nella company
			company.custom_wolters_kluwer_access_token = token_data["access_token"]
			if "refresh_token" in token_data:
				company.custom_wolters_kluwer_refresh_token = token_data["refresh_token"]
			company.save()
			
			# Pulisci la sessione
			frappe.session["wolterskluwer_oauth_state"] = None
			frappe.session["wolterskluwer_oauth_company"] = None
			
			frappe.respond_as_json(
				{
					"success": True,
					"message": "Authorization successful",
					"company": company_name,
				}
			)
		
		except Exception as e:
			logger.error(f"Errore scambio token: {str(e)}")
			frappe.respond_as_json(
				{
					"success": False,
					"message": f"Token exchange failed: {str(e)}",
				},
				status_code=400,
			)
	
	except Exception as e:
		logger.exception(f"Errore callback OAuth: {str(e)}")
		frappe.respond_as_json(
			{
				"success": False,
				"message": f"Callback error: {str(e)}",
			},
			status_code=500,
		)


@whitelist(allow_guest=True)
def wolters_kluwer_webhook():
	"""
	Webhook per notifiche di Wolters Kluwer
	Riceve notifiche sullo stato delle fatture
	"""
	try:
		# Ottieni il corpo della richiesta
		data = frappe.request.get_json() or {}
		
		# Verifica la firma della richiesta (consigliato per sicurezza)
		if not _verify_webhook_signature(data):
			logger.warning("Webhook signature verification failed")
			frappe.respond_as_json(
				{
					"success": False,
					"message": "Invalid signature",
				},
				status_code=403,
			)
			return
		
		# Determina il provider e la company dalla notifica
		piva = data.get("company_piva")
		if not piva:
			frappe.respond_as_json(
				{
					"success": False,
					"message": "Missing company_piva in notification",
				},
				status_code=400,
			)
			return
		
		# Trova la company con questa partita IVA
		companies = frappe.get_list(
			"Company",
			filters={"tax_id": piva},
			fields=["name"]
		)
		
		if not companies:
			logger.warning(f"Company not found for PIVA: {piva}")
			frappe.respond_as_json(
				{
					"success": False,
					"message": f"Company not found for PIVA: {piva}",
				},
				status_code=404,
			)
			return
		
		company = companies[0]["name"]
		provider = get_sdi_provider(company)
		
		# Elabora la notifica
		result = provider.handle_notification(data)
		
		if result["success"]:
			frappe.respond_as_json(result, status_code=200)
		else:
			frappe.respond_as_json(result, status_code=400)
	
	except Exception as e:
		logger.exception(f"Errore webhook Wolters Kluwer: {str(e)}")
		frappe.respond_as_json(
			{
				"success": False,
				"message": f"Webhook error: {str(e)}",
			},
			status_code=500,
		)


def _verify_webhook_signature(data: dict) -> bool:
	"""
	Verifica la firma della richiesta webhook
	Implementa HMAC-SHA256 come consigliato da Wolters Kluwer
	
	Args:
	    data: Dati del webhook
	
	Returns:
	    bool: True se la firma è valida
	"""
	try:
		import hashlib
		import hmac
		
		# Ottieni la firma dall'header
		signature = frappe.request.headers.get("X-Wolters-Kluwer-Signature")
		if not signature:
			logger.warning("Missing webhook signature in headers")
			return False
		
		# Ottieni la chiave segreta (dovrebbe essere salvata in settings)
		webhook_secret = frappe.get_value(
			"Italian Invoice Settings",
			"Italian Invoice Settings",
			"custom_wolters_kluwer_webhook_secret"
		)
		
		if not webhook_secret:
			logger.warning("Webhook secret not configured")
			return False
		
		# Calcola la firma attesa
		payload = frappe.request.get_data()
		expected_signature = hmac.new(
			webhook_secret.encode(),
			payload,
			hashlib.sha256
		).hexdigest()
		
		# Confronta le firme usando constant-time comparison
		return hmac.compare_digest(signature, expected_signature)
	
	except Exception as e:
		logger.error(f"Errore verifica firma webhook: {str(e)}")
		return False


@whitelist()
def authorize_wolters_kluwer(company_name: str) -> dict:
	"""
	Avvia il flusso OAuth per Wolters Kluwer
	Genera URL di autorizzazione da inviare all'utente
	
	Args:
	    company_name: Nome della company
	
	Returns:
	    dict: URL di autorizzazione e stato
	"""
	try:
		# Verifiche di sicurezza
		if not frappe.db.exists("Company", company_name):
			frappe.throw(f"Company non trovata: {company_name}")
		
		# Verifica permessi utente
		if not frappe.has_permission("Company", ptype="read", doc=company_name):
			raise Forbidden(f"Non hai permesso di accedere alla company {company_name}")
		
		company = frappe.get_doc("Company", company_name)
		provider = get_sdi_provider(company_name)
		
		# Genera uno state casuale per CSRF protection
		import secrets
		import json
		
		state = secrets.token_urlsafe(32)
		
		# Salva lo state in sessione
		frappe.session["wolterskluwer_oauth_state"] = state
		frappe.session["wolterskluwer_oauth_company"] = company_name
		
		# Ottieni le credenziali
		credentials = provider._get_oauth_credentials(company)
		
		# Costruisci l'URL di autorizzazione
		auth_endpoint = provider.openid_config.get("authorization_endpoint")
		
		authorization_url = (
			f"{auth_endpoint}?"
			f"client_id={credentials['client_id']}&"
			f"response_type=code&"
			f"scope=sdi_api&"
			f"redirect_uri={credentials['redirect_uri']}&"
			f"state={state}"
		)
		
		return {
			"authorization_url": authorization_url,
			"state": state,
			"company": company_name,
		}
	
	except Exception as e:
		logger.exception(f"Errore autorizzazione Wolters Kluwer: {str(e)}")
		frappe.throw(f"Errore autorizzazione: {str(e)}")


@whitelist()
def test_wolters_kluwer_connection(company_name: str) -> dict:
	"""
	Testa la connessione con Wolters Kluwer
	Valida le credenziali e la configurazione
	
	Args:
	    company_name: Nome della company
	
	Returns:
	    dict: Risultato test
	"""
	try:
		# Verifiche di sicurezza
		if not frappe.db.exists("Company", company_name):
			frappe.throw(f"Company non trovata: {company_name}")
		
		if not frappe.has_permission("Company", ptype="read", doc=company_name):
			raise Forbidden(f"Non hai permesso di accedere alla company {company_name}")
		
		provider = get_sdi_provider(company_name)
		company = frappe.get_doc("Company", company_name)
		
		# Tenta di ottenere un token
		try:
			token = provider._get_access_token(company)
			return {
				"success": True,
				"message": "Connessione riuscita",
				"token_obtained": bool(token),
			}
		except Exception as e:
			return {
				"success": False,
				"message": f"Errore connessione: {str(e)}",
			}
	
	except Exception as e:
		logger.exception(f"Errore test connessione: {str(e)}")
		frappe.throw(f"Errore test: {str(e)}")
