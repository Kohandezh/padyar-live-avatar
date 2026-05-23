# ریسک‌ها و کنترل‌های اتصال موتور — Padyar Live Avatar

**Powered by:** Mohammad Kohandezh — KSF Company
**تماس:** info@ksf.ir

---

## ریسک‌های تأخیر (Latency)

| ریسک | احتمال | تأثیر | کنترل |
|---|---|---|---|
| تأخیر شبکه بین runtime و engine | بالا | بالا | استقرار در همان datacenter، health check دوره‌ای، monitoring تأخیر |
| تأخیر استنتاج GPU | متوسط | بالا | batch optimization در موتور، مدل سبک‌تر برای real-time، آمادگی GPU قبل از درخواست |
| تأخیر رمزگذاری/رمزگشایی صوتی | پایین | متوسط | استفاده از PCM raw بدون رمزگذاری اضافی |
| تجمع صف در زمان اوج بار | متوسط | بالا | backpressure در scheduler، صف محدود، reject در سرریز |

### کنترل تأخیر end-to-end

```
تأخیر هدف: < 200ms (audio in → frame out)

audio chunk receive:  ~5ms
audio send to engine: ~10ms
engine inference:     ~80-150ms
frame return:         ~10ms
frame send to client: ~5ms
──────────────────────────
total:                ~110-180ms
```

اگر مجموع از `frame_timeout` (پیش‌فرض: 2s) فراتر رود، fallback فعال می‌شود.

## ریسک‌های حافظه و GPU (Memory/GPU)

| ریسک | احتمال | تأثیر | کنترل |
|---|---|---|---|
| نشت حافظه در موتور | متوسط | بالا | restart دوره‌ای موتور، memory monitoring، limit حافظه process |
| اشباع VRAM | متوسط | بالا | محدود کردن نشست‌های همزمان، page-out مدل‌های غیرفعال |
| OOM (Out of Memory) GPU | پایین | بحرانی | graceful degradation، reject نشست‌های جدید، fallback |
| نشت حافظه در runtime | پایین | متوسط | TTL نشست، cleanup خودکار، memory profiling |

### کنترل منابع GPU

- حداکثر نشست‌های همزمان بر اساس VRAM موجود
- تخمین مصرف VRAM به‌ازای هر نشست
- reject نشست‌های جدید قبل از اشباع
- monitoring لحظه‌ای VRAM

## ریسک‌های آلودگی وابستگی (Dependency Contamination)

| ریسک | احتمال | تأثیر | کنترل |
|---|---|---|---|
| وارد کردن تصادفی ML در runtime | پایین | بحرانی | `test_governance_imports` و `test_governance_deps` |
| import مستقیم از PadYar-LipSync-master | پایین | بحرانی | `test_governance_architecture`، code review |
| اضافه کردن dependency غیرمجاز | متوسط | بالا | `test_governance_deps`، pyproject.toml محدود |
| bypass کردن EngineAdapter | پایین | بحرانی | `test_adapter_contract`، code review |

### قوانین سخت

- runtime فقط مجاز به: FastAPI, Uvicorn, Pydantic
- runtime ممنوع از: torch, tensorflow, onnxruntime, diffusers, transformers, و غیره
- هر نقض توسط CI مسدود می‌شود

## ریسک‌های خرابی پردازش (Process Crash)

| ریسک | احتمال | تأثیر | کنترل |
|---|---|---|---|
| crash موتور استنتاج | متوسط | بالا | health check دوره‌ای، reconnect خودکار، fallback |
| crash runtime | پایین | بحرانی | process manager (systemd/supervisor)، restart خودکار |
| crash هر دو | بسیار پایین | بحرانی | infrastructure monitoring، alerting |
| deadlock در ارتباط | پایین | بالا | timeout در تمام عملیات، watchdog |

### استراتژی بازیابی

1. **موتور crash کند:**
   - health check ناموفق → موتور از rotation خارج
   - نشست‌های فعال → fallback mode
   - reconnect خودکار در پس‌زمینه
   - پس از reconnect → عملیات عادی از سر گرفته می‌شود

2. **runtime crash کند:**
   - process manager restart خودکار
   - نشست‌ها از بین می‌روند (stateless restart)
   - کلاینت‌ها reconnect می‌کنند
   - نشست‌های جدید ایجاد می‌شود

## ریسک‌های بارگذاری مدل (Model Loading)

| ریسک | احتمال | تأثیر | کنترل |
|---|---|---|---|
| زمان بارگذاری طولانی مدل | بالا | متوسط | pre-loading در startup، warmup requests |
| مدل پیدا نشود | متوسط | بالا | validation در startup، health check شامل بررسی مدل |
| نسخه مدل ناسازگار | پایین | بالا | versioning پروتکل، validation در اتصال |
| فایل مدل خراب | بسیار پایین | بحرانی | checksum verification، backup مدل |

### استراتژی بارگذاری

```
startup → بارگذاری مدل → warmup → health_check = True → آماده دریافت
                                             ↓
                           health_check = False → عدم پذیرش نشست
```

## ریسک‌های فایل‌ها و مدل‌های حجیم (Large File/Model Handling)

| ریسک | احتمال | تأثیر | کنترل |
|---|---|---|---|
| مدل بزرگ در VRAM | قطعی | بالا | انتخاب مدل مناسب، quantization، model swapping |
| فایل صوتی بزرگ در حافظه | متوسط | متوسط | chunk processing، عدم بارگذاری کامل در حافظه |
| تعداد زیاد فریم در حافظه | متوسط | متوسط | bounded queue در scheduler، backpressure |
| اسنپشات تاریخی حجیم در repo | قطعی | پایین | `PadYar-LipSync-master/` فقط مرجع، اجرا نمی‌شود |

### استراتژی جلوگیری

- audio: chunk به chunk پردازش شود، نه فایل کامل
- frames: bounded queue، فریم‌های قدیمی discard شوند
- models: در engine lifecycle مدیریت شود، نه در runtime

## ریسک‌های timeout در API

| ریسک | احتمال | تأثیر | کنترل |
|---|---|---|---|
| timeout در generate_frames | متوسط | بالا | `frame_timeout` + fallback frame |
| timeout در health_check | پایین | متوسط | `health_timeout` + موتور از rotation خارج |
| timeout در کلاینت WebSocket | متوسط | متوسط | ping/pong، client-side reconnect |
| timeout در ایجاد اتصال | پایین | بالا | `connect_timeout` + retry |

### سلسله‌مراتب timeout

```
connect_timeout (5s)
    └── frame_timeout (2s per frame)
            └── max_consecutive_timeouts (3)
                    └── fallback mode activation
                            └── reconnect_interval (10s)
```

## استراتژی Fallback

### سطح ۱: فریم جایگزین
- آخرین فریم موفق تکرار شود
- یا فریم خنثی (neutral) ارسال شود
- کلاینت متوجه قطعی نمی‌شود

### سطح ۲: کاهش کیفیت
- رزولوشن فریم کاهش یابد
- frame rate کاهش یابد
- تأخیر قابل‌قبول حفظ شود

### سطح ۳: حالت آفلاین
- آواتار ثابت با پیام "در حال اتصال مجدد"
- تلاش reconnect در پس‌زمینه

### معیار فعال‌سازی

```
fallback_rate > 0.5   → هشدار
fallback_rate > 0.8   → کاهش کیفیت
fallback_rate = 1.0   → حالت آفلاین
```

## استراتژی Rollback

اگر اتصال موتور باعث مشکلات شود:

### rollback بدون downtime

1. `RealEngineAdapter` → غیرفعال
2. `FakeEngineAdapter` → فعال (در صورت نیاز)
3. نشست‌های فعال → تکمیل شوند
4. نشست‌های جدید → reject یا صف
5. بررسی و رفع مشکل
6. reconnect و validation
7. بازگشت به `RealEngineAdapter`

### rollback اضطراری

```bash
# غیرفعال کردن engine در runtime config
ENGINE_ENABLED=false
# یا
ENGINE_ADAPTER=fake
```

با تغییر متغیر محیطی، runtime بدون restart به fallback mode می‌رود.

## درب‌های تأیید (Approval Gates)

| مرحله | تأیید لازم |
|---|---|
| طراحی قرارداد EngineAdapter (این فاز) | تأیید مالک محصول |
| پیاده‌سازی RealEngineAdapter | تأیید مالک محصول |
| تست یکپارچگی با موتور واقعی | تأیید مالک محصول + تست موفق |
| استقرار staging | تأیید مالک محصول |
| استقرار production | تأیید صریح مالک محصول |

هر مرحله بدون تأیید مکتوب نباید شروع شود.

---

*Powered by Mohammad Kohandezh — KSF Company*
*info@ksf.ir*
