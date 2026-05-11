[![en](https://img.shields.io/badge/lang-en-red.svg) ENGLISH](README.md)

# v2rayN Routing Rules Generator + رابط وب

یک ابزار پایتون که قوانین مسیریابی را با فرمت JSON برای برنامه‌ی
[v2rayN](https://github.com/2dust/v2rayN) تولید می‌کند، به همراه یک
**رابط وب سبک محلی** برای مدیریت دامنه‌های اختصاصی روی لیست‌های آپ‌استریم.

هدف اصلی این قوانین: نگه‌داشتن سایت‌های ایرانی روی مسیر مستقیم (بدون VPN)
تا خراب نشن، و عبور بقیه‌ی ترافیک از پراکسی.

فورک از [mer30hamid/v2rayN-Routing-Rules-Generator](https://github.com/mer30hamid/v2rayN-Routing-Rules-Generator).

## چه چیزی به این فورک اضافه شده

- **رابط وب** ([app.py](app.py)) برای اضافه/حذف دامنه بدون ویرایش دستی فایل.
- **لایه‌ی دامنه‌های اختصاصی** ([custom_domains.txt](custom_domains.txt)) که
  روی لیست‌های آپ‌استریم merge می‌شه، پس آپدیت‌های آپ‌استریم اضافه‌های دستی
  رو پاک نمی‌کنن. دامنه‌های اختصاصی در ابتدای لیست نهایی قرار می‌گیرن.
- **commit + push خودکار** به `origin` بعد از هر تغییر — subscription URL
  همیشه آخرین نسخه‌ی قوانین رو سرو می‌کنه.
- **template به‌روز شده** مطابق UI جدید v2rayN: هر قانون `Remarks` خودش رو
  داره، `ruleType: 1` (معادل "routing")، و ترتیب قوانین به‌گونه‌ای تنظیم
  شده که بعد از import نیازی به تنظیم دستی نباشه.

## Subscription URL

این آدرس رو در v2rayN به‌عنوان subscription URL استفاده کن:

```
https://raw.githubusercontent.com/aminmoghadas/v2rayN-Routing-Rules-Generator/main/v2rayN_rules.json
```

## رابط وب

اپ Flask سبک روی `http://127.0.0.1:8765` (فقط لوکال‌هاست). تک‌صفحه‌ای؛
یه تب انتخاب کن، دامنه (یا URL کامل — خودش نرمالایز می‌کنه) رو تایپ کن
و **Add** بزن. backend فایل `v2rayN_rules.json` رو دوباره می‌سازه،
commit می‌کنه و به `origin/main` push می‌کنه. دفعه‌ی بعدی که v2rayN
subscription رو refresh کنه، تغییرات live می‌شن.

امکانات:

- تب Whitelist (قوانین → `direct`، برای سایت‌های ایرانی) و Blocklist
  (قوانین → `block`).
- نرمالایز ورودی: `https://Foo.COM/path` → `foo.com`.
- جلوگیری از تکرار: دامنه‌ای که در همون لیست custom، در لیست مقابل custom،
  یا از قبل در لیست آپ‌استریم همان گروه باشه رد می‌شه.
- نمایش subscription URL با دکمه‌ی کپی.
- نمایش آخرین commit لوکال و آخرین commit روی `origin/main`.
- دکمه‌ی «به‌روزرسانی لیست‌های آپ‌استریم» برای دانلود مجدد دستی.

### اجرا

اولین بار:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

سپس:

```bash
.venv/bin/python app.py
```

`http://127.0.0.1:8765` رو در مرورگر باز کن.

> توجه: UI فقط روی `127.0.0.1` گوش می‌ده و push با همون احراز هویت git
> (SSH/HTTPS) که از قبل تنظیم شده انجام می‌شه — لایه‌ی احراز جداگانه نداره.

## وارد کردن قوانین در v2rayN

1. در v2rayN: **Settings → Routing Setting → Add Rule**
2. **Remarks**: `Iran` (یا هر اسمی)
3. **URL (optional)**: آدرس subscription بالا رو paste کن
4. روی **Import Rules From Subscription URL** کلیک کن و تأیید کن
5. در پایین v2rayN، بخش routing، اسم تازه‌ساخته رو انتخاب کن

بعد از اولین import لازم نیست این مراحل رو تکرار کنی — v2rayN به‌صورت
دستی (راست‌کلیک روی subscription → Update) یا بر اساس بازه‌ی auto-update
(در تنظیمات کلی v2rayN) از همون URL آخرین قوانین رو می‌گیره.

## اجرای generator بدون UI

اگه فقط فایل JSON رو می‌خوای، entry point اصلی هنوز کار می‌کنه:

```bash
.venv/bin/python generate-rules.py
```

این فقط با لیست‌های آپ‌استریم (بدون دامنه‌های custom) فایل
`v2rayN_rules.json` رو می‌سازه و کش رو در `iran_domains/` آپدیت می‌کنه.

## فایل‌ها

| مسیر | توضیح |
|---|---|
| [generate-rules.py](generate-rules.py) | generator اصلی CLI |
| [app.py](app.py) | backend Flask و منطق git push |
| [templates/index.html](templates/index.html) | UI تک‌صفحه‌ای |
| [v2rayN-rules-template.json](v2rayN-rules-template.json) | اسکلت قوانین |
| [v2rayN_rules.json](v2rayN_rules.json) | خروجی نهایی (commit شده) |
| [custom_domains.txt](custom_domains.txt) | دامنه‌های اختصاصی |
| [iran_domains/](iran_domains/) | کش لیست‌های آپ‌استریم (در gitignore) |

## منابع آپ‌استریم

- [SamadiPour/iran-hosted-domains](https://github.com/SamadiPour/iran-hosted-domains) — لیست سفید سایت‌های ایرانی
- [MasterKia/PersianBlocker](https://github.com/MasterKia/PersianBlocker) — لیست بلاک تبلیغات و ترکرهای فارسی
