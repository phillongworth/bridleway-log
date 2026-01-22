// Bridleway Log - Main JavaScript

const API_BASE = '/api';

// Path type colors
const PATH_COLORS = {
    'Footpath': '#e74c3c',
    'Bridleway': '#3498db',
    'Restricted Byway': '#9b59b6',
    'BOAT': '#27ae60',
    'default': '#95a5a6'
};

// State
let map;
let pathsLayer;
let useImperial = false;

// Initialize application
document.addEventListener('DOMContentLoaded', () => {
    initMap();
    loadFilters();
    loadStats();
    loadPaths();
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

    addLegend();
}

function styleFeature(feature) {
    const pathType = feature.properties.path_type || 'default';
    return {
        color: PATH_COLORS[pathType] || PATH_COLORS.default,
        weight: 3,
        opacity: 0.8
    };
}

function onEachFeature(feature, layer) {
    const props = feature.properties;
    const length = formatDistance(props.length_km);

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
        </div>
    `;

    layer.bindPopup(content);
}

function addLegend() {
    const legend = L.control({ position: 'bottomright' });

    legend.onAdd = function() {
        const div = L.DomUtil.create('div', 'legend');
        div.innerHTML = '<strong>Path Types</strong><br>';

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

        let html = `
            <div class="stat-row">
                <span class="stat-label">Total Paths</span>
                <span class="stat-value">${stats.total_paths.toLocaleString()}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Total Length</span>
                <span class="stat-value">${totalLength}</span>
            </div>
        `;

        if (Object.keys(stats.by_type).length > 0) {
            html += '<div class="stat-group"><div class="stat-group-title">By Type</div>';
            for (const [type, data] of Object.entries(stats.by_type)) {
                const length = formatDistance(data.length_km);
                html += `
                    <div class="stat-row">
                        <span class="stat-label">${type}</span>
                        <span class="stat-value">${data.count} (${length})</span>
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

    const btn = document.getElementById('apply-filters');

    btn.disabled = true;
    btn.textContent = 'Loading...';

    try {
        const params = new URLSearchParams();
        selectedAreas.forEach(area => params.append('area', area));
        selectedTypes.forEach(type => params.append('path_type', type));

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

function setupEventListeners() {
    document.getElementById('apply-filters').addEventListener('click', loadPaths);

    document.getElementById('clear-filters').addEventListener('click', () => {
        document.querySelectorAll('.checkbox-group input[type="checkbox"]').forEach(cb => {
            cb.checked = false;
        });
        loadPaths();
    });

    document.getElementById('unit-toggle').addEventListener('change', (e) => {
        useImperial = e.target.checked;
        loadStats();
        // Refresh popups by reloading paths
        loadPaths();
    });
}

function formatDistance(km) {
    if (km === null || km === undefined) return '-';

    if (useImperial) {
        const miles = km * 0.621371;
        return `${miles.toFixed(2)} mi`;
    }
    return `${km.toFixed(2)} km`;
}
