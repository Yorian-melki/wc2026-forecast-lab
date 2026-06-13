# Domain / DNS Audit

Generated 2026-06-13T17:21:42 UTC · **read-only, no DNS changed**

- Registrar: Spaceship, Inc. · created 2026-03-23 · expires 2027-03-23
- Nameservers: launch1.spaceship.net, launch2.spaceship.net (DNS managed at Spaceship)
- Root A: 216.198.79.1 (Vercel anycast)
- www CNAME: ae4e6dba669ff61a.vercel-dns-017.com (Vercel)

## Interpretation
- DNS is managed at Spaceship (nameservers launch1/2.spaceship.net).
- Root (@) A record points to a Vercel anycast IP -> root is Vercel-ready.
- www is CNAME'd to Vercel DNS -> www is delegated to Vercel.
- Conclusion: the apex + www are already wired to Vercel. A portfolio on Vercel needs minimal config.
- A new subdomain (wc2026.yorian-melki.com) requires ADDING a DNS record AT SPACESHIP pointing to the chosen app host. This is a USER action; Claude must not change DNS.

> To add wc2026.yorian-melki.com you must add a CNAME at Spaceship to the app host. Claude will not change DNS.
