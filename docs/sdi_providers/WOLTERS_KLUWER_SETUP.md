# Integrazione Wolters Kluwer SDI

Guida per integrare il provider Wolters Kluwer per l'invio di fatture elettroniche al Sistema di Interscambio (SDI) italiano.

## Configurazione

### Requisiti
- Account Wolters Kluwer attivo
- Credenziali OAuth 2.0 (Client ID e Client Secret)
- URL di callback OAuth configurato

### Passaggi di configurazione

1. **Ottenere le credenziali OAuth**
   - Accedi al tuo account Wolters Kluwer
   - Naviga nella sezione "API Management" o "OAuth"
   - Crea una nuova applicazione OAuth 2.0
   - Nota il **Client ID** e il **Client Secret**

2. **Configurare la Company in ERPNext**
   - Apri la Company desiderata
   - Nella sezione "SDI", seleziona **"Wolters Kluwer"** nel campo "Provider SDI"
   - Compila i seguenti campi:
     - **Client ID**: Il Client ID da Wolters Kluwer
     - **Client Secret**: Il Client Secret da Wolters Kluwer
     - **Redirect URI**: URL di callback (default: `http://localhost:8000/api/method/italian_invoice.api.sdi_provider.wolters_kluwer_callback`)
   - Salva la Company

3. **Autorizzazione OAuth**
   - Accedi come utente con permessi sulla Company
   - Fai clic su "Autorizza Wolters Kluwer"
   - Verrai reindirizzato a Wolters Kluwer per autorizzare l'accesso
   - Dopo l'autorizzazione, il token di accesso sarà salvato automaticamente

4. **Configurare i Webhook**
   - Nella Company, fai clic su "Configura Webhook"
   - Questo configurerà i webhook presso Wolters Kluwer per ricevere notifiche

## API Endpoints

### Autorizzazione
```
POST /api/method/italian_invoice.api.authorize_wolters_kluwer
Parametri: company_name
```

### Test Connessione
```
POST /api/method/italian_invoice.api.test_wolters_kluwer_connection
Parametri: company_name
```

### Webhook Callback
```
POST /api/method/italian_invoice.api.sdi_provider.wolters_kluwer_callback
```

### Webhook Notifiche
```
POST /api/method/italian_invoice.api.sdi_provider.wolters_kluwer_webhook
```

## Invio Fatture

Una volta configurato, l'invio delle fatture sarà automatico quando:
- La fattura è finalizzata
- Il provider SDI della Company è impostato su "Wolters Kluwer"

La fattura verrà:
1. Convertita in formato XML conforme a standard FATTURAPA
2. Inviata a Wolters Kluwer tramite l'API
3. Una transazione SDI sarà creata con UUID e stato

## Ricezione Notifiche

Wolters Kluwer invierà notifiche tramite webhook per:
- **invoice.sent**: Fattura inviata al SDI
- **invoice.accepted**: Fattura accettata dal SDI
- **invoice.rejected**: Fattura rifiutata
- **invoice.delivered**: Fattura consegnata al cliente
- **invoice.failed**: Errore nell'invio

Queste notifiche aggiornano automaticamente lo stato della transazione SDI.

## Troubleshooting

### Errore: "Client ID not configured"
**Soluzione**: Verifica che il Client ID sia compilato nella configurazione della Company.

### Errore: "Token exchange failed"
**Soluzione**: Verifica che:
- Client ID e Client Secret siano corretti
- Redirect URI corrisponda a quella registrata in Wolters Kluwer

### Webhook non riceve notifiche
**Soluzione**:
- Verifica che il webhook sia stato configurato correttamente
- Controlla il file di log per eventuali errori
- Assicurati che l'URL di webhook sia raggiungibile da Wolters Kluwer

## Struttura Provider

### Metodi Disponibili

```python
from italian_invoice.providers.wolters_kluwer_provider import WoltersKluwerProvider

provider = WoltersKluwerProvider()

# Invia una fattura
result = provider.send_invoice(xml_content, doc, company)

# Scarica una fattura
content = provider.download_invoice(uuid, format, company)

# Ottieni lo stato di una fattura
status = provider.get_invoice_status(uuid, company)

# Configura webhook
webhook_config = provider.configure_webhooks(company)

# Registra una company
register_result = provider.setup_business_register(company, config)
```

## Specifiche Tecniche

### Autenticazione
- **Metodo**: OAuth 2.0 - Client Credentials
- **Token Endpoint**: `https://login.wolterskluwer.eu/auth/core/...`
- **Scope**: `sdi_api`
- **Token TTL**: 3600 secondi (1 ora)

### Rate Limiting
Wolters Kluwer applica rate limiting. Consultare la documentazione ufficiale per i limiti attuali.

### Timeout
Timeout di default per le richieste API: 30 secondi

## Riferimenti

- OpenID Configuration: https://login.wolterskluwer.eu/auth/core/.well-known/openid-configuration
- Documentazione Wolters Kluwer: [Consultare il supporto Wolters Kluwer]
- Specifiche FATTURAPA: https://www.agenziaentrate.gov.it/portale/

## Support

Per problemi di integrazione contattare:
- **Supporto Wolters Kluwer**: support@wolterskluwer.eu
- **Supporto Italian Invoice**: [Contatti locali]
