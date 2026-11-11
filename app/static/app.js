const camera = document.querySelector("#camera");
const landmarkCanvas = document.querySelector("#landmarkCanvas");
const cameraStatus = document.querySelector("#cameraStatus");
const repCount = document.querySelector("#repCount");
const startCamera = document.querySelector("#startCamera");
const calibratePose = document.querySelector("#calibratePose");
const startDrill = document.querySelector("#startDrill");
const drillCards = document.querySelectorAll(".drill-card");

let stream = null;
let drillActive = false;
let landmarkLoopId = null;
let landmarkDetectionTimerId = null;
let landmarkLoopGeneration = 0;
let selectedDrill = "read";
let latestPoseResult = { landmarks: [], message: "Waiting for pose detection" };
let jumpStatusUntil = 0;
let calibrationReady = false;

const CAPTURE_WIDTH = 640;
const JUMP_STATUS_DURATION_MS = 750;
const captureCanvas = document.createElement("canvas");
const captureContext = captureCanvas.getContext("2d");

function syncCameraHeight() {
  document.documentElement.style.setProperty("--camera-height", `${window.innerHeight}px`);
}

syncCameraHeight();
window.addEventListener("resize", syncCameraHeight);
window.addEventListener("orientationchange", syncCameraHeight);

function startLandmarkLoop() {
  stopLandmarkLoop();
  const generation = landmarkLoopGeneration;

  const draw = () => {
    if (generation !== landmarkLoopGeneration) {
      return;
    }

    resizeLandmarkCanvas(camera, landmarkCanvas);
    drawLandmarkOverlay(landmarkCanvas, latestPoseResult);
    landmarkLoopId = requestAnimationFrame(draw);
  };

  const detect = async () => {
    let retryDelay = 0;
    try {
      latestPoseResult = await requestLandmarkAnalysis(camera);
      applyVisionState(latestPoseResult);
    } catch (error) {
      console.error("Landmark detection failed", error);
      const message = error instanceof Error ? error.message : "";
      if (message === "Camera frame is not ready") {
        retryDelay = 50;
      } else {
        if (performance.now() >= jumpStatusUntil) {
          cameraStatus.textContent = message || "Vision reconnecting";
        }
        retryDelay = 500;
      }
    } finally {
      if (generation === landmarkLoopGeneration) {
        // Start the next capture as soon as this request finishes, without
        // allowing multiple expensive vision requests to overlap.
        landmarkDetectionTimerId = window.setTimeout(detect, retryDelay);
      }
    }
  };

  draw();
  detect();
}

function stopLandmarkLoop() {
  landmarkLoopGeneration += 1;

  if (landmarkLoopId) {
    cancelAnimationFrame(landmarkLoopId);
    landmarkLoopId = null;
  }

  if (landmarkDetectionTimerId) {
    clearTimeout(landmarkDetectionTimerId);
    landmarkDetectionTimerId = null;
  }
}

async function enableCamera() {
  if (!navigator.mediaDevices?.getUserMedia) {
    cameraStatus.textContent = "Camera needs HTTPS or localhost";
    return;
  }

  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: "environment",
        width: { ideal: 1280 },
        height: { ideal: 720 },
      },
      audio: false,
    });

    camera.srcObject = stream;
    await camera.play();
    startLandmarkLoop();
    cameraStatus.textContent = "Camera live";
    startCamera.textContent = "Camera on";
    startCamera.disabled = true;
    calibratePose.disabled = false;
    startDrill.disabled = true;
  } catch (error) {
    const name = error && error.name;
    if (name === "NotAllowedError" || name === "PermissionDeniedError") {
      cameraStatus.textContent = "Camera permission blocked";
    } else if (name === "SecurityError" || name === "NotSupportedError") {
      cameraStatus.textContent = "Camera needs HTTPS or localhost";
    } else {
      cameraStatus.textContent = "Camera unavailable";
    }
    console.error(error);
  }
}

async function startCalibration() {
  try {
    const calibration = await postJson("/api/calibration/start");
    applyCalibrationState(calibration);
  } catch (error) {
    cameraStatus.textContent = error.message;
  }
}

async function toggleDrill() {
  try {
    if (drillActive) {
      applyDrillState(await postJson("/api/drill/stop"));
      return;
    }

    const formData = new FormData();
    formData.append("drill", selectedDrill);
    applyDrillState(await postJson("/api/drill/start", formData));
  } catch (error) {
    cameraStatus.textContent = error.message;
  }
}

function applyDrillState(state) {
  drillActive = state.active;
  repCount.textContent = state.repLabel;
  startDrill.textContent = state.buttonLabel;
  calibratePose.disabled = drillActive || !stream;

  // Only the running drill is authoritative. Idle vision frames keep the
  // default drill name and must not undo the card the athlete selected.
  if (state.active && state.drill) {
    selectedDrill = state.drill;
    drillCards.forEach((card) => {
      card.classList.toggle("active", card.dataset.drill === state.drill);
    });
  }
  drillCards.forEach((card) => {
    card.disabled = drillActive;
  });

  if (performance.now() >= jumpStatusUntil) {
    cameraStatus.textContent = state.status;
  }
}

function showPoseMessage(message) {
  if (message && performance.now() >= jumpStatusUntil && !drillActive) {
    cameraStatus.textContent = message;
  }
}

function applyVisionState(poseResult) {
  if (poseResult.calibration) {
    applyCalibrationState(poseResult.calibration);
  }

  if (poseResult.calibration?.active) {
    return;
  }

  const landmarks = poseResult.landmarks || [];
  if (
    typeof poseResult.isLoaded !== "boolean" ||
    typeof poseResult.isJumped !== "boolean"
  ) {
    showPoseMessage(poseResult.message);
    return;
  }

  if (!poseResult.calibration?.ready) {
    if (!poseResult.calibration?.message) {
      showPoseMessage(poseResult.message);
    }
    return;
  }

  if (poseResult.drill) {
    applyDrillState(poseResult.drill);
  }

  if (!landmarks.length && poseResult.message) {
    cameraStatus.textContent = poseResult.message;
    return;
  }

  if (poseResult.isJumped) {
    jumpStatusUntil = performance.now() + JUMP_STATUS_DURATION_MS;
  }

  if (performance.now() < jumpStatusUntil) {
    cameraStatus.textContent = "Jumped";
    return;
  }

  if (drillActive) {
    return;
  }

  cameraStatus.textContent = poseResult.isLoaded
    ? "Loaded stance"
    : poseResult.basePose
      ? "Stand loaded"
      : poseResult.message;
}

function applyCalibrationState(calibration) {
  calibrationReady = calibration.ready;

  if (!calibration.active) {
    calibratePose.disabled = !stream || drillActive;
    calibratePose.textContent = calibration.ready ? "Recalibrate" : "Calibrate";
    startDrill.disabled = !stream || !calibrationReady;
    if (calibration.message && performance.now() >= jumpStatusUntil) {
      cameraStatus.textContent = calibration.message;
    }
    return;
  }

  calibratePose.disabled = true;
  startDrill.disabled = true;
  if (!calibration.collecting) {
    cameraStatus.textContent = `Stand tall: ${Math.ceil(calibration.delayRemaining)}s`;
    calibratePose.textContent = "Waiting";
    return;
  }

  const sampleLabel = `${calibration.samples}/${calibration.minimumSamples}`;
  cameraStatus.textContent = `Calibrating: ${Math.ceil(calibration.timeRemaining)}s (${sampleLabel})`;
  calibratePose.textContent = "Calibrating";
}

async function requestLandmarkAnalysis(video) {
  const frame = await captureFrame(video);
  const formData = new FormData();
  formData.append("frame", frame, "camera-frame.jpg");

  return postJson("/api/vision/analyze", formData);
}

async function captureFrame(video) {
  const sourceWidth = video.videoWidth;
  const sourceHeight = video.videoHeight;
  if (!sourceWidth || !sourceHeight) {
    throw new Error("Camera frame is not ready");
  }

  const captureHeight = Math.round(CAPTURE_WIDTH * (sourceHeight / sourceWidth));

  if (captureCanvas.width !== CAPTURE_WIDTH || captureCanvas.height !== captureHeight) {
    captureCanvas.width = CAPTURE_WIDTH;
    captureCanvas.height = captureHeight;
  }

  captureContext.drawImage(video, 0, 0, CAPTURE_WIDTH, captureHeight);

  return new Promise((resolve, reject) => {
    captureCanvas.toBlob((blob) => {
      if (blob) {
        resolve(blob);
      } else {
        reject(new Error("Unable to capture camera frame"));
      }
    }, "image/jpeg", 0.6);
  });
}

async function postJson(url, body = undefined) {
  const response = await fetch(url, {
    method: "POST",
    body,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Request failed (${response.status})`);
  }

  return response.json();
}

function resizeLandmarkCanvas(video, canvas) {
  const width = video.videoWidth || video.clientWidth;
  const height = video.videoHeight || video.clientHeight;

  if (!width || !height) {
    return;
  }

  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width;
    canvas.height = height;
  }
}

function markerRadius(canvas) {
  const displayedWidth = canvas.clientWidth || canvas.width;
  const displayedHeight = canvas.clientHeight || canvas.height;
  if (!canvas.width || !canvas.height || !displayedWidth || !displayedHeight) {
    return 8;
  }

  // object-fit: cover scales the frame uniformly, then crops it. Size the
  // marker in bitmap pixels so it stays readable on the phone screen.
  const coverScale = Math.max(displayedWidth / canvas.width, displayedHeight / canvas.height);
  return Math.max(4, 8 / coverScale);
}

function drawLandmarkOverlay(canvas, poseResult) {
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    return;
  }

  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const landmarks = poseResult.landmarks || [];
  const radius = markerRadius(canvas);
  landmarks.forEach((landmark) => {
    drawPoint(ctx, landmark.x * canvas.width, landmark.y * canvas.height, radius);
  });
}

function drawPoint(ctx, x, y, radius) {
  ctx.beginPath();
  ctx.arc(x, y, radius, 0, Math.PI * 2);
  ctx.fillStyle = "rgba(255, 176, 92, 0.92)";
  ctx.fill();
}

drillCards.forEach((card) => {
  card.addEventListener("click", () => {
    if (drillActive || card.disabled) {
      return;
    }

    drillCards.forEach((item) => item.classList.remove("active"));
    card.classList.add("active");
    selectedDrill = card.dataset.drill;
  });
});

startCamera.addEventListener("click", enableCamera);
calibratePose.addEventListener("click", startCalibration);
startDrill.addEventListener("click", toggleDrill);

document.addEventListener("visibilitychange", () => {
  if (document.hidden) {
    stopLandmarkLoop();
  } else if (stream) {
    startLandmarkLoop();
  }
});

window.addEventListener("pagehide", () => {
  stopLandmarkLoop();
  stream?.getTracks().forEach((track) => track.stop());
});

