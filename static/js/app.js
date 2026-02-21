document.addEventListener("DOMContentLoaded", () => {
    const appShell = document.querySelector(".app-shell");
    const sidebarToggle = document.getElementById("sidebarToggle");

    if (appShell && sidebarToggle) {
        sidebarToggle.addEventListener("click", () => {
            appShell.classList.toggle("sidebar-open");
        });
    }

    document.querySelectorAll(".confirm-delete").forEach((form) => {
        form.addEventListener("submit", (event) => {
            const ok = window.confirm("Are you sure you want to delete this record?");
            if (!ok) {
                event.preventDefault();
            }
        });
    });

    setTimeout(() => {
        document.querySelectorAll(".flash").forEach((el) => {
            el.style.opacity = "0";
            setTimeout(() => el.remove(), 250);
        });
    }, 2800);
});
