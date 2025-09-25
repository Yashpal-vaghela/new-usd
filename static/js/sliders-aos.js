// Swiper for Testimonials (myswiper)
document.addEventListener("DOMContentLoaded", function () {
  const totalslides = document.querySelectorAll(".myswiper .swiper-slide").length;
  const enableLoop = totalslides > 2;

  const mySwiper = new Swiper(".myswiper", {
    loop: enableLoop,
    centeredSlides: true,
    autoplay: { delay: 3000, disableOnInteraction: false },
    slidesPerView: "auto",
    spaceBetween: 40,
    speed: 800,
    effect: "slide",
    grabCursor: true,
    observer: true,
    observeParents: true,
    breakpoints: {
      576: { slidesPerView: 1.4, spaceBetween: 30 },
      768: { slidesPerView: 2, spaceBetween: 40 },
      1024: { slidesPerView: 3, spaceBetween: 20 },
      1200: { slidesPerView: 3, spaceBetween: 40 },
    },
  });
});
