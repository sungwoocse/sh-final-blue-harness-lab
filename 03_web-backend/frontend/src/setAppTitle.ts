import i18n from './lib/i18n';

function setDocumentTitle() {
  const title = i18n.t('app.title');
  document.title = title;
  // Update meta tags
  document.querySelector('meta[name="description"]')?.setAttribute('content', `${title} Platform`);
  document.querySelector('meta[name="author"]')?.setAttribute('content', title);
  document.querySelector('meta[property="og:title"]')?.setAttribute('content', title);
  document.querySelector('meta[property="og:description"]')?.setAttribute('content', `${title} Platform`);
}

// Set on initial load
setDocumentTitle();

// Update on language change
if (i18n.on) {
  i18n.on('languageChanged', setDocumentTitle);
}
