# Integrazione Wolters Kluwer - Riepilogo

## Data: 18 Marzo 2026

### 📦 Componenti Aggiunti

#### 1. **Provider Wolters Kluwer** (`providers/wolters_kluwer_provider.py`)
   - Classe `WoltersKluwerProvider` per gestire l'intermediazione SDI
   - Autenticazione OAuth 2.0 completa
   - Gestione automatica dei token di accesso
   - Metodi per invio, download e gestione fatture
   - Supporto completo per webhook e notifiche

#### 2. **API Endpoints** (`api/sdi_provider/wolters_kluwer.py`)
   - `authorize_wolters_kluwer`: Avvia flusso OAuth
   - `wolters_kluwer_callback`: Callback per OAuth
   - `test_wolters_kluwer_connection`: Test connessione
   - `wolters_kluwer_webhook`: Ricevi notifiche
   - Verifica firma webhook (HMAC-SHA256)

#### 3. **Custom Fields per Company** (`fixtures/custom_field.json`)
   - `custom_wolters_kluwer_section`: Sezione collapsible
   - `custom_wolters_kluwer_client_id`: Client ID OAuth
   - `custom_wolters_kluwer_client_secret`: Client Secret OAuth
   - `custom_wolters_kluwer_redirect_uri`: URL callback
   - `custom_wolters_kluwer_access_token`: Token di accesso
   - `custom_wolters_kluwer_refresh_token`: Refresh token
   - `custom_wolters_kluwer_webhook_id`: ID webhook

#### 4. **File di Test** (`providers/test_wolters_kluwer_provider.py`)
   - Unit test per tutte le funzionalità principali
   - Mock per API calls
   - Test autenticazione OAuth
   - Test gestione notifiche

#### 5. **Documentazione**
   - `docs/sdi_providers/WOLTERS_KLUWER_SETUP.md`: Guida di confgurazione
   - `docs/sdi_providers/WOLTERS_KLUWER_ARCHITECTURE.md`: Architettura tecnica
   - `docs/sdi_providers/WOLTERS_KLUWER_INTEGRATION.md`: Riepilogo integrazione
   - `providers/README.md`: Aggiornato con nuovo provider

### 🔧 Configurazione Richiesta

#### Per configurare Wolters Kluwer in una Company:

1. **Ottenere Credenziali da Wolters Kluwer**:
   - Client ID
   - Client Secret
   - URL OAuth: https://login.wolterskluwer.eu/auth/core/.well-known/openid-configuration

2. **Configurare Company**:
   ```
   Company > SDI Provider > seleziona "Wolters Kluwer"
   Compila:
   - Client ID
   - Client Secret
   - Redirect URI (usa default o personalizza)
   ```

3. **Autorizzare**:
   ```
   Company > Autorizza Wolters Kluwer
   (reindirizzamento OAuth)
   ```

4. **Configurare Webhook** (opzionale):
   ```
   Company > Configura Webhook Wolters Kluwer
   ```

### 🚀 Funzionalità Implementate

- ✅ OAuth 2.0 Client Credentials
- ✅ Invio fatture XML a Wolters Kluwer
- ✅ Download fatture da SDI
- ✅ Verifica stato fatture
- ✅ Ricezione notifiche webhook
- ✅ Registrazione business/company
- ✅ Cache token con TTL
- ✅ Verifica firma webhook (HMAC-SHA256)
- ✅ Gestione transazioni SDI
- ✅ Dettagliata gestione errori
- ✅ Supporto multi-company

### 📁 File Modificati/Creati

```
italian_invoice/
├── providers/
│   ├── wolters_kluwer_provider.py          [NUOVO]
│   ├── test_wolters_kluwer_provider.py     [NUOVO]
│   ├── __init__.py                         [MODIFICATO]
│   └── README.md                           [MODIFICATO]
├── api/
│   └── sdi_provider/
│       ├── __init__.py                     [NUOVO]
│       └── wolters_kluwer.py               [NUOVO]
├── utilities/
│   └── fatture.py                          [MODIFICATO - get_sdi_provider()]
├── fixtures/
│   └── custom_field.json                   [MODIFICATO - aggiunti 7 custom fields]
└── docs/
    └── sdi_providers/
        ├── WOLTERS_KLUWER_SETUP.md         [NUOVO]
        ├── WOLTERS_KLUWER_ARCHITECTURE.md  [NUOVO]
        └── WOLTERS_KLUWER_INTEGRATION.md   [NUOVO]
```

### 📝 Note Implementazione

#### OAuth Flow
```
Client ID -> Code -> Exchange Code -> Access Token -> API Calls
```
- Token cachato in memoria con TTL di 3600 secondi
- Buffer di 60 secondi prima della scadenza per refresh
- Session-based state parameter per CSRF protection

#### API Integration
```
Base URL: https://api.wolterskluwer.eu/sdi (da config OpenID)
Endpoint: https://login.wolterskluwer.eu/auth/core/.well-known/openid-configuration
```

#### Webhook Handling
```
POST /api/method/italian_invoice.api.sdi_provider.wolters_kluwer_webhook
- Verifica firma HMAC-SHA256
- Identifica company da PIVA
- Aggiorna stato Transazione SDI
- Log di tutte le operazioni
```

### 🧪 Test

Esegui i test con:
```bash
bench run-tests italian_invoice.providers.test_wolters_kluwer_provider
```

### 🔐 Sicurezza

- ✅ Password fields cifrati in database
- ✅ HMAC-SHA256 per webhook signature
- ✅ CSRF protection con state parameter
- ✅ Timeout 30 secondi su API calls
- ✅ Logging di errori per audit trail
- ✅ Permessi Frappe per accesso Company

### 🐛 Troubleshooting

**Errori comuni e soluzioni** in `docs/sdi_providers/WOLTERS_KLUWER_SETUP.md`

### 📞 Supporto

- Contattare Wolters Kluwer per problemi API: support@wolterskluwer.eu
- Consultare `docs/sdi_providers/WOLTERS_KLUWER_ARCHITECTURE.md` per dettagli tecnici

### 🎯 Prossimi Passi (Opzionali)

1. Implementare refresh token rotation
2. Aggiungere batch processing per fatture
3. Supporto per firma digitale
4. Dashboard per monitoraggio transazioni SDI
5. Integrazione con backup SDI pubblico

---

**Versione**: 1.0
**Provider**: WoltersKluwerProvider
**OpenID Config**: https://login.wolterskluwer.eu/auth/core/.well-known/openid-configuration
