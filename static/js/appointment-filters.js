// Handle appointment booking
function BookAppoinment(name, city) {
  const doctordata = { name: name };
  localStorage.setItem("selectedDoctor", JSON.stringify(doctordata));
  window.location.href = "/consult-with-dentist/";
}
// Handle city filter and dentist list refresh
document.addEventListener("DOMContentLoaded", function () {
  const dropdown = document.getElementById("cityDropdown");
  if (!dropdown) return;

  dropdown.addEventListener("change", function () {
    let form = document.getElementById("searchForm");
    if (!form) return;

    let formData = new FormData(form);
    let url = form.getAttribute("action") + "?" + new URLSearchParams(formData).toString();

    fetch(url)
      .then(response => response.text())
      .then(data => {
        let parser = new DOMParser();
        let doc = parser.parseFromString(data, "text/html");
        let newContent = doc.querySelector("#dentist-list");

        if (newContent) {
          document.getElementById("dentist-list").innerHTML = newContent.innerHTML;
        }

        let selectedCityName = dropdown.options[dropdown.selectedIndex].text;
        document.querySelector(".dentists_subtitle").textContent =
          selectedCityName && selectedCityName !== "Select Location"
            ? `Best Dentist Near ${selectedCityName} - ADE Verified`
            : `Best Dentists Near You - ADE Verified`;
      })
      .catch(error => console.error("Error:", error));
  });
});
