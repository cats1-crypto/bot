#!/usr/bin/env python3
"""
Bot Telegram لتوليد روابط إحالة (Affiliate Links) لمنتجات AliExpress
مشابه لـ @LoucoMoedasBot — يستقبل رابط منتج ويرجع رابط أفلييت + عرض السعر والخصم.

يعمل على Termux (Android) بدون تثبيت معقد.

الإعداد:
1) pip install python-telegram-bot==21.* requests --break-system-packages  (على Termux: pkg install python ثم pip install ...)
2) انسخ config.example.env إلى .env وعبّئ القيم:
   - TELEGRAM_BOT_TOKEN   (من @BotFather)
   - ALIEXPRESS_APP_KEY
   - ALIEXPRESS_APP_SECRET
   - ALIEXPRESS_TRACKING_ID   (tracking_id من حساب الأفلييت)
3) شغّل: python bot.py

ملاحظة أمان: لا تكتب المفاتيح مباشرة في الكود. استخدم .env دائمًا
لأنك في محادثات سابقة سرّبت مفاتيح API عدة مرات — هذا الملف مصمم لتفادي ذلك.
"""

import os
import re
import time
import hmac
import hashlib
import logging
import asyncio
from urllib.parse import quote

import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
APP_KEY = os.getenv("ALIEXPRESS_APP_KEY")
APP_SECRET = os.getenv("ALIEXPRESS_APP_SECRET")
TRACKING_ID = os.getenv("ALIEXPRESS_TRACKING_ID", "default")

API_URL = "https://api-sg.aliexpress.com/sync"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger(__name__)

PRODUCT_LINK_RE = re.compile(r"(https?://[^\s]*aliexpress\.[^\s]+)", re.IGNORECASE)
PRODUCT_ID_RE = re.compile(r"/item/(?:.*?)?(\d+)\.html|/(\d{9,})(?:\.html)?|item_id=(\d+)")


def sign_request(params: dict) -> str:
    """توقيع HMAC-SHA256 المطلوب من AliExpress Open Platform."""
    sorted_params = sorted(params.items())
    base_string = "".join(f"{k}{v}" for k, v in sorted_params)
    signature = hmac.new(
        APP_SECRET.encode("utf-8"), base_string.encode("utf-8"), hashlib.sha256
    ).hexdigest().upper()
    return signature


def extract_product_id(url: str) -> str | None:
    match = PRODUCT_ID_RE.search(url)
    if not match:
        return None
    return next(g for g in match.groups() if g)


def _call_link_generate(product_url: str, promotion_link_type: str) -> str | None:
    """يستدعي aliexpress.affiliate.link.generate ويرجع الرابط الأول إن وُجد."""
    params = {
        "app_key": APP_KEY,
        "method": "aliexpress.affiliate.link.generate",
        "sign_method": "sha256",
        "timestamp": str(int(time.time() * 1000)),
        "format": "json",
        "v": "2.0",
        "promotion_link_type": promotion_link_type,
        "source_values": product_url,
        "tracking_id": TRACKING_ID,
    }
    params["sign"] = sign_request(params)
    resp = requests.get(API_URL, params=params, timeout=15)
    data = resp.json()
    promo_links = (
        data.get("aliexpress_affiliate_link_generate_response", {})
        .get("resp_result", {})
        .get("result", {})
        .get("promotion_links", {})
        .get("promotion_link", [])
    )
    if not promo_links:
        log.warning("Empty response (type=%s): %s", promotion_link_type, data)
        return None
    return promo_links[0]["promotion_link"]


def generate_affiliate_links(product_url: str) -> dict:
    """
    Gera dois links de afiliado:
    - mobile: promotion_link_type=2 (link 'hot product', costuma abrir o app e ativar desconto de moedas)
    - desktop: promotion_link_type=0 (link geral, funciona bem em navegador/PC)

    NOTA: a API da AliExpress não documenta oficialmente qual tipo é
    "mobile" vs "desktop" — teste os dois links no celular e no PC.
    Se estiverem trocados, basta inverter os valores "2" e "0" abaixo.
    """
    return {
        "mobile": _call_link_generate(product_url, "2"),
        "desktop": _call_link_generate(product_url, "0"),
    }


def get_product_detail(product_id: str) -> dict:
    """يجلب تفاصيل المنتج (السعر، الخصم، الصورة) عبر aliexpress.affiliate.productdetail.get."""
    params = {
        "app_key": APP_KEY,
        "method": "aliexpress.affiliate.productdetail.get",
        "sign_method": "sha256",
        "timestamp": str(int(time.time() * 1000)),
        "format": "json",
        "v": "2.0",
        "product_ids": product_id,
        "tracking_id": TRACKING_ID,
        "target_currency": "BRL",
        "target_language": "PT",
    }
    params["sign"] = sign_request(params)
    resp = requests.get(API_URL, params=params, timeout=15)
    return resp.json()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Olá! 👋\n"
        "Me envie o link de qualquer produto da AliExpress e eu te devolvo:\n"
        "📱 Link para CELULAR (com desconto de moedas)\n"
        "💻 Link para DESKTOP/NOTEBOOK\n\n"
        "É só colar o link aqui."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    match = PRODUCT_LINK_RE.search(text)
    if not match:
        await update.message.reply_text("Por favor, envie um link válido de produto da AliExpress 🙏")
        return

    product_url = match.group(1)
    await update.message.reply_text("⏳ Gerando seus links de afiliado...")

    try:
        links = generate_affiliate_links(product_url)
        mobile_link = links.get("mobile")
        desktop_link = links.get("desktop")

        if not mobile_link and not desktop_link:
            await update.message.reply_text(
                "⚠️ Não consegui gerar o link de afiliado. Verifique o link enviado ou as configurações da API."
            )
            return

        reply = "Para CELULAR (com desconto de moedas):\n"
        reply += f"{mobile_link}\n\n" if mobile_link else "(indisponível)\n\n"
        reply += "Para DESKTOP/NOTEBOOK:\n"
        reply += f"{desktop_link}\n\n" if desktop_link else "(indisponível)\n\n"
        reply += (
            "Importante: O desconto com moedas só aparece se você abrir o "
            "link do celular diretamente no aplicativo do AliExpress"
        )

        await update.message.reply_text(reply)

    except Exception as e:
        log.exception("Error generating link")
        await update.message.reply_text(f"❌ Ocorreu um erro: {e}")


def main():
    if not BOT_TOKEN or not APP_KEY or not APP_SECRET:
        raise SystemExit(
            "❌ Configure TELEGRAM_BOT_TOKEN, ALIEXPRESS_APP_KEY e ALIEXPRESS_APP_SECRET no arquivo .env"
        )

    # إصلاح توافق Python 3.14: بعض النسخ الحديثة ما عادش كتخلق event loop
    # تلقائيًا فـ الـ MainThread، وهاد الشيء كان كيخلي run_polling() يطيح
    # بـ RuntimeError. هاد الجزء كيضمن وجود event loop قبل ما نبدأو.
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .pool_timeout(30)
        .build()
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    log.info("🚀 Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
