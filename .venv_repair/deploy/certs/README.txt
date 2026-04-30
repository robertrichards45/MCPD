Place the real CAC trust-chain certificate files in this folder, then build the PEM bundle.

Accepted input files:
- .cer
- .crt
- .pem
- .p7b

Recommended contents:
- Federal Common Policy CA
- Federal Bridge CA (if required by your issuing chain)
- DoD root / intermediate CA certificates that issued the CAC client certificate

Build the bundle with:
  C:\Users\rober\Desktop\mcpd-portal\deploy\build_cac_chain_from_files.cmd C:\Users\rober\Desktop\mcpd-portal\deploy\certs

That writes:
  C:\Users\rober\Desktop\mcpd-portal\deploy\cac-chain.pem

Then start the local CAC proxy with:
  C:\Users\rober\Desktop\mcpd-portal\deploy\run_caddy_real_cac.cmd
