/**
 * examples/test.js — aicortex JS SDK smoke test
 * Run: node examples/test.js
 */
const AICortex = require('../aicortex.js');

const ai = new AICortex();

async function run() {
  console.log('🧠 aicortex JS SDK — smoke test\n');

  // 1. Models (no network needed — bundled data)
  console.log('1️⃣  Models (bundled, no network):');
  const models = ai.models();
  console.log(`   ${models.length} models: ${models.slice(0, 5).join(', ')}…\n`);

  // 2. Families
  console.log('2️⃣  Families:', ai.families().join(', '), '\n');

  // 3. Best server for a model
  const server = ai.bestServer('mistral:7b');
  console.log('3️⃣  Best server for mistral:7b:');
  console.log(`   ${server?.url} — ${server?.tps} t/s — ${server?.city}, ${server?.country}\n`);

  // 4. LangChain params
  const params = ai.llmParams('mistral:7b');
  console.log('4️⃣  LangChain-ready params:', params, '\n');

  // 5. Live chat (requires network)
  console.log('5️⃣  Live chat (community server)…');
  try {
    const reply = await ai.chat('Say "pong" and nothing else.', { model: 'mistral:7b' });
    console.log('   Reply:', reply.trim(), '\n');
  } catch (e) {
    console.log('   ⚠️  Skipped (no network or servers offline):', e.message, '\n');
  }

  // 6. Streaming
  console.log('6️⃣  Streaming…');
  try {
    process.stdout.write('   ');
    const stream = ai.stream('Count from 1 to 3. Numbers only.', { model: 'mistral:7b' });
    for await (const token of stream) process.stdout.write(token);
    console.log(`\n   Full text: "${stream.text.trim()}"\n`);
  } catch (e) {
    console.log('   ⚠️  Skipped:', e.message, '\n');
  }

  // 7. Session
  console.log('7️⃣  Session memory…');
  try {
    const session = ai.session();
    await ai.chat('My favourite colour is indigo.', { model: 'mistral:7b', session });
    const answer = await ai.chat('What is my favourite colour?', { model: 'mistral:7b', session });
    console.log('   Answer:', answer.trim());
    console.log('   Session turns:', session.turns, '\n');
  } catch (e) {
    console.log('   ⚠️  Skipped:', e.message, '\n');
  }

  console.log('✅ Done!');
}

run().catch(err => { console.error('❌', err.message); process.exit(1); });
