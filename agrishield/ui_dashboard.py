"""Streamlit UI: bottom-tab navigation, onboarding, home, crops, livestock, farm ledger, profile."""
import csv
import io
import json
import urllib.parse
from datetime import date, datetime

import streamlit as st

from . import ai_diagnosis as AI
from . import crop_protection as C
from . import livestock_manager as L
from . import user_profile as U
from .i18n import LANGS, make_t

try:
    from streamlit_js_eval import get_geolocation, streamlit_js_eval
except Exception:  # optional dependency
    get_geolocation = streamlit_js_eval = None

CATS = [("بذور", "Semences", "Seeds"), ("أسمدة", "Engrais", "Fertilizer"), ("علف", "Aliments", "Feed"), ("بيطري", "Véto", "Vet"),
        ("عمال", "Main-d'œuvre", "Labor"), ("وقود/ماء", "Carburant/eau", "Fuel/water"), ("مبيعات", "Ventes", "Sales"), ("أخرى", "Autre", "Other")]
DEFAULT_PRICE = dict(hay=35, barley=55, bran=40)

CSS = """@import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&display=swap');
:root{--em:#1b5e20;--mint:#4caf50;--sl:#546e7a;--bg:#eef2f1;--line:#dbe3e1}
html,body,.stApp,button,input,textarea,select{font-family:'Tajawal',sans-serif!important}
.stApp{background:var(--bg);color:#263238}
header,footer,#MainMenu{visibility:hidden}
.block-container{max-width:760px;padding:1rem 1rem 6.5rem}
.hero{background:linear-gradient(135deg,#1b5e20,#2e7d32 60%,#4caf50);color:#fff;border-radius:24px;padding:1.3rem 1.4rem;margin-bottom:1rem;box-shadow:0 8px 24px rgba(27,94,32,.25)}
.hero h2{margin:.1rem 0 .6rem;color:#fff;font-weight:800;font-size:1.5rem}
.hero small{opacity:.85}
.now{font-size:2.6rem;font-weight:800;line-height:1}
.now span{font-size:.95rem;font-weight:500;margin-inline-start:.6rem;opacity:.9}
.card,[data-testid=stMetric]{background:#fff;border-radius:16px;padding:1rem 1.1rem;margin-bottom:.8rem;border:1px solid var(--line);box-shadow:0 2px 8px rgba(38,50,56,.05)}
[data-testid=stMetric]{padding:.7rem .9rem}
[data-testid=stMetricValue]{color:var(--em);font-weight:800}
.card h4{margin:0 0 .6rem;font-size:1.05rem;color:var(--em)}
.alert{border-inline-start:5px solid;border-radius:12px;padding:.6rem .9rem;margin-bottom:.5rem;background:#fff;font-weight:500;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
.alert.high{border-color:#c62828;background:#fdecea}.alert.mid{border-color:#ef8f00;background:#fff6e5}.alert.low{border-color:var(--mint);background:#eef8ee}
.strip{display:grid;grid-template-columns:repeat(7,1fr);gap:5px}
.cell{border-radius:10px;padding:.45rem 0;text-align:center;font-size:.72rem;line-height:1.3}
.cell b{display:block}.cell span{font-size:.95rem;font-weight:700}
.cell.low{background:#d7efd8}.cell.mid{background:#ffe3a3}.cell.high{background:#f4b1ab}
.fc{background:#fff;border:1px solid var(--line)}
.fc span{font-weight:500;font-size:.75rem;color:var(--sl)}
.stTabs [data-baseweb=tab-list]{gap:6px;background:#fff;border-radius:14px;padding:4px;border:1px solid var(--line)}
.stTabs [data-baseweb=tab]{border-radius:10px;padding:.4rem .9rem;color:var(--sl);height:auto}
.stTabs [aria-selected=true]{background:var(--em);color:#fff}
.stTabs [data-baseweb=tab-highlight],.stTabs [data-baseweb=tab-border]{display:none}
[data-testid=stSidebar]{background:#fff;border-inline-end:1px solid var(--line)}
.side{background:linear-gradient(135deg,#1b5e20,#4caf50);color:#fff;border-radius:16px;padding:1rem;margin-bottom:1rem;line-height:1.8}
.st-key-nav{position:fixed;bottom:0;left:0;right:0;z-index:999;background:#fff;border-top:1px solid var(--line);padding:.35rem .4rem calc(.35rem + env(safe-area-inset-bottom))}
.st-key-nav [role=radiogroup]{justify-content:space-around;flex-wrap:nowrap;width:100%;max-width:760px;margin:auto;gap:0}
.st-key-nav label{margin:0;padding:.35rem .6rem;border-radius:14px;font-size:.8rem;text-align:center}
.st-key-nav label>div:first-child{display:none}
.st-key-nav label:has(input:checked){background:var(--em);color:#fff}
.st-key-nav label:has(input:checked) *{color:#fff!important}
.stButton>button,.stFormSubmitButton>button,.stLinkButton>a{border-radius:14px;font-weight:700;background:var(--em);color:#fff;border:0}
.stButton>button:hover,.stFormSubmitButton>button:hover{background:var(--mint);color:#fff}
"""


def wx(lat, lon):
    """Forecast with a 30-min disk cache; offline, falls back to the last saved forecast (flagged _stale)."""
    c = U.load("wx", None)
    same = c and abs(c.get("_lat", 0) - lat) < 0.01 and abs(c.get("_lon", 0) - lon) < 0.01
    if same and (datetime.now() - datetime.fromisoformat(c["_ts"])).total_seconds() < 1800:
        return c
    try:
        w = C.weather(lat, lon)
        w.update(_ts=datetime.now().isoformat(timespec="minutes"), _lat=lat, _lon=lon)
        U.save("wx", w)
        return w
    except Exception:
        return dict(c, _stale=True) if same else None


def lv_name(t):
    return dict(low=t("منخفض", "Faible", "Low"), mid=t("متوسط", "Moyen", "Medium"), high=t("مرتفع", "Élevé", "High"))


def strip(rs):
    return '<div class="strip">' + "".join(
        f'<div class="cell {C.level(s)}"><b>{d[8:10]}/{d[5:7]}</b><span>{int(s)}%</span></div>' for d, s in rs) + "</div>"


def bars(items, color="#2e7d32", unit="", dec=0):
    """Dependency-free bar chart card: items = [(label, value)]; negative values are red."""
    top = max((abs(v) for _, v in items), default=0) or 1
    rows = "".join(
        f'<div style="display:flex;align-items:center;gap:8px;margin:3px 0;font-size:.8rem"><span style="width:84px;flex:none">{k}</span>'
        f'<div style="flex:1;background:#eef2f1;border-radius:6px"><div style="width:{max(2, abs(v) / top * 100):.0f}%;background:{color if v >= 0 else "#c62828"};height:14px;border-radius:6px"></div></div>'
        f'<b style="width:74px;text-align:end;flex:none">{v:,.{dec}f}{unit}</b></div>' for k, v in items)
    st.markdown(f'<div class="card">{rows}</div>', unsafe_allow_html=True)


def place_search(t, p, key):
    """Place-name search or GPS; updates p in place and returns True when the location changed."""
    q = st.text_input(t("ابحث عن موقعك (بلدية/ولاية)", "Rechercher votre commune", "Search your town"), p.get("place", ""), key=key)
    if q and q != p.get("place"):
        try:
            res = C.geocode(q, t.lang)
        except Exception:
            res = []
        if res:
            lab = st.selectbox(t("اختر", "Choisir", "Choose"), [r[0] for r in res], key=key + "s")
            r = next(x for x in res if x[0] == lab)
            p.update(place=r[0], lat=r[1], lon=r[2])
            return True
        st.caption(t("لا نتائج أو لا يوجد اتصال.", "Aucun résultat ou hors ligne.", "No results or offline."))
    if get_geolocation and st.toggle(t("استخدم GPS", "Utiliser le GPS", "Use GPS"), key=key + "g"):
        g = get_geolocation()
        if g and "coords" in g:
            p.update(place="GPS", lat=g["coords"]["latitude"], lon=g["coords"]["longitude"])
            return True
    return False


def onboarding(t, p):
    st.markdown(f'<div class="hero"><h2>🌾 AgriShield-AI</h2><small>{t("مساعدك الزراعي: طقس، أمراض، سقي، مواشي وحسابات", "Météo, maladies, irrigation, élevage et comptes", "Weather, disease, irrigation, livestock and accounts")}</small></div>', unsafe_allow_html=True)
    lang = st.selectbox("Langue / اللغة", list(LANGS), format_func=LANGS.get, index=list(LANGS).index(p.get("lang", "ar")))
    if lang != p.get("lang", "ar"):
        p["lang"] = lang
        U.save("profile", p)
        st.rerun()
    p["name"] = st.text_input(t("الاسم", "Nom", "Name"))
    place_search(t, p, "ob")
    p["crops"] = st.multiselect(t("محاصيلك", "Vos cultures", "Your crops"), list(C.CROPS), format_func=lambda k: t.p(C.CROPS[k]["n"]))
    p["animals"] = st.multiselect(t("مواشيك", "Votre élevage", "Your livestock"), list(L.ANIMALS), format_func=lambda k: t.p(L.ANIMALS[k]["n"]))
    if st.button(t("ابدأ", "Commencer", "Start"), use_container_width=True) and p["name"]:
        p.setdefault("lat", 36.75), p.setdefault("lon", 3.06), p.setdefault("place", "Alger")
        U.save("profile", p)
        st.rerun()


def notify(t, p, alerts):
    """Browser notification for high-risk alerts, once per day (works while the app is open; needs permission)."""
    hi = [m for a, m in alerts if a == "high"]
    key = f"{date.today()}:{len(hi)}"
    if p.get("notify") and hi and streamlit_js_eval and p.get("last_notif") != key:
        js = ('(async()=>{const P=window.parent;if(P.Notification.permission!=="granted")await P.Notification.requestPermission();'
              'if(P.Notification.permission==="granted")new P.Notification("AgriShield-AI",{body:%s});return 1})()' % json.dumps(" | ".join(hi)[:200]))
        streamlit_js_eval(js_expressions=js, key="notif" + key)
        p["last_notif"] = key
        U.save("profile", p)


def page_home(t, p, w):
    cur = w["current"] if w else None
    hero = f'<div class="hero"><small>{date.today():%d/%m/%Y} · 📍 {p["place"]}</small><h2>{U.greeting(t)} {p["name"]}</h2>'
    if cur:
        hero += f'<div class="now">{C.icon(cur["weather_code"])} {cur["temperature_2m"]:.0f}°<span>💧{cur["relative_humidity_2m"]}%  💨{cur["wind_speed_10m"]:.0f} km/h</span></div>'
    st.markdown(hero + "</div>", unsafe_allow_html=True)
    if not w:
        return st.warning(t("لا يوجد اتصال بخدمة الطقس.", "Météo indisponible (hors ligne).", "Weather unavailable (offline)."))
    d, names = w["daily"], lv_name(t)
    m1, m2, m3 = st.columns(3)
    m1.metric(t("رطوبة", "Humidité", "Humidity"), f'{cur["relative_humidity_2m"]}%')
    m2.metric(t("أمطار 3 أيام", "Pluie 3 j", "Rain 3 d"), f'{sum(C.n(x) for x in d["precipitation_sum"][:3]):.0f} mm')
    m3.metric("ET₀", f'{C.n(d["et0_fao_evapotranspiration"][0]):.1f} mm')
    alerts = []
    for k in p["crops"]:
        c = C.CROPS[k]
        rs = C.risk(w, c, date.today().month)[:4]
        worst = max(rs, key=lambda r: r[1])
        if C.level(worst[1]) != "low":
            sw = C.spray(w, [r[0] for r in rs].index(worst[0]))
            tip = t(f" · أفضل رش: {sw[0]}:00–{sw[1]}:00", f" · pulvériser {sw[0]}h–{sw[1]}h", f" · spray {sw[0]}:00–{sw[1]}:00") if sw else ""
            alerts.append((C.level(worst[1]), f'{t.p(c["n"])}: {t.p(c["d"])} {names[C.level(worst[1])]} ({int(worst[1])}%) {worst[0][5:]}{tip}'))
    rain = sum(C.n(x) for x in d["precipitation_sum"][:3])
    alerts.append(("low" if rain < 5 else "mid", t(f"أمطار متوقعة 3 أيام: {rain:.0f} ملم", f"Pluie 3 jours : {rain:.0f} mm", f"Rain next 3 days: {rain:.0f} mm")))
    if max(C.n(x) for x in d["temperature_2m_min"][:3]) is not None and min(C.n(x) for x in d["temperature_2m_min"][:3]) <= 2:
        alerts.append(("high", t("خطر صقيع قريب: غطِّ الشتلات.", "Risque de gel : protégez les plants.", "Frost risk: cover seedlings.")))
    st.markdown("".join(f'<div class="alert {a}">{m}</div>' for a, m in alerts), unsafe_allow_html=True)
    notify(t, p, alerts)
    st.link_button(t("📤 شارك الملخص عبر واتساب", "📤 Partager sur WhatsApp", "📤 Share digest on WhatsApp"),
                   "https://wa.me/?text=" + urllib.parse.quote("🌾 AgriShield-AI\n" + "\n".join(m for _, m in alerts)), use_container_width=True)
    cells = "".join(f'<div class="cell fc"><b>{x[8:10]}/{x[5:7]}</b>{C.icon(c)}<br><b>{hi:.0f}°</b><span>{lo:.0f}°</span></div>'
                    for x, c, hi, lo in zip(d["time"], d["weather_code"], d["temperature_2m_max"], d["temperature_2m_min"]))
    st.markdown(f'<div class="card"><h4>{t("7 أيام", "7 jours", "7 days")}</h4><div class="strip">{cells}</div></div>', unsafe_allow_html=True)
    j = U.load("journal", [])
    if j:
        net = U.ledger_summary(j)[2]
        st.metric(t("صافي المزرعة (دج)", "Bilan ferme (DZD)", "Farm net (DZD)"), f"{net:,.0f}")


def diag_section(t, p, w):
    with st.expander(t("📷 تشخيص مرض من صورة", "📷 Diagnostic par photo", "📷 Diagnose from a photo")):
        key = AI.api_key(p)
        if not key:
            return st.info(t("أدخل مفتاح Anthropic API في «حسابي» لتفعيل التشخيص.", "Saisissez la clé API Anthropic dans Profil.", "Add your Anthropic API key in Profile to enable this."))
        crop = st.selectbox(t("المحصول", "Culture", "Crop"), p["crops"], format_func=lambda k: t.p(C.CROPS[k]["n"]), key="dc")
        cam = st.radio("src", [1, 0], format_func=lambda v: t("كاميرا", "Caméra", "Camera") if v else t("رفع صورة", "Importer", "Upload"), horizontal=True, label_visibility="collapsed")
        img = st.camera_input("📷", label_visibility="collapsed") if cam else st.file_uploader("img", ["jpg", "jpeg", "png"], label_visibility="collapsed")
        if img and st.button(t("حلّل الصورة", "Analyser", "Analyse"), use_container_width=True):
            cur = w["current"]
            ctx = f'{cur["temperature_2m"]}C, humidity {cur["relative_humidity_2m"]}%, rain next 3 days {sum(C.n(x) for x in w["daily"]["precipitation_sum"][:3]):.0f}mm, month {date.today().month}'
            with st.spinner("…"):
                try:
                    st.session_state["diag"] = AI.diagnose(img.getvalue(), key, C.CROPS[crop]["n"][2], t.lang, ctx)
                except Exception:
                    st.error(t("تعذّر التحليل: تحقق من المفتاح والاتصال.", "Échec : vérifiez la clé et la connexion.", "Failed: check the key and connection."))
        if st.session_state.get("diag"):
            with st.container(border=True):
                st.markdown(st.session_state["diag"])
            st.caption(t("تشخيص تقريبي بالذكاء الاصطناعي؛ أكّده مع مهندس زراعي.", "Indicatif (IA) ; confirmez avec un agronome.", "AI estimate; confirm with an agronomist."))


def page_crops(t, p, w):
    if not p["crops"]:
        return st.info(t("أضف محاصيل من حسابي.", "Ajoutez des cultures dans Profil.", "Add crops in Profile."))
    if not w:
        return st.warning(t("لا يوجد اتصال.", "Hors ligne.", "Offline."))
    area, names = p.get("area", 1.0), lv_name(t)
    diag_section(t, p, w)
    for k in p["crops"]:
        c = C.CROPS[k]
        rs = C.risk(w, c, date.today().month)
        st.markdown(f'<div class="card"><h4>{t.p(c["n"])} · {t.p(c["d"])}</h4>{strip(rs)}</div>', unsafe_allow_html=True)
        windows = [(i, C.spray(w, i)) for i in range(7)]
        ok = [(i, s) for i, s in windows if s]
        if ok and max(r[1] for r in rs[:4]) >= 20:
            i, s = ok[0]
            st.success(t(f"نافذة رش مناسبة: {rs[i][0][5:]} من {s[0]}:00 إلى {s[1]}:00 (رياح خفيفة وبلا مطر)",
                         f"Fenêtre de traitement : {rs[i][0][5:]} {s[0]}h–{s[1]}h (peu de vent, sans pluie)",
                         f"Spray window: {rs[i][0][5:]} {s[0]}:00–{s[1]}:00 (calm, dry)"))
        top = C.level(max(r[1] for r in rs[:3]))
        st.info(t.p(C.ADVICE[top]) + t(f" (بلل الأوراق اليوم ≈ {C.wetness(w, 0)} س)", f" (humectation foliaire ≈ {C.wetness(w, 0)} h)", f" (leaf wetness today ≈ {C.wetness(w, 0)} h)"))
        mm = C.irrigation(w, c["kc"])
        ih = next((x for x in (C.irrigation_time(w, i) for i in range(3)) if x is not None), None)
        if sum(mm[:3]) > 1 and ih is not None:
            st.caption(t(f"💧 أفضل وقت للسقي: {ih}:00 صباحاً، فتجف الأوراق قبل المساء.", f"💧 Meilleur moment d'irriguer : {ih}h, le feuillage séchera avant le soir.", f"💧 Best irrigation start: {ih}:00, leaves dry before evening."))
        with st.expander(t("احتياج السقي", "Besoin en eau", "Irrigation need")):
            st.caption(t(f"المجموع 7 أيام: {sum(mm):.0f} ملم ≈ {sum(mm) * 10 * area:.0f} م³ لمساحة {area} هكتار",
                         f"Total 7 j : {sum(mm):.0f} mm ≈ {sum(mm) * 10 * area:.0f} m³ pour {area} ha",
                         f"7-day total: {sum(mm):.0f} mm ≈ {sum(mm) * 10 * area:.0f} m³ for {area} ha"))
            bars([(x[5:], v) for x, v in zip(w["daily"]["time"], mm)], dec=1, unit=" mm")
    st.caption(t("المخاطر مؤشرية؛ استشر مهندسا زراعيا.", "Indicatif ; consultez un agronome.", "Indicative only; consult an agronomist."))


def page_herd(t, p, w):
    if not p["animals"]:
        return st.info(t("أضف مواشي من حسابي.", "Ajoutez des animaux dans Profil.", "Add livestock in Profile."))
    tab1, tab2, tab3 = st.tabs([t("العلف", "Ration", "Feed"), t("فرز بيطري", "Triage véto", "Vet triage"), t("التلقيح", "Vaccins", "Vaccines")])
    price = p.get("price", DEFAULT_PRICE)
    with tab1:
        a = st.selectbox(t("النوع", "Espèce", "Species"), p["animals"], format_func=lambda k: t.p(L.ANIMALS[k]["n"]))
        c1, c2 = st.columns(2)
        n = c1.number_input(t("العدد", "Nombre", "Count"), 1, 10000, 20)
        wt = c2.number_input(t("الوزن (كغ)", "Poids (kg)", "Weight (kg)"), 0.5, 900.0, float(L.ANIMALS[a]["w"]))
        pu = st.radio(t("الغرض", "Objectif", "Purpose"), list(L.PURPOSES), format_func=lambda k: t.p(L.PURPOSES[k][0]), horizontal=True)
        r = L.feed(a, n, wt, pu, price)
        st.markdown(f'<div class="card"><h4>{t("يوميا للقطيع", "Par jour (troupeau)", "Daily (herd)")}</h4>'
                    f'🌿 {t("تبن/علف", "Foin", "Hay")}: <b>{r["day"]["hay"]:.1f}</b> kg<br>🌾 {t("شعير", "Orge", "Barley")}: <b>{r["day"]["barley"]:.1f}</b> kg<br>'
                    f'🟤 {t("نخالة", "Son", "Bran")}: <b>{r["day"]["bran"]:.1f}</b> kg<br>💧 {t("ماء", "Eau", "Water")}: <b>{r["water"]:.0f}</b> L</div>', unsafe_allow_html=True)
        st.metric(t("التكلفة (دج) يوم / شهر", "Coût (DZD) jour / mois", "Cost (DZD) day / month"), f'{r["cost_day"]:,.0f} / {r["cost_month"]:,.0f}')
    with tab2:
        keys = st.multiselect(t("الأعراض", "Symptômes", "Symptoms"), list(L.SYM), format_func=lambda k: t.p(L.SYM[k][0]))
        if keys:
            lv = L.triage(keys)
            ic, msg = L.TRIAGE[lv]
            lab = dict(critical=t("حرجة", "Critique", "Critical"), warning=t("تحذير", "Alerte", "Warning"), safe=t("آمنة", "Sans danger", "Safe"))[lv]
            cls = {"critical": "high", "warning": "mid"}.get(lv, "low")
            st.markdown(f'<div class="alert {cls}"><b>{lab}</b> {ic} {t.p(msg)}</div>', unsafe_allow_html=True)
        st.caption(t("لا يغني عن الطبيب البيطري.", "Ne remplace pas le vétérinaire.", "Does not replace a veterinarian."))
    with tab3:
        m = date.today().month
        for a in p["animals"]:
            for mo, nm in sorted(L.VACC[a], key=lambda x: (x[0] - m) % 12):
                soon = (mo - m) % 12 <= 1
                st.markdown(f'<div class="alert {"mid" if soon else "low"}">{"🔔 " if soon else ""}{t.p(L.ANIMALS[a]["n"])} · {t.p(nm)} · {mo:02d}/</div>', unsafe_allow_html=True)
        st.caption(t("تأكد من مواعيد الحملات من المصالح البيطرية.", "Confirmez les dates auprès des services vétérinaires.", "Confirm dates with the veterinary services."))


def page_farm(t, p, w):
    j = U.load("journal", [])
    with st.form("add", clear_on_submit=True):
        c1, c2 = st.columns(2)
        ty = c1.radio(t("النوع", "Type", "Type"), ["out", "in"], format_func=lambda k: t("مصروف", "Dépense", "Expense") if k == "out" else t("دخل", "Revenu", "Income"), horizontal=True)
        cat = c2.selectbox(t("الفئة", "Catégorie", "Category"), range(len(CATS)), format_func=lambda i: t.p(CATS[i]))
        amt = st.number_input(t("المبلغ (دج)", "Montant (DZD)", "Amount (DZD)"), 0.0, step=500.0)
        note = st.text_input(t("ملاحظة", "Note", "Note"))
        if st.form_submit_button(t("حفظ", "Enregistrer", "Save"), use_container_width=True) and amt > 0:
            U.add_entry(ty, cat, amt, note)
            st.rerun()
    if not j:
        return st.info(t("سجّل أول عملية لترى أرباحك.", "Saisissez une opération pour suivre vos marges.", "Log your first entry to track your margin."))
    inc, exp, net = U.ledger_summary(j)
    a, b, c = st.columns(3)
    a.metric(t("دخل", "Revenus", "Income"), f"{inc:,.0f}")
    b.metric(t("مصروف", "Dépenses", "Expenses"), f"{exp:,.0f}")
    c.metric(t("صافي", "Net", "Net"), f"{net:,.0f}")
    month, cats = {}, {}
    for e in j:
        month[e["date"][:7]] = month.get(e["date"][:7], 0) + e["amount"] * (1 if e["type"] == "in" else -1)
        if e["type"] == "out":
            nm = t.p(CATS[e["cat"]])
            cats[nm] = cats.get(nm, 0) + e["amount"]
    bars(sorted(month.items()))
    if cats:
        st.caption(t("المصاريف حسب الفئة", "Dépenses par catégorie", "Expenses by category"))
        bars(sorted(cats.items(), key=lambda x: -x[1]), "#e9c46a")
    buf = io.StringIO()
    wr = csv.writer(buf)
    wr.writerow(["date", "type", "category", "amount", "note"])
    wr.writerows([e["date"], e["type"], t.p(CATS[e["cat"]]), e["amount"], e.get("note", "")] for e in j)
    st.download_button("CSV", buf.getvalue(), "journal.csv", use_container_width=True)


def page_profile(t, p, w):
    p["name"] = st.text_input(t("الاسم", "Nom", "Name"), p["name"])
    lang = st.selectbox("Langue / اللغة", list(LANGS), format_func=LANGS.get, index=list(LANGS).index(p["lang"]))
    p["crops"] = st.multiselect(t("محاصيلك", "Cultures", "Crops"), list(C.CROPS), p["crops"], format_func=lambda k: t.p(C.CROPS[k]["n"]))
    p["animals"] = st.multiselect(t("مواشيك", "Élevage", "Livestock"), list(L.ANIMALS), p["animals"], format_func=lambda k: t.p(L.ANIMALS[k]["n"]))
    p["area"] = st.number_input(t("المساحة (هكتار)", "Surface (ha)", "Area (ha)"), 0.1, 1000.0, float(p.get("area", 1.0)))
    pr = p.get("price", dict(DEFAULT_PRICE))
    with st.expander(t("أسعار العلف (دج/كغ)", "Prix aliments (DZD/kg)", "Feed prices (DZD/kg)")):
        for k, lab in (("hay", t("تبن", "Foin", "Hay")), ("barley", t("شعير", "Orge", "Barley")), ("bran", t("نخالة", "Son", "Bran"))):
            pr[k] = st.number_input(lab, 1.0, 1000.0, float(pr[k]), key="pr" + k)
    p["price"] = pr
    p["notify"] = st.toggle(t("إشعارات المتصفح للتنبيهات الخطيرة", "Notifications du navigateur (alertes graves)", "Browser notifications for severe alerts"), p.get("notify", False))
    p["api_key"] = st.text_input("Anthropic API key", p.get("api_key", ""), type="password", help="console.anthropic.com")
    place_search(t, p, "pf")
    st.caption(f'📍 {p["place"]}')
    if st.button(t("حفظ", "Enregistrer", "Save"), use_container_width=True):
        p["lang"] = lang
        U.save("profile", p)
        st.rerun()


def main():
    st.set_page_config("AgriShield-AI", "🌾", layout="centered", initial_sidebar_state="auto")
    p = U.load_profile()
    p["crops"] = [c for c in p["crops"] if c in C.CROPS]
    p["animals"] = [a for a in p["animals"] if a in L.ANIMALS]
    if p["lang"] not in LANGS:
        p["lang"] = "ar"
    t = make_t(p["lang"])
    st.markdown(f"<style>{CSS}{'.stApp,[data-testid=stSidebar]{direction:rtl;text-align:right}' if t.rtl else ''}</style>", unsafe_allow_html=True)
    if not p.get("name"):
        return onboarding(t, p)
    with st.sidebar:
        st.markdown(f'<div class="side"><b>🌾 AgriShield-AI</b><br>👤 {p["name"]}<br>📍 {p["place"]}</div>', unsafe_allow_html=True)
        lg = st.selectbox("Langue / اللغة", list(LANGS), format_func=LANGS.get, index=list(LANGS).index(p["lang"]), key="sblang")
        if lg != p["lang"]:
            p["lang"] = lg
            U.save("profile", p)
            st.rerun()
        st.caption(t("النصائح استرشادية؛ استشر مهندساً زراعياً أو طبيباً بيطرياً.", "Conseils indicatifs ; consultez un agronome ou un vétérinaire.", "Advice is indicative; consult an agronomist or veterinarian."))
    pages = {"home": ("🏠", t("الرئيسية", "Accueil", "Home"), page_home), "crops": ("🌱", t("المحاصيل", "Cultures", "Crops"), page_crops),
             "herd": ("🐑", t("المواشي", "Élevage", "Herd"), page_herd), "farm": ("📒", t("المزرعة", "Ferme", "Farm"), page_farm),
             "me": ("⚙️", t("حسابي", "Profil", "Profile"), page_profile)}
    with st.container(key="nav"):
        k = st.radio("nav", list(pages), format_func=lambda k: f"{pages[k][0]}\n{pages[k][1]}", horizontal=True, label_visibility="collapsed", key="page")
    w = wx(p["lat"], p["lon"])
    if w and w.get("_stale"):
        st.warning(t(f"وضع بدون إنترنت: آخر تحديث {w['_ts'].replace('T', ' ')}", f"Hors ligne : dernière mise à jour {w['_ts'].replace('T', ' ')}", f"Offline: last updated {w['_ts'].replace('T', ' ')}"))
    pages[k][2](t, p, w)
