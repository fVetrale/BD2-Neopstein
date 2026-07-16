#!/usr/bin/env node
// Compila (SENZA MAI submittare) il form CryptPad "FORM3 Issue/Feature Survey".
//
// Uso:
//   node fill-form.js --dump                    elenca le domande del form (numero, tipo, opzioni)
//   node fill-form.js answers.json               compila il form e lascia il browser aperto per la review manuale
//   node fill-form.js answers.json --headless    compila in background e salva solo uno screenshot
//
// answers.json: oggetto con chiave = numero domanda (es. "1") o testo esatto della domanda,
// valore = stringa da inserire (campi testo) o testo esatto dell'opzione da selezionare (radio).
// Genera un template con `--dump` e usalo come riferimento.
//
// ponytail: questo script non contiene MAI una chiamata che clicca il bottone SUBMIT.
// La review/invio finale restano sempre manuali.

const { chromium } = require('playwright');
const fs = require('fs');

const FORM_URL = 'https://cryptpad.fr/form/#/2/form/view/sul+mlxF-8YrToTYcRIhxHFMm7I--Sbittf7vircH68/';

async function getFormFrame(page) {
  await page.goto(FORM_URL, { waitUntil: 'load', timeout: 60000 });
  for (let i = 0; i < 45; i++) {
    for (const frame of page.frames()) {
      const count = await frame.locator('fieldset.cp-form-block').count().catch(() => 0);
      if (count > 0) return frame;
    }
    await page.waitForTimeout(1000);
  }
  throw new Error('Timeout: il form non si è caricato (CryptPad usa iframe annidati + websocket).');
}

async function readQuestions(frame) {
  const meta = await frame.locator('fieldset.cp-form-block').evaluateAll((els) =>
    els.map((el) => ({
      type: el.dataset.type,
      text: el.querySelector('.cp-form-block-question-text')?.textContent?.trim() || '',
      options: [...el.querySelectorAll('.cp-checkmark-label')].map((s) => s.textContent.trim()),
    }))
  );
  return meta
    .map((b, blockIndex) => ({ ...b, blockIndex }))
    .filter((b) => b.type === 'input' || b.type === 'radio')
    .map((b, i) => ({ index: i + 1, ...b }));
}

async function main() {
  const args = process.argv.slice(2);
  const headless = args.includes('--headless');
  const dump = args.includes('--dump');
  const answersPath = args.find((a) => !a.startsWith('--'));

  if (!dump && !answersPath) {
    console.error(
      'Uso:\n  node fill-form.js --dump\n  node fill-form.js answers.json [--headless]'
    );
    process.exit(1);
  }

  const browser = await chromium.launch({ headless: dump ? true : headless });
  const page = await browser.newPage();
  const frame = await getFormFrame(page);
  const questions = await readQuestions(frame);

  if (dump) {
    console.log(JSON.stringify(questions.map(({ blockIndex, ...q }) => q), null, 2));
    await browser.close();
    return;
  }

  const answers = JSON.parse(fs.readFileSync(answersPath, 'utf8'));
  const blocks = await frame.locator('fieldset.cp-form-block').all();
  let filled = 0;
  const skipped = [];

  for (const q of questions) {
    const answer = answers[q.index] ?? answers[String(q.index)] ?? answers[q.text];
    const block = blocks[q.blockIndex];

    if (answer === undefined) {
      skipped.push(`${q.index}. ${q.text}`);
      continue;
    }

    if (q.type === 'input') {
      await block.locator('input[type="text"]').fill(String(answer));
      filled++;
    } else if (q.type === 'radio') {
      const labels = block.locator('.cp-checkmark-label');
      const texts = await labels.allTextContents();
      const idx = texts.findIndex((t) => t.trim() === String(answer).trim());
      if (idx === -1) {
        skipped.push(`${q.index}. ${q.text} (opzione "${answer}" non trovata tra: ${texts.join(' | ')})`);
        continue;
      }
      await labels.nth(idx).locator('xpath=..').click();
      filled++;
    }
  }

  console.log(`Compilati ${filled}/${questions.length} campi.`);
  if (skipped.length) {
    console.log('Non compilati:\n - ' + skipped.join('\n - '));
  }

  const screenshotPath = answersPath.replace(/\.json$/, '') + '-preview.png';
  await page.screenshot({ path: screenshotPath, fullPage: true });
  console.log(`Screenshot: ${screenshotPath}`);
  console.log('SUBMIT NON premuto. Controlla il form e invialo manualmente.');

  if (!headless) {
    console.log('Browser aperto per la review. Premi Invio nel terminale per chiuderlo...');
    await new Promise((resolve) => process.stdin.once('data', resolve));
  }
  await browser.close();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
