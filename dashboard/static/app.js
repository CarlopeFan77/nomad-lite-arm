async function loadStatus() {
    const response = await fetch("/api/status");
    const data = await response.json();

    const status = document.getElementById(
        "service-status"
    );

    const openButton = document.getElementById(
        "open-library-button"
    );

    if (data.running) {

        status.textContent = "Kiwix Running";
        status.className = "status running";

        openButton.disabled = false;

    } else {

        status.textContent = "Kiwix Stopped";
        status.className = "status stopped";

        openButton.disabled = true;
    }
}


function openLibrary() {
    window.open(
        "http://localhost:8080",
        "_blank"
    );
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

        let statusText;
        let statusClass;
        let actionButton;

        if (item.downloading) {

            statusText = "Downloading...";
            statusClass = "available";

            actionButton = `
                <button disabled>
                    Downloading...
                </button>
            `;

        } else if (item.installed) {

            statusText = "Installed";
            statusClass = "installed";

            actionButton = `
                <button
                    onclick="removeCollection('${item.id}')"
                >
                    Remove
                </button>
            `;

        } else {

            statusText = "Available";
            statusClass = "available";

            actionButton = `
                <button
                    onclick="installCollection('${item.id}')"
                >
                    Install
                </button>
            `;
        }

        card.innerHTML = `
            <h3>${item.name}</h3>

            <p>${item.size}</p>

            <p class="${statusClass}">
                ${statusText}
            </p>

            ${actionButton}
        `;

        library.appendChild(card);
    }
}

async function installCollection(id) {
    await fetch(
        `/api/library/install/${id}`,
        { method: "POST" }
    );

    await loadLibrary();
}


async function removeCollection(id) {

    const confirmed = confirm(
        "Remove this offline collection?"
    );

    if (!confirmed) {
        return;
    }

    await fetch(
        `/api/library/remove/${id}`,
        { method: "POST" }
    );

    await loadLibrary();
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

setInterval(() => {
    loadStatus();
    loadLibrary();
}, 5000);
