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

    // Contact modal form elements
    const leadForm = document.getElementById("leadForm");
    const leadName = document.getElementById("leadName");
    const leadPhone = document.getElementById("leadPhone");
    const leadCity = document.getElementById("leadCity");
    const leadEmail = document.getElementById("leadEmail");
    const leadFormMsg = document.getElementById("leadFormMsg");
    const leadSubmitBtn = document.getElementById("leadSubmitBtn");

    const ctx = canvas.getContext("2d", { willReadFrequently: true });

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

    // ✅ WhatsApp dedupe flags
    let whatsappTriggered = false;
    let whatsappInFlight = false;

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

        if (pBefore) pBefore.src = generationResult.beforeUrl || capturedDataUrl;
        if (pAfter) pAfter.src = generationResult.afterUrl || generationResult.beforeUrl;

        const contactModal = bootstrap.Modal.getInstance(
          document.getElementById("contactModal")
        );
        contactModal?.hide();

        const previewEl = document.getElementById("PreviewModal");
        const previewModal =
          bootstrap.Modal.getInstance(previewEl) || new bootstrap.Modal(previewEl);
        previewModal.show();

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

    function setControlsForVerifying() {
      captureBtn.classList.remove("hidden", "d-none");
      recaptureBtn.classList.add("hidden");
      confirmBtn.classList.add("hidden");

      captureBtn.disabled = true;
      captureBtn.textContent = "Verifying...";
    }


    async function startCamera() {
      stopCamera();

      stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 1184, height: 864 },
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

      console.log("DETECT RESPONSE", data);

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
      captureBtn.disabled = !enabled;
      captureBtn.textContent = enabled ? "Capture Now" : "Capture";
    }

    function setControlsForLive() {
      captureBtn.classList.remove("hidden");
      captureBtn.classList.remove("d-none");
      recaptureBtn.classList.add("hidden");
      confirmBtn.classList.add("hidden");
      captureBtn.textContent = "Capture";
      captureBtn.disabled = true;
      confirmBtn.disabled = true;
    }

    function setControlsForCaptured() {
      captureBtn.classList.add("hidden");
      recaptureBtn.classList.remove("hidden");
      confirmBtn.classList.remove("hidden");
      confirmBtn.disabled = !capturedDataUrl;
      captureBtn.disabled = true;
    }

    function drawCurrentFrameToCanvas() {
      canvas.width = video.videoWidth || 1184;
      canvas.height = video.videoHeight || 864;

      ctx.save();
      ctx.translate(canvas.width, 0);
      ctx.scale(-1, 1);
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      ctx.restore();
    }

    function setVerifyingUI(isVerifying) {
      if (!captureBtn) return;
      if (isVerifying) {
        captureBtn.disabled = true;
        captureBtn.textContent = "Verifying...";
      } else {
        captureBtn.disabled = false;
        captureBtn.textContent = "Capture";
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
          if (!isCapturing) {
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
        const contactModalEl = document.getElementById("contactModal");
        const contactModal =
          bootstrap.Modal.getInstance(contactModalEl) || new bootstrap.Modal(contactModalEl);
        contactModal.show();
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

        const payload = {
          name: leadName ? leadName.value.trim() : "",
          phone: leadPhone ? leadPhone.value.trim() : "",
          city: leadCity ? leadCity.value.trim() : "",
          email: leadEmail ? leadEmail.value.trim() : "",
          nonce: captureNonce,
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

    if (smileModalEl) {
      smileModalEl.addEventListener("shown.bs.modal", async () => {
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

        try {
          setControlsForLive();
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
        }
      });

      smileModalEl.addEventListener("hidden.bs.modal", () => {
        running = false;
        stopCamera();
        hideFreeze();
        resetResult();

        generationPromise = null;
        generationResult = null;
        capturedDataUrl = null;

        // ✅ reset detect snapshot
        lastConf = 0;
        lastVisible = false;
        lastDetectAt = 0;

        leadSubmitted = false;
        leadId = null;

        // ✅ reset WhatsApp flags
        whatsappTriggered = false;
        whatsappInFlight = false;

        setControlsForLive();
        // console.log("Camera stopped (modal closed)");
      });
    }
  })();