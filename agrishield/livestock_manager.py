"""Feed calculator, vet triage and vaccination calendar."""
ANIMALS = {
    "sheep": dict(n=("غنم", "Ovins", "Sheep"), dm=0.03, w=60, water=5),
    "cattle": dict(n=("بقر", "Bovins", "Cattle"), dm=0.025, w=450, water=45),
    "goat": dict(n=("ماعز", "Caprins", "Goats"), dm=0.035, w=45, water=4),
    "poultry": dict(n=("دجاج", "Volaille", "Poultry"), dm=0.06, w=1.8, water=0.25),
}
PURPOSES = {  # dry-matter factor, forage share
    "maint": (("صيانة", "Entretien", "Maintenance"), 1.0, 0.75),
    "lact": (("حلب/إرضاع", "Lactation", "Lactation"), 1.25, 0.55),
    "fatt": (("تسمين", "Engraissement", "Fattening"), 1.15, 0.35),
}


def feed(animal, count, weight, purpose, price):
    a, (_, f, share) = ANIMALS[animal], PURPOSES[purpose]
    share = 0 if animal == "poultry" else share
    dm = a["dm"] * weight * f
    kg = dict(hay=dm * share / 0.88, barley=dm * (1 - share) * 0.7 / 0.88, bran=dm * (1 - share) * 0.3 / 0.88)
    day = {k: v * count for k, v in kg.items()}
    cost = sum(day[k] * price[k] for k in day)
    return dict(per_head=kg, day=day, cost_day=cost, cost_month=cost * 30, water=a["water"] * count * (1.3 if purpose == "lact" else 1))


# symptom: (names, points, red flag)
SYM = {
    "bloat": (("انتفاخ البطن", "Ballonnement", "Bloat"), 5, 1),
    "breath": (("صعوبة التنفس", "Difficulté respiratoire", "Breathing difficulty"), 4, 1),
    "seizure": (("تشنجات/ترنح", "Convulsions", "Seizures"), 5, 1),
    "bloody": (("إسهال دموي", "Diarrhée sanglante", "Bloody diarrhea"), 4, 1),
    "birth": (("عسر ولادة", "Dystocie", "Birthing trouble"), 5, 1),
    "deaths": (("نفوق مفاجئ في القطيع", "Mortalité subite", "Sudden deaths in herd"), 5, 1),
    "fever": (("حمى", "Fièvre", "Fever"), 3, 0),
    "diarrhea": (("إسهال", "Diarrhée", "Diarrhea"), 2, 0),
    "noeat": (("فقدان الشهية", "Perte d'appétit", "Not eating"), 2, 0),
    "cough": (("سعال", "Toux", "Cough"), 2, 0),
    "udder": (("ورم الضرع", "Mammite", "Swollen udder"), 3, 0),
    "skin": (("آفات جلدية", "Lésions cutanées", "Skin lesions"), 2, 0),
    "limp": (("عرج", "Boiterie", "Limping"), 1, 0),
    "nasal": (("إفرازات أنفية", "Écoulement nasal", "Nasal discharge"), 1, 0),
}
TRIAGE = {
    "critical": ("🔴", ("اتصل بالطبيب البيطري الآن، واعزل الحيوان.", "Appelez le vétérinaire maintenant et isolez l'animal.", "Call the vet now and isolate the animal.")),
    "warning": ("🟠", ("اعرضه على الطبيب خلال 24 ساعة، واعزله عن القطيع.", "Consultez sous 24 h et isolez l'animal.", "See a vet within 24 h and isolate the animal.")),
    "safe": ("🟢", ("راقب الحيوان وسجّل الحرارة والأكل، وأعد التقييم غدا.", "Surveillez, notez température et appétit, réévaluez demain.", "Monitor, log temperature and appetite, reassess tomorrow.")),
}


def triage(keys):
    score = sum(SYM[k][1] for k in keys)
    return "critical" if any(SYM[k][2] for k in keys) or score >= 8 else "warning" if score >= 4 else "safe"


# animal: [(month, names)]; confirm dates with the official vet campaign.
VACC = {
    "sheep": [(3, ("جدري الأغنام", "Clavelée", "Sheep pox")), (9, ("التسمم المعوي", "Entérotoxémie", "Enterotoxemia")), (11, ("الحمى القلاعية (حسب الحملة)", "Fièvre aphteuse (campagne)", "FMD (state campaign)"))],
    "goat": [(9, ("التسمم المعوي", "Entérotoxémie", "Enterotoxemia")), (4, ("الحمى المالطية", "Brucellose", "Brucellosis"))],
    "cattle": [(4, ("الحمى القلاعية (حسب الحملة)", "Fièvre aphteuse (campagne)", "FMD (state campaign)")), (10, ("الجلد العقدي", "Dermatose nodulaire", "Lumpy skin disease"))],
    "poultry": [(1, ("نيوكاسل", "Newcastle", "Newcastle")), (6, ("غامبورو", "Gumboro", "Gumboro"))],
}
