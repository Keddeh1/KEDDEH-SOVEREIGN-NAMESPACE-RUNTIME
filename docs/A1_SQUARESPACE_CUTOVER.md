# Track A operator runbook

Source of truth: REV-002-source.txt, sections 3–4. No DNS transaction was executed while preparing this repository.

1. Capture every Type, Host, Priority, TTL and Value from current Squarespace DNS, with UTC timestamp and hash. Preserve MX/SPF/DKIM/DMARC, verification, CAA and unrelated records.
2. For keddeh.com add apex A 162.159.143.30 and 172.66.3.26, plus the two apex verification TXT values exactly as supplied in REV-002. TTL 30 minutes. Do not create an apex CNAME.
3. Keep www CNAME custom-domains.chatgpt.site and its two existing verification TXT records. Preserve the complete Google DKIM value and existing mail configuration; source values are not a substitute for current authoritative inventory.
4. Confirm mail/unrelated records, then remove only confirmed conflicting apex web A/AAAA records. 198.185.159.144 is a conflict only at host @. Save and retain the transaction receipt.
5. Read back A, CNAME, verification TXT, MX, SPF, DKIM, DMARC and CAA against authoritative servers and independently through recursive resolvers. Compare with custody inventory. Check HTTPS response and hostname certificate coverage for apex and www.
6. If web TLS/HTTP regresses, restore only preserved apex web records. Mail regressions require exact restoration of affected preserved records.

Track B delegation is a separate change window. Require both stable public IPs, complete zones, authoritative UDP/TCP answers, equal SOA serials, DNSSEC validation, recursion refusal, TSIG-protected transfers and independent receipts. Coordinate any existing DS before changing nameservers.
