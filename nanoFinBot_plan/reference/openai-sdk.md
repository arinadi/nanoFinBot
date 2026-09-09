# OpenAI SDK 1.x — reference

One SDK (`openai>=1,<2`) drives every provider via a configurable `base_url`. Pin major 1.

```python
from openai import OpenAI

client = OpenAI(base_url=config.base_url, api_key=config.api_key)
```

**Text / chat completion**

```python
resp = client.chat.completions.create(
    model=config.model,
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_text},
    ],
    response_format={"type": "json_object"},   # force JSON; requires "json" in prompt
)
text = resp.choices[0].message.content          # a JSON string when json_object
```

**Vision (image) call** — same endpoint, `image_url` content part with a base64 data URI:

```python
import base64
data_uri = "data:image/jpeg;base64," + base64.b64encode(img_bytes).decode()
resp = client.chat.completions.create(
    model=image_model,
    messages=[
        {"role": "user", "content": [
            {"type": "text", "text": SYSTEM_PROMPT},
            {"type": "image_url", "image_url": {"url": data_uri}},
        ]},
    ],
    response_format={"type": "json_object"},
)
```

**Error handling** — a bad key / wrong base_url raises `openai.APIError` subclasses
(`AuthenticationError` on 401, `APIConnectionError` when unreachable). Wrap calls and
map to the "provider auth error" vs "network error" states in `architecture.md` §5.

Notes:
- `response_format={"type":"json_object"}` requires the word "json" in the prompt; always
  validate the returned JSON against the expected schema and fall back to an empty draft
  on parse failure (see risk chain 1).
- The SDK reads `OPENAI_API_KEY`/`OPENAI_BASE_URL` env vars only if you don't pass
  explicit args — always pass them explicitly from config.
