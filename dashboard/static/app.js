async function loadStatus() {
    const response = await fetch("/api/status");
    const data = await response.json();

    const status = document.getElementById(
        "service-status"
    );

    if (data.running) {
        status.textContent = "Kiwix Running";
        status.className = "status running";
    } else {
        status.textContent = "Kiwix Stopped";
        status.className = "status stopped";
    }
}


async function loadSystem() {
    const response = await fetch("/api/system");
    const data = await response.json();

    document.getElementById(
        "system-info"
    ).textContent = data.output;
}


async function loadLibrary() {
    const response = await fetch("/api/library");
    const data = await response.json();

    const library = document.getElementById(
        "library"
    );

    library.innerHTML = "";

    for (const item of data.collections) {

        const card = document.createElement("div");
        card.className = "library-card";

        const statusClass =
            item.installed
                ? "installed"
                : "available";

        const statusText =
            item.installed
                ? "Installed"
                : "Available";

        card.innerHTML = `
            <h3>${item.name}</h3>
            <p>${item.size}</p>
            <p class="${statusClass}">
                ${statusText}
            </p>
        `;

        library.appendChild(card);
    }
}


async function startNomad() {
    await fetch(
        "/api/start",
        { method: "POST" }
    );

    await loadStatus();
}


async function stopNomad() {
    await fetch(
        "/api/stop",
        { method: "POST" }
    );

    await loadStatus();
}


async function initialize() {
    await Promise.all([
        loadStatus(),
        loadLibrary(),
        loadSystem()
    ]);
}


initialize();
