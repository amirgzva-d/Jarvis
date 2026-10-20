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

## Incremental delivery v1.2.0 — 2026-10-20

**Implemented and unit-tested locally:**
- Live server-side weather/geolocation with Open-Meteo, topic headlines via Google News RSS, and reference FX rates via ExchangeRate-API open access. Data is attributed with source and timestamps; failures are explicit, not hallucinated. No secret credentials or arbitrary-URL proxy.
- New, responsive in-app Live Intelligence modal. Dynamic loading, error/attribution states and safe external news links. `POST /api/live` is constrained to fixed upstream providers.
- Opt-in native wake worker outside the browser tab while the Jarvis desktop process runs. Uses local audio (sounddevice and faster-whisper), local model path, secure microphone opt-in, optional current-user autostart, time-based wake throttle, and never performs spoken privileged actions in the background. Reopens Jarvis UI when awake. Not a Windows service running after the Jarvis process is terminated.
- Wake status and autostart controls are real, permission-guarded routes, not simulated UI. If dependencies, local model or GPU are unavailable, the feature reports it and stays disabled.
- Real audio waveform amplitude integration when Edge TTS MP3 plays through WebAudio; browser synthesized voices have state-based animation without claiming exact audio samples.
- Updated Windows packaging to collect offline speech dependencies; model weights remain external user-provisioned data.

**Hardware verification still needed before any 100% claim:** speech recognition accuracy with actual microphone, NVIDIA GPU/CUDA support, startup after reboot, native Windows command operation, external API network access, and installer usability. 8 GB RAM / GeForce MX450 2GB device is a restricted-performance target; CPU fallback is available but depends on model selection.

- Natural Persian requests for weather, news topics and FX conversion now route through attributed live providers instead of guessing from personal notes.
- 42 deterministic unit/security tests green in development; Windows build/test and packaging via CI.

## Windows 11 acceptance — Jarvis v1.2.0 (2026-10-20)

- Repository remains independent from both MARIA repositories.
- On DESKTOP-LR1PDM2, Jarvis 1.1.0 installer downloaded from the tagged GitHub Release, and its SHA-256 matched the published asset digest.
- Installation completed without errors; its packaged local HTTP server returned status with 30 sample notes.
- Live Windows test: Open-Meteo weather, Google News RSS, and reference FX rates all returned source-attributed data.
- Packaged Edge TTS returned an audio/mpeg payload of 27,072 bytes. That verifies the API response, not the user's speaker output or microphone capture.
- A Windows timer executed via a guarded local endpoint and reported its completion event.
- This patch adds private-safe diagnostics in Settings, improved wake phrase recognition and CPU fallback when CUDA is unavailable. 48 automated tests passed on the Windows machine.
- Native background listening remains opt-in and OFF; it needs local faster-whisper weights and access to a microphone.
- Neither Codex CLI nor Claude CLI was detected in PATH during preflight. Generative-model functionality remains unverified until an account/provider is configured.
- GPU/CUDA model inference, real spoken Persian recognition, audible speaker output, reboot autostart, and v1.2.0 packaged installer must be individually checked. Do not report them as 100% verified beforehand.
