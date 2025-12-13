from gigachat import GigaChat

auth_key = "MDE5YjBlYWUtNzYxMS03MTQ3LThkMjAtNTg4N2ZiYjUyMWM2OjQyMTZmM2E0LWZkYjAtNGFmMi1iMWY3LWQ4NGU2MzM0MTRiMA=="

giga = GigaChat(
  credentials=auth_key,
  scope="GIGACHAT_API_PERS",
  ca_bundle_file="/usr/share/ca-certificates/rus/russian_trusted_root_ca_pem.crt"
)