const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const { test } = require('node:test');
const code = fs.readFileSync('templates/index.html', 'utf8').match(/<script>([\s\S]*?)<\/script>/)[1];
function setup() {
  const elements = new Map();
  const element = () => ({ addEventListener() {}, setAttribute() {}, appendChild(child) { (this.children ||= []).push(child); }, append() {}, replaceChildren() {}, style: {}, classList: {add() {}, remove() {}} });
  const document = {getElementById(id) { if (!elements.has(id)) elements.set(id, element()); return elements.get(id); }, querySelectorAll() { return []; }, addEventListener() {}, createElement: element};
  const context = vm.createContext({document, window: {}, console, FormData, crypto: require('node:crypto').webcrypto, Uint8Array});
  vm.runInContext(code, context);
  return {context, document};
}
test('save uses next free filename, preserves existing files, and writes PDF', async () => {
  const {context} = setup();
  let selected, written, closed = false;
  const directory = {
    async *values() { yield {name: 'doc_unlocked.pdf'}; yield {name: 'doc_unlocked_1.pdf'}; },
    async getFileHandle(name) { selected = name; return {async createWritable() {return {async write(blob) {written = blob;}, async close() {closed = true;}};}}; }
  };
  const blob = new Blob(['pdf']);
  const name = await context.saveUnlockedCopy(directory, 'doc_unlocked.pdf', blob);
  assert.equal(name, 'doc_unlocked_2.pdf');
  assert.equal(selected, name);
  assert.equal(written, blob);
  assert.equal(closed, true);
});
test('failed write aborts the file stream', async () => {
  const {context} = setup();
  let aborted = false;
  const directory = {async *values() {}, async getFileHandle() {return {async createWritable() {return {async write() {throw Error('disk full');}, async abort() {aborted = true;}};}};}};
  await assert.rejects(context.saveUnlockedCopy(directory, 'a.pdf', new Blob()), /disk full/);
  assert.equal(aborted, true);
});
test('unsupported browser explains original-folder limitation', async () => {
  const {context, document} = setup();
  assert.equal(await context.chooseUnlockFolder(), false);
  assert.match(document.getElementById('unlock-result').textContent, /modo terminal/);
});
test('batch continues after failure and saves successful files separately', async () => {
  const {context, document} = setup();
  let saved = [];
  context.directory = {name: 'Originals', async *values() {}, async getFileHandle(name) {return {async createWritable() {return {async write() {saved.push(name);}, async close() {}};}};}};
  context.files = ['a.pdf', 'bad.pdf', 'c.pdf'].map(name => new File(['pdf'], name));
  vm.runInContext('unlockFiles = files; unlockDirectory = directory;', context);
  document.getElementById('unlock-pass').value = 'shared';
  let uploads = 0;
  context.fetch = async (url, options) => {
    if (!options) return {ok: true, async blob() {return new Blob(['pdf']);}};
    assert.equal(options.body.get('password'), 'shared');
    uploads++;
    if (uploads === 2) return {ok: false, async json() {return {errors: ['Incorrect password']};}};
    return {ok: true, async json() {return {outputs: [{download_url: '/download/out.pdf', filename: 'out.pdf'}]};}};
  };
  await context.doUnlock();
  assert.deepEqual(saved, ['a_unlocked.pdf', 'c_unlocked.pdf']);
  assert.equal(uploads, 3);
  assert.match(document.getElementById('unlock-result').children[0].textContent, /2 de 3/);
  assert.equal(document.getElementById('unlock-btn').disabled, false);
});
