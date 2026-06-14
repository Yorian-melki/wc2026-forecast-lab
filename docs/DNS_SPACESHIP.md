# DNS — Spaceship (do NOT auto-change)

Current (KEEP — serves the portfolio on Vercel):
| Type | Host | Value | TTL |
|---|---|---|---|
| A | @ | 216.198.79.1 | 1 min |
| CNAME | www | ae4e6dba669ff61a.vercel-dns-017.com | 1 min |

**Do NOT edit/delete @ or www.**

Add LATER (only after Render gives a target):
| Type | Host | Value | TTL |
|---|---|---|---|
| CNAME | wc2026 | `<RENDER_TARGET>.onrender.com` | 1 min / Automatic |

Spaceship → Domain → Advanced DNS → Add record → CNAME → Host `wc2026` → Value = Render target → Save.
Propagation up to a few minutes; Render issues TLS after. This is a USER action — agents must not change DNS.
