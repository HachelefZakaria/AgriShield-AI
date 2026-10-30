"""Leaf-photo diagnosis via the Claude API. Key: st.secrets / env ANTHROPIC_API_KEY / profile."""
import base64
import io
import json
import os
import urllib.request


MODEL = "claude-sonnet-5-5"


def api_key(p):
    try:
        import streamlit as st
        k = st.secrets.get("ANTHROPIC_API_KEY")
    except Exception:
        k = None
    return k or os.environ.get("ANTHROPIC_API_KEY") or p.get("api_key")


def diagnose(img_bytes, key, crop, lang, ctx):
    from PIL import Image  # imported lazily so the app starts even where Pillow is blocked

    im = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    im.thumbnail((1280, 1280))
    b = io.BytesIO()
    im.save(b, "JPEG", quality=85)
    L = {"ar": "العربية", "fr": "français", "en": "English"}[lang]
    prompt = (f"You are an agronomist helping Algerian farmers. Crop: {crop}. Local conditions: {ctx}. Analyse the photo. Reply in {L}, concise, with: "
              "1) most likely problem plus two alternatives, each with confidence (low/medium/high); 2) visible evidence; "
              "3) what to do now: cultural practices and treatment classes, no doses; 4) when to call an agronomist. "
              "If the photo is unclear or not a plant, say so and ask for a better one.")
    img = dict(type="base64", media_type="image/jpeg", data=base64.b64encode(b.getvalue()).decode())
    body = json.dumps(dict(model=MODEL, max_tokens=900, messages=[dict(role="user", content=[
        dict(type="image", source=img), dict(type="text", text=prompt)])])).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", body,
                                 {"content-type": "application/json", "x-api-key": key, "anthropic-version": "2023-06-01"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return "".join(c.get("text", "") for c in json.load(r)["content"])
