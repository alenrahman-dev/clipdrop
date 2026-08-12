const urlInput = document.getElementById("url");
const analyzeBtn = document.getElementById("analyzeBtn");
const downloadBtn = document.getElementById("downloadBtn");
const statusEl = document.getElementById("status");
const result = document.getElementById("result");
const formatsEl = document.getElementById("formats");
const titleEl = document.getElementById("title");
const durationEl = document.getElementById("duration");
const thumbEl = document.getElementById("thumb");

let currentUrl = "";
let selectedFormat = null;

function setStatus(text, error = false) {
  statusEl.textContent = text;
  statusEl.style.color = error ? "#ff7272" : "#9ca5b5";
}

function formatDuration(seconds) {
  if (!seconds) return "";
  seconds = Math.round(seconds);
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  return h ? `${h}:${String(m).padStart(2,"0")}:${String(s).padStart(2,"0")}` : `${m}:${String(s).padStart(2,"0")}`;
}

analyzeBtn.onclick = async () => {
  const url = urlInput.value.trim();
  if (!url) return setStatus("Paste a URL first.", true);

  analyzeBtn.disabled = true;
  result.classList.add("hidden");
  downloadBtn.disabled = true;
  formatsEl.innerHTML = "";
  setStatus("Analyzing available formats...");

  try {
    const res = await fetch("/api/info", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({url})
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Could not analyze URL.");

    currentUrl = url;
    titleEl.textContent = data.title;
    durationEl.textContent = formatDuration(data.duration);
    thumbEl.src = data.thumbnail || "";
    formatsEl.innerHTML = "";

    data.formats.forEach((f, index) => {
      const btn = document.createElement("button");
      btn.className = "format";
      btn.innerHTML = `<strong>${f.label}</strong><small>${f.ext.toUpperCase()} ${f.has_audio ? "• combined" : "• audio will be merged"}</small>`;

      btn.onclick = () => {
        document.querySelectorAll(".format").forEach(x => x.classList.remove("selected"));
        btn.classList.add("selected");
        selectedFormat = f.format_id;
        downloadBtn.disabled = false;
      };

      formatsEl.appendChild(btn);

      if (index === 0) btn.click();
    });

    result.classList.remove("hidden");
    setStatus(`${data.formats.length} quality options found.`);
  } catch (err) {
    setStatus(err.message, true);
  } finally {
    analyzeBtn.disabled = false;
  }
};

downloadBtn.onclick = async () => {
  if (!currentUrl || !selectedFormat) return;

  downloadBtn.disabled = true;
  downloadBtn.textContent = "Preparing MP4...";
  setStatus("Downloading and combining video + audio...");

  try {
    const res = await fetch("/api/download", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        url: currentUrl,
        format_id: selectedFormat
      })
    });

    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.detail || "Download failed.");
    }

    const blob = await res.blob();
    const objectUrl = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = objectUrl;
    a.download = "video.mp4";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(objectUrl);

    setStatus("Download complete.");
  } catch (err) {
    setStatus(err.message, true);
  } finally {
    downloadBtn.disabled = false;
    downloadBtn.textContent = "Download MP4";
  }
};
