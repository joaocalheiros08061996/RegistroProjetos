async function loadPrivacyNoticeMetadata() {
  const config = await getAppConfig();
  const controllerName = config.privacy_controller_name || "não informado";
  const contactEmail = config.privacy_contact_email || "não informado";
  const policyVersion = config.privacy_policy_version || "não informada";

  document.getElementById("privacy-controller-name").textContent = controllerName;
  document.getElementById("privacy-policy-version").textContent = policyVersion;

  const contact = document.getElementById("privacy-contact-email");
  contact.textContent = contactEmail;
  contact.href = config.privacy_contact_email
    ? `mailto:${config.privacy_contact_email}`
    : "#";
}

loadPrivacyNoticeMetadata().catch(() => {
  document.getElementById("privacy-contact-email").textContent =
    "contato não configurado";
});
