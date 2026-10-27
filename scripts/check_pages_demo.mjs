/** Smoke-test the exact WebAssembly/Pydantic runtime shipped to Pages. */
import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";

const output = path.resolve(process.argv[2] || "dist/pages");
const vendor = path.join(output, "static/demo/vendor/pyodide");
const { loadPyodide } = await import(pathToFileURL(path.join(vendor, "pyodide.mjs")));
const python = await loadPyodide({ indexURL: vendor + path.sep });
await python.loadPackage(["pydantic", "tzdata"]);
const source = path.join(output, "static/demo/python");
const manifest = JSON.parse(await fs.readFile(path.join(source, "manifest.json"), "utf8"));
for (const file of manifest.files) {
  const destination = `/home/pyodide/${file}`;
  python.FS.mkdirTree(path.posix.dirname(destination));
  python.FS.writeFile(destination, await fs.readFile(path.join(source, file), "utf8"));
}
await python.runPythonAsync(`
from kairos.demo.runtime import DemoAPI
from kairos.demo.scenarios import examples
from uuid import UUID

for language in ('it', 'en'):
    for scenario in examples(language):
        api = DemoAPI(delay=0)
        session = api.create_session({'language': language, 'timezone': 'Europe/Rome'})
        for step in scenario['steps']:
            events = []
            await api.turn(session['id'], {'message': step['message']}, events.append)
            assert events[-1]['event'] == 'completed', events
            session = events[-1]['data']['session']
        assert session['state']['status'] == 'ready_for_review'
        events = []
        await api.turn(session['id'], {'action': {'type': 'set_duration', 'value': 2880}}, events.append)
        assert events[-1]['data']['session']['state']['draft']['duration_minutes'] == 2880
        saved = api.sessions[UUID(session['id'])].state.draft.model_dump()
        changed = api.change_language(session['id'], {'language': 'en' if language == 'it' else 'it'})
        assert api.sessions[UUID(session['id'])].state.draft.model_dump() == saved
        assert changed['language'] != language
        print('Verified WebAssembly scenario:', language, scenario['id'])

assert 'httpx' not in __import__('sys').modules
assert 'psycopg' not in __import__('sys').modules
`);
const html = await fs.readFile(path.join(output, "index.html"), "utf8");
for (const forbidden of ["provider-select", "diagnostic-logs", "raw-panel", "/admin/", "http://localhost"]) {
  if (html.includes(forbidden)) throw new Error(`Private control leaked into public HTML: ${forbidden}`);
}
console.log("Pages artifact verified: real Python workflow, six bilingual scenarios, no live provider or admin UI.");
