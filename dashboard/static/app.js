let libraryCollections = [];
let educationCourses = [];

function formatBytes(bytes) {
    if (!bytes || bytes <= 0) {
        return "Size unavailable";
    }

    const mb = bytes / (1024 * 1024);

    if (mb < 1024) {
        return `${Math.round(mb)} MB`;
    }

    const gb = mb / 1024;

    return `${gb.toFixed(2)} GB`;
}

async function loadKiwixStatus() {
    const response = await fetch(
        "/api/kiwix/status"
    );

    const data = await response.json();

    const status =
        document.getElementById(
            "kiwix-status"
        );

    const openButton =
        document.getElementById(
            "open-library-button"
        );

    if (data.running) {
        status.textContent = "Running";
        status.className =
            "service-status installed";

        openButton.disabled = false;
    } else {
        status.textContent = "Stopped";
        status.className =
            "service-status available";

        openButton.disabled = true;
    }
}


async function loadEducationStatus() {
    const response = await fetch(
        "/api/education/status"
    );

    const data = await response.json();

    const status =
        document.getElementById(
            "education-status"
        );

    const openButton =
        document.getElementById(
            "open-education-button"
        );

    if (data.running) {
        status.textContent = "Running";
        status.className =
            "service-status installed";

        openButton.disabled = false;
    } else {
        status.textContent = "Stopped";
        status.className =
            "service-status available";

        openButton.disabled = true;
    }
}


async function loadSystem() {
    const response = await fetch(
        "/api/system"
    );

    const data = await response.json();

    document.getElementById(
        "system-info"
    ).textContent = data.output;
}


async function loadEducation() {
    const response = await fetch(
        "/api/education/library"
    );

    const data = await response.json();

    educationCourses = data.courses;

    renderEducation();
}


function renderEducation() {
    const container =
        document.getElementById(
            "education-library"
        );

    const searchBox =
        document.getElementById(
            "education-search"
        );

    const query = searchBox
        ? searchBox.value
            .trim()
            .toLowerCase()
        : "";

    const filtered =
        educationCourses.filter(
            (item) => {

                const text = [
                    item.name,
                    item.category,
                    item.description,
                    item.id,
                ]
                    .join(" ")
                    .toLowerCase();

                return text.includes(query);
            }
        );

    container.innerHTML = "";

    if (filtered.length === 0) {
        container.innerHTML = `
            <div class="panel">
                No matching courses found.
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

    for (
        const [category, items]
        of Object.entries(categories)
    ) {

        const section =
            document.createElement("div");

        section.className =
            "library-category";

        const title =
            document.createElement("h3");

        title.className =
            "category-title";

        title.textContent = category;

        const grid =
            document.createElement("div");

        grid.className =
            "library-grid";

        section.appendChild(title);
        section.appendChild(grid);

        for (const item of items) {

            const card =
                document.createElement("div");

            card.className =
                "library-card";

            let statusText;
            let statusClass;
            let button;

            if (item.downloading) {

                statusText = "Installing...";
                statusClass = "available";

                button = `
                    <button disabled>
                        Installing...
                    </button>
                `;

            } else if (item.installed) {

                statusText = "Installed";
                statusClass = "installed";

                button = `
                    <button
                        onclick="openEducation()"
                    >
                        Open Course
                    </button>
                `;

            } else {

                statusText = "Available";
                statusClass = "available";

                button = `
                    <button
                        onclick="
                            installEducation(
                                '${item.id}'
                            )
                        "
                    >
                        Install
                    </button>
                `;
            }

            const totalSize =
                formatBytes(item.total_bytes);

            const remainingSize =
                formatBytes(
                    item.remaining_bytes
                );

            let sizeText = totalSize;

            if (
                item.remaining_bytes > 0
                &&
                item.remaining_bytes
                    < item.total_bytes
            ) {
                sizeText =
                    `${remainingSize} needed`;
            }

            card.innerHTML = `
                <h3>${item.name}</h3>

                <p class="library-description">
                    ${item.description}
                </p>

                <div class="library-meta">

                    <span>
                        Approx. ${sizeText}
                    </span>

                    <span class="${statusClass}">
                        ${statusText}
                    </span>

                </div>

                <p class="course-resources">
                    ${item.resources} resources
                </p>

                ${button}
            `;

            grid.appendChild(card);
        }

        container.appendChild(section);
    }
}


async function installEducation(id) {
    await fetch(
        `/api/education/install/${id}`,
        {
            method: "POST"
        }
    );

    await loadEducation();
}


async function loadLibrary() {
    const response = await fetch(
        "/api/library"
    );

    const data = await response.json();

    libraryCollections =
        data.collections;

    renderLibrary();
}


function renderLibrary() {
    const library =
        document.getElementById(
            "library"
        );

    const searchBox =
        document.getElementById(
            "library-search"
        );

    const query = searchBox
        ? searchBox.value
            .trim()
            .toLowerCase()
        : "";

    const filtered =
        libraryCollections.filter(
            (item) => {

                const text = [
                    item.name,
                    item.category,
                    item.description,
                    item.id,
                ]
                    .join(" ")
                    .toLowerCase();

                return text.includes(query);
            }
        );

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

        categories[item.category].push(
            item
        );
    }

    for (
        const [category, items]
        of Object.entries(categories)
    ) {

        const section =
            document.createElement("div");

        section.className =
            "library-category";

        const title =
            document.createElement("h3");

        title.className =
            "category-title";

        title.textContent = category;

        const grid =
            document.createElement("div");

        grid.className =
            "library-grid";

        section.appendChild(title);
        section.appendChild(grid);

        for (const item of items) {

            const card =
                document.createElement("div");

            card.className =
                "library-card";

            let statusText;
            let statusClass;
            let actionButton;

            if (item.downloading) {

                statusText =
                    "Downloading...";

                statusClass =
                    "available";

                actionButton = `
                    <button disabled>
                        Downloading...
                    </button>
                `;

            } else if (item.installed) {

                statusText =
                    "Installed";

                statusClass =
                    "installed";

                actionButton = `
                    <button
                        onclick="
                            removeCollection(
                                '${item.id}'
                            )
                        "
                    >
                        Remove
                    </button>
                `;

            } else {

                statusText =
                    "Available";

                statusClass =
                    "available";

                actionButton = `
                    <button
                        onclick="
                            installCollection(
                                '${item.id}'
                            )
                        "
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

                    <span>
                        ${item.size}
                    </span>

                    <span
                        class="${statusClass}"
                    >
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
        {
            method: "POST"
        }
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
        {
            method: "POST"
        }
    );

    await loadLibrary();
}


async function startKiwix() {
    await fetch(
        "/api/kiwix/start",
        {
            method: "POST"
        }
    );

    await loadKiwixStatus();
}


async function stopKiwix() {
    await fetch(
        "/api/kiwix/stop",
        {
            method: "POST"
        }
    );

    await loadKiwixStatus();
}


async function startEducation() {
    await fetch(
        "/api/education/start",
        {
            method: "POST"
        }
    );

    await loadEducationStatus();
}


async function stopEducation() {
    await fetch(
        "/api/education/stop",
        {
            method: "POST"
        }
    );

    await loadEducationStatus();
}


function openLibrary() {
    window.open(
        "http://localhost:8080",
        "_blank"
    );
}


function openEducation() {
    window.open(
        "http://localhost:8082",
        "_blank"
    );
}


async function initialize() {
    await Promise.all([
        loadKiwixStatus(),
        loadEducationStatus(),
        loadEducation(),
        loadLibrary(),
        loadSystem(),
    ]);
}


initialize();


setInterval(() => {
    loadKiwixStatus();
    loadEducationStatus();
    loadEducation();
    loadLibrary();
}, 5000);
