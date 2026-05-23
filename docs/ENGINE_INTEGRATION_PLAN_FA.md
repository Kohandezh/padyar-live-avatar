# طرح اتصال runtime به موتور استنتاج — Padyar Live Avatar

**Powered by:** Mohammad Kohandezh — KSF Company
**تماس:** info@ksf.ir

---

## هدف اتصال runtime به engine

هدف این است که لایه بلادرنگ (`src/padyar_live/`) بتواند بدون هیچ وابستگی مستقیم به فریمورک‌های یادگیری ماشین، فریم‌های تصویری آواتار را از یک موتور استنتاج خارجی (PadYar-LipSync) دریافت کند و از طریق WebSocket به کلاینت‌ها استریم کند.

این اتصال باید:
- بدون وارد کردن ML در runtime انجام شود
- از طریق رابط `EngineAdapter` باشد
- قابل تست بدون GPU باشد
- قابل جایگزینی با موتورهای دیگر باشد

## چرا runtime نباید مستقیماً ML داشته باشد

اگر runtime مستقیماً از torch یا onnxruntime استفاده کند:

1. **نیاز به GPU در هر سرور runtime** — حتی سرورهایی که فقط مدیریت نشست و WebSocket انجام می‌دهند
2. **عدم امکان تست بدون سخت‌افزار** — هر توسعه‌دهنده‌ای به GPU نیاز دارد
3. **وابستگی سنگین** — آپگرید فریمورک ML تمام runtime را تحت تأثیر قرار می‌دهد
4. **عدم مقیاس‌پذیری مستقل** — نمی‌توان runtime و موتور را جداگانه scale کرد
5. **ریسک امنیتی** — مدل‌های ML حجیم سطح حمله را افزایش می‌دهند

به همین دلیل، تمام دسترسی به موتور استنتاج از طریق رابط `EngineAdapter` انجام می‌شود.

## نقش EngineAdapter

`EngineAdapter` یک کلاس انتزاعی (ABC) است که تنها نقطه ارتباط بین runtime و موتور استنتاج را تعریف می‌کند:

```python
class EngineAdapter(ABC):
    @abstractmethod
    async def generate_frames(self, ...) -> AsyncIterator[bytes]: ...

    @abstractmethod
    async def health_check(self) -> bool: ...
```

هر موتوری که این دو متد را پیاده‌سازی کند، بدون تغییر در کد runtime قابل اتصال است.

## تفاوت FakeEngineAdapter و RealEngineAdapter

| ویژگی | FakeEngineAdapter | RealEngineAdapter (آینده) |
|---|---|---|
| هدف | تست بدون GPU | اتصال به موتور واقعی |
| خروجی | فریم JPEG ساختگی | فریم JPEG واقعی از lip-sync |
| وابستگی | هیچ | اتصال شبکه‌ای به PadYar-LipSync |
| تأخیر | نزدیک صفر | وابسته به شبکه و GPU |
| fallback | غیرضروری | ضروری |
| وضعیت | پیاده‌سازی شده | نیازمند طراحی و پیاده‌سازی |

## گزینه‌های اتصال

### ۱. HTTP Bridge

runtime از طریق HTTP request به سرور PadYar-LipSync درخواست فریم می‌فرستد.

```
runtime ──HTTP POST──> PadYar-LipSync server
runtime <──JPEG bytes── PadYar-LipSync server
```

**مزایا:**
- ساده‌ترین پیاده‌سازی
- دیباگ آسان با curl یا httpx
- caching با HTTP standard

**معایب:**
- overhead هر request (TCP handshake، headers)
- مناسب استریم پیوسته نیست
- تأخیر بالاتر نسبت به WebSocket

### ۲. WebSocket Bridge (پیشنهاد شده برای MVP)

runtime یک اتصال WebSocket دائمی به سرور PadYar-LipSync برقرار می‌کند و فریم‌ها را به‌صورت بلادرنگ دریافت می‌کند.

```
runtime ──WebSocket──> PadYar-LipSync server
runtime <──binary frames── PadYar-LipSync server
```

**مزایا:**
- اتصال دائمی، بدون overhead تکراری
- مناسب استریم بلادرنگ
- bidirectional — امکان ارسال audio و دریافت فریم همزمان
- ping/pong برای تشخیص اتصال

**معایب:**
- پیچیدگی بیشتر در مدیریت اتصال
- نیاز به reconnect logic

### ۳. Local Process Bridge

runtime موتور استنتاج را به‌عنوان subprocess اجرا می‌کند و از طریق stdin/stdout یا shared memory ارتباط می‌گیرد.

```
runtime ──subprocess──> PadYar-LipSync process
runtime <──stdout/shared mem── PadYar-LipSync process
```

**مزایا:**
- بدون تأخیر شبکه
- مناسب deployment تک‌سرور

**معایب:**
- runtime باید روی همان سرور GPU باشد (نقض جداسازی)
- مدیریت lifecycle پیچیده (crash recovery، memory leak)
- مقیاس‌پذیری محدود

### ۴. gRPC Bridge (آینده)

runtime از طریق gRPC با protobuf به سرور PadYar-LipSync ارتباط می‌گیرد.

```
runtime ──gRPC──> PadYar-LipSync server
runtime <──protobuf── PadYar-LipSync server
```

**مزایا:**
- schema-defined با protobuf
- streaming بومی
- type-safe
- مناسب production در مقیاس بالا

**معایب:**
- پیچیدگی پیاده‌سازی بیشتر
- نیاز به تعریف .proto
- overkill برای MVP

## پیشنهاد بهترین مسیر برای MVP

**WebSocket Bridge** به‌عنوان مسیر اصلی MVP پیشنهاد می‌شود:

```
کلاینت ──WebSocket──> runtime ──WebSocket──> PadYar-LipSync
                          │
                          ├── Session Manager
                          ├── Frame Scheduler
                          ├── Latency Tracker
                          └── Fallback Handler
```

دلایل:
1. runtime از قبل WebSocket دارد — الگوی ارتباطی یکسان
2. bidirectional — ارسال audio و دریافت فریم
3. کمترین overhead برای استریم پیوسته
4. reconnect logic قابل پیاده‌سازی
5. مقیاس‌پذیری مستقل runtime و engine

## چرا import مستقیم از PadYar-LipSync-master ممنوع است

پوشه `PadYar-LipSync-master/` یک اسنپشات تاریخی از موتور استنتاج است:

- این کد وارد (import) نمی‌شود
- این کد اجرا نمی‌شود
- این کد نگهداری نمی‌شود
- موتور فعال در مخزن مجزاست

دلایل ممنوعیت:
1. **آلودگی وابستگی:** import مستقیم باعث وارد شدن torch، diffusers و سایر فریمورک‌های ML می‌شود
2. **تست حاکمیت شکسته می‌شود:** `test_governance_imports` و `test_governance_deps` ناموفق می‌شوند
3. **جداسازی نقض می‌شود:** runtime وابسته به کد داخلی موتور می‌شود
4. **نسخه‌بندی:** تغییر در موتور مستقیماً runtime را می‌شکند

## مسیر توسعه مرحله‌ای

### مرحله ۱: تقویت قرارداد EngineAdapter
- افزودن `connect()` و `disconnect()` به lifecycle
- تعریف error taxonomy
- تعریف versioning
- **خروجی:** قرارداد به‌روز شده، بدون پیاده‌سازی واقعی

### مرحله ۲: پیاده‌سازی RealEngineAdapter (WebSocket)
- اتصال WebSocket به PadYar-LipSync
- ارسال audio chunk
- دریافت فریم JPEG
- reconnect logic
- **خروجی:** `RealEngineAdapter` قابل استفاده

### مرحله ۳: یکپارچگی و تست
- تست یکپارچگی با موتور واقعی
- تست fallback
- تست تأخیر end-to-end
- تست long-running session
- **خروجی:** تست‌های یکپارچگی

### مرحله ۴: استقرار
- Docker configuration
- environment variables
- health check endpoints
- monitoring و alerting
- **خروجی:** runtime آماده production

هر مرحله نیاز به تأیید صریح قبل از شروع دارد.

---

*Powered by Mohammad Kohandezh — KSF Company*
*info@ksf.ir*
