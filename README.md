# بوت روابط إحالة AliExpress (Telegram)

بوت بسيط: يستقبل رابط منتج AliExpress ويرجع رابط أفلييت (Affiliate Link) + السعر والخصم — بنفس فكرة `@LoucoMoedasBot`.

## التشغيل على Render.com (يبقى خدام حتى PC مطفي)

### الطريقة: رفع المشروع لـ GitHub ثم ربطه بـ Render

1. أنشئ repo جديد على GitHub وارفع فيه هاد الملفات كاملة (`bot.py`, `requirements.txt`, `Procfile`, `render.yaml`).
   **لا ترفع ملف `.env` أبدًا** — تأكد من وجود `.gitignore` يحتوي `.env`.
2. سجّل الدخول على [render.com](https://render.com) وربط حساب GitHub.
3. اضغط **New +** → **Blueprint**، اختر الـ repo. Render غادي يقرا `render.yaml` أوتوماتيكيًا ويقترح إنشاء **Background Worker**.
4. فخانة Environment Variables، عبّي:
   - `TELEGRAM_BOT_TOKEN`
   - `ALIEXPRESS_APP_KEY`
   - `ALIEXPRESS_APP_SECRET`
   - `ALIEXPRESS_TRACKING_ID`
5. اضغط **Apply** / **Create**. Render غادي يبني وينشغل البوت أوتوماتيكيًا، ويبقى خدام 24/7 حتى ولو PC ديالك مطفي.

### ملاحظات Render
- الخطة المجانية (`plan: free`) ديال Background Worker عندها حدود ساعات فالشهر — تأكد من حدود Render الحالية فالتوثيق الرسمي إذا بغيتي يخدم بلا توقف نهائيًا.
- Render كيدير **restart أوتوماتيكي** إذا طاح البوت، فما خاصكش تقلق على الاستقرار.
- خاصك Repo على GitHub (يقدر يكون Private) — Render Background Worker محتاج Git repo إجباريًا.

---

## التشغيل على Termux (بديل محلي، إيلا بغيتي تجرب قبل النشر)

```bash
pkg install python -y
pip install -r requirements.txt --break-system-packages
cp config.example.env .env
nano .env   # عبّئ التوكن والمفاتيح
python bot.py
```

## من أين تحصل على القيم؟

- **TELEGRAM_BOT_TOKEN**: أنشئ بوت جديد عبر [@BotFather](https://t.me/BotFather) بأمر `/newbot`
- **ALIEXPRESS_APP_KEY / APP_SECRET**: من [AliExpress Open Platform](https://portals.aliexpress.com) بعد تفعيل تطبيق Affiliate
- **ALIEXPRESS_TRACKING_ID**: من حسابك في AliExpress Affiliate Portal (نفس الـ tracking_id المستخدم في أدواتك الحالية)

## تشغيله باستمرار في الخلفية على Termux

```bash
pkg install tmux -y
tmux new -s aliexbot
python bot.py
# اضغط Ctrl+B ثم D للخروج بدون إيقاف البوت
```

## ملاحظات مهمة

- **لا تشارك ملف `.env` أو محتواه في أي محادثة** — لاحظتُ في مشاريعك السابقة تسريب مفاتيح API عدة مرات، وهذا يعرضها للاستخدام من طرف آخرين. إذا انكشف أي مفتاح، ألغِه فورًا من AliExpress Open Platform.
- إذا أردت لاحقًا ربط البوت تلقائيًا بقناتك على Telegram (@Ofertassdiariasaliexpresss) أو بـ Pinterest/Buffer عبر Make.com، يمكن توسيع هذا الكود ليرسل الروابط تلقائيًا بدل الرد اليدوي فقط — أخبرني إذا تريد ذلك.
- الكود يفترض استخدام واجهة AliExpress Affiliate API الرسمية. إذا كنت تستخدم مزود آخر (مثل RapidAPI) بدلاً منها، أخبرني لأعدّل دوال `generate_affiliate_link` و `get_product_detail`.
