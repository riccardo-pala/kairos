/** A private Python interpreter per browser tab. Source comes from this repository. */
let runtime;
try {
  postMessage({ type: "status", message: "Carico il motore Python della demo…" });
  const { loadPyodide } = await import("./vendor/pyodide/pyodide.mjs");
  const python = await loadPyodide({ indexURL: new URL("./vendor/pyodide/", import.meta.url).href });
  await python.loadPackage(["pydantic", "tzdata"]);
  postMessage({ type: "status", message: "Preparo il workflow condiviso…" });
  const manifestResponse = await fetch(new URL("./python/manifest.json", import.meta.url));
  if (!manifestResponse.ok) throw new Error("Missing demo source manifest");
  const manifest = await manifestResponse.json();
  await Promise.all(manifest.files.map(async path => {
    const response = await fetch(new URL(`./python/${path}`, import.meta.url));
    if (!response.ok) throw new Error(`Missing Python source: ${path}`);
    const destination = `/home/pyodide/${path}`;
    python.FS.mkdirTree(destination.substring(0, destination.lastIndexOf("/")));
    python.FS.writeFile(destination, await response.text());
  }));
  runtime = python.pyimport("kairos.demo.runtime");
  postMessage({ type: "ready" });
} catch (error) {
  console.error("Demo initialization failed", error);
  postMessage({ type: "fatal", message: "La demo non è disponibile. Ricarica la pagina per riprovare." });
}

let queue = Promise.resolve();
onmessage = ({ data }) => {
  queue = queue.then(async () => {
    try {
      if (!runtime) throw new Error("Demo runtime unavailable");
      const result = await runtime.handle_json(JSON.stringify(data), event => {
        postMessage({ type: "event", id: data.id, event: JSON.parse(event) });
      });
      postMessage({ type: "result", id: data.id, result: JSON.parse(result) });
    } catch (error) {
      console.error("Demo request failed", error);
      postMessage({ type: "error", id: data.id, message: "Controlla i dati della sessione e riprova." });
    }
  });
};
