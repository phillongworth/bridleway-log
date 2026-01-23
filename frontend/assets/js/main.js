// Bridleway Log - Main JavaScript

const API_BASE = '/api';

// Path type colors (footpaths excluded from application)
const PATH_COLORS = {
    'Bridleway': '#3498db',
    'Restricted Byway': '#9b59b6',
    'BOAT': '#27ae60',
    'default': '#95a5a6'
};

// Coverage colors
const RIDDEN_COLOR = '#22c55e';  // Green for ridden
const NOT_RIDDEN_COLOR = '#ef4444';  // Red for not ridden
const FILTERED_COLOR = '#3b82f6';  // Blue for filtered paths (ridden only / not ridden only)
const RIDE_TRACE_COLOR = '#f97316';  // Orange for GPX ride traces

// State
let map;
let pathsLayer;
let ridesLayer;  // Layer group for ride traces
let rideData = {};  // Store ride GeoJSON features by ID
let rideLayers = {};  // Store individual ride layers by ID
let useImperial = false;
let colorByRidden = true;  // Toggle between coverage and path type coloring
let currentRiddenFilter = 'all';  // Track current ridden filter for styling

// Initialize application
document.addEventListener('DOMContentLoaded', () => {
    initMap();
    loadFilters();
    loadStats();
    loadPaths();
    loadRides();
    setupEventListeners();
});

function initMap() {
    // Center on Calderdale area
    map = L.map('map').setView([53.765, -1.99], 12);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://openstreetmap.org/copyright">OpenStreetMap</a>'
    }).addTo(map);

    pathsLayer = L.geoJSON(null, {
        style: styleFeature,
        onEachFeature: onEachFeature
    }).addTo(map);

    // Layer group for ride traces (on top of paths)
    ridesLayer = L.layerGroup().addTo(map);

    addLegend();
}

function styleFeature(feature) {
    const props = feature.properties;
    const isRidden = props.is_ridden || false;
    const coverage = props.coverage_fraction || 0;

    // Color based on ridden status with coverage affecting opacity
    if (colorByRidden) {
        // Use blue when filtering by specific ridden status for clear distinction
        if (currentRiddenFilter === 'ridden' || currentRiddenFilter === 'not_ridden') {
            return {
                color: FILTERED_COLOR,
                weight: 3,
                opacity: 0.8
            };
        }

        const baseColor = isRidden ? RIDDEN_COLOR : NOT_RIDDEN_COLOR;
        // Vary opacity based on coverage (minimum 0.4 for visibility)
        const opacity = isRidden ? (0.5 + (coverage * 0.5)) : 0.7;

        return {
            color: baseColor,
            weight: 3,
            opacity: opacity
        };
    } else {
        // Original path type coloring
        const pathType = props.path_type || 'default';
        return {
            color: PATH_COLORS[pathType] || PATH_COLORS.default,
            weight: 3,
            opacity: 0.8
        };
    }
}

function onEachFeature(feature, layer) {
    const props = feature.properties;
    const length = formatDistance(props.length_km);
    const coverage = props.coverage_fraction ? (props.coverage_fraction * 100).toFixed(0) : '0';
    const lastRidden = props.last_ridden_date
        ? new Date(props.last_ridden_date).toLocaleDateString()
        : 'Never';

    const content = `
        <div class="path-popup-content">
            <div class="popup-row">
                <span class="popup-label">Name:</span>
                <strong>${props.name || 'Unnamed'}</strong>
            </div>
            <div class="popup-row">
                <span class="popup-label">Type:</span>
                <span>${props.path_type || 'Unknown'}</span>
            </div>
            <div class="popup-row">
                <span class="popup-label">Route Code:</span>
                <span>${props.route_code || '-'}</span>
            </div>
            <div class="popup-row">
                <span class="popup-label">Length:</span>
                <span>${length}</span>
            </div>
            <div class="popup-row popup-divider">
                <span class="popup-label">Ridden:</span>
                <span class="${props.is_ridden ? 'status-ridden' : 'status-not-ridden'}">
                    ${props.is_ridden ? 'Yes' : 'No'}
                </span>
            </div>
            <div class="popup-row">
                <span class="popup-label">Coverage:</span>
                <span>${coverage}%</span>
            </div>
            <div class="popup-row">
                <span class="popup-label">Last Ridden:</span>
                <span>${lastRidden}</span>
            </div>
        </div>
    `;

    layer.bindPopup(content);
}

function addLegend() {
    const legend = L.control({ position: 'bottomright' });

    legend.onAdd = function() {
        const div = L.DomUtil.create('div', 'legend');
        div.innerHTML = `
            <strong>Coverage Status</strong><br>
            <div class="legend-item">
                <span class="legend-color" style="background: ${RIDDEN_COLOR}"></span>
                <span>Ridden</span>
            </div>
            <div class="legend-item">
                <span class="legend-color" style="background: ${NOT_RIDDEN_COLOR}"></span>
                <span>Not Ridden</span>
            </div>
            <div class="legend-item">
                <span class="legend-color" style="background: ${FILTERED_COLOR}"></span>
                <span>Filtered</span>
            </div>
            <hr style="margin: 8px 0; border: none; border-top: 1px solid #ddd;">
            <strong>GPX Traces</strong><br>
            <div class="legend-item">
                <span class="legend-color" style="background: ${RIDE_TRACE_COLOR}"></span>
                <span>Ride Track</span>
            </div>
            <hr style="margin: 8px 0; border: none; border-top: 1px solid #ddd;">
            <strong>Path Types</strong><br>
        `;

        for (const [type, color] of Object.entries(PATH_COLORS)) {
            if (type === 'default') continue;
            div.innerHTML += `
                <div class="legend-item">
                    <span class="legend-color" style="background: ${color}"></span>
                    <span>${type}</span>
                </div>
            `;
        }

        return div;
    };

    legend.addTo(map);
}

async function loadFilters() {
    try {
        const [areasRes, typesRes] = await Promise.all([
            fetch(`${API_BASE}/areas`),
            fetch(`${API_BASE}/path-types`)
        ]);

        const areasData = await areasRes.json();
        const typesData = await typesRes.json();

        const areaFilters = document.getElementById('area-filters');
        areaFilters.innerHTML = areasData.areas.map(area => `
            <label>
                <input type="checkbox" name="area" value="${area}">
                ${area}
            </label>
        `).join('');

        const typeFilters = document.getElementById('type-filters');
        typeFilters.innerHTML = typesData.path_types.map(type => `
            <label>
                <input type="checkbox" name="path_type" value="${type}">
                ${type}
            </label>
        `).join('');
    } catch (err) {
        console.error('Error loading filters:', err);
    }
}

async function loadStats() {
    const panel = document.getElementById('stats-panel');

    try {
        const res = await fetch(`${API_BASE}/stats`);
        const stats = await res.json();

        const totalLength = formatDistance(stats.total_length_km);
        const riddenLength = formatDistance(stats.ridden_length_km);
        const notRiddenLength = formatDistance(stats.not_ridden_length_km);

        // Calculate overall coverage percentage
        const overallCoverage = stats.total_paths > 0
            ? ((stats.ridden_paths / stats.total_paths) * 100).toFixed(1)
            : '0.0';

        let html = `
            <div class="stat-row">
                <span class="stat-label">Total Paths</span>
                <span class="stat-value">${stats.total_paths.toLocaleString()}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Total Length</span>
                <span class="stat-value">${totalLength}</span>
            </div>
            <div class="stat-row stat-highlight">
                <span class="stat-label">Overall Coverage</span>
                <span class="stat-value">${overallCoverage}%</span>
            </div>
            <div class="stat-group">
                <div class="stat-group-title">Coverage</div>
                <div class="stat-row">
                    <span class="stat-label status-ridden">Ridden</span>
                    <span class="stat-value">${stats.ridden_paths} (${riddenLength})</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label status-not-ridden">Not Ridden</span>
                    <span class="stat-value">${stats.not_ridden_paths} (${notRiddenLength})</span>
                </div>
            </div>
        `;

        if (Object.keys(stats.by_type).length > 0) {
            html += '<div class="stat-group"><div class="stat-group-title">By Type</div>';
            for (const [type, data] of Object.entries(stats.by_type)) {
                const length = formatDistance(data.length_km);
                const riddenCount = data.ridden_count || 0;
                const typeRiddenLength = formatDistance(data.ridden_length_km || 0);
                html += `
                    <div class="stat-row">
                        <span class="stat-label">${type}</span>
                        <span class="stat-value">${data.count} (${length})</span>
                    </div>
                    <div class="stat-row stat-subrow">
                        <span class="stat-label">Ridden</span>
                        <span class="stat-value">${riddenCount} (${typeRiddenLength})</span>
                    </div>
                `;
            }
            html += '</div>';
        }

        panel.innerHTML = html;
    } catch (err) {
        console.error('Error loading stats:', err);
        panel.innerHTML = '<p>Error loading statistics</p>';
    }
}

async function loadPaths() {
    const selectedAreas = Array.from(
        document.querySelectorAll('#area-filters input[type="checkbox"]:checked')
    ).map(cb => cb.value);

    const selectedTypes = Array.from(
        document.querySelectorAll('#type-filters input[type="checkbox"]:checked')
    ).map(cb => cb.value);

    const riddenFilter = document.querySelector('input[name="ridden"]:checked')?.value || 'all';
    const minCoverage = parseInt(document.getElementById('coverage-slider').value) / 100;

    // Update global state for styling
    currentRiddenFilter = riddenFilter;

    const btn = document.getElementById('apply-filters');

    btn.disabled = true;
    btn.textContent = 'Loading...';

    try {
        const params = new URLSearchParams();
        selectedAreas.forEach(area => params.append('area', area));
        selectedTypes.forEach(type => params.append('path_type', type));

        // Add ridden filter
        if (riddenFilter === 'ridden') {
            params.append('ridden', 'true');
        } else if (riddenFilter === 'not_ridden') {
            params.append('ridden', 'false');
        }

        // Add min coverage filter
        if (minCoverage > 0) {
            params.append('min_coverage', minCoverage.toString());
        }

        const url = `${API_BASE}/paths${params.toString() ? '?' + params.toString() : ''}`;
        const res = await fetch(url);
        const data = await res.json();

        pathsLayer.clearLayers();
        pathsLayer.addData(data);

        if (data.features.length > 0) {
            map.fitBounds(pathsLayer.getBounds(), { padding: [20, 20] });
        }
    } catch (err) {
        console.error('Error loading paths:', err);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Apply Filters';
    }
}

async function loadRides() {
    const panel = document.getElementById('rides-panel');

    try {
        // Fetch both ride list and geometries
        const [ridesRes, geoRes] = await Promise.all([
            fetch(`${API_BASE}/rides`),
            fetch(`${API_BASE}/rides/geojson`)
        ]);

        const data = await ridesRes.json();
        const geoData = await geoRes.json();

        // Clear existing ride layers
        ridesLayer.clearLayers();
        rideLayers = {};
        rideData = {};

        // Index GeoJSON features by ride ID
        for (const feature of geoData.features) {
            rideData[feature.properties.id] = feature;
        }

        if (data.rides.length === 0) {
            panel.innerHTML = '<p class="empty-text">No rides uploaded yet</p>';
            return;
        }

        let html = `
            <div class="rides-header">
                <div class="rides-summary">${data.total} ride(s)</div>
                <label class="rides-select-all">
                    <input type="checkbox" id="rides-select-all" checked>
                    <span>Show all</span>
                </label>
            </div>
        `;
        html += '<div class="rides-list">';

        for (const ride of data.rides) {
            const date = ride.date_recorded
                ? new Date(ride.date_recorded).toLocaleDateString()
                : 'Unknown date';
            const distance = formatDistance(ride.distance_km);

            html += `
                <div class="ride-item" data-id="${ride.id}">
                    <label class="ride-checkbox">
                        <input type="checkbox" class="ride-visibility" data-ride-id="${ride.id}" checked>
                    </label>
                    <div class="ride-info">
                        <div class="ride-filename">${ride.filename}</div>
                        <div class="ride-meta">${date} - ${distance}</div>
                    </div>
                    <button class="ride-delete" onclick="deleteRide(${ride.id})" title="Delete ride">
                        &times;
                    </button>
                </div>
            `;

            // Create layer for this ride if we have geometry
            if (rideData[ride.id]) {
                const layer = L.geoJSON(rideData[ride.id], {
                    style: {
                        color: RIDE_TRACE_COLOR,
                        weight: 4,
                        opacity: 0.85
                    },
                    onEachFeature: (feature, lyr) => {
                        const props = feature.properties;
                        const rideDate = props.date_recorded
                            ? new Date(props.date_recorded).toLocaleDateString()
                            : 'Unknown date';
                        const rideDist = formatDistance(props.distance_km);
                        const elevation = props.elevation_gain_m
                            ? `${props.elevation_gain_m.toFixed(0)}m`
                            : '-';

                        lyr.bindPopup(`
                            <div class="ride-popup-content">
                                <strong>${props.filename}</strong><br>
                                Date: ${rideDate}<br>
                                Distance: ${rideDist}<br>
                                Elevation: ${elevation}
                            </div>
                        `);
                    }
                });
                rideLayers[ride.id] = layer;
                ridesLayer.addLayer(layer);
            }
        }

        html += '</div>';
        panel.innerHTML = html;

        // Add event listeners for ride visibility
        setupRideVisibilityListeners();
    } catch (err) {
        console.error('Error loading rides:', err);
        panel.innerHTML = '<p>Error loading rides</p>';
    }
}

function setupRideVisibilityListeners() {
    // Individual ride checkboxes
    document.querySelectorAll('.ride-visibility').forEach(checkbox => {
        checkbox.addEventListener('change', (e) => {
            const rideId = parseInt(e.target.dataset.rideId);
            toggleRideVisibility(rideId, e.target.checked);
            updateSelectAllState();
        });
    });

    // Select all checkbox
    const selectAll = document.getElementById('rides-select-all');
    if (selectAll) {
        selectAll.addEventListener('change', (e) => {
            const checked = e.target.checked;
            document.querySelectorAll('.ride-visibility').forEach(checkbox => {
                checkbox.checked = checked;
                const rideId = parseInt(checkbox.dataset.rideId);
                toggleRideVisibility(rideId, checked);
            });
        });
    }
}

function toggleRideVisibility(rideId, visible) {
    const layer = rideLayers[rideId];
    if (!layer) return;

    if (visible) {
        if (!ridesLayer.hasLayer(layer)) {
            ridesLayer.addLayer(layer);
        }
    } else {
        if (ridesLayer.hasLayer(layer)) {
            ridesLayer.removeLayer(layer);
        }
    }
}

function updateSelectAllState() {
    const checkboxes = document.querySelectorAll('.ride-visibility');
    const selectAll = document.getElementById('rides-select-all');
    if (!selectAll || checkboxes.length === 0) return;

    const allChecked = Array.from(checkboxes).every(cb => cb.checked);
    const someChecked = Array.from(checkboxes).some(cb => cb.checked);

    selectAll.checked = allChecked;
    selectAll.indeterminate = someChecked && !allChecked;
}

async function uploadGPX() {
    const input = document.getElementById('gpx-input');
    const statusDiv = document.getElementById('upload-status');
    const uploadBtn = document.getElementById('upload-btn');

    if (!input.files || input.files.length === 0) {
        statusDiv.innerHTML = '<p class="error">Please select GPX file(s)</p>';
        return;
    }

    uploadBtn.disabled = true;
    uploadBtn.textContent = 'Uploading...';
    statusDiv.innerHTML = '<p>Uploading...</p>';

    const formData = new FormData();
    for (const file of input.files) {
        formData.append('files', file);
    }

    try {
        const res = await fetch(`${API_BASE}/rides/upload`, {
            method: 'POST',
            body: formData
        });

        const data = await res.json();

        let html = `<div class="upload-results">`;
        html += `<p>Processed ${data.total_files} file(s): ${data.imported} imported, ${data.skipped} skipped, ${data.errors} error(s)</p>`;

        for (const result of data.results) {
            const statusClass = result.status === 'imported' ? 'success'
                : result.status === 'skipped_duplicate' ? 'warning'
                : 'error';
            html += `<div class="upload-result ${statusClass}">${result.filename}: ${result.message}</div>`;
        }

        html += '</div>';
        statusDiv.innerHTML = html;

        // Clear input and file count
        input.value = '';
        document.getElementById('file-count').textContent = '';

        // Reload rides, stats, and paths
        if (data.imported > 0) {
            await Promise.all([loadRides(), loadStats(), loadPaths()]);
        }
    } catch (err) {
        console.error('Error uploading GPX:', err);
        statusDiv.innerHTML = `<p class="error">Upload failed: ${err.message}</p>`;
    } finally {
        uploadBtn.disabled = false;
        uploadBtn.textContent = 'Upload Now';
    }
}

async function deleteRide(rideId) {
    if (!confirm('Delete this ride? Coverage will be recalculated.')) {
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/rides/${rideId}`, {
            method: 'DELETE'
        });

        if (res.ok) {
            // Reload rides, stats, and paths
            await Promise.all([loadRides(), loadStats(), loadPaths()]);
        } else {
            const data = await res.json();
            alert(`Error deleting ride: ${data.detail || 'Unknown error'}`);
        }
    } catch (err) {
        console.error('Error deleting ride:', err);
        alert(`Error deleting ride: ${err.message}`);
    }
}

function setupEventListeners() {
    document.getElementById('apply-filters').addEventListener('click', loadPaths);

    document.getElementById('clear-filters').addEventListener('click', () => {
        // Clear checkboxes
        document.querySelectorAll('.checkbox-group input[type="checkbox"]').forEach(cb => {
            cb.checked = false;
        });
        // Reset radio to "all"
        document.querySelector('input[name="ridden"][value="all"]').checked = true;
        // Reset coverage slider
        document.getElementById('coverage-slider').value = 0;
        document.getElementById('coverage-value').textContent = '0%';

        loadPaths();
    });

    document.getElementById('unit-toggle').addEventListener('change', (e) => {
        useImperial = e.target.checked;
        loadStats();
        loadRides();
        // Refresh popups by reloading paths
        loadPaths();
    });

    // Coverage slider
    document.getElementById('coverage-slider').addEventListener('input', (e) => {
        document.getElementById('coverage-value').textContent = `${e.target.value}%`;
    });

    // File input - show selected file count
    document.getElementById('gpx-input').addEventListener('change', (e) => {
        const fileCount = e.target.files.length;
        const countDiv = document.getElementById('file-count');
        if (fileCount === 0) {
            countDiv.textContent = '';
        } else if (fileCount === 1) {
            countDiv.textContent = '1 file selected';
        } else {
            countDiv.textContent = `${fileCount} files selected`;
        }
    });

    // Upload button
    document.getElementById('upload-btn').addEventListener('click', uploadGPX);
}

function formatDistance(km) {
    if (km === null || km === undefined) return '-';

    if (useImperial) {
        const miles = km * 0.621371;
        return `${miles.toFixed(2)} mi`;
    }
    return `${km.toFixed(2)} km`;
}
