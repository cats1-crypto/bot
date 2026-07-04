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


def generate_affiliate_link(product_url: str) -> dict:
    """يستدعي aliexpress.affiliate.link.generate لتحويل رابط عادي إلى رابط أفلييت."""
    params = {
        "app_key": APP_KEY,
        "method": "aliexpress.affiliate.link.generate",
        "sign_method": "sha256",
        "timestamp": str(int(time.time() * 1000)),
        "format": "json",
        "v": "2.0",
        "promotion_link_type": "0",
        "source_values": product_url,
        "tracking_id": TRACKING_ID,
    }
    params["sign"] = sign_request(params)
    resp = requests.get(API_URL, params=params, timeout=15)
    return resp.json()


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
        "أهلاً 👋\n"
        "أرسل لي رابط أي منتج من AliExpress وسأرجع لك:\n"
        "🔗 رابط الإحالة (Affiliate Link)\n"
        "💰 السعر الحالي والخصم\n\n"
        "فقط الصق الرابط هنا."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    match = PRODUCT_LINK_RE.search(text)
    if not match:
        await update.message.reply_text("من فضلك أرسل رابط منتج صالح من AliExpress 🙏")
        return

    product_url = match.group(1)
    await update.message.reply_text("⏳ جاري توليد رابط الإحالة...")

    try:
        link_data = generate_affiliate_link(product_url)
        promo_links = (
            link_data.get("aliexpress_affiliate_link_generate_response", {})
            .get("resp_result", {})
            .get("result", {})
            .get("promotion_links", {})
            .get("promotion_link", [])
        )
        if not promo_links:
            await update.message.reply_text(
                "⚠️ لم أتمكن من توليد رابط الإحالة. تأكد من صلاحية الرابط أو من إعدادات API."
            )
            log.warning("Empty response: %s", link_data)
            return

        affiliate_url = promo_links[0]["promotion_link"]

        product_id = extract_product_id(product_url)
        price_text = ""
        if product_id:
            try:
                detail = get_product_detail(product_id)
                products = (
                    detail.get("aliexpress_affiliate_productdetail_get_response", {})
                    .get("resp_result", {})
                    .get("result", {})
                    .get("products", {})
                    .get("product", [])
                )
                if products:
                    p = products[0]
                    orig = p.get("original_price")
                    sale = p.get("target_sale_price") or p.get("sale_price")
                    title = p.get("product_title", "")
                    if orig and sale:
                        price_text = f"\n🏷️ {title[:60]}\n💵 ~~{orig}~~ ➜ {sale} BRL"
            except Exception as e:
                log.warning("Product detail fetch failed: %s", e)

        await update.message.reply_text(
            f"✅ رابط الإحالة جاهز:\n{affiliate_url}{price_text}"
        )

    except Exception as e:
        log.exception("Error generating link")
        await update.message.reply_text(f"❌ حدث خطأ: {e}")


def main():
    if not BOT_TOKEN or not APP_KEY or not APP_SECRET:
        raise SystemExit(
            "❌ تأكد من ضبط TELEGRAM_BOT_TOKEN و ALIEXPRESS_APP_KEY و ALIEXPRESS_APP_SECRET في ملف .env"
        )

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    log.info("🚀 Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
