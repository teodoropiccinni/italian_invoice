"""
Test per Wolters Kluwer Provider
Testa l'integrazione con Wolters Kluwer SDI
"""

from unittest.mock import MagicMock, patch
from frappe.tests.utils import FrappeTestCase
import frappe

from italian_invoice.providers.wolters_kluwer_provider import WoltersKluwerProvider


class TestWoltersKluwerProvider(FrappeTestCase):
	"""Test cases per WoltersKluwerProvider"""

	def setUp(self):
		"""Setup per i test"""
		self.provider = WoltersKluwerProvider()

	@patch('requests.get')
	def test_openid_config_loading(self, mock_get):
		"""Test caricamento configurazione OpenID"""
		mock_response = MagicMock()
		mock_response.json.return_value = {
			"issuer": "https://login.wolterskluwer.eu",
			"authorization_endpoint": "https://login.wolterskluwer.eu/auth/core/authorize",
			"token_endpoint": "https://login.wolterskluwer.eu/auth/core/token",
			"userinfo_endpoint": "https://login.wolterskluwer.eu/auth/core/userinfo",
		}
		mock_get.return_value = mock_response

		# Ricrea provider per triggerare il caricamento
		with patch.object(WoltersKluwerProvider, '_load_openid_config') as mock_load:
			provider = WoltersKluwerProvider()
			mock_load.assert_called_once()

	def test_oauth_credentials_extraction(self):
		"""Test estrazione credenziali OAuth"""
		# Mock company
		company = MagicMock()
		company.custom_wolters_kluwer_client_id = "test_client_id"
		company.custom_wolters_kluwer_client_secret = "test_client_secret"
		company.custom_wolters_kluwer_redirect_uri = "http://localhost:8000/callback"

		credentials = self.provider._get_oauth_credentials(company)

		self.assertEqual(credentials["client_id"], "test_client_id")
		self.assertEqual(credentials["client_secret"], "test_client_secret")
		self.assertEqual(
			credentials["redirect_uri"],
			"http://localhost:8000/callback"
		)

	@patch('requests.post')
	def test_get_access_token(self, mock_post):
		"""Test ottenimento token di accesso"""
		mock_response = MagicMock()
		mock_response.json.return_value = {
			"access_token": "test_token_12345",
			"token_type": "Bearer",
			"expires_in": 3600,
		}
		mock_post.return_value = mock_response

		# Mock company and openid_config
		company = MagicMock()
		company.custom_wolters_kluwer_client_id = "test_client_id"
		company.custom_wolters_kluwer_client_secret = "test_client_secret"

		self.provider.openid_config = {
			"token_endpoint": "https://login.wolterskluwer.eu/auth/core/token"
		}

		with patch.object(self.provider, '_get_oauth_credentials') as mock_creds:
			mock_creds.return_value = {
				"client_id": "test_client_id",
				"client_secret": "test_client_secret",
			}

			token = self.provider._get_access_token(company)

			self.assertEqual(token, "test_token_12345")
			self.assertIsNotNone(self.provider.token_expiry)

	@patch('requests.post')
	@patch.object(WoltersKluwerProvider, '_get_access_token')
	def test_send_invoice(self, mock_get_token, mock_post):
		"""Test invio fattura"""
		mock_get_token.return_value = "test_token"

		mock_response = MagicMock()
		mock_response.status_code = 200
		mock_response.json.return_value = {
			"uuid": "550e8400-e29b-41d4-a716-446655440000",
			"status": "success",
		}
		mock_post.return_value = mock_response

		# Mock documents
		company = MagicMock()
		doc = MagicMock()
		doc.doctype = "Sales Invoice"
		doc.name = "SINV-2025-00001"

		self.provider.openid_config = {
			"sdi_api_url": "https://api.wolterskluwer.eu/sdi"
		}

		xml_content = "<Fattura>Test</Fattura>"

		# Mock frappe.new_doc and save
		with patch('frappe.new_doc') as mock_new_doc:
			transazione = MagicMock()
			mock_new_doc.return_value = transazione

			result = self.provider.send_invoice(xml_content, doc, company)

			self.assertTrue(result["success"])
			self.assertEqual(
				result["uuid"],
				"550e8400-e29b-41d4-a716-446655440000"
			)
			mock_new_doc.assert_called_once_with("Transazione SDI")

	@patch('requests.get')
	@patch.object(WoltersKluwerProvider, '_get_access_token')
	def test_get_invoice_status(self, mock_get_token, mock_get):
		"""Test recupero stato fattura"""
		mock_get_token.return_value = "test_token"

		mock_response = MagicMock()
		mock_response.status_code = 200
		mock_response.json.return_value = {
			"uuid": "550e8400-e29b-41d4-a716-446655440000",
			"status": "delivered",
			"delivery_date": "2025-01-18T10:30:00Z",
		}
		mock_get.return_value = mock_response

		company = MagicMock()

		self.provider.openid_config = {
			"sdi_api_url": "https://api.wolterskluwer.eu/sdi"
		}

		result = self.provider.get_invoice_status(
			"550e8400-e29b-41d4-a716-446655440000",
			company
		)

		self.assertTrue(result["success"])
		self.assertEqual(result["status"], "delivered")

	def test_handle_notification(self):
		"""Test gestione notifiche"""
		notification_data = {
			"uuid": "550e8400-e29b-41d4-a716-446655440000",
			"status": "accepted",
		}

		with patch('frappe.get_list') as mock_get_list:
			with patch('frappe.get_doc') as mock_get_doc:
				# Mock transazione trovata
				mock_get_list.return_value = [
					{"name": "SDI-2025-00001"}
				]

				transazione = MagicMock()
				mock_get_doc.return_value = transazione

				result = self.provider.handle_notification(notification_data)

				self.assertTrue(result["success"])
				self.assertEqual(result["uuid"], notification_data["uuid"])

	def test_api_url_construction(self):
		"""Test costruzione URL API"""
		self.provider.openid_config = {
			"sdi_api_url": "https://api.wolterskluwer.eu/sdi"
		}

		url = self.provider._get_api_url("invoices/send")

		self.assertEqual(
			url,
			"https://api.wolterskluwer.eu/sdi/invoices/send"
		)


if __name__ == "__main__":
	import unittest
	unittest.main()
