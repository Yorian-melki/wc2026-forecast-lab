"""Privacy-first PostHog web analytics for the Streamlit app.

Consent-gated by design (GDPR): NOTHING is loaded or tracked until the visitor clicks
"Accept" on the banner. On Accept, PostHog loads with autocapture (every click/event) +
session replay. On Decline, nothing loads and the choice is remembered. The choice lives
in localStorage (`wc_consent`).

The PostHog public project key is read from POSTHOG_KEY (env). It is a *public*, client-side
token by design — safe to ship in the page — but we still read it from env so it is never
hard-coded. Host defaults to US cloud (set POSTHOG_HOST to override).

Streamlit caveat (verified): components.html runs in a same-origin iframe; we inject the
bootstrap into `window.parent.document` so PostHog attaches to the REAL app window and its
autocapture sees the app's clicks (not just the iframe). Custom-component iframes still
escape autocapture — coverage is high, not 100%.
"""
from __future__ import annotations

import json
import os

# Official PostHog web-install array stub (verified current, 2026). Runs in the parent window.
_PH_STUB = (
    r"""!function(t,e){var o,n,p,r;e.__SV||(window.posthog=e,e._i=[],e.init=function(i,s,a){"""
    r"""function g(t,e){var o=e.split(".");2==o.length&&(t=t[o[0]],e=o[1]),t[e]=function(){"""
    r"""t.push([e].concat(Array.prototype.slice.call(arguments,0)))}}(p=t.createElement("script"))"""
    r""".type="text/javascript",p.crossOrigin="anonymous",p.async=!0,"""
    r"""p.src=s.api_host.replace(".i.posthog.com","-assets.i.posthog.com")+"/static/array.js","""
    r"""(r=t.getElementsByTagName("script")[0]).parentNode.insertBefore(p,r);var u=e;"""
    r"""for(void 0!==a?u=e[a]=[]:a="posthog",u.people=u.people||[],u.toString=function(t){"""
    r"""var e="posthog";return"posthog"!==a&&(e+="."+a),t||(e+=" (stub)"),e},"""
    r"""u.people.toString=function(){return u.toString(1)+".people (stub)"},"""
    r"""o="init capture register register_once register_for_session unregister unregister_for_session """
    r"""getFeatureFlag getFeatureFlagPayload isFeatureEnabled reloadFeatureFlags identify setPersonProperties """
    r"""group startSessionRecording stopSessionRecording opt_in_capturing opt_out_capturing """
    r"""has_opted_in_capturing has_opted_out_capturing reset get_distinct_id debug".split(" "),"""
    r"""n=0;n<o.length;n++)g(u,o[n]);e._i.push([i,s,a])},e.__SV=1)}(document,window.posthog||[]);"""
)

_PRIVACY_URL = "https://github.com/Yorian-melki/wc2026-forecast-lab/blob/main/docs/PRIVACY.md"

# Bootstrap runs in the PARENT window (script appended to parent document).
_BOOTSTRAP = (
    """(function(){
  var KEY="__PH_KEY__", HOST="__PH_HOST__";
  if(window.__wcConsentReady) return; window.__wcConsentReady=1;
  var FR=(navigator.language||"").toLowerCase().indexOf("fr")===0;
  function loadPH(){
    if(window.__wcPHinit) return; window.__wcPHinit=true;
    """ + _PH_STUB + """
    posthog.init(KEY,{api_host:HOST, defaults:'2026-01-30'});
  }
  var c=null; try{c=localStorage.getItem('wc_consent');}catch(e){}
  if(c==='accept'){ loadPH(); return; }
  if(c==='reject'){ return; }
  if(document.getElementById('wc-consent')) return;
  var txt=FR?"Ce site utilise PostHog (clics, navigation, replay de session) pour s'améliorer. Données traitées aux États-Unis. Tu peux accepter ou refuser.":"This site uses PostHog (clicks, navigation, session replay) to improve. Data is processed in the US. You can accept or decline.";
  var pol=FR?"Politique de confidentialité":"Privacy policy";
  var acc=FR?"Accepter":"Accept", rej=FR?"Refuser":"Decline";
  var b=document.createElement('div'); b.id='wc-consent';
  b.style.cssText="position:fixed;left:16px;right:16px;bottom:16px;z-index:100000;background:#12121e;border:1px solid #2A9D8F;border-radius:14px;padding:14px 18px;display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:space-between;box-shadow:0 10px 34px rgba(0,0,0,.55);font-family:system-ui,-apple-system,sans-serif";
  b.innerHTML='<div style="color:#C9C9E0;font-size:13px;max-width:700px;line-height:1.5">'+txt+' <a href="'+"__PRIVACY__"+'" target="_blank" style="color:#2A9D8F;text-decoration:none">'+pol+'</a></div><div style="display:flex;gap:8px"><button id="wc-reject" style="background:transparent;color:#9a9ab5;border:1px solid #2a2a40;border-radius:8px;padding:8px 16px;font-size:13px;cursor:pointer">'+rej+'</button><button id="wc-accept" style="background:#2A9D8F;color:#06060a;border:0;border-radius:8px;padding:8px 18px;font-size:13px;font-weight:600;cursor:pointer">'+acc+'</button></div>';
  document.body.appendChild(b);
  document.getElementById('wc-accept').onclick=function(){try{localStorage.setItem('wc_consent','accept');}catch(e){} b.remove(); loadPH(); try{posthog.capture('consent_accepted');}catch(e){}};
  document.getElementById('wc-reject').onclick=function(){try{localStorage.setItem('wc_consent','reject');}catch(e){} b.remove();};
})();"""
)


def inject(st) -> bool:
    """Inject consent-gated PostHog into the parent app window. No-op if POSTHOG_KEY unset.

    Returns True if the analytics bootstrap was injected, False if inert (not configured).
    """
    key = os.getenv("POSTHOG_KEY", "").strip()
    if not key:
        return False
    host = os.getenv("POSTHOG_HOST", "https://us.i.posthog.com").strip()
    boot = (_BOOTSTRAP
            .replace("__PH_KEY__", key)
            .replace("__PH_HOST__", host)
            .replace("__PRIVACY__", _PRIVACY_URL))
    shim = (
        "<script>(function(){var P=window.parent;if(!P||P.__wcAnalytics)return;"
        "P.__wcAnalytics=1;var d=P.document;var s=d.createElement('script');"
        "s.textContent=" + json.dumps(boot) + ";d.head.appendChild(s);})();</script>"
    )
    import streamlit.components.v1 as components
    components.html(shim, height=0)
    return True
