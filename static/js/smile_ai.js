(async function () {
  const video = document.getElementById("video");
  const freezeImg = document.getElementById("freezeImg");
  const canvas = document.getElementById("canvas");
  const captureBtn = document.getElementById("captureBtn");
  const recaptureBtn = document.getElementById("recaptureBtn");
  const confirmBtn = document.getElementById("confirmBtn");
  const status = document.getElementById("status");
  const msg = document.getElementById("msg");

  const resultWrap = document.getElementById("resultWrap");
  const resultStatus = document.getElementById("resultStatus");
  const beforeImg = document.getElementById("beforeImg");
  const afterImg = document.getElementById("afterImg");
  const dlBefore = document.getElementById("dlBefore");
  const dlAfter = document.getElementById("dlAfter");
  const errorBox = document.getElementById("errorBox");

  const ctx = canvas.getContext("2d", { willReadFrequently: true });

  let stream = null;
  let running = false;          // detection loop running
  let capturedDataUrl = null;   // captured full frame
  let lastConf = 0;             // latest confidence from detect loop

  function getThreshold() {
    if (typeof window.THRESHOLD === "number") return window.THRESHOLD;
    if (typeof THRESHOLD === "number") return THRESHOLD; // eslint-disable-line no-undef
    return 0.55;
  }

  function showFreeze() {
    freezeImg.classList.remove("hidden");
    freezeImg.classList.remove("visually-hidden");
    video.classList.add("hidden");
  }

  function hideFreeze() {
    freezeImg.classList.add("hidden");
    freezeImg.classList.add("visually-hidden");
    freezeImg.src = "";
    video.classList.remove("hidden");
  }

  function showError(text) {
    if (!errorBox) return;
    if (!text) {
      errorBox.classList.add("hidden");
      errorBox.textContent = "";
      return;
    }
    errorBox.classList.remove("hidden");
    errorBox.textContent = text;
  }

  function setMessage(text, kind) {
    if (!msg) return;
    msg.textContent = text || "";
    msg.className = "muted";
    if (kind === "ok") msg.className = "ok";
    if (kind === "error") msg.className = "error";
  }

  function resetResult() {
    if (!resultWrap || !resultStatus || !beforeImg || !afterImg || !dlBefore || !dlAfter) return;
    resultWrap.classList.add("hidden");
    resultStatus.textContent = "";
    beforeImg.src = "";
    afterImg.src = "";
    dlBefore.href = "#";
    dlAfter.href = "#";
  }

  async function startCamera() {
    stopCamera();

    stream = await navigator.mediaDevices.getUserMedia({
      video: { width: 640, height: 480 },
      audio: false,
    });

    video.srcObject = stream;

    hideFreeze();
    video.classList.remove("hidden");

    await video.play();
  }

  function stopCamera() {
    try {
      if (video && video.srcObject) {
        const s = video.srcObject;
        s.getTracks().forEach((t) => t.stop());
      }
    } catch (e) {}
    video.srcObject = null;
    stream = null;
  }

  async function detectOnce(frameDataUrl) {
    const resp = await fetch("/virtual-smile-try-on/api/detect/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image: frameDataUrl }),
    });
    return await resp.json();
  }

  async function saveCapture(frameDataUrl, conf) {
    const resp = await fetch("/virtual-smile-try-on/api/capture/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image: frameDataUrl, conf: conf }),
    });
    return await resp.json();
  }

  async function callGemini(frameDataUrl) {
    const resp = await fetch("/virtual-smile-try-on/api/smile-design/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image: frameDataUrl }),
    });
    const json = await resp.json();
    return { status: resp.status, json };
  }

  // ✅ UPDATED: button structure as you asked
  function setControlsForLive() {
  // ✅ ONLY Capture visible
  captureBtn.classList.remove("hidden");
  recaptureBtn.classList.add("hidden");
  confirmBtn.classList.add("hidden");

  captureBtn.disabled = true;    
  confirmBtn.disabled = true;
}

function setControlsForCaptured() {
  // ✅ ONLY Retake + Continue visible
  captureBtn.classList.add("hidden");
  recaptureBtn.classList.remove("hidden");
  confirmBtn.classList.remove("hidden");

  confirmBtn.disabled = !capturedDataUrl;
  captureBtn.disabled = true;
}

  async function detectLoop() {
    running = true;

    while (running) {
      try {
        if (!video.srcObject || video.readyState < 2) {
          await new Promise((r) => setTimeout(r, 120));
          continue;
        }

        canvas.width = video.videoWidth || 640;
        canvas.height = video.videoHeight || 480;

        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        const frame = canvas.toDataURL("image/jpeg", 0.8);

        const data = await detectOnce(frame);

        const conf =
          typeof data.confidence === "number"
            ? data.confidence
            : (typeof data.conf === "number" ? data.conf : 0);

        lastConf = conf;

        const visible = !!(
          data.visible ||
          data.smile_visible ||
          data.is_smile_visible
        );

        const threshold = getThreshold();

        if (status) {
          status.textContent =
            `Confidence: ${conf.toFixed(2)} — Visible: ${visible} — Threshold: ${threshold}`;
        }

        // ✅ This will enable Capture ONLY in live mode
        captureBtn.disabled = !(visible && conf >= threshold);
      } catch (e) {
        console.error("detectLoop error:", e);
      }

      await new Promise((r) => setTimeout(r, 180));
    }
  }

  captureBtn.addEventListener("click", async () => {
    showError("");
    resetResult();
    setMessage("");

    if (!video.srcObject || video.readyState < 2) {
      setMessage("Camera not ready. Please try again.", "error");
      return;
    }

    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;

    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    capturedDataUrl = canvas.toDataURL("image/jpeg", 0.92);

    if (!capturedDataUrl || capturedDataUrl.length < 100) {
      setMessage("Capture failed. Try again.", "error");
      return;
    }

    freezeImg.src = capturedDataUrl;
    showFreeze();

    running = false;
    stopCamera();

    try {
      const saved = await saveCapture(capturedDataUrl, lastConf);
      if (saved && saved.saved) {
        setMessage(
          `Captured ✅ (confidence ${(saved.conf || lastConf || 0).toFixed(2)})`,
          "ok"
        );
      } else {
        setMessage("Captured ✅", "ok");
      }
    } catch (e) {
      setMessage("Captured ✅", "ok");
    }

    // ✅ now show Retake + Continue, hide Capture
    setControlsForCaptured();
  });

  recaptureBtn.addEventListener("click", async () => {
    showError("");
    resetResult();
    setMessage("");

    capturedDataUrl = null;
    lastConf = 0;

    hideFreeze();

    try {
      await startCamera();
      setMessage("Camera restarted. Smile to enable Capture.", "muted");

      // ✅ back to Capture only
      setControlsForLive();
      detectLoop();
    } catch (e) {
      console.error(e);
      setMessage("Camera access failed: " + e.message, "error");
      showError("Allow camera access in browser, then refresh.");
    }
  });

  confirmBtn.addEventListener("click", async () => {
    showError("");
    resetResult();

    if (!capturedDataUrl) {
      setMessage("Please capture an image first.", "error");
      return;
    }

    confirmBtn.disabled = true;
    setMessage("Generating with Gemini…", "muted");

    try {
      const { status: httpStatus, json } = await callGemini(capturedDataUrl);

      if (httpStatus >= 200 && httpStatus < 300) {
        const beforeUrl = json.before_url || json.before || "";
        const afterUrl = json.after_url || json.after || "";

        if (resultWrap && resultStatus) {
          resultWrap.classList.remove("hidden");
          resultStatus.textContent = "Result ready ✅";
        }

        if (beforeImg) beforeImg.src = beforeUrl || capturedDataUrl;
        if (afterImg) afterImg.src = afterUrl || beforeUrl || capturedDataUrl;

        if (dlBefore) dlBefore.href = beforeUrl || capturedDataUrl;
        if (dlAfter) dlAfter.href = afterUrl || beforeUrl || capturedDataUrl;

        setMessage("Done ✅", "ok");
        return;
      }

      if (httpStatus === 501) {
        setMessage("Gemini is not configured on the server.", "error");
        showError(
          "Fix: set GEMINI_API_KEY (and optionally GEMINI_MODEL_NAME) then restart server.\n\n" +
            (json.error || "Gemini not configured")
        );
        return;
      }

      setMessage("Failed to generate. Check console/server logs.", "error");
      showError(json.error || "Unknown error");
    } catch (e) {
      console.error(e);
      setMessage("Error while generating.", "error");
      showError(e.message || String(e));
    } finally {
      confirmBtn.disabled = false;
    }
  });

  // Boot
  try {
    setControlsForLive();
    await startCamera();
    detectLoop();
    setMessage(
      "Camera started. Smile and the Capture button will enable automatically.",
      "muted"
    );
  } catch (e) {
    console.error(e);
    setMessage("Camera access failed: " + e.message, "error");
    showError("Allow camera access in browser, then refresh.");
  }
})();
