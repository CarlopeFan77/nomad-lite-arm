let libraryCollections = [];


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

    libraryCollections = data.collections;

    renderLibrary();
}


function renderLibrary() {
    const library = document.getElementById("library");

    const searchBox = document.getElementById(
        "library-search"
    );

    const query = searchBox
        ? searchBox.value.trim().toLowerCase()
        : "";

    const filtered = libraryCollections.filter((item) => {
        const text = [
            item.name,
            item.category,
            item.description,
            item.id,
        ]
            .join(" ")
            .toLowerCase();

        return text.includes(query);
    });

    library.innerHTML = "";

    if (filtered.length === 0) {
        library.innerHTML = `
            <div class="panel">
                No matching collections found.
            </div>
        `;

        return;
    }

    const categories = {};

    for (const item of filtered) {
        if (!categories[item.category]) {
            categories[item.category] = [];
        }

        categories[item.category].push(item);
    }

    for (const [category, items] of Object.entries(categories)) {

        const section = document.createElement("div");
        section.className = "library-category";

        const title = document.createElement("h3");
        title.className = "category-title";
        title.textContent = category;

        const grid = document.createElement("div");
        grid.className = "library-grid";

        section.appendChild(title);
        section.appendChild(grid);

        for (const item of items) {
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

                <p class="library-description">
                    ${item.description}
                </p>

                <div class="library-meta">
                    <span>${item.size}</span>

                    <span class="${statusClass}">
                        ${statusText}
                    </span>
                </div>

                ${actionButton}
            `;

            grid.appendChild(card);
        }

        library.appendChild(section);
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


function openLibrary() {
    window.open(
        "http://localhost:8080",
        "_blank"
    );
}


async function initialize() {
    await Promise.all([
        loadStatus(),
        loadLibrary(),
        loadSystem(),
    ]);
}


initialize();


setInterval(() => {
    loadStatus();
    loadLibrary();
}, 5000);
