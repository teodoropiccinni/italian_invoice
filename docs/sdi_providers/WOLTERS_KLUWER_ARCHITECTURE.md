# Architettura Integrazione Wolters Kluwer

## Panoramica

L'integrazione Wolters Kluwer fornisce un provider SDI completo per ERPNext che supporta:
- Autenticazione OAuth 2.0
- Invio fatture elettroniche
- Ricezione notifiche tramite webhook
- Gestione dello stato delle transazioni
- Registrazione business

## Flusso di Autenticazione

```
┌─────────────────────┐
│   User/Company      │
└──────────┬──────────┘
           │
           │ 1. Richiede autorizzazione
           ↓
┌─────────────────────────────────────────┐
│  authorize_wolters_kluwer() API         │
│  - Genera state (CSRF protection)       │
│  - Salva in session                     │
│  - Restituisce authorization_url        │
└──────────────┬──────────────────────────┘
               │
               │ 2. Utente autorizza
               ↓
┌──────────────────────────────────────────┐
│  Wolters Kluwer Auth Server             │
│  https://login.wolterskluwer.eu/auth    │
└──────────────┬───────────────────────────┘
               │
               │ 3. Callback con code + state
               ↓
┌──────────────────────────────────────────┐
│  wolters_kluwer_callback() Webhook       │
│  - Verifica state                        │
│  - Scambia code con token                │
│  - Salva token in Company                │
└──────────────────────────────────────────┘
```

## Flusso di Invio Fattura

```
┌─────────────────────┐
│   Sales Invoice     │
│   Finalizzata       │
└──────────┬──────────┘
           │
           │ 1. Hook: on_submit
           ↓
┌──────────────────────────────────────────┐
│  Genera XML FATTURAPA                    │
│  - Valida contro XSD                     │
│  - Serializza dati fattura               │
└──────────┬───────────────────────────────┘
           │
           │ 2. Ottiene provider per Company
           ↓
┌──────────────────────────────────────────┐
│  get_sdi_provider(company_name)          │
│  - Legge custom_sdi_provider              │
│  - Istanzia WoltersKluwerProvider        │
└──────────┬───────────────────────────────┘
           │
           │ 3. Ottiene access token
           ↓
┌──────────────────────────────────────────┐
│  _get_access_token()                     │
│  - Controlla cache + scadenza            │
│  - Se scaduto: richiede nuovo token      │
│  - Token endpoint: Wolters Kluwer        │
└──────────┬───────────────────────────────┘
           │
           │ 4. Invia fattura
           ↓
┌──────────────────────────────────────────┐
│  send_invoice() API call                 │
│  POST /sdi/invoices/send                 │
│  Authorization: Bearer {token}           │
│  Content-Type: application/xml           │
└──────────┬───────────────────────────────┘
           │
           │ 5. Riceve risposta
           ↓
┌──────────────────────────────────────────┐
│  Processa risposta                       │
│  - Estrae UUID                           │
│  - Crea Transazione SDI                  │
│  - Collega a Sales Invoice               │
└──────────────────────────────────────────┘
```

## Flow Webhook (Notifiche)

```
┌─────────────────────────────────────────┐
│  Wolters Kluwer Notification             │
│  (invoice.accepted, invoice.rejected...)│
└──────────┬──────────────────────────────┘
           │
           │ POST /api/sdi_provider/wolters_kluwer_webhook
           ↓
┌──────────────────────────────────────────┐
│  wolters_kluwer_webhook()                │
│  - Verifica firma webhook (HMAC-SHA256)  │
│  - Estrae company_piva                   │
│  - Trova Company nel sistema             │
└──────────┬──────────────────────────────┘
           │
           │ Ottiene provider
           ↓
┌──────────────────────────────────────────┐
│  handle_notification()                   │
│  - Estrae UUID e status                  │
│  - Trova Transazione SDI                 │
│  - Aggiorna stato                        │
└──────────────────────────────────────────┘
```

## Struttura Classi

```
┌──────────────────────────────────────────┐
│        SDIProvider (ABC)                 │
│  - Interface base per tutti i provider   │
│  - Metodi astratti da implementare       │
└──────────┬───────────────────────────────┘
           │
           ├─────────────────────────────────┐
           │                                 │
           ↓                                 ↓
┌──────────────────────────────────────┐  ┌──────────────────────┐
│   WoltersKluwerProvider              │  │  OpenAPIProvider     │
│  - OAuth 2.0 Authentication          │  │  ManualProvider      │
│  - Gestione Token                    │  │  Custom Provider ... │
│  - Webhook Management                │  │                      │
│  - Business Registration             │  └──────────────────────┘
│                                      │
│  Metodi Chiave:                      │
│  - send_invoice()                    │
│  - download_invoice()                │
│  - get_invoice_status()              │
│  - handle_notification()             │
│  - configure_webhooks()              │
│  - setup_business_register()         │
└──────────────────────────────────────┘
```

## Gestione Token OAuth

```
┌─────────────────────────────────────┐
│  _get_access_token(company)         │
└────────────────┬────────────────────┘
                 │
                 ├─ Se token in cache + non scaduto?
                 │  └─ SÌ: return token
                 │
                 └─ NO:
                    └─ Richiedi nuovo token
                       - Token endpoint: Wolters Kluwer
                       - Credenziali: Client ID/Secret
                       - Scope: sdi_api
                       │
                       └─ Cache token + scadenza (TTL - 60s)
                          └─ return token
```

## Sequenza Webhook Configuration

```
1. User chiama configure_webhooks() in Company

2. Provider riceve called per Company

3. Ottiene access token

4. Invia POST a /business/webhooks

5. Payload contiene:
   - webhook_url: URL callback nel nostro sistema
   - events: Lista di eventi da ricevere
   - company_piva: Identificativo company

6. Wolters Kluwer restituisce webhook_id

7. Salva webhook_id in Company.custom_wolters_kluwer_webhook_id

8. D'ora in poi Wolters Kluwer invierà notifiche all'URL configurato
```

## Sicurezza

### OAuth 2.0
- Flow: Client Credentials
- Scope limitato: `sdi_api`
- Token with TTL (scadenza)
- Refresh token per estensione sessione

### Webhook Signature Verification
```python
# Firma HMAC-SHA256
signature = HMAC-SHA256(
    secret=webhook_secret,
    message=request_body
)

# Verifica in _verify_webhook_signature()
```

### Protezione CSRF
- State parameter in OAuth flow
- Salvato in sessione durante authorization
- Verificato nel callback

### Password Fields
- Client Secret memorizzato come Password (cifrato in DB)
- Access Token memorizzato come Password (cifrato)
- Refresh Token memorizzato come Password (cifrato)

## Rate Limiting e Timeout

- **Timeout API**: 30 secondi
- **Rate Limit**: Dipende da Wolters Kluwer (consultare docs)
- **Cache Token**: 3600 secondi - 60 secondi (buffer)

## Error Handling

```
try:
    - Effettua operazione API
except Exception as e:
    - Log errore
    - Restituisce dict con success=False
    - Mostra messaggio descrittivo all'utente
```

## Transazione SDI

Ogni fattura inviata crea/aggiorna una `Transazione SDI` con:
- `uuid`: Identificativo univoco da Wolters Kluwer
- `tipo_fattura`: SalesInvoice o PurchaseInvoice
- `fattura`: Riferimento al documento fattura
- `stato_invio`: Stato corrente (Inviata, Accettata, Rifiutata, ecc)
- `provider`: "Wolters Kluwer"
- `risposta_provider`: Risposta JSON dall'API

## Monitoraggio

### Logging
```python
logger = logging.getLogger("italian_invoice.wolters_kluwer_provider")

# Livelli:
- logger.info(): Operazioni normali
- logger.error(): Errori recuperabili
- logger.exception(): Eccezioni non gestite
```

### Debugging
- Attiva logging DEBUG per dettagli token
- Ispeziona request/response HTTP
- Controlla sessione per state parameter
- Verifica firma webhook

## Estensioni Future

1. **Refresh Token Rotation**
   - Implementare refresh automatico con refresh_token

2. **Batch Processing**
   - Supporto per invio fatture batch

3. **Advanced Webhook Management**
   - Retry logic per webhook failed
   - Webhook status monitoring

4. **Certificati Digitali**
   - Supporto per firma digitale delle fatture

5. **Integration con SDI Pubblico**
   - Supporto per backup via intermediario SDI ufficiale
