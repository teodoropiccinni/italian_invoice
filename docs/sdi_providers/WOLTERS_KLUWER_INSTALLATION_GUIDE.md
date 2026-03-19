# Guida di Installazione - Wolters Kluwer Integration

## Prerequisiti

- ERPNext v13+ (o versione compatibile)
- Italian Invoice pacchetto installato
- Accesso admin al sistema
- Account Wolters Kluwer con credenziali OAuth

## Fasi di Installazione

### Fase 1: Aggiornamento Code

```bash
# 1. Naviga nella cartella del workspace
cd /Users/teodoro/Workspace/italian_invoice

# 2. Aggiorna il pacchetto dal repository (se gestito in git)
git pull origin main

# 3. Verifica che i nuovi file siano presenti
ls -la italian_invoice/providers/wolters_kluwer_provider.py
ls -la italian_invoice/api/sdi_provider/wolters_kluwer.py
```

### Fase 2: Aggiornamento Fixture

```bash
# 1. Naviga nella cartella ERPNext
cd ~/frappe-bench

# 2. Esegui migrate per aggiornare i custom fields
bench migrate

# 3. Opzionale: ricarica fixtures
bench execute italian_invoice.install.after_install

# 4. Oppure carica manualmente:
bench execute frappe.client.insert --args='{"doctype":"Custom Field", "json": "..."}'
```

### Fase 3: Verifica Installazione

```python
# In ERPNext console
bench console

import frappe
from italian_invoice.providers.wolters_kluwer_provider import WoltersKluwerProvider
from italian_invoice.api.sdi_provider import wolters_kluwer

# Testa import
provider = WoltersKluwerProvider()
print("✓ Provider caricato con successo")

# Testa endpoint
from frappe import get_doc
company = get_doc("Company", "Company Name")
print("✓ Company caricata")
```

### Fase 4: Configurazione Company

1. **Accedi a ERPNext**
   - URL: `http://localhost:8000`
   - User: Admin

2. **Apri una Company**
   - Naviga in: Company (Azienda)
   - Seleziona la company da configurare

3. **Abilita Wolters Kluwer**
   - Scroll fino alla sezione SDI
   - "Provider SDI" → seleziona "Wolters Kluwer"
   - Appare la sezione "Wolters Kluwer" con i campi

4. **Compila Credenziali**
   ```
   Client ID: [da Wolters Kluwer]
   Client Secret: [da Wolters Kluwer]
   Redirect URI: http://localhost:8000/api/method/italian_invoice.api.sdi_provider.wolters_kluwer_callback
   ```
   ⚠️ Nota: Sostituisci `localhost:8000` con il tuo dominio

5. **Salva Configurazione**
   - Click "Salva"

### Fase 5: Autorizzazione OAuth

1. **Nella Company**, click sul pulsante "Autorizza Wolters Kluwer"
   ```
   (Nota: Il pulsante non è automatico, è presente a livello di codice)
   ```

2. **Via API call** (se il pulsante non è visibile):
   ```bash
   curl -X POST http://localhost:8000/api/method/italian_invoice.api.authorize_wolters_kluwer \
     -H "X-Frappe-CSRF-Token: [TOKEN]" \
     -d "company_name=Your Company Name"
   ```

3. **Verrai reindirizzato a Wolters Kluwer**
   - Accedi con le tue credenziali
   - Autorizza l'applicazione
   - Verrai redietto al sistema

4. **Token salvato automaticamente**
   - Il campo "Access Token" verrà riempito
   - Salvato cifrato nel database

### Fase 6: Test Connessione

```bash
# Via API
curl -X POST http://localhost:8000/api/method/italian_invoice.api.test_wolters_kluwer_connection \
  -H "X-Frappe-CSRF-Token: [TOKEN]" \
  -d "company_name=Your Company Name"

# Risposta attesa:
# {
#   "success": true,
#   "message": "Connessione riuscita",
#   "token_obtained": true
# }
```

### Fase 7: Configurazione Webhook (Opzionale)

```python
from italian_invoice.utilities.fatture import get_sdi_provider

provider = get_sdi_provider("Your Company Name")
company = frappe.get_doc("Company", "Your Company Name")

# Configura webhook
result = provider.configure_webhooks(company)
print(result)
```

### Fase 8: Test Invio Fattura

1. **Crea una Sales Invoice**
   - Company: Seleziona quella configurata
   - Completa tutti i dati
   - "Salva" → "Sottometti"

2. **Automaticamente**:
   - Fattura sarà convertita in XML FATTURAPA
   - Inviata a Wolters Kluwer
   - Transazione SDI creata

3. **Verifica Risultato**
   - Visualizza la Sales Invoice
   - Sezione SDI dovrebbe mostrare: UUID, Stato "Inviata"

## Configurazione Avanzata

### Webhook Secret (Optional)

Se Wolters Kluwer richiede firma webhook:

1. **Genera una chiave segreta**:
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Salva in Italian Invoice Settings**:
   ```python
   settings = frappe.get_doc("Italian Invoice Settings")
   settings.custom_wolters_kluwer_webhook_secret = "tua-chiave-segreta"
   settings.save()
   ```

3. **Configura in Wolters Kluwer**:
   - Registra la chiave segreta nel loro panel

### Dominio Personalizzato

Se usi un dominio personalizzato, aggiorna il Redirect URI:

```
Redirect URI: https://tuo-dominio.com/api/method/italian_invoice.api.sdi_provider.wolters_kluwer_callback
```

Registra lo stesso URI in Wolters Kluwer.

## Troubleshooting Installazione

### Errore: "Custom Field non trovato"
```
Soluzione: Esegui bench migrate
```

### Errore: "Module not found: wolters_kluwer_provider"
```
Soluzione:
1. Verifica che il file sia in: italian_invoice/providers/
2. Esegui: bench clear-cache
3. Riavvia bench: bench restart
```

### Errore: "Company not found in session"
```
Soluzione: Accedi all'API con sessione valida
- Genera X-Frappe-CSRF-Token
- Usa la sezione API in ERPNext
```

### Errore API: "Invalid signature"
```
Soluzione: Verifica webhook secret configurato
- Deve corrispondere su entrambi i lati
- Controlla se Wolters Kluwer rinvia nei headers
```

## Migrazione da altro Provider

Se passi da un altro provider SDI a Wolters Kluwer:

```python
# 1. Esamina le transazioni SDI esistenti
transazioni = frappe.get_list("Transazione SDI", 
    filters={"provider": "OpenAPI"})

# 2. Opzionalmente: aggiorna il provider
for trans in transazioni:
    doc = frappe.get_doc("Transazione SDI", trans.name)
    doc.provider = "Wolters Kluwer"
    doc.save()

# 3. Cambia il provider della Company
company = frappe.get_doc("Company", "Your Company")
company.custom_sdi_provider = "Wolters Kluwer"
company.save()

# 4. Nuove fatture useranno Wolters Kluwer
```

## Performance e Monitoring

### Logging

Abilita debug logging per il provider:

```python
# In console.py o tramite bench execute
import logging
logging.getLogger("italian_invoice.wolters_kluwer_provider").setLevel(logging.DEBUG)
```

### Monitoraggio Trasazioni

```bash
# Visualizza transazioni recenti
bench execute "frappe.get_list('Transazione SDI', \
  filters={'modified': ['>=', frappe.utils.today()]}, \
  order_by='modified desc', \
  limit_page_length=20)"
```

## Rollback

Se devi tornare a un altro provider:

1. **Scarica il backup database**
2. **Ripristina (opzionale)**
3. **Cambia provider della Company**:
   ```python
   company.custom_sdi_provider = "OpenAPI"  # o "Manual"
   company.save()
   ```
4. **Nuove fatture** useranno il provider precedente
5. **Transazioni SDI** rimangono nel history

## Support e Contatti

### Problemi ERPNext/Italian Invoice
- Consulta: `docs/sdi_providers/WOLTERS_KLUWER_SETUP.md`
- Consulta: `docs/sdi_providers/WOLTERS_KLUWER_ARCHITECTURE.md`

### Problemi Wolters Kluwer API
- Contatta: support@wolterskluwer.eu
- Documentazione: https://login.wolterskluwer.eu/auth/core/.well-known/openid-configuration

### Test API
- Endpoint test in: `italian_invoice/api/sdi_provider/wolters_kluwer.py`
- Unit test in: `italian_invoice/providers/test_wolters_kluwer_provider.py`

## Checklist Post-Installazione

- [ ] File `wolters_kluwer_provider.py` presente
- [ ] File `wolters_kluwer.py` (API) presente
- [ ] Custom fields presenti in Company
- [ ] Credenziali Wolters Kluwer salvate
- [ ] OAuth autorizzazione completata
- [ ] Test connessione riuscito
- [ ] Webhook configurato (opzionale)
- [ ] Test fattura inviata con successo
- [ ] Transazione SDI creata e aggiornata
- [ ] Logging attivo per debugging

---

**Versione**: 1.0
**Data**: 18 Marzo 2026
**Supporto**: Contattare il team di sviluppo
