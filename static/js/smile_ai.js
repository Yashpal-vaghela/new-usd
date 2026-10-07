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
  const switchCameraBtn = document.getElementById("switchCameraBtn");

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
  let previewOpened = false;
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

  function tryOpenPreviewInline() {
    if (previewOpened) return;
    if (!leadSubmitted) return;
    if (!generationResult || generationResult.done !== true) return;

    // stop loader
    if (leadFormMsg) {
      leadFormMsg.innerHTML = "";
      leadFormMsg.style.color = "";
    }

    if (generationResult.ok === true) {
      const pBefore = document.getElementById("previewBeforeImg");
      const pAfter = document.getElementById("previewAfterImg");

      if (pBefore) {
        pBefore.src = generationResult.beforeUrl || capturedDataUrl;
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
      if (pAfter) pAfter.src = generationResult.afterUrl || generationResult.beforeUrl;

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

      previewOpened = true;
      leadForm?.reset();

      // ✅ Only triggers once due to whatsappInFlight lock
      tryTriggerWhatsapp();
    } else {
      leadFormMsg.style.color = "red";
      leadFormMsg.textContent = generationResult.error || "Smile generation failed.";
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

    const resp = await fetch("https://ai.ultimatesmiledesign.com/detect", {
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
            tryOpenPreviewInline();
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

          tryOpenPreviewInline();
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

      // Show processing message while ensuring Gemini generation completes
      if (leadFormMsg) {
        leadFormMsg.style.color = "white";
        leadFormMsg.innerHTML = `
            <div class="d-flex align-items-center justify-content-center gap-2">
              <span class="spinner-border spinner-border-sm"></span>
              <span>Processing smile design… please wait</span>
            </div>`;
      }

      // ✅ Wait for Gemini generation to finish if still in flight
      if (generationPromise) {
        try {
          await generationPromise;
        } catch (err) {
          console.warn("Generation promise error:", err);
        }
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

        if (!res.ok || !data.ok) {
          leadFormMsg.style.color = "red";
          leadFormMsg.textContent = data?.error || "Form error. Please check fields.";
          if (leadSubmitBtn) leadSubmitBtn.disabled = false;
          return;
        }

        leadSubmitted = true;
        leadId = data.id || null;
        previewOpened = false;

        function showLeadLoader(text = "Your smile generation is in process…") {
          if (!leadFormMsg) return;
          leadFormMsg.style.color = "white";
          leadFormMsg.innerHTML = `
              <div class="d-flex align-items-center justify-content-center gap-2">
                <span class="spinner-border spinner-border-sm"></span>
                <span>${text}</span>
              </div>`;
        }

        showLeadLoader();

        tryOpenPreviewInline();
        tryTriggerWhatsapp(); // ✅ safe now
      } catch (err) {
        leadFormMsg.style.color = "red";
        leadFormMsg.textContent = "Network error. Please try again.";
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
      previewOpened = false;
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
      if (!isTransitioningStep && !previewOpened && !leadSubmitted) {
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
      previewOpened = false;

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