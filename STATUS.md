# Jarvis v1.0.0 — اجرایی / محدودیت‌ها

- [x] پروژه کاملاً جدا از Black-Clover- و Black-Clover-Maria-Backups
- [x] شش پرامپت پایه PDF در کد پیاده‌سازی شده‌اند
- [x] ۳۰ یادداشت فارسی نمونه و ۱۸ اتصال (تعداد وابسته به تغییر یادداشت‌ها)
- [x] سرور Python Stdlib و APIهای ask/remember/speak/status/graph
- [x] نسخه تعاملی وب، 3D با CDN و نمای 2D بدون CDN
- [x] مسیرهای مدل Claude/Codex/OpenAI/Anthropic و بازگشت شفاف به خلاصه محلی
- [x] پنل ستاره، پاسخ با منابع و تمرکز روی خوشه، میکروفون و کنترل پخش صدا
- [x] امنیت پایه localhost، Origin، allowlist و عدم ارائه کلید
- [x] ۱۶ آزمون واحد و API موفق در محیط توسعه
- [x] آزمون رابط DOM با مرورگر Chromium و API شبیه‌سازی‌شده: سؤال، پاسخ و یادداشت جدید بدون خطای JS
- [x] پایپ‌لاین ساخت Jarvis.exe و Jarvis-Setup-1.0.0.exe برای Windows
- [ ] اجرای مستقیم روی Windows کاربر؛ دستگاه Desktop Commander اکنون Offline بود
- [ ] کامپایل و امضای نصب‌کننده Windows (اینجا سیستم Linux است)
- [ ] انتشار در GitHub با مخزن کاملاً جدید Jarvis (ابزار GitHub فعلی قابلیت ایجاد repository ندارد)
- [ ] تأیید میکروفون، Edge TTS آنلاین و Claude/Codex login در سیستم کاربر
- [ ] تست واقعی کتابخانه 3d-force-graph از CDN و WebGL در ویندوز (در محیط آزمون دسترسی خارجی مرورگر بسته بود)

از بیان «۱۰۰٪ آماده و نصب‌شده» تا زمان بررسی موارد باز خودداری شود.


## Premium integration — 2026-10-20
- [x] Cinematic high-density RTL UI, responsive desktop/mobile, animated holographic HUD, particle visual, source wave, category filters, quick actions.
- [x] Browser wake phrase with explicit opt-in and limits; no unsupported always-on OS claim.
- [x] Safe allowlisted Windows actions + explicit lock approval + origin-guarded execute endpoint.
- [x] Optional offline faster-whisper integration requiring a pre-installed model; no silent download.
- [x] Offline WebGL 3D renderer alongside CDN version; 2D fallback for no GPU.
- [x] 27 Python unit/security tests passing in development container; simulated browser interaction passed.
- [ ] Real Windows device currently offline; microphone, GPU, speech and OS commands not validated on target machine.
- [ ] Windows packaged EXE/NSIS install verification requires successful GitHub Actions run or connected Windows device.
- [ ] Always-on wake outside browser and verified in-app real-time news/weather/price APIs are NOT implemented (requires native service / providers).
