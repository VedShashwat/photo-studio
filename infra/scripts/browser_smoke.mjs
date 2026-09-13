import { writeFileSync } from "node:fs";

const cdpBaseUrl = process.env.CDP_URL ?? "http://127.0.0.1:9222";
const appUrl = process.env.APP_URL ?? "http://localhost:3001";
const outputPath = process.argv[2];
const width = Number(process.argv[3] ?? 1440);
const height = Number(process.argv[4] ?? 1000);
const mobile = process.argv[5] === "mobile";

if (!outputPath || !Number.isInteger(width) || !Number.isInteger(height)) {
  throw new Error("Usage: node browser_smoke.mjs OUTPUT_PATH [WIDTH] [HEIGHT] [mobile]");
}

const targetResponse = await fetch(`${cdpBaseUrl}/json/new?${encodeURIComponent("about:blank")}`, {
  method: "PUT",
});
if (!targetResponse.ok) throw new Error(`Could not create browser target: ${targetResponse.status}`);
const target = await targetResponse.json();
const socket = new WebSocket(target.webSocketDebuggerUrl);
const pending = new Map();
let commandId = 0;

await new Promise((resolve, reject) => {
  socket.addEventListener("open", resolve, { once: true });
  socket.addEventListener("error", reject, { once: true });
});

socket.addEventListener("message", (event) => {
  const message = JSON.parse(event.data);
  if (!message.id || !pending.has(message.id)) return;
  const { resolve, reject } = pending.get(message.id);
  pending.delete(message.id);
  if (message.error) reject(new Error(message.error.message));
  else resolve(message.result);
});
socket.addEventListener("close", () => {
  for (const { reject } of pending.values()) reject(new Error("Browser target closed unexpectedly"));
  pending.clear();
});

function send(method, params = {}) {
  commandId += 1;
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      pending.delete(commandId);
      reject(new Error(`CDP command timed out: ${method}`));
    }, 10000);
    pending.set(commandId, {
      resolve: (value) => { clearTimeout(timeout); resolve(value); },
      reject: (error) => { clearTimeout(timeout); reject(error); },
    });
    socket.send(JSON.stringify({ id: commandId, method, params }));
  });
}

function sleep(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

async function evaluate(expression) {
  const response = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
  if (response.exceptionDetails) throw new Error(response.exceptionDetails.text);
  return response.result.value;
}

async function waitFor(expression, timeoutMilliseconds = 5000) {
  const deadline = Date.now() + timeoutMilliseconds;
  while (Date.now() < deadline) {
    if (await evaluate(expression)) return;
    await sleep(100);
  }
  throw new Error(`Browser condition timed out: ${expression}`);
}

await send("Page.enable");
await send("Runtime.enable");
await send("Emulation.setDeviceMetricsOverride", {
  width,
  height,
  deviceScaleFactor: 1,
  mobile,
});
await send("Page.navigate", { url: appUrl });
await waitFor(`document.querySelectorAll(".history-card").length > 0`);

const restored = await evaluate(`(() => {
  const button = [...document.querySelectorAll("button")].find((item) => item.textContent?.includes("Restore job"));
  if (!button) return false;
  button.click();
  return true;
})()`);
if (!restored) throw new Error("No generation-history restore action was found");
await waitFor(`document.querySelectorAll(".output-card img").length === 3 && Boolean(document.querySelector(".before-after"))`);
await waitFor(`[...document.images].every((image) => image.complete && image.naturalWidth > 0)`);

const assertions = await evaluate(`(() => ({
  viewportWidth: window.innerWidth,
  scrollWidth: document.documentElement.scrollWidth,
  outputImages: document.querySelectorAll(".output-card img").length,
  downloads: document.querySelectorAll(".output-download").length,
  hasComparison: Boolean(document.querySelector(".before-after")),
  statusText: [...document.querySelectorAll('[role="status"]')].map((item) => item.textContent).join(" | "),
  pageHeight: Math.max(document.body.scrollHeight, document.documentElement.scrollHeight),
}))()`);

if (assertions.scrollWidth > assertions.viewportWidth) {
  throw new Error(`Horizontal overflow: ${assertions.scrollWidth}px > ${assertions.viewportWidth}px`);
}
if (assertions.outputImages !== 3 || assertions.downloads !== 3 || !assertions.hasComparison) {
  throw new Error(`Restored job is incomplete: ${JSON.stringify(assertions)}`);
}
if (!assertions.statusText.includes("Generation succeeded: 3/3 outputs")) {
  throw new Error(`Unexpected generation status: ${assertions.statusText}`);
}

const screenshot = await send("Page.captureScreenshot", {
  format: "png",
  captureBeyondViewport: true,
  clip: { x: 0, y: 0, width, height: assertions.pageHeight, scale: 1 },
});
writeFileSync(outputPath, Buffer.from(screenshot.data, "base64"));
console.log(JSON.stringify({ ...assertions, screenshot: outputPath }));
await send("Page.close");
socket.close();
