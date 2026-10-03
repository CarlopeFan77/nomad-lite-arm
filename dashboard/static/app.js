let libraryCollections = [];
let educationCourses = [];

let mapsUrl =
    "http://localhost:8083/map";

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


async function loadMapsStatus() {

    const response = await fetch(
        "/api/maps/status"
    );

    const data = await response.json();

    const status =
        document.getElementById(
            "maps-status"
        );


    if (data.url) {
        mapsUrl = data.url;
    }


    if (data.running) {

        if (data.state_name) {

            status.textContent =
                `Running — ${data.state_name}`;

        } else {

            status.textContent =
                "Running";
        }

        status.className =
            "service-status installed";

    } else {

        status.textContent =
            "Stopped";

        status.className =
            "service-status available";
    }
}


async function loadMapStates() {

    const response = await fetch(
        "/api/maps/states"
    );

    const data = await response.json();

    const container =
        document.getElementById(
            "maps-states"
        );


    const previousSelect =
        document.getElementById(
            "map-state-select"
        );

    const previousSelection =
        previousSelect
            ? previousSelect.value
            : null;


    container.replaceChildren();


    const states = (
        data.states || []
    ).sort(
        (a, b) =>
            a.name.localeCompare(
                b.name
            )
    );


    if (states.length === 0) {

        const message =
            document.createElement(
                "p"
            );

        message.textContent =
            "No offline maps installed.";

        container.appendChild(
            message
        );

        return;
    }


    const count =
        document.createElement(
            "div"
        );

    count.className =
        "map-state-count";

    count.textContent =
        states.length === 1
            ? "1 state installed"
            : `${states.length} states installed`;

    container.appendChild(
        count
    );


    /*
     * With three or fewer states,
     * show each one directly.
     */
    if (states.length <= 3) {

        for (const state of states) {

            const row =
                document.createElement(
                    "div"
                );

            row.className =
                "map-state-row";


            const info =
                document.createElement(
                    "div"
                );


            const name =
                document.createElement(
                    "strong"
                );

            name.textContent =
                state.name;


            const profile =
                document.createElement(
                    "span"
                );

            profile.className =
                "map-state-profile";

            profile.textContent =
                `${state.profile} installed`;


            info.appendChild(
                name
            );

            info.appendChild(
                profile
            );


            const button =
                document.createElement(
                    "button"
                );

            button.textContent =
                "Open";

            button.addEventListener(
                "click",
                () => {
                    openStateMap(
                        state.id
                    );
                }
            );


            row.appendChild(
                info
            );

            row.appendChild(
                button
            );

            container.appendChild(
                row
            );
        }

        return;
    }


    /*
     * Four or more states:
     * switch to a compact selector.
     */

    const controls =
        document.createElement(
            "div"
        );

    controls.className =
        "map-state-controls";


    const select =
        document.createElement(
            "select"
        );

    select.id =
        "map-state-select";

    select.className =
        "map-state-select";


    for (const state of states) {

        const option =
            document.createElement(
                "option"
            );

        option.value =
            state.id;

        option.textContent =
            `${state.name} — ${state.profile}`;

        select.appendChild(
            option
        );
    }


    if (
        previousSelection
        && states.some(
            state =>
                state.id
                === previousSelection
        )
    ) {

        select.value =
            previousSelection;
    }


    const button =
        document.createElement(
            "button"
        );

    button.textContent =
        "Open Map";

    button.addEventListener(
        "click",
        () => {
            openStateMap(
                select.value
            );
        }
    );


    controls.appendChild(
        select
    );

    controls.appendChild(
        button
    );

    container.appendChild(
        controls
    );
}


async function openStateMap(
    stateId
) {

    /*
     * Open a blank tab immediately so the
     * browser treats this as a user click
     * rather than blocking it as a popup.
     */
    const mapWindow =
        window.open(
            "about:blank",
            "_blank"
        );


    const response = await fetch(
        "/api/maps/start/"
        + encodeURIComponent(
            stateId
        ),
        {
            method: "POST"
        }
    );

    const data =
        await response.json();


    if (data.success === false) {

        if (mapWindow) {
            mapWindow.close();
        }

        alert(
            data.output
            || "Could not start Maps."
        );

        return;
    }


    await loadMapsStatus();


    if (mapWindow) {

        mapWindow.location.href =
            mapsUrl;

    } else {

        window.location.href =
            mapsUrl;
    }
}


async function stopMaps() {

    await fetch(
        "/api/maps/stop",
        {
            method: "POST"
        }
    );

    await loadMapsStatus();
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
        loadMapsStatus(),
        loadMapStates(),
        loadEducation(),
        loadLibrary(),
        loadSystem(),
    ]);
}


initialize();


setInterval(() => {
    loadKiwixStatus();
    loadEducationStatus();
    loadMapsStatus();
    loadEducation();
    loadLibrary();
}, 5000);

setInterval(() => {
    loadMapStates();
}, 30000);
