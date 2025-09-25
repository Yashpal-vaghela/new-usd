// Video fallback handler
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll("video").forEach(video => {
    let fallbackImg = document.createElement("img");
    fallbackImg.src = video.getAttribute("data-fallback");
    fallbackImg.alt = video.getAttribute("alt") + " fallback";
    fallbackImg.className = video.className;
    fallbackImg.style.display = "none";

    video.parentNode.insertBefore(fallbackImg, video.nextSibling);

    video.oncanplay = () => video.setAttribute("data-loaded", "true");

    setTimeout(() => {
      if (!video.getAttribute("data-loaded")) {
        video.style.display = "none";
        fallbackImg.style.display = "block";
      }
    }, 4000);
  });
});

// Snow effect
const canvas = document.getElementById("snow-canvas");
if (canvas) {
  const ctx = canvas.getContext("2d");

  function resizeCanvas() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  }
  resizeCanvas();
  window.addEventListener("resize", resizeCanvas);

  const MAX_HEIGHT = window.innerHeight * 0.4;

  class Particle {
    constructor(side) {
      this.size = Math.random() * 2 + 0.5;
      this.x = side === "left" ? Math.random() * 50 : canvas.width - Math.random() * 50;
      this.y = Math.random() * MAX_HEIGHT;
      this.speedY = Math.random() * 1 + 0.5;
      this.speedX = side === "left" ? Math.random() * 0.5 + 0.2 : -(Math.random() * 0.5 + 0.2);
      this.alpha = Math.random() * 0.8 + 0.2;
    }
    update() {
      this.x += this.speedX;
      this.y += this.speedY;
      if (this.y > MAX_HEIGHT || this.x < 0 || this.x > canvas.width) {
        this.reset();
      }
    }
    reset() {
      let side = Math.random() > 0.5 ? "left" : "right";
      this.size = Math.random() * 1 + 0.5;
      this.x = side === "left" ? Math.random() * 50 : canvas.width - Math.random() * 50;
      this.y = 0;
      this.speedY = Math.random() * 1 + 0.5;
      this.speedX = side === "left" ? Math.random() * 0.5 + 0.2 : -(Math.random() * 0.5 + 0.2);
      this.alpha = Math.random() * 0.8 + 0.2;
    }
    draw() {
      ctx.beginPath();
      ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(255, 255, 255, ${this.alpha})`;
      ctx.fill();
    }
  }

  let particles = [];
  let isSnowEnabled = window.innerWidth >= 768;

  if (isSnowEnabled) {
    for (let i = 0; i < 80; i++) {
      let side = Math.random() > 0.5 ? "left" : "right";
      particles.push(new Particle(side));
    }
  }

  function animate() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    particles.forEach(p => {
      p.update();
      p.draw();
    });
    requestAnimationFrame(animate);
  }

  animate();

  window.addEventListener("resize", () => {
    resizeCanvas();
    isSnowEnabled = window.innerWidth >= 768;
    if (isSnowEnabled && particles.length === 0) {
      for (let i = 0; i < 80; i++) {
        let side = Math.random() > 0.5 ? "left" : "right";
        particles.push(new Particle(side));
      }
    } else if (!isSnowEnabled) {
      particles = [];
    }
  });
}
