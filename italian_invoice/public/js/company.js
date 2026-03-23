// Company Form Script - Handle Wolters Kluwer SDI Provider
frappe.ui.form.on('Company', {
    custom_sdi_provider: function(frm) {
        if (frm.doc.custom_sdi_provider === 'Wolters Kluwer') {
            // Popola automaticamente il Redirect URI con l'URL corrente
            const redirectUri = `${window.location.origin}/api/method/italian_invoice.api.sdi_provider.wolters_kluwer_callback`;
            frm.set_value('custom_wolters_kluwer_redirect_uri', redirectUri);
        }
    },

    onload: function(frm) {
        // Se Wolters Kluwer è già selezionato e il campo è vuoto, popola il campo
        if (frm.doc.custom_sdi_provider === 'Wolters Kluwer') {
            if (!frm.doc.custom_wolters_kluwer_redirect_uri) {
                const redirectUri = `${window.location.origin}/api/method/italian_invoice.api.sdi_provider.wolters_kluwer_callback`;
                frm.set_value('custom_wolters_kluwer_redirect_uri', redirectUri);
            }
        }
    }
});
