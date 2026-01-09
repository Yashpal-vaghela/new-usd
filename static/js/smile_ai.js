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

  // Contact modal form elements (added)
  const leadForm = document.getElementById("leadForm");
  const leadName = document.getElementById("leadName");
  const leadPhone = document.getElementById("leadPhone");
  const leadCity = document.getElementById("leadCity");
  const leadMessage = document.getElementById("leadMessage");
  const leadFormMsg = document.getElementById("leadFormMsg");
  const leadSubmitBtn = document.getElementById("leadSubmitBtn");

  const ctx = canvas.getContext("2d", { willReadFrequently: true });

  let stream = null;
  let running = false;   
  let capturedDataUrl = null;  
  let lastConf = 0;  
  let generationPromise = null;
  let generationResult = null;       

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


  function setControlsForLive() {
    captureBtn.classList.remove("hidden");
    recaptureBtn.classList.add("hidden");
    confirmBtn.classList.add("hidden");

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

  async function detectLoop() {
    running = true;

    while (running) {
      try {
        if (!video.srcObject || video.readyState < 2) {
          await new Promise((r) => setTimeout(r, 120));
          continue;
        }

        canvas.width = video.videoWidth || 1184;
        canvas.height = video.videoHeight || 864;

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

    canvas.width = video.videoWidth || 1184;
    canvas.height = video.videoHeight || 864;

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

    // try {
    //   const saved = await saveCapture(capturedDataUrl, lastConf);
    //   if (saved && saved.saved) {
    //     setMessage(
    //       `Captured ✅ (confidence ${(saved.conf || lastConf || 0).toFixed(2)})`,
    //       "ok"
    //     );
    //   } else {
    //     setMessage("Captured ✅", "ok");
    //   }
    // } catch (e) {
    //   setMessage("Captured ✅", "ok");
    // }

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
    // resetResult();

    if (!capturedDataUrl) {
      setMessage("Please capture an image first.", "error");
      return;
    }

    confirmBtn.disabled = true;
    setMessage("Generating with Gemini…", "muted");

    // ✅ Start Gemini async ONCE (do not block UI)
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
            return generationResult;
          }

          generationResult = {
            ok: true,
            beforeUrl: result.beforeUrl,
            afterUrl: result.afterUrl,
            done:true,
          };

          // OPTIONAL: status text only (NO preview update)
          if (resultWrap && resultStatus) {
            resultWrap.classList.remove("hidden");
            resultStatus.textContent = "Smile generated ✅";
          }

          return generationResult;

        } catch (e) {
          generationResult = {
            ok: false,
            error: e.message || String(e),
          };
          return generationResult;
        }
      })();
    }


    // ✅ Open Contact modal immediately (user can fill while Gemini runs)
    try {
      const contactModalEl = document.getElementById("contactModal");
      const contactModal =
        bootstrap.Modal.getInstance(contactModalEl) || new bootstrap.Modal(contactModalEl);
      contactModal.show();
    } catch (e) {
      console.warn("Contact modal show error:", e);
    }

    // keep confirm enabled again (user can still submit contact)
    confirmBtn.disabled = false;
  });


  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
      const cookies = document.cookie.split(";");
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + "=")) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  const csrftoken = getCookie("csrftoken");

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
        message: leadMessage ? leadMessage.value.trim() : "",
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
          const errText =
            (data && (data.error || (data.errors && JSON.stringify(data.errors)))) ||
            "Form error. Please check fields.";
          if (leadFormMsg) {
            leadFormMsg.style.color = "red";
            leadFormMsg.textContent = errText;
          }
          return;
        }

          if (leadFormMsg) {
          leadFormMsg.style.color = "green";
          leadFormMsg.textContent = "Submitted ✅";
        }

        // ✅ If Gemini result is already ready → open PreviewModal immediately
        const openPreviewWith = (beforeUrl, afterUrl) => {
          try {
            // set preview images
            const pBefore = document.getElementById("previewBeforeImg");
            const pAfter = document.getElementById("previewAfterImg");
            if (pBefore) pBefore.src = beforeUrl || capturedDataUrl;
            if (pAfter) pAfter.src = afterUrl || beforeUrl || capturedDataUrl;

            // close contact modal
            const contactEl = document.getElementById("contactModal");
            const contactModal = bootstrap.Modal.getInstance(contactEl);
            if (contactModal) contactModal.hide();

            // open preview modal
            const previewEl = document.getElementById("PreviewModal");
            const previewModal =
              bootstrap.Modal.getInstance(previewEl) || new bootstrap.Modal(previewEl);
            previewModal.show();
          } catch (e) {
            console.warn("Preview modal open error:", e);
          }
        };

        // CASE 1: already generated
        if (generationResult && generationResult.ok) {
          openPreviewWith(
            generationResult.beforeUrl,
            generationResult.afterUrl
          );
          leadForm.reset();
          return;
        }

        // CASE 2: not ready yet → show loader and wait
          leadFormMsg.style.color = "white";
          leadFormMsg.innerHTML =
            `<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>` +
            `Generating your smile preview…`;
          leadSubmitBtn.disabled = true;

        // wait for generation to complete
        const result = await generationPromise;

        if (result && result.ok) {
          openPreviewWith(result.beforeUrl, result.afterUrl);
          leadForm.reset();
          return;
        }
        // if (!result || result.ok !== true) {
        //   leadFormMsg.style.color = "white";
        //   leadFormMsg.innerHTML =
        //     `<span class="spinner-border spinner-border-sm me-2"></span>
        //     Your smile transformation is in process…`;
        //   return;
        // }
        // CASE 3: Gemini finished but FAILED
        leadFormMsg.style.color = "red";
        leadFormMsg.textContent =
          result?.error || "Failed to generate preview.";
        return;
      } catch (err) {
        if (leadFormMsg) {
          leadFormMsg.style.color = "red";
          leadFormMsg.textContent = "Network error. Please try again.";
        }
      } finally {
        if (leadSubmitBtn) leadSubmitBtn.disabled = false;
      }
    });
  }
 //start Camera On Model
  const smileModalEl = document.getElementById("smileModal");

  if (smileModalEl) {
    smileModalEl.addEventListener("shown.bs.modal", async () => {
      // 🔁 RESET PREVIOUS SESSION STATE
      generationPromise = null;
      generationResult = null;
      capturedDataUrl = null;
      lastConf = 0;

      // clear preview images
      const pBefore = document.getElementById("previewBeforeImg");
      const pAfter = document.getElementById("previewAfterImg");
      if (pBefore) pBefore.src = "";
      if (pAfter) pAfter.src = "";

      // clear UI
      resetResult();
      hideFreeze();

      try {
        setControlsForLive();
        await startCamera();
        if (!running) {
          detectLoop();
        }
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
      lastConf = 0;
      setControlsForLive();
      console.log("Camera stopped (modal closed)");
    });
  }
})();