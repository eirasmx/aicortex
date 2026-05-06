# 🧠 aicortex — JavaScript SDK

[![npm](https://img.shields.io/npm/v/aicortex-core)](https://www.npmjs.com/package/aicortex-core)
[![License](https://img.shields.io/badge/License-LGPL_v3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0)

**Zero API keys. Zero signup. Zero server setup. Completely free.**

The `aicortex-core` JavaScript SDK gives you instant access to dozens of LLMs — Llama, Mistral, Gemma, DeepSeek, Qwen and more — served by community-hosted Ollama servers **bundled directly in the package**. Just install and go.

---

## Installation

```bash
npm install aicortex-core
```

**Or via CDN (no install at all):**
```html
<script src="https://unpkg.com/aicortex-core/aicortex.js"></script>
```

---

## 2-line quick start

```js
const ai = new AICortex();
const reply = await ai.chat('Explain neural networks like I am five.');
console.log(reply);
```

That's it. No config. No API keys. The SDK automatically picks the fastest available community server for you.

---

## Chat

```js
import AICortex from 'aicortex-core';

const ai = new AICortex();

// Simple
const reply = await ai.chat('What is the speed of light?');

// Specific model + params
const reply = await ai.chat('Write a Python sort function.', {
  model: 'deepseek-r1:7b',
  temperature: 0.2,
  maxTokens: 200,
});

// With system prompt
const reply = await ai.chat('Tell me a joke.', {
  system: 'You are a pirate. Respond only in pirate speak.',
});
```

---

## Streaming

```js
const stream = ai.stream('Write a haiku about the ocean.');

for await (const token of stream) {
  process.stdout.write(token);           // Node.js
  // document.getElementById('out').textContent += token;  // Browser
}
console.log('\nFull text:', stream.text);
```

Or collect everything at once:
```js
const text = await ai.stream('Tell me a story.').collect();
```

---

## Multi-turn sessions

```js
const session = ai.session();

await ai.chat('My name is Alice.', { session });
const name = await ai.chat('What is my name?', { session });
// → "Your name is Alice."

console.log(session.turns);    // 2
console.log(session.history);  // full message array
session.reset();               // clear history
```

---

## Model discovery

```js
// All available models (no network needed — bundled data)
ai.models();
// → ['deepseek-r1:1.5b', 'deepseek-r1:7b', 'llama3.2:3b', 'mistral:7b', ...]

// Filter by family
ai.models('deepseek');   // → ['deepseek-r1:1.5b', 'deepseek-r1:7b', ...]
ai.models('llama');      // → ['llama3.2:3b', 'llama3.2:latest', ...]
ai.models('others');     // → ['nomic-embed-text', 'GLM-OCR:latest', 'llava:13b', ...]

// List families
ai.families();
// → ['deepseek', 'gemma', 'llama', 'mistral', 'others', 'smollm', ...]

// Best server for a model (no network needed)
ai.bestServer('mistral:7b');
// → { url: 'http://130.61.213.45:11434', tps: 26.95, city: 'Frankfurt am Main', ... }

// LangChain-compatible params
ai.llmParams('mistral:7b');
// → { model: 'mistral:7b', base_url: 'http://130.61.213.45:11434' }
```

---

## Use your own Ollama server

```js
// Point at your own local or hosted Ollama
const ai = new AICortex({ ollamaUrl: 'http://localhost:11434' });
const reply = await ai.chat('Hello!', { model: 'llama3.2:3b' });
```

---

## Framework examples

### React
```jsx
import { useState } from 'react';
import AICortex from 'aicortex-core';

const ai = new AICortex();

export default function Chat() {
  const [output, setOutput] = useState('');

  async function ask(prompt) {
    setOutput('');
    for await (const token of ai.stream(prompt)) {
      setOutput(prev => prev + token);
    }
  }

  return (
    <>
      <button onClick={() => ask('Tell me a joke')}>Ask AI</button>
      <p>{output}</p>
    </>
  );
}
```

### Vue 3
```html
<script setup>
import AICortex from 'aicortex-core';
import { ref } from 'vue';

const ai = new AICortex();
const output = ref('');

async function ask(prompt) {
  output.value = '';
  for await (const token of ai.stream(prompt)) {
    output.value += token;
  }
}
</script>
<template>
  <button @click="ask('What is AI?')">Ask</button>
  <p>{{ output }}</p>
</template>
```

### Vanilla JS (CDN)
```html
<script src="https://unpkg.com/aicortex-core/aicortex.js"></script>
<div id="output"></div>
<button onclick="ask()">Ask AI</button>
<script>
  const ai = new AICortex();
  async function ask() {
    const out = document.getElementById('output');
    out.textContent = '';
    for await (const token of ai.stream('Write a haiku about the ocean.')) {
      out.textContent += token;
    }
  }
</script>
```

---

## Constructor options

| Option       | Type     | Default    | Description                                    |
|--------------|----------|------------|------------------------------------------------|
| `model`      | `string` | auto       | Default model for all requests                 |
| `ollamaUrl`  | `string` | community  | Override with your own Ollama server URL       |
| `temperature`| `number` | `0.7`      | Sampling temperature (0–2)                     |
| `maxTokens`  | `number` | `1024`     | Max tokens to generate                         |
| `timeout`    | `number` | `30000`    | Request timeout in ms                          |
| `retries`    | `number` | `3`        | How many servers to try before throwing        |

---

## Error handling

Error classes are attached as static properties on `AICortex`:

```js
import AICortex from 'aicortex-core';

const { AICortexConnectionError, AICortexModelNotFoundError, AICortexNoInternetError } = AICortex;

const ai = new AICortex();
try {
  const reply = await ai.chat('Hello!');
} catch (err) {
  if (err instanceof AICortexConnectionError) {
    console.error('All servers unreachable');
  } else if (err instanceof AICortexModelNotFoundError) {
    console.error('Model not found:', err.model);
  } else if (err instanceof AICortexNoInternetError) {
    console.error('No internet connection');
  }
}
```

---

## Note on browser CORS

Community Ollama servers may not have CORS headers configured. If you hit CORS errors in the browser, use one of these options:

1. **Your own Ollama instance** with `OLLAMA_ORIGINS=*` set
2. **A lightweight proxy** on your own backend that forwards requests to community servers
3. **Node.js / server-side** — no CORS restrictions apply

---

## License

[LGPL-3.0](LICENSE) — free for open-source and commercial use.
