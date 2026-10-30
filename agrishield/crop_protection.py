"""Weather (Open-Meteo, no API key), fungal-disease risk, spray windows and irrigation needs."""
import json
import urllib.parse
import urllib.request

CROPS = {
    "wheat": dict(n=("قمح", "Blé", "Wheat"), d=("الصدأ", "Rouille", "Rust"), t=(10, 22), h=80, m=(2, 3, 4, 5), kc=1.1),
    "potato": dict(n=("بطاطس", "Pomme de terre", "Potato"), d=("اللفحة المتأخرة", "Mildiou", "Late blight"), t=(10, 24), h=85, m=(2, 3, 4, 5, 9, 10, 11), kc=1.1),
    "tomato": dict(n=("طماطم", "Tomate", "Tomato"), d=("اللفحة والبياض", "Mildiou", "Blight"), t=(12, 26), h=80, m=(3, 4, 5, 6, 9, 10), kc=1.1),
    "olive": dict(n=("زيتون", "Olivier", "Olive"), d=("عين الطاووس", "Œil de paon", "Peacock spot"), t=(12, 20), h=80, m=(10, 11, 12, 1, 2, 3, 4), kc=0.65),
    "grape": dict(n=("عنب", "Vigne", "Grape"), d=("البياض الزغبي", "Mildiou", "Downy mildew"), t=(15, 25), h=75, m=(3, 4, 5, 6, 7), kc=0.7),
}
n = lambda v: 0 if v is None else v


def _get(url):
    with urllib.request.urlopen(url, timeout=8) as r:
        return json.load(r)


def geocode(name, lang="en"):
    q = urllib.parse.urlencode(dict(name=name, count=5, language=lang))
    res = _get("https://geocoding-api.open-meteo.com/v1/search?" + q).get("results", [])
    return [(f'{r["name"]}, {r.get("admin1", "")}'.strip(", "), r["latitude"], r["longitude"]) for r in res]


def weather(lat, lon):
    q = urllib.parse.urlencode(dict(
        latitude=lat, longitude=lon, timezone="auto", forecast_days=7,
        current="temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
        hourly="temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
        daily="temperature_2m_max,temperature_2m_min,precipitation_sum,et0_fao_evapotranspiration,weather_code"))
    return _get("https://api.open-meteo.com/v1/forecast?" + q)


def icon(code):
    return "☀️" if code == 0 else "⛅" if code < 4 else "🌫️" if code < 50 else "🌧️" if code < 70 else "❄️" if code < 80 else "🌦️" if code < 90 else "⛈️"


def risk(w, c, month):
    """Daily fungal risk 0-100 from temperature, humidity and estimated leaf wetness (RH>=90% or rain), damped off-season."""
    h, out = w["hourly"], []
    for i, d in enumerate(w["daily"]["time"]):
        fav = wet = 0
        for j in range(i * 24, i * 24 + 24):
            if c["t"][0] <= n(h["temperature_2m"][j]) <= c["t"][1]:
                fav += n(h["relative_humidity_2m"][j]) >= c["h"]
                wet += n(h["relative_humidity_2m"][j]) >= 90 or n(h["precipitation"][j]) > 0
        out.append((d, min(100, (fav / 24 * 100 + wet / 24 * 40) * (1 if month in c["m"] else 0.4))))
    return out


def wetness(w, i):
    """Estimated leaf-wetness hours on day i (RH >= 90% or rain)."""
    h = w["hourly"]
    return sum(1 for j in range(i * 24, i * 24 + 24) if n(h["relative_humidity_2m"][j]) >= 90 or n(h["precipitation"][j]) > 0)


def irrigation_time(w, i):
    """Earliest start hour (04-09h) with 3 calm, dry hours: early watering lets leaves dry before evening."""
    h = w["hourly"]
    for s in range(4, 10):
        if all(n(h["wind_speed_10m"][j]) < 12 and n(h["precipitation"][j]) == 0 for j in range(i * 24 + s, i * 24 + s + 3)):
            return s
    return None


ADVICE = dict(
    low=("الظروف غير ملائمة للمرض: راقب الحقل أسبوعياً.", "Conditions défavorables : surveillance hebdomadaire.", "Unfavourable for disease: scout weekly."),
    mid=("خطر متوسط: تفقّد الأوراق السفلية وجهّز علاجاً وقائياً.", "Risque moyen : inspectez les feuilles basses, préparez un traitement préventif.", "Medium risk: check lower leaves and prepare a protective treatment."),
    high=("خطر مرتفع: عالج وقائياً قبل فترة الإصابة، وناوب بين مجموعات المبيدات، وتجنّب الرش مع رياح أو قبل المطر بأقل من 4 ساعات.",
          "Risque élevé : traitez en préventif avant la période d'infection, alternez les modes d'action, évitez vent et pluie dans les 4 h.",
          "High risk: apply a protectant before the infection period, rotate modes of action, avoid wind and rain within 4 h."))


def level(s):
    return "high" if s >= 45 else "mid" if s >= 20 else "low"


def spray(w, i):
    """Longest daytime run (>=3h) with wind < 15 km/h and no rain, as (start_hour, end_hour) or None."""
    h, best, run = w["hourly"], (0, 0, 0), 0
    for j in range(i * 24 + 6, i * 24 + 20):
        run = run + 1 if n(h["wind_speed_10m"][j]) < 15 and n(h["precipitation"][j]) == 0 else 0
        if run > best[0]:
            best = (run, j - i * 24 - run + 1, j - i * 24 + 1)
    return best[1:] if best[0] >= 3 else None


def irrigation(w, kc):
    """Net water need per day in mm: ET0 x Kc minus 80% of rain."""
    d = w["daily"]
    return [max(0.0, n(e) * kc - 0.8 * n(r)) for e, r in zip(d["et0_fao_evapotranspiration"], d["precipitation_sum"])]
