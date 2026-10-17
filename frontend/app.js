// Weather App Client Logic
const API_BASE = window.location.origin && window.location.origin.startsWith("http") && !window.location.origin.includes(":5500") && !window.location.origin.includes(":3000")
  ? window.location.origin
  : "http://127.0.0.1:8000";

// WMO Weather interpretation codes to emoji
const WMO_EMOJIS = {
  0: { icon: "☀️", text: "Clear sky" },
  1: { icon: "🌤️", text: "Mainly clear" },
  2: { icon: "⛅", text: "Partly cloudy" },
  3: { icon: "☁️", text: "Overcast" },
  45: { icon: "🌫️", text: "Fog" },
  48: { icon: "🌫️", text: "Depositing rime fog" },
  51: { icon: "🌦️", text: "Light drizzle" },
  53: { icon: "🌦️", text: "Moderate drizzle" },
  55: { icon: "🌧️", text: "Dense drizzle" },
  61: { icon: "🌧️", text: "Slight rain" },
  63: { icon: "🌧️", text: "Moderate rain" },
  65: { icon: "🌧️", text: "Heavy rain" },
  71: { icon: "🌨️", text: "Slight snow" },
  73: { icon: "🌨️", text: "Moderate snow" },
  75: { icon: "❄️", text: "Heavy snow" },
  80: { icon: "🌦️", text: "Rain showers" },
  81: { icon: "🌧️", text: "Moderate showers" },
  82: { icon: "⛈️", text: "Violent showers" },
  95: { icon: "⛈️", text: "Thunderstorm" },
  96: { icon: "⛈️", text: "Thunderstorm with hail" },
};

function getWeatherMeta(code, defaultDesc = "") {
  return WMO_EMOJIS[code] || { icon: "🌤️", text: defaultDesc || "Unknown" };
}

// Format helper to safely display numeric weather values or fallback to "N/A"
function fmt(value, suffix = "", round = false) {
  if (value === null || value === undefined || value === "") return "N/A";
  const num = Number(value);
  if (Number.isNaN(num)) return "N/A";
  const val = round ? Math.round(num) : num;
  return `${val}${suffix}`;
}

// DOM Elements
const searchForm = document.getElementById("searchForm");
const locationInput = document.getElementById("locationInput");
const latInput = document.getElementById("latInput");
const lonInput = document.getElementById("lonInput");
const modeSelect = document.getElementById("modeSelect");
const daysInput = document.getElementById("daysInput");
const startDateInput = document.getElementById("startDateInput");
const endDateInput = document.getElementById("endDateInput");
const searchBtn = document.getElementById("searchBtn");
const weatherResult = document.getElementById("weatherResult");
const historyContainer = document.getElementById("historyList");
const toast = document.getElementById("toast");

// Set default dates
const today = new Date();
const tomorrow = new Date(today);
tomorrow.setDate(today.getDate() + 1);
startDateInput.value = today.toISOString().split("T")[0];
endDateInput.value = tomorrow.toISOString().split("T")[0];

// Tab Switching (City vs Coords)
let activeSearchType = "city";
document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    activeSearchType = btn.dataset.tab;

    if (activeSearchType === "city") {
      document.getElementById("cityInputGroup").classList.remove("hidden");
      document.getElementById("coordsInputGroup").classList.add("hidden");
    } else {
      document.getElementById("cityInputGroup").classList.add("hidden");
      document.getElementById("coordsInputGroup").classList.remove("hidden");
    }
  });
});

// Mode Switching (Current vs Forecast vs Persist Range)
modeSelect.addEventListener("change", () => {
  const mode = modeSelect.value;
  if (mode === "current") {
    document.getElementById("forecastDaysGroup").classList.add("hidden");
    document.getElementById("dateRangeGroup").classList.add("hidden");
  } else if (mode === "forecast") {
    document.getElementById("forecastDaysGroup").classList.remove("hidden");
    document.getElementById("dateRangeGroup").classList.add("hidden");
  } else {
    document.getElementById("forecastDaysGroup").classList.add("hidden");
    document.getElementById("dateRangeGroup").classList.remove("hidden");
  }
});

// Show Toast
function showToast(message, isError = false) {
  toast.textContent = message;
  toast.className = isError ? "show error" : "show success";
  setTimeout(() => {
    toast.className = "";
  }, 3500);
}

// Search Handler
searchForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const mode = modeSelect.value;
  searchBtn.innerHTML = `<span class="spinner"></span> Loading...`;
  searchBtn.disabled = true;

  try {
    let url = "";
    let options = { method: "GET" };

    if (mode === "current") {
      url = `${API_BASE}/api/v1/weather/current?`;
      if (activeSearchType === "city") {
        if (!locationInput.value.trim()) throw new Error("Please enter a location name.");
        url += `location=${encodeURIComponent(locationInput.value.trim())}`;
      } else {
        url += `latitude=${latInput.value}&longitude=${lonInput.value}`;
      }
    } else if (mode === "forecast") {
      url = `${API_BASE}/api/v1/weather/forecast?days=${daysInput.value}&`;
      if (activeSearchType === "city") {
        if (!locationInput.value.trim()) throw new Error("Please enter a location name.");
        url += `location=${encodeURIComponent(locationInput.value.trim())}`;
      } else {
        url += `latitude=${latInput.value}&longitude=${lonInput.value}`;
      }
    } else {
      // POST search & persist to database
      url = `${API_BASE}/api/v1/weather/search`;
      const body = {
        start_date: startDateInput.value,
        end_date: endDateInput.value,
      };
      if (activeSearchType === "city") {
        if (!locationInput.value.trim()) throw new Error("Please enter a location name.");
        body.location = locationInput.value.trim();
      } else {
        body.latitude = parseFloat(latInput.value);
        body.longitude = parseFloat(lonInput.value);
      }
      options = {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      };
    }

    const res = await fetch(url, options);
    const data = await res.json();

    if (!res.ok) {
      const msg = data.error?.message || data.detail || "Failed to fetch weather data.";
      throw new Error(msg);
    }

    // Render result
    if (mode === "current") {
      renderCurrentWeather(data.data);
      showToast("Current weather retrieved!");
    } else if (mode === "forecast") {
      renderForecastWeather(data.data);
      showToast("Forecast loaded!");
    } else {
      renderPersistedWeather(data.data);
      showToast("Weather searched & saved to database!");
      loadHistory(); // refresh history
    }
  } catch (err) {
    showToast(err.message, true);
  } finally {
    searchBtn.innerHTML = `Search Weather`;
    searchBtn.disabled = false;
  }
});

// Renderers
function renderCurrentWeather(data) {
  data = { ...data, ...(data.weather || {}), latitude: data.latitude, longitude: data.longitude };
  const meta = getWeatherMeta(data.weather_code, data.weather_description);
  const coordsText = (data.latitude != null && data.longitude != null && !isNaN(data.latitude) && !isNaN(data.longitude))
    ? `${Number(data.latitude).toFixed(4)}°, ${Number(data.longitude).toFixed(4)}° • ${data.timezone || "UTC"}`
    : (data.timezone || "UTC");

  weatherResult.innerHTML = `
    <div class="weather-hero">
      <div>
        <div class="location-title">
          <h2>${data.location_name || "Coordinates"}</h2>
          ${data.country ? `<span class="country-badge">${data.country}</span>` : ""}
        </div>
        <div class="coords-sub">${coordsText}</div>
      </div>
      <div class="temp-large">
        <span class="weather-icon">${meta.icon}</span>
        <div>
          <div class="temperature-val">${fmt(data.temperature, data.temperature_unit || "°C", true)}</div>
          <div class="condition-text">${meta.text}</div>
        </div>
      </div>
    </div>
    <div class="metrics-grid">
      <div class="metric-item">
        <span class="metric-label">Feels Like</span>
        <span class="metric-value">${fmt(data.apparent_temperature, data.temperature_unit || "°C", true)}</span>
      </div>
      <div class="metric-item">
        <span class="metric-label">Humidity</span>
        <span class="metric-value">${fmt(data.relative_humidity, "%")}</span>
      </div>
      <div class="metric-item">
        <span class="metric-label">Wind</span>
        <span class="metric-value">${fmt(data.wind_speed, ` ${data.wind_speed_unit || "km/h"}`)}</span>
      </div>
      <div class="metric-item">
        <span class="metric-label">Precipitation</span>
        <span class="metric-value">${fmt(data.precipitation, " mm")}</span>
      </div>
    </div>
  `;
  weatherResult.classList.remove("hidden");
}

function renderForecastWeather(data) {
  data = { ...data, days: data.days || data.forecast?.days || data.forecast || [] };
  const days = Array.isArray(data.days) ? data.days : [];
  const firstDay = days[0] || {};
  const meta = getWeatherMeta(firstDay.weather_code, firstDay.weather_description);
  const coordsText = (data.latitude != null && data.longitude != null && !isNaN(data.latitude) && !isNaN(data.longitude))
    ? `${Number(data.latitude).toFixed(4)}°, ${Number(data.longitude).toFixed(4)}° • ${days.length} Days`
    : `${days.length} Days`;

  let daysHtml = days.map(d => {
    const dMeta = getWeatherMeta(d.weather_code, d.weather_description);
    const maxStr = fmt(d.temperature_max, "°", true);
    const minStr = fmt(d.temperature_min, "°", true);
    return `
      <div class="forecast-card">
        <div class="forecast-date">${d.date || "N/A"}</div>
        <div class="forecast-icon">${dMeta.icon}</div>
        <div class="forecast-temp">${maxStr} / ${minStr}</div>
        <div class="forecast-condition">${dMeta.text}</div>
      </div>
    `;
  }).join("");

  weatherResult.innerHTML = `
    <div class="weather-hero">
      <div>
        <div class="location-title">
          <h2>${data.location_name || "Forecast Area"}</h2>
          ${data.country ? `<span class="country-badge">${data.country}</span>` : ""}
        </div>
        <div class="coords-sub">${coordsText}</div>
      </div>
      <div class="temp-large">
        <span class="weather-icon">${meta.icon}</span>
        <div>
          <div class="temperature-val">${fmt(firstDay.temperature_max, "°C", true)}</div>
          <div class="condition-text">${meta.text}</div>
        </div>
      </div>
    </div>
    <h3 style="font-size: 0.95rem; margin-top: 1.5rem; color: var(--text-muted);">Daily Forecast:</h3>
    <div class="forecast-scroll">${daysHtml}</div>
  `;
  weatherResult.classList.remove("hidden");
}

function renderPersistedWeather(record) {
  const wd = record.weather_data || {};
  if (wd.days) {
    renderForecastWeather({
      location_name: record.location_name,
      country: record.country,
      latitude: record.latitude,
      longitude: record.longitude,
      days: wd.days,
    });
  } else {
    renderCurrentWeather({
      location_name: record.location_name,
      country: record.country,
      latitude: record.latitude,
      longitude: record.longitude,
      ...wd,
    });
  }
}

// Load Search History
async function loadHistory() {
  try {
    const res = await fetch(`${API_BASE}/api/v1/weather/history?limit=10`);
    if (!res.ok) return;
    const json = await res.json();
    const records = json.data?.items || [];

    if (records.length === 0) {
      historyContainer.innerHTML = `<p style="color: var(--text-dim); font-size: 0.9rem;">No search history records yet.</p>`;
      return;
    }

    historyContainer.innerHTML = records.map(r => `
      <div class="history-item">
        <div class="history-info">
          <span class="history-location">${r.location_name} ${r.country ? `(${r.country})` : ""}</span>
          <span class="history-dates">Range: ${r.start_date} → ${r.end_date}</span>
        </div>
        <div class="history-actions">
          <button class="btn-secondary" onclick="viewHistoryItem(${r.id})">View</button>
          <button class="btn-danger" onclick="deleteHistoryItem(${r.id})">Delete</button>
        </div>
      </div>
    `).join("");
  } catch (err) {
    console.error("Failed to load history:", err);
  }
}

// Global actions for history
window.viewHistoryItem = async function(id) {
  try {
    const res = await fetch(`${API_BASE}/api/v1/weather/history/${id}`);
    const json = await res.json();
    if (res.ok && json.data) {
      renderPersistedWeather(json.data);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  } catch (err) {
    showToast("Failed to load record details", true);
  }
};

window.deleteHistoryItem = async function(id) {
  if (!confirm("Are you sure you want to delete this weather record?")) return;
  try {
    const res = await fetch(`${API_BASE}/api/v1/weather/history/${id}`, { method: "DELETE" });
    if (res.ok) {
      showToast("Record deleted successfully");
      loadHistory();
    } else {
      showToast("Failed to delete record", true);
    }
  } catch (err) {
    showToast("Error deleting record", true);
  }
};

// Export Triggers
document.getElementById("exportCsvBtn").addEventListener("click", () => {
  window.open(`${API_BASE}/api/v1/weather/export?format=csv`, "_blank");
});

document.getElementById("exportJsonBtn").addEventListener("click", () => {
  window.open(`${API_BASE}/api/v1/weather/export?format=json`, "_blank");
});

document.getElementById("refreshHistoryBtn").addEventListener("click", loadHistory);

// Initialize on load
loadHistory();
