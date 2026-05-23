# انتخاب Adapter در Runtime — مستند فنی

**Powered by:** Mohammad Kohandezh — KSF Company
**تماس:** info@ksf.ir

---

## هدف Adapter Selection

runtime بتواند بر اساس تنظیمات (environment variables یا config)، بین `FakeEngineAdapter` و `RemoteEngineAdapter` انتخاب کند. این امکان را می‌دهد که:

- در محیط توسعه بدون GPU از `fake` استفاده شود
- در محیط production با engine واقعی از `remote` استفاده شود
- بدون تغییر کد، فقط با تغییر متغیر محیطی، رفتار عوض شود

## Environment Variables

| متغیر | پیش‌فرض | مقادیر مجاز | توضیح |
|---|---|---|---|
| `PADYAR_ENGINE_ADAPTER` | `fake` | `fake`, `remote` | نوع adapter |
| `PADYAR_ENGINE_URL` | `http://localhost:9000` | هر URL معتبر | آدرس سرور engine |
| `PADYAR_ENGINE_API_KEY` | `None` | رشته اختیاری | کلید API |

**نکته:** متغیرها با پیشوند `PADYAR_` به `RuntimeConfig` منتقل می‌شوند.

## Fake Mode

استفاده بدون engine واقعی. برای توسعه و تست.

```bash
PADYAR_ENGINE_ADAPTER=fake python -m padyar_live
```

یا بدون تنظیم متغیر (پیش‌فرض fake):

```bash
python -m padyar_live
```

رفتار:
- `FakeEngineAdapter` فریم‌های JPEG ساختگی تولید می‌کند
- هیچ درخواست شبکه‌ای ارسال نمی‌شود
- بدون نیاز به GPU یا engine

## Remote Mode

اتصال به engine واقعی از طریق HTTP.

```bash
PADYAR_ENGINE_ADAPTER=remote \
PADYAR_ENGINE_URL=http://localhost:9000 \
PADYAR_ENGINE_API_KEY=XXXXXXXX \
python -m padyar_live
```

رفتار:
- `RemoteEngineAdapter` درخواست HTTP به `{engine_url}/generate_frames` ارسال می‌کند
- audio chunk به‌صورت base64 در JSON ارسال می‌شود
- فریم‌های JPEG به‌صورت base64 دریافت و decode می‌شوند
- در صورت خطا، `RemoteEngineError` throw می‌شود و scheduler fallback می‌کند

## Security Note

- `engine_api_key` به‌صورت `Authorization: Bearer <key>` ارسال می‌شود
- API key در `repr()` یا log ظاهر نمی‌شود
- **توصیه:** API key را از environment variable بخوانید، نه hardcoded

```python
import os

config = RuntimeConfig(
    engine_adapter=os.environ.get("PADYAR_ENGINE_ADAPTER", "fake"),
    engine_url=os.environ.get("PADYAR_ENGINE_URL", "http://localhost:9000"),
    engine_api_key=os.environ.get("PADYAR_ENGINE_API_KEY"),
)
```

## چرا runtime همچنان ML-free است

این قابلیت فقط configuration wiring اضافه کرده:

- هیچ dependency جدید اضافه نشده
- هیچ ML code وارد runtime نشده
- `create_engine_adapter()` فقط بر اساس config، یک instance از adapter موجود ایجاد می‌کند
- `RuntimeConfig` فقط فیلدهای جدید گرفته، رفتار Pydantic تغییر نکرده
- `EngineAdapter` contract بدون تغییر باقی مانده

## آماده‌سازی برای تست با engine واقعی

پس از استقرار PadYar-LipSync روی سرور:

```bash
PADYAR_ENGINE_ADAPTER=remote \
PADYAR_ENGINE_URL=http://your-engine-server:9000 \
python -m padyar_live
```

runtime به‌صورت خودکار به engine وصل می‌شود. اگر engine در دسترس نباشد:

- `health_check()` مقدار `False` برمی‌گرداند
- scheduler از fallback استفاده می‌کند
- خدمات قطع نمی‌شود

## Factory Function

`create_engine_adapter(config)` در `src/padyar_live/adapters/factory.py`:

```python
def create_engine_adapter(config: RuntimeConfig) -> EngineAdapter:
    if config.engine_adapter == "fake":
        return FakeEngineAdapter()
    if config.engine_adapter == "remote":
        return RemoteEngineAdapter(RemoteEngineConfig(
            base_url=config.engine_url,
            timeout_seconds=config.engine_timeout_seconds,
            api_key=config.engine_api_key,
        ))
    raise ValueError(...)
```

`create_app()` از این factory استفاده می‌کند مگر اینکه adapter به‌صورت صریح پاس داده شود.

---

*Powered by Mohammad Kohandezh — KSF Company*
*info@ksf.ir*
