# ADR 0007: Caller Identity Privacy Guard and OTP Authentication Roadmap

## Status
Accepted

## Context
Callers on public web/telephony channels are identified primarily by phone number. Phone number alone is a weak factor of identity, making voice AI agents vulnerable to social engineering or caller spoofing if full customer records are disclosed over speech.

## Decision
1. **Privacy Guard (Current Policy)**:
   - When a caller is verified by phone number, Epixa confirms only minimal identifying details (e.g., first name: "Thank you, Sarah") and never reads out full contact details, addresses, or historic ticket transcripts.
2. **Future Upgrade Path (OTP / 2FA)**:
   - For privileged customer actions (e.g., billing inquiries, refund processing, address changes), introduce an SMS/WhatsApp One-Time Password (OTP) verification node:
     1. Agent triggers a 6-digit OTP delivery via Twilio/SendGrid.
     2. Caller speaks the 6-digit code.
     3. Agent validates code before unlocking sensitive customer context.

## Consequences
- Mitigates unauthorized disclosure of customer PII over voice.
- Establishes a clear architecture for future high-security customer workflows.
