# 🌾 AgriShield-AI

**EN** · [العربية](#-العربية)

A mobile-first, privacy-first AgriTech assistant for smallholder farmers, built with Streamlit. Available in **English, French and Arabic (full RTL)**. No account, no tracking: everything is stored on your device in `~/.agrishield/`.

## Features
| Page | What it does |
|---|---|
| 🏠 Home | Current weather, 7-day forecast, metric cards and prioritised alerts (disease, rain, frost) with a WhatsApp digest |
| 🌱 Crops | Daily fungal risk per crop (temperature + humidity + estimated leaf wetness), spray windows (calm, dry hours), irrigation need (ET₀ × Kc) and best watering hour, AI leaf-photo diagnosis |
| 🐑 Herd | Ration and cost calculator (cattle, sheep, goats, poultry; by weight and purpose), vet triage classified **Critical / Warning / Safe**, vaccination calendar |
| 📒 Farm | Income and expense ledger, monthly net chart, CSV export |
| ⚙️ Profile | Language, location (search or GPS), crops, livestock, field area, feed prices, notifications |

Also: offline mode (last forecast cached), browser notifications for severe alerts (while the app is open).

## Install
Python 3.10–3.13 (very new pre-release Pythons may lack wheels for pandas).

    git clone https://github.com/<you>/AgriShield-AI.git
    cd AgriShield-AI
    python -m venv venv
    venv\Scripts\activate          # Linux/macOS: source venv/bin/activate
    python -m pip install -r requirements.txt
    python -m streamlit run app.py

Weather comes from [Open-Meteo](https://open-meteo.com) (no key). Optional photo diagnosis needs an Anthropic API key in `ANTHROPIC_API_KEY`, `st.secrets`, or the Profile page.
Browser GPS and notifications need HTTPS or `localhost`.

## Structure
    app.py                         entry point (delegates to the UI)
    agrishield/ui_dashboard.py     pages, navigation, styling
    agrishield/crop_protection.py  weather, fungal risk, spray and irrigation logic
    agrishield/livestock_manager.py feed calculator, triage, vaccines
    agrishield/user_profile.py     local profile and ledger storage
    agrishield/ai_diagnosis.py     leaf-photo diagnosis (Claude API)
    agrishield/i18n.py             language helper
    .streamlit/config.toml         light theme

## Disclaimer
Risk scores and advice are indicative heuristics, not professional guidance. Always consult an agronomist or a veterinarian, and follow pesticide labels and local regulations.

---

# 🇩🇿 العربية

مساعد زراعي يعمل بالهاتف أولاً ويحترم الخصوصية، مبني بـ Streamlit، بالعربية (RTL كامل) والفرنسية والإنجليزية. بلا حساب ولا تتبّع: كل بياناتك تُحفظ على جهازك في `~/.agrishield/`.

## المميزات
- 🏠 **الرئيسية:** الطقس وتوقعات 7 أيام وتنبيهات (أمراض، أمطار، صقيع) مع مشاركة عبر واتساب.
- 🌱 **المحاصيل:** خطر الأمراض الفطرية (حرارة + رطوبة + بلل الأوراق)، نوافذ الرش، احتياج السقي وأفضل ساعة له، وتشخيص بصورة الورقة بالذكاء الاصطناعي.
- 🐑 **المواشي:** حاسبة علف وتكلفة (بقر، غنم، ماعز، دجاج)، فرز بيطري **حرج / تحذير / آمن**، وروزنامة تلقيح.
- 📒 **المزرعة:** دفتر دخل ومصروفات مع رسوم بيانية وتصدير CSV.
- ⚙️ **حسابي:** اللغة والموقع والمحاصيل والمواشي والمساحة وأسعار العلف.

## التثبيت
    python -m venv venv
    venv\Scripts\activate
    python -m pip install -r requirements.txt
    python -m streamlit run app.py

التنبيهات استرشادية؛ استشر دائماً مهندساً زراعياً أو طبيباً بيطرياً والتزم بملصق المبيد.

## License
MIT
