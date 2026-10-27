(async function () {
  const video = document.getElementById("video");
  const freezeImg = document.getElementById("freezeImg");
  const canvas = document.getElementById("canvas");
  const captureBtn = document.getElementById("captureBtn");
  const recaptureBtn = document.getElementById("recaptureBtn");
  const confirmBtn = document.getElementById("confirmBtn");
  const status = document.getElementById("status");
  const msg = document.getElementById("msg");
  const guideLine = document.getElementById("smileGuideLine");
  const faceOverlay = document.getElementById("faceOverlay");
  const smileDetectBadge = document.getElementById("smileDetectBadge");
  const smileDetectPercent = document.getElementById("smileDetectPercent");
  const detectRingProgress = document.getElementById("detectRingProgress");
  const switchCameraBtn = document.getElementById("switchCameraBtn");

  function updateDetectScore(conf, visible) {
    if (!smileDetectPercent) return;

    let pct = 0;
    if (typeof conf === "number" && !isNaN(conf) && conf > 0) {
      const scaled = conf <= 1 ? Math.round(conf * 100) : Math.round(conf);
      pct = Math.min(100, Math.max(0, scaled));
    }

    smileDetectPercent.textContent = pct + "%";

    if (detectRingProgress) {
      const radius = 18;
      const circumference = 2 * Math.PI * radius; // 113.1
      const offset = circumference - (pct / 100) * circumference;
      detectRingProgress.style.strokeDashoffset = offset;
    }

    if (smileDetectBadge) {
      if (pct >= 55) {
        smileDetectBadge.classList.add("score-high");
      } else {
        smileDetectBadge.classList.remove("score-high");
      }
    }
  }

  const resultWrap = document.getElementById("resultWrap");
  const resultStatus = document.getElementById("resultStatus");
  const beforeImg = document.getElementById("beforeImg");
  const afterImg = document.getElementById("afterImg");
  const dlBefore = document.getElementById("dlBefore");
  const dlAfter = document.getElementById("dlAfter");
  const errorBox = document.getElementById("errorBox");

  // Contact modal form elements
  const leadForm = document.getElementById("leadForm");
  const leadName = document.getElementById("leadName");
  const leadPhone = document.getElementById("leadPhone");
  const leadPincode = document.getElementById("leadPincode") || document.getElementById("pincodeInput");
  const leadCity = document.getElementById("leadCity");
  const leadEmail = document.getElementById("leadEmail");
  const leadFormMsg = document.getElementById("leadFormMsg");
  const leadSubmitBtn = document.getElementById("leadSubmitBtn");

  // ✨ "Your smile design processing" loader (ChatGPT style golden dot grid + progress %)
  // Preview popup ke white border box ke andar dikhta hai, image ready hone tak
  const processLoader = createProcessLoader();

  function createProcessLoader() {
    const wrap = document.querySelector("#PreviewModal .preview-wrapper");
    const box = document.getElementById("smileProcessLoader");
    const titleEl = document.getElementById("smileProcessTitle");
    const dotCanvas = document.getElementById("smileProcessCanvas");
    const percentEl = document.getElementById("smileProcessPercent");
    const dotCtx = dotCanvas ? dotCanvas.getContext("2d") : null;

    if (!wrap || !box || !dotCtx || !percentEl) {
      return { start() { }, finish(cb) { if (cb) cb(); }, stop() { }, fail() { } };
    }

    const defaultTitle = titleEl ? titleEl.textContent.trim() : "";
    const GAP = 12; // dot spacing (css px)
    const RADIUS = 1.1; // dot radius (css px)
    const LEVELS = 16; // brightness steps
    const FINISH_MS = 650; // current % -> 100% animation
    const HOLD_MS = 300; // 100% dikhane ke baad result dikhao
    const TAU = Math.PI * 2;
    const reduceMotion = !!(
      window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches
    );

    // Dim dark gold (#C3942F) -> bright champagne gold (#E7DC96)
    const palette = [];
    for (let l = 0; l < LEVELS; l++) {
      const k = l / (LEVELS - 1);
      const r = Math.round(195 + (231 - 195) * k);
      const g = Math.round(148 + (220 - 148) * k);
      const b = Math.round(47 + (150 - 47) * k);
      palette.push(`rgba(${r}, ${g}, ${b}, ${(0.18 + 0.82 * k).toFixed(3)})`);
    }

    let dots = null;
    let viewW = 0;
    let viewH = 0;
    let active = false;
    let rafId = 0;
    let startedAt = 0;
    let shownPct = 0;
    let finishFrom = 0;
    let finishAt = 0;
    let finishTimer = 0;
    let onFinished = null;

    function layoutDots() {
      const rect = dotCanvas.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      viewW = Math.max(1, Math.round(rect.width));
      viewH = Math.max(1, Math.round(rect.height));
      dotCanvas.width = Math.round(viewW * dpr);
      dotCanvas.height = Math.round(viewH * dpr);
      dotCtx.setTransform(dpr, 0, 0, dpr, 0, 0);

      const cols = Math.max(1, Math.floor(viewW / GAP));
      const rows = Math.max(1, Math.floor(viewH / GAP));
      const offX = (viewW - (cols - 1) * GAP) / 2;
      const offY = (viewH - (rows - 1) * GAP) / 2;
      const count = cols * rows;

      dots = {
        count,
        x: new Float32Array(count),
        y: new Float32Array(count),
        col: new Float32Array(count),
        row: new Float32Array(count),
        edge: new Float32Array(count),
        phase: new Float32Array(count),
        speed: new Float32Array(count),
        level: new Uint8Array(count),
      };

      let i = 0;
      for (let row = 0; row < rows; row++) {
        for (let col = 0; col < cols; col++, i++) {
          // outer rows/cols thode dim (soft edge)
          const edgeDist = Math.min(col, row, cols - 1 - col, rows - 1 - row);
          dots.x[i] = offX + col * GAP;
          dots.y[i] = offY + row * GAP;
          dots.col[i] = col;
          dots.row[i] = row;
          dots.edge[i] = Math.min(1, 0.35 + edgeDist * 0.22);
          dots.phase[i] = Math.random() * TAU;
          dots.speed[i] = 1.2 + Math.random() * 2.4;
        }
      }
    }

    function drawDots(t) {
      if (!dots) return;
      const { count, x, y, col, row, edge, phase, speed, level } = dots;

      // diagonal sweep + drifting clouds + per-dot twinkle
      for (let i = 0; i < count; i++) {
        const c = col[i];
        const r = row[i];
        const sweep = 0.5 + 0.5 * Math.sin((c + r) * 0.16 - t * 2.2);
        const cloud = 0.5 + 0.5 * Math.sin(c * 0.21 + t * 0.9) * Math.sin(r * 0.27 - t * 0.7);
        const drift = 0.5 + 0.5 * Math.sin(c * 0.12 - r * 0.19 + t * 1.3);
        const twinkle = 0.5 + 0.5 * Math.sin(t * speed[i] + phase[i]);
        let v = sweep * 0.4 + cloud * 0.3 + drift * 0.15 + twinkle * 0.15;
        v = Math.pow(v, 1.6) * edge[i];
        level[i] = Math.min(LEVELS - 1, (v * LEVELS) | 0);
      }

      dotCtx.clearRect(0, 0, viewW, viewH);

      // ek brightness level = ek path (kam fill() calls, smooth on mobile)
      for (let l = 0; l < LEVELS; l++) {
        const rad = RADIUS * (0.85 + 0.45 * (l / (LEVELS - 1)));
        let has = false;
        dotCtx.beginPath();
        for (let i = 0; i < count; i++) {
          if (level[i] !== l) continue;
          dotCtx.moveTo(x[i] + rad, y[i]);
          dotCtx.arc(x[i], y[i], rad, 0, TAU);
          has = true;
        }
        if (has) {
          dotCtx.fillStyle = palette[l];
          dotCtx.fill();
        }
      }
    }

    function setPercent(pct) {
      shownPct = pct;
      const val = Math.min(100, Math.floor(pct));
      const text = val + "%";
      if (percentEl.textContent !== text) {
        percentEl.textContent = text;
        box.setAttribute("aria-valuenow", String(val));
      }
    }

    function tick(now) {
      if (!active) return;
      if (finishAt) {
        const k = Math.min(1, (now - finishAt) / FINISH_MS);
        setPercent(finishFrom + (100 - finishFrom) * (1 - Math.pow(1 - k, 3)));
      } else {
        // estimated progress: pehle fast, phir result aane tak 96% ke paas slow
        setPercent(Math.max(shownPct, 96 * (1 - Math.exp(-(now - startedAt) / 9000))));
      }
      if (!reduceMotion) drawDots((now - startedAt) / 1000);
      rafId = requestAnimationFrame(tick);
    }

    function flushFinished() {
      clearTimeout(finishTimer);
      finishTimer = 0;
      const cb = onFinished;
      onFinished = null;
      if (cb) cb();
    }

    function start() {
      stop();
      active = true;
      if (titleEl) titleEl.textContent = defaultTitle;
      wrap.classList.add("is-processing");
      box.setAttribute("aria-hidden", "false");
      startedAt = performance.now();
      setPercent(0);
      layoutDots();
      drawDots(0);
      rafId = requestAnimationFrame(tick);
    }

    // Progress 100% tak le jao, phir cb (result dikhao)
    function finish(cb) {
      if (!active) {
        if (cb) cb();
        return;
      }
      onFinished = cb || null;
      if (finishAt) return;
      finishFrom = shownPct;
      finishAt = performance.now();
      finishTimer = setTimeout(flushFinished, FINISH_MS + HOLD_MS);
    }

    // loader hatao (fade out ke time 100% hi dikhe, isliye % reset start() me hota hai)
    function stop() {
      flushFinished(); // pending result callback kabhi miss na ho
      active = false;
      cancelAnimationFrame(rafId);
      rafId = 0;
      finishAt = 0;
      wrap.classList.remove("is-processing", "is-failed");
      box.setAttribute("aria-hidden", "true");
    }

    // error: box me hi message dikhao, buttons hidden rahenge
    function fail(message) {
      clearTimeout(finishTimer);
      finishTimer = 0;
      onFinished = null;
      active = false;
      cancelAnimationFrame(rafId);
      rafId = 0;
      finishAt = 0;
      if (titleEl) titleEl.textContent = message;
      wrap.classList.add("is-processing", "is-failed");
      box.setAttribute("aria-hidden", "false");
    }

    // popup open hote hi (aur screen resize pe) box ke size ke hisab se dots
    function relayoutIfResized() {
      if (!active) return;
      const rect = dotCanvas.getBoundingClientRect();
      if (Math.round(rect.width) === viewW && Math.round(rect.height) === viewH) return;
      layoutDots();
      drawDots((performance.now() - startedAt) / 1000);
    }

    if (typeof ResizeObserver === "function") {
      new ResizeObserver(relayoutIfResized).observe(dotCanvas);
    } else {
      window.addEventListener("resize", relayoutIfResized);
    }

    return { start, finish, stop, fail };
  }

  const ctx = canvas.getContext("2d", { willReadFrequently: true });

  function pingDetectApi() {
    const dummyCanvas = document.createElement("canvas");
    dummyCanvas.width = 640;
    dummyCanvas.height = 480;
    const dCtx = dummyCanvas.getContext("2d");
    dCtx.fillstyle = "#808080";
    dCtx.fillRect(0, 0, 640, 480);

    fetch("https://ai.ultimatesmiledesign.com/detect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image: dummyCanvas.toDataURL("image/jpeg") })
    }).catch(() => { });
  }

  // pingDetectApi();

  let stream = null;
  let running = false;
  let capturedDataUrl = null;
  let lastConf = 0;
  let generationPromise = null;
  let generationResult = null;
  let leadSubmitted = false;
  let resultShown = false; // is run me preview box me result dikh chuka
  let submitRun = 0; // preview band hone pe purane submit ka async kaam ignore
  let leadId = null;
  let captureNonce = null;
  let isCapturing = false;
  let currentFacingMode = "user"; // "user" or "environment"
  let hasMultipleCameras = false;
  const isMobile = /Mobi|Android|iPhone|iPad|iPod/i.test(navigator.userAgent);

  // ✅ WhatsApp dedupe flags
  let whatsappTriggered = false;
  let whatsappInFlight = false;

  // Modal flow transition state
  let isTransitioningStep = false;

  function cleanupModalBackdrops() {
    document.querySelectorAll(".modal-backdrop").forEach((el) => el.remove());
    document.body.classList.remove("modal-open");
    document.body.style.removeProperty("overflow");
    document.body.style.removeProperty("padding-right");
  }

  // ✅ NEW: last detect snapshot + freshness
  let lastDetectAt = 0;
  let lastVisible = false;
  const DETECT_FRESH_MS = 350; // adjust if needed

  function setPreviewImages(beforeSrc, afterSrc) {
    const pBefore = document.getElementById("previewBeforeImg");
    const pAfter = document.getElementById("previewAfterImg");

    if (pBefore && beforeSrc) {
      pBefore.src = beforeSrc;
      const syncAspect = () => {
        const wrap = document.querySelector(".preview-modal-wrapper");
        if (wrap && pBefore.naturalWidth && pBefore.naturalHeight) {
          wrap.style.aspectRatio = `${pBefore.naturalWidth} / ${pBefore.naturalHeight}`;
        }
      };
      if (pBefore.complete && pBefore.naturalWidth) {
        syncAspect();
      } else {
        pBefore.onload = syncAspect;
      }
    }
    if (pAfter && afterSrc) pAfter.src = afterSrc;
  }

  // dono images load (ya error / timeout) hone par cb sirf ek baar
  function whenImagesReady(imgs, cb, timeoutMs = 10000) {
    let pending = 0;
    let done = false;
    const finish = () => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      cb();
    };
    const timer = setTimeout(finish, timeoutMs);

    imgs.forEach((img) => {
      if (!img || (img.complete && img.naturalWidth)) return;
      pending++;
      const settle = () => {
        if (--pending === 0) finish();
      };
      img.addEventListener("load", settle, { once: true });
      img.addEventListener("error", settle, { once: true });
    });

    if (pending === 0) finish();
  }

  function resetPreviewSlider() {
    const slider = document.getElementById("slider");
    if (!slider) return;
    slider.value = 50;
    slider.dispatchEvent(new Event("input"));
  }

  // ✅ Form submit hote hi next step (preview) open; image ready hone tak box me loader
  function openPreviewWithLoader() {
    // captured photo se box ka size abhi set ho jata hai (final image same size ki hoti hai)
    setPreviewImages(capturedDataUrl, capturedDataUrl);
    processLoader.start();

    isTransitioningStep = true;

    // Close smileModal completely if still open
    const smileModal = bootstrap.Modal.getInstance(smileModalEl);
    if (smileModal && smileModalEl && smileModalEl.classList.contains("show")) {
      smileModal.hide();
    }

    const contactModalEl = document.getElementById("contactModal");
    const contactModal = contactModalEl ? bootstrap.Modal.getInstance(contactModalEl) : null;

    const previewEl = document.getElementById("PreviewModal");
    const previewModal =
      bootstrap.Modal.getInstance(previewEl) || new bootstrap.Modal(previewEl);

    if (contactModal && contactModalEl && contactModalEl.classList.contains("show")) {
      contactModalEl.addEventListener(
        "hidden.bs.modal",
        () => {
          previewModal.show();
        },
        { once: true }
      );
      contactModal.hide();
    } else {
      contactModal?.hide();
      previewModal.show();
    }
  }

  // Generation + lead dono ready → box me before/after slider + buttons
  function tryShowPreviewResult() {
    if (resultShown) return;
    if (!leadSubmitted) return;
    if (!generationResult || generationResult.done !== true) return;

    resultShown = true;

    if (generationResult.ok === true) {
      setPreviewImages(
        generationResult.beforeUrl || capturedDataUrl,
        generationResult.afterUrl || generationResult.beforeUrl
      );

      // images load hone ke baad 100% → loader hatao, slider + buttons dikhao
      whenImagesReady(
        [document.getElementById("previewBeforeImg"), document.getElementById("previewAfterImg")],
        () => {
          processLoader.finish(() => {
            processLoader.stop();
            resetPreviewSlider();
          });
        }
      );

      leadForm?.reset();

      // ✅ Only triggers once due to whatsappInFlight lock
      tryTriggerWhatsapp();
    } else {
      processLoader.fail(generationResult.error || "Smile generation failed. Please try again.");
    }
  }

  function getThreshold() {
    if (typeof window.THRESHOLD === "number") return window.THRESHOLD;
    if (typeof THRESHOLD === "number") return THRESHOLD;
    return 0.55;
  }

  function showFreeze() {
    freezeImg.classList.remove("hidden");
    freezeImg.classList.remove("visually-hidden");
    video.classList.add("hidden");
    const camVp = document.getElementById("cameraViewport");
    if (camVp) camVp.classList.add("is-captured");
    if (faceOverlay) {
      faceOverlay.classList.remove("ready");
      faceOverlay.classList.add("d-none");
    }
    if (guideLine) {
      guideLine.classList.add("d-none");
    }
    if (smileDetectBadge) {
      smileDetectBadge.classList.add("d-none");
    }
  }

  function hideFreeze() {
    freezeImg.classList.add("hidden");
    freezeImg.classList.add("visually-hidden");
    freezeImg.src = "";
    video.classList.remove("hidden");
    const camVp = document.getElementById("cameraViewport");
    if (camVp) camVp.classList.remove("is-captured");
    if (faceOverlay) {
      faceOverlay.classList.remove("d-none");
    }
    if (guideLine) {
      guideLine.classList.remove("d-none");
    }
    if (smileDetectBadge) {
      smileDetectBadge.classList.remove("d-none");
    }
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

  function setControlsForVerifying() {
    captureBtn.classList.remove("hidden", "d-none");
    recaptureBtn.classList.add("hidden", "d-none");
    confirmBtn.classList.add("hidden", "d-none");

    captureBtn.disabled = true;
    captureBtn.classList.remove("btn-capture-ready");
    captureBtn.innerHTML = '<span class="capture-inner">Verifying...</span>';
    if (faceOverlay) {
      faceOverlay.classList.remove("ready");
      faceOverlay.classList.add("d-none");
    }
    if (guideLine) {
      guideLine.classList.add("d-none");
    }
    if (smileDetectBadge) {
      smileDetectBadge.classList.add("d-none");
    }
    updateSwitchCameraButtonVisibility();
  }


  async function checkCameraDevices() {
    try {
      if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
        const devices = await navigator.mediaDevices.enumerateDevices();
        const videoDevices = devices.filter((d) => d.kind === "videoinput");
        hasMultipleCameras = videoDevices.length > 1;

        // Log the detected cameras to the console for easy verification
        console.log("--- Detected Camera Devices ---");
        console.table(videoDevices.map(c => ({ Name: c.label || 'Unnamed Camera', ID: c.deviceId })));
      }
    } catch (e) {
      console.warn("enumerateDevices failed:", e);
    }
    updateSwitchCameraButtonVisibility();
  }

  function updateSwitchCameraButtonVisibility() {
    if (!switchCameraBtn) return;
    if (!isCapturing && !capturedDataUrl) {
      switchCameraBtn.classList.remove("hidden");
    } else {
      switchCameraBtn.classList.add("hidden");
    }
  }

  async function startCamera() {
    stopCamera();

    const cameraDeniedOverlay = document.getElementById("cameraDeniedOverlay");

    const constraints = {
      video: {
        width: { ideal: 1184 },
        height: { ideal: 864 },
        facingMode: { ideal: currentFacingMode }
      },
      audio: false,
    };

    stream = await navigator.mediaDevices.getUserMedia(constraints);

    video.srcObject = stream;

    if (currentFacingMode === "environment") {
      video.classList.add("no-mirror");
    } else {
      video.classList.remove("no-mirror");
    }

    hideFreeze();
    video.classList.remove("hidden");

    await video.play();
    await checkCameraDevices();

    // Camera stream playing: hide permission overlay and show camera UI
    const cameraViewport = document.getElementById("cameraViewport");
    if (cameraViewport) cameraViewport.classList.remove("permission-pending");
    if (cameraDeniedOverlay) cameraDeniedOverlay.classList.add("d-none");
  }

  function stopCamera() {
    try {
      if (video && video.srcObject) {
        const s = video.srcObject;
        s.getTracks().forEach((t) => t.stop());
      }
    } catch (e) { }
    video.srcObject = null;
    stream = null;
    updateSwitchCameraButtonVisibility();
  }

  async function detectOnce(canvas) {
    console.log("CALLING /detect (json base64)");

    const dataUrl = canvas.toDataURL("image/jpeg", 0.85);

    // same-origin call (no CORS)
    const resp = await fetch("/virtual-smile-try-on/api/detect/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image: dataUrl }),
    });

    const text = await resp.text();
    let data;
    try {
      data = JSON.parse(text);
    } catch {
      data = { detail: text };
    }

    // console.log("DETECT RESPONSE", data);

    if (!resp.ok) {
      throw new Error(data?.detail || `Detect failed: ${resp.status}`);
    }

    return data;
  }

  async function saveCapture(frameDataUrl, conf) {
    const resp = await fetch("/virtual-smile-try-on/api/capture/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrftoken,
      },
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

    const data = await resp.json();

    if (!resp.ok || !data.ok) {
      return {
        ok: false,
        error: data?.error || "Smile design failed",
        status: resp.status,
      };
    }

    return {
      ok: true,
      beforeUrl: data.before_url,
      afterUrl: data.after_url,
    };
  }

  function updateCaptureButtonState(enabled) {
    if (!captureBtn) return;

    captureBtn.classList.remove("hidden", "d-none");

    if (enabled) {
      captureBtn.disabled = false;
      captureBtn.classList.add("btn-capture-ready");
      captureBtn.innerHTML = '<span class="capture-inner">Capture Now</span>';
      if (faceOverlay) {
        faceOverlay.classList.add("ready");
      }
    } else {
      captureBtn.disabled = true;
      captureBtn.classList.remove("btn-capture-ready");
      captureBtn.innerHTML = '<span class="capture-inner">Capture Now</span>';
      if (faceOverlay) {
        faceOverlay.classList.remove("ready");
      }
    }
    updateSwitchCameraButtonVisibility();
  }

  function setControlsForLive() {
    captureBtn.classList.remove("hidden", "d-none");
    recaptureBtn.classList.add("hidden", "d-none");
    confirmBtn.classList.add("hidden", "d-none");
    captureBtn.innerHTML = '<span class="capture-inner">Capture Now</span>';
    captureBtn.disabled = true;
    captureBtn.classList.remove("btn-capture-ready");
    confirmBtn.disabled = true;
    const camVp = document.getElementById("cameraViewport");
    if (camVp) camVp.classList.remove("is-captured");
    if (faceOverlay) {
      faceOverlay.classList.remove("ready");
      faceOverlay.classList.remove("d-none");
    }
    if (guideLine) {
      guideLine.classList.remove("d-none");
    }
    if (smileDetectBadge) {
      smileDetectBadge.classList.remove("d-none");
      updateDetectScore(0, false);
    }
    updateSwitchCameraButtonVisibility();
  }

  function setControlsForCaptured() {
    captureBtn.classList.add("hidden", "d-none");
    captureBtn.classList.remove("btn-capture-ready");
    recaptureBtn.classList.remove("hidden", "d-none");
    confirmBtn.classList.remove("hidden", "d-none");
    confirmBtn.disabled = !capturedDataUrl;
    captureBtn.disabled = true;
    const camVp = document.getElementById("cameraViewport");
    if (camVp) camVp.classList.add("is-captured");
    if (faceOverlay) {
      faceOverlay.classList.remove("ready");
      faceOverlay.classList.add("d-none");
    }
    if (guideLine) {
      guideLine.classList.add("d-none");
    }
    if (smileDetectBadge) {
      smileDetectBadge.classList.add("d-none");
    }
    updateSwitchCameraButtonVisibility();
  }

  function drawCurrentFrameToCanvas() {
    canvas.width = video.videoWidth || 1184;
    canvas.height = video.videoHeight || 864;

    ctx.save();
    if (currentFacingMode === "user") {
      ctx.translate(canvas.width, 0);
      ctx.scale(-1, 1);
    }
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    ctx.restore();
  }

  function setVerifyingUI(isVerifying) {
    if (!captureBtn) return;
    captureBtn.classList.remove("hidden", "d-none");
    if (isVerifying) {
      captureBtn.disabled = true;
      captureBtn.innerHTML = '<span class="capture-inner">Verifying...</span>';
    } else {
      captureBtn.disabled = false;
      captureBtn.innerHTML = '<span class="capture-inner">Capture Now</span>';
    }
  }


  // NEW: On-click hard gate (validate the exact frame being captured)
  async function captureAndValidateNow() {
    drawCurrentFrameToCanvas();

    const data = await detectOnce(canvas);

    const conf =
      typeof data.conf === "number"
        ? data.conf
        : typeof data.confidence === "number"
          ? data.confidence
          : 0;

    const visible = !!data.visible;
    const threshold = getThreshold();

    if (!(visible && conf >= threshold)) {
      throw new Error(
        `Not smiling enough. Confidence ${conf.toFixed(2)} (need ${threshold}).`
      );
    }

    return {
      dataUrl: canvas.toDataURL("image/jpeg", 0.92),
      conf,
      visible,
    };
  }

  async function detectLoop() {
    running = true;

    while (running) {
      try {
        if (!video.srcObject || video.readyState < 2) {
          await new Promise((r) => setTimeout(r, 120));
          continue;
        }

        drawCurrentFrameToCanvas();

        const data = await detectOnce(canvas);

        if (!running) break;

        const conf =
          typeof data.conf === "number"
            ? data.conf
            : typeof data.confidence === "number"
              ? data.confidence
              : 0;

        const visible = !!data.visible;
        lastConf = conf;

        // ✅ store last detect snapshot time + visible
        lastVisible = visible;
        lastDetectAt = Date.now();

        const threshold = getThreshold();
        if (status) {
          status.textContent = `Confidence: ${conf.toFixed(2)} | Visible: ${visible} | Threshold: ${threshold}`;
        }

        // Live update detection percentage indicator
        updateDetectScore(conf, visible);

        // Optional: require freshness (small extra protection)
        const fresh = Date.now() - lastDetectAt <= DETECT_FRESH_MS;
        if (!isCapturing && running) {
          updateCaptureButtonState(fresh && visible && conf >= threshold);
        }
      } catch (e) {
        console.error("detectLoop error:", e);
      }

      await new Promise((r) => setTimeout(r, 200));
    }
  }

  captureBtn.addEventListener("click", async () => {
    if (isCapturing) return;
    isCapturing = true;

    showError("");
    resetResult();
    setMessage("");

    // extra safety
    if (captureBtn.disabled) {
      isCapturing = false;
      return;
    }

    if (!video.srcObject || video.readyState < 2) {
      setMessage("Camera not ready. Please try again.", "error");
      isCapturing = false;
      return;
    }

    try {
      // ✅ Freeze the exact frame immediately
      drawCurrentFrameToCanvas();
      const snapDataUrl = canvas.toDataURL("image/jpeg", 0.92);

      freezeImg.src = snapDataUrl;
      showFreeze();

      // ✅ Show Verifying...
      setControlsForVerifying();
      setMessage("Please wait… your image is being verified.", "muted");

      // ✅ Verify the frozen frame
      const data = await detectOnce(canvas);

      const conf =
        typeof data.conf === "number"
          ? data.conf
          : typeof data.confidence === "number"
            ? data.confidence
            : 0;

      const visible = !!data.visible;
      const threshold = getThreshold();

      // ❌ FAIL → back to live → Capture Now (disabled until smile again)
      if (!(visible && conf >= threshold)) {
        hideFreeze();
        setControlsForLive();
        setMessage("Verification failed ❌ Please smile and try again.", "error");

        // ensure detect loop runs to re-enable button
        if (!running) detectLoop();

        isCapturing = false;
        return;
      }

      // ✅ PASS → keep frozen → show Recapture + Continue
      setMessage("Verified ✅ Captured successfully.", "ok");

      capturedDataUrl = snapDataUrl;
      lastConf = conf;

      // backend capture save
      try {
        const saved = await saveCapture(capturedDataUrl, lastConf);
        if (saved && saved.ok) {
          captureNonce = saved.nonce || null;
        } else {
          // treat backend reject as FAIL
          hideFreeze();
          setControlsForLive();
          setMessage("Capture validation failed. Please try again.", "error");
          if (!running) detectLoop();
          isCapturing = false;
          return;
        }
      } catch (e) {
        hideFreeze();
        setControlsForLive();
        setMessage("Capture failed. Please try again.", "error");
        if (!running) detectLoop();
        isCapturing = false;
        return;
      }

      // stop camera only after PASS + saved
      running = false;
      stopCamera();

      setControlsForCaptured(); // ✅ Recapture + Continue
      isCapturing = false;
    } catch (e) {
      hideFreeze();
      setControlsForLive();
      setMessage("Verification failed ❌ Please try again.", "error");
      if (!running) detectLoop();
      isCapturing = false;
    }
  });

  recaptureBtn.addEventListener("click", async () => {
    showError("");
    resetResult();
    setMessage("");

    capturedDataUrl = null;
    lastConf = 0;
    lastVisible = false;
    lastDetectAt = 0;

    hideFreeze();

    try {
      await startCamera();
      setMessage("Camera restarted. Smile to enable Capture.", "muted");
      setControlsForLive();
      detectLoop();
    } catch (e) {
      console.error(e);
      setMessage("Camera access failed: " + e.message, "error");
      showError("Allow camera access in browser, then refresh.");
      const cameraDeniedOverlay = document.getElementById("cameraDeniedOverlay");
      if (cameraDeniedOverlay) cameraDeniedOverlay.classList.remove("d-none");
    }
  });

  switchCameraBtn?.addEventListener("click", async () => {
    if (isCapturing || !running) return;

    currentFacingMode = currentFacingMode === "user" ? "environment" : "user";

    setMessage("Switching camera...", "muted");

    try {
      await startCamera();
      setMessage("Camera switched.", "muted");
      if (!running) detectLoop();
    } catch (e) {
      console.error(e);
      // Fallback: switch back
      currentFacingMode = currentFacingMode === "user" ? "environment" : "user";
      try {
        await startCamera();
      } catch (err) {
        setMessage("Failed to switch camera: " + e.message, "error");
        const cameraDeniedOverlay = document.getElementById("cameraDeniedOverlay");
        if (cameraDeniedOverlay) cameraDeniedOverlay.classList.remove("d-none");
      }
    }
  });

  confirmBtn.addEventListener("click", async () => {
    showError("");

    if (!capturedDataUrl) {
      setMessage("Please capture an image first.", "error");
      return;
    }

    confirmBtn.disabled = true;
    setMessage("Generating with Gemini…", "muted");

    if (!generationPromise) {
      generationPromise = (async () => {
        try {
          const result = await callGemini(capturedDataUrl);

          if (!result || !result.ok) {
            generationResult = {
              ok: false,
              error: result?.error || "Smile generation failed",
              done: true,
            };
            tryShowPreviewResult();
            return generationResult;
          }

          generationResult = {
            ok: true,
            beforeUrl: result.beforeUrl,
            afterUrl: result.afterUrl,
            done: true,
          };

          if (resultWrap && resultStatus) {
            resultWrap.classList.remove("hidden");
            resultStatus.textContent = "Smile generated ✅";
          }

          tryShowPreviewResult();
          return generationResult;
        } catch (e) {
          generationResult = { ok: false, error: e.message || String(e), done: true };
          return generationResult;
        }
      })();
    }

    try {
      isTransitioningStep = true;
      const contactModalEl = document.getElementById("contactModal");
      const contactModal =
        bootstrap.Modal.getInstance(contactModalEl) || new bootstrap.Modal(contactModalEl);

      const smileModal = bootstrap.Modal.getInstance(smileModalEl);
      if (smileModal && smileModalEl && smileModalEl.classList.contains("show")) {
        smileModalEl.addEventListener(
          "hidden.bs.modal",
          () => {
            contactModal.show();
          },
          { once: true }
        );
        smileModal.hide();
      } else {
        contactModal.show();
      }
    } catch (e) {
      console.warn("Contact modal show error:", e);
    }

    confirmBtn.disabled = false;
  });

  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
      const cookies = document.cookie.split(";");
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === name + "=") {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

    function getCsrfToken() {
    return getCookie("csrftoken") || document.querySelector('[name=csrfmiddlewaretoken]')?.value || "";
  }
  const csrftoken = getCookie("csrftoken");

  async function triggerWhatsappWebhook() {
    const res = await fetch("/virtual-smile-try-on/api/whatsapp/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrftoken,
      },
      body: JSON.stringify({
        lead_id: leadId,
        before_url: generationResult?.beforeUrl || "",
        after_url: generationResult?.afterUrl || "",
      }),
    });
    return await res.json();
  }

  // ✅ UPDATED: prevents double call with whatsappInFlight
  async function tryTriggerWhatsapp() {
    if (whatsappTriggered || whatsappInFlight) return;

    if (!leadSubmitted || !leadId) return;
    if (!generationResult || generationResult.done !== true) return;
    if (!generationResult.ok) return;

    whatsappInFlight = true;
    try {
      const data = await triggerWhatsappWebhook();
      if (data && data.ok) {
        whatsappTriggered = true;
      } else {
        console.warn("WhatsApp webhook failed:", data);
      }
    } catch (e) {
      console.warn("WhatsApp webhook error:", e);
    } finally {
      whatsappInFlight = false;
    }
  }

  if (leadForm) {
    leadForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      if (leadFormMsg) {
        leadFormMsg.textContent = "";
        leadFormMsg.style.color = "";
      }

      if (leadSubmitBtn) leadSubmitBtn.disabled = true;

      // ✅ Submit hote hi preview popup open, image ready hone tak white border box me loader
      openPreviewWithLoader();
      const run = ++submitRun;

      // ✅ Wait for Gemini generation to finish if still in flight
      if (generationPromise) {
        try {
          await generationPromise;
        } catch (err) {
          console.warn("Generation promise error:", err);
        }
      }

      // user ne beech me preview band kar diya → ye submit yahin khatam
      if (run !== submitRun) {
        if (leadSubmitBtn) leadSubmitBtn.disabled = false;
        return;
      }

      const selectedCodeEl = document.getElementById("selectedCode");
      const selectedDialCode = selectedCodeEl ? selectedCodeEl.textContent.trim().replace(/[^\d+]/g, "") : "+91";
      const rawDigits = leadPhone ? leadPhone.value.trim().replace(/\D/g, "") : "";
      const fullInputVal = document.getElementById("fullPhoneInput") ? document.getElementById("fullPhoneInput").value.trim().replace(/\s+/g, "") : "";

      let phoneToSend = fullInputVal;
      if (!phoneToSend && rawDigits) {
        phoneToSend = `${selectedDialCode}${rawDigits}`;
      } else if (rawDigits && !phoneToSend.startsWith("+")) {
        phoneToSend = `${selectedDialCode}${rawDigits}`;
      }

      const payload = {
        name: leadName ? leadName.value.trim() : "",
        phone: phoneToSend,
        pincode: leadPincode ? leadPincode.value.trim() : "",
        city: leadCity ? leadCity.value.trim() : "",
        email: leadEmail ? leadEmail.value.trim() : "",
        nonce: captureNonce,
        before_image: generationResult?.beforeUrl || capturedDataUrl || "",
        after_image: generationResult?.afterUrl || "",
      };

      try {
        const res = await fetch("/virtual-smile-try-on/api/smile-lead/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrftoken,
          },
          body: JSON.stringify(payload),
        });

        const data = await res.json();
        if (run !== submitRun) return;

        if (!res.ok || !data.ok) {
          // form band ho chuka hai, isliye error preview box me hi
          processLoader.fail(data?.error || "Could not save your details. Please try again.");
          if (leadSubmitBtn) leadSubmitBtn.disabled = false;
          return;
        }

        leadSubmitted = true;
        leadId = data.id || null;
        resultShown = false;

        tryShowPreviewResult();
        tryTriggerWhatsapp(); // ✅ safe now
      } catch (err) {
        if (run === submitRun) processLoader.fail("Network error. Please try again.");
      } finally {
        if (leadSubmitBtn) leadSubmitBtn.disabled = false;
      }
    });
  }

  const smileModalEl = document.getElementById("smileModal");
  const smileIntroView = document.getElementById("smileIntroView");
  const smileCameraView = document.getElementById("smileCameraView");
  const nextIntroBtn = document.getElementById("nextIntroBtn");
  const backToIntroBtn = document.getElementById("backToIntroBtn");
  const guidelineVideo = document.getElementById("guidelineVideo");

  async function openLiveCamera() {
    if (guidelineVideo) {
      try { guidelineVideo.pause(); } catch (e) { }
    }
    if (smileIntroView) smileIntroView.classList.add("d-none");
    if (smileCameraView) smileCameraView.classList.remove("d-none");

    // Show Image 2 permission prompt until camera is allowed
    const cameraViewport = document.getElementById("cameraViewport");
    if (cameraViewport) cameraViewport.classList.add("permission-pending");
    const cameraDeniedOverlay = document.getElementById("cameraDeniedOverlay");
    if (cameraDeniedOverlay) cameraDeniedOverlay.classList.remove("d-none");

    setControlsForLive();
    try {
      await startCamera();
      if (!running) detectLoop();
      setMessage(
        "Camera started. Smile and the Capture button will enable automatically.",
        "muted"
      );
    } catch (e) {
      console.error(e);
      setMessage("Camera access failed: " + e.message, "error");
      showError("Allow camera access in browser, then refresh.");
      if (cameraViewport) cameraViewport.classList.add("permission-pending");
      if (cameraDeniedOverlay) cameraDeniedOverlay.classList.remove("d-none");
    }
  }

  function playGuidelineVideo() {
    if (!guidelineVideo) return;
    try {
      const sources = Array.from(guidelineVideo.querySelectorAll("source"));
      const matched = sources.find((s) => !s.media || window.matchMedia(s.media).matches);
      if (matched && guidelineVideo.currentSrc && !guidelineVideo.currentSrc.endsWith(matched.getAttribute("src"))) {
        guidelineVideo.src = matched.src || matched.getAttribute("src");
        guidelineVideo.load();
      }
    } catch (_) {}
    guidelineVideo.currentTime = 0;
    guidelineVideo.play().catch(() => { });
  }

  function returnToIntroGuide() {
    running = false;
    stopCamera();
    hideFreeze();
    resetResult();

    if (smileDetectBadge) {
      smileDetectBadge.classList.add("d-none");
      updateDetectScore(0, false);
    }
    if (smileCameraView) smileCameraView.classList.add("d-none");
    if (smileIntroView) smileIntroView.classList.remove("d-none");

    playGuidelineVideo();
  }

  if (nextIntroBtn) {
    nextIntroBtn.addEventListener("click", () => {
      openLiveCamera();
    });
  }

  if (backToIntroBtn) {
    backToIntroBtn.addEventListener("click", () => {
      returnToIntroGuide();
    });
  }

  if (smileModalEl) {
    smileModalEl.addEventListener("shown.bs.modal", async () => {
      currentFacingMode = "user";
      isTransitioningStep = false;
      generationPromise = null;
      generationResult = null;
      capturedDataUrl = null;
      leadSubmitted = false;
      resultShown = false;
      leadId = null;

      // ✅ reset WhatsApp flags for new session
      whatsappTriggered = false;
      whatsappInFlight = false;

      // ✅ reset detect snapshot
      lastConf = 0;
      lastVisible = false;
      lastDetectAt = 0;

      const pBefore = document.getElementById("previewBeforeImg");
      const pAfter = document.getElementById("previewAfterImg");
      if (pBefore) pBefore.src = "";
      if (pAfter) pAfter.src = "";

      resetResult();
      hideFreeze();
      if (smileDetectBadge) {
        updateDetectScore(0, false);
      }

      // Show Figma Intro View first
      if (smileCameraView) smileCameraView.classList.add("d-none");
      if (smileIntroView) smileIntroView.classList.remove("d-none");

      // Autoplay guideline video non-stop (mobile / pc responsive)
      playGuidelineVideo();
    });

    smileModalEl.addEventListener("hidden.bs.modal", () => {
      currentFacingMode = "user";
      running = false;
      stopCamera();
      hideFreeze();
      resetResult();

      if (guidelineVideo) {
        try { guidelineVideo.pause(); } catch (e) { }
      }

      if (smileCameraView) smileCameraView.classList.add("d-none");
      if (smileIntroView) smileIntroView.classList.remove("d-none");
      if (smileDetectBadge) {
        smileDetectBadge.classList.add("d-none");
        updateDetectScore(0, false);
      }

      if (!isTransitioningStep) {
        generationPromise = null;
        generationResult = null;
        capturedDataUrl = null;

        // ✅ reset detect snapshot
        lastConf = 0;
        lastVisible = false;
        lastDetectAt = 0;

        leadSubmitted = false;
        leadId = null;
        captureNonce = null;

        // ✅ reset WhatsApp flags
        whatsappTriggered = false;
        whatsappInFlight = false;

        setControlsForLive();
      }
    });
  }

  // ✅ Contact modal lifecycle events
  const contactModalEl = document.getElementById("contactModal");
  if (contactModalEl) {
    contactModalEl.addEventListener("shown.bs.modal", () => {
      isTransitioningStep = false;
    });

    contactModalEl.addEventListener("hidden.bs.modal", () => {
      // If user manually closed contactModal without moving to Preview
      if (!isTransitioningStep && !resultShown && !leadSubmitted) {
        const smileModal = bootstrap.Modal.getInstance(smileModalEl);
        if (smileModal && smileModalEl && smileModalEl.classList.contains("show")) {
          smileModal.hide();
        }

        cleanupModalBackdrops();
        hideFreeze();
        resetResult();
        setControlsForLive();

        generationPromise = null;
        generationResult = null;
        capturedDataUrl = null;
        lastConf = 0;
        lastVisible = false;
        lastDetectAt = 0;
        leadSubmitted = false;
        leadId = null;
        captureNonce = null;
        whatsappTriggered = false;
        whatsappInFlight = false;
      }
    });
  }

  // ✅ Preview modal lifecycle events - ensure clean close and no leftover modals
  const previewEl = document.getElementById("PreviewModal");
  if (previewEl) {
    previewEl.addEventListener("shown.bs.modal", () => {
      isTransitioningStep = false;
    });

    previewEl.addEventListener("hidden.bs.modal", () => {
      isTransitioningStep = false;
      resultShown = false;

      // loader band + chal raha submit ignore (agla run fresh)
      submitRun++;
      processLoader.stop();

      // Ensure smileModal and contactModal are definitely closed
      const smileModal = bootstrap.Modal.getInstance(smileModalEl);
      if (smileModal && smileModalEl && smileModalEl.classList.contains("show")) {
        smileModal.hide();
      }

      const contactModal = contactModalEl ? bootstrap.Modal.getInstance(contactModalEl) : null;
      if (contactModal && contactModalEl && contactModalEl.classList.contains("show")) {
        contactModal.hide();
      }

      cleanupModalBackdrops();

      hideFreeze();
      resetResult();
      setControlsForLive();

      // Reset flow data for next run
      generationPromise = null;
      generationResult = null;
      capturedDataUrl = null;
      lastConf = 0;
      lastVisible = false;
      lastDetectAt = 0;
      leadSubmitted = false;
      leadId = null;
      captureNonce = null;
      whatsappTriggered = false;
      whatsappInFlight = false;
    });
  }
})();