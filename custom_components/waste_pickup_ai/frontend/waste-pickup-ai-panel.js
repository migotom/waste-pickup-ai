class WastePickupAIPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._state = null;
    this._loading = false;
    this._message = "";
    this._error = "";
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._state && !this._loading) {
      this._load();
    }
  }

  connectedCallback() {
    this._render();
  }

  async _load() {
    if (!this._hass) return;
    this._loading = true;
    this._error = "";
    this._render();
    try {
      this._state = await this._hass.callApi("GET", "waste_pickup_ai/schedule");
    } catch (err) {
      this._error = this._formatError(err);
    } finally {
      this._loading = false;
      this._render();
    }
  }

  async _scan() {
    const labels = getLabels(this._hass);
    const fileInput = this.shadowRoot.querySelector("#image");
    const yearInput = this.shadowRoot.querySelector("#year");
    const file = fileInput.files[0];
    if (!file) {
      this._error = labels.selectFile;
      this._render();
      return;
    }
    this._loading = true;
    this._error = "";
    this._message = "";
    this._render();
    try {
      const dataUrl = await readFileAsDataURL(file);
      const year = parseInt(yearInput.value, 10);
      await this._hass.callApi("POST", "waste_pickup_ai/scan", {
        filename: file.name,
        data_url: dataUrl,
        year: Number.isFinite(year) ? year : undefined,
      });
      this._message = labels.scanDone;
      await this._load();
    } catch (err) {
      this._error = this._formatError(err);
    } finally {
      this._loading = false;
      this._render();
    }
  }

  async _saveCell(input) {
    const rowIndex = parseInt(input.dataset.rowIndex, 10);
    const month = input.dataset.month;
    try {
      await this._hass.callApi("POST", "waste_pickup_ai/cell", {
        row_index: rowIndex,
        month,
        value: input.value,
      });
      await this._load();
    } catch (err) {
      this._error = this._formatError(err);
      this._render();
    }
  }

  async _activate() {
    const labels = getLabels(this._hass);
    const yearInput = this.shadowRoot.querySelector("#year");
    const year = parseInt(yearInput.value, 10);
    if (!Number.isFinite(year)) {
      this._error = labels.enterYear;
      this._render();
      return;
    }
    if (!window.confirm(labels.activateConfirm)) {
      return;
    }
    this._loading = true;
    this._error = "";
    this._message = "";
    this._render();
    try {
      await this._hass.callApi("POST", "waste_pickup_ai/activate", { year });
      this._message = labels.scheduleActive;
      await this._load();
    } catch (err) {
      this._error = this._formatError(err);
    } finally {
      this._loading = false;
      this._render();
    }
  }

  async _testNotification() {
    const labels = getLabels(this._hass);
    try {
      await this._hass.callApi("POST", "waste_pickup_ai/test_notification", {});
      this._message = labels.testSent;
      this._error = "";
      this._render();
    } catch (err) {
      this._error = this._formatError(err);
      this._render();
    }
  }

  async _saveOptions() {
    const labels = getLabels(this._hass);
    const checkedTargets = Array.from(
      this.shadowRoot.querySelectorAll("input[name='notify-target']:checked")
    ).map((input) => input.value);
    const customTargets = splitTargets(this.shadowRoot.querySelector("#custom-notify")?.value || "");
    const notifyTargets = uniqueValues([...checkedTargets, ...customTargets]);

    this._loading = true;
    this._error = "";
    this._message = "";
    this._render();
    try {
      await this._hass.callApi("POST", "waste_pickup_ai/options", {
        notify_targets: notifyTargets,
        morning_time: this.shadowRoot.querySelector("#morning-time")?.value,
        evening_time: this.shadowRoot.querySelector("#evening-time")?.value,
        annual_scan_reminder_time: this.shadowRoot.querySelector("#annual-time")?.value,
      });
      this._message = labels.optionsSaved;
      await this._load();
    } catch (err) {
      this._error = this._formatError(err);
    } finally {
      this._loading = false;
      this._render();
    }
  }

  _draft() {
    return this._state && this._state.draft_schedule;
  }

  _active() {
    return this._state && this._state.active_schedule;
  }

  _formatError(err) {
    const labels = getLabels(this._hass);
    if (!err) return labels.unknownError;
    if (typeof err === "string") return err;
    if (err.message) return err.message;
    return JSON.stringify(err);
  }

  _render() {
    const draft = this._draft();
    const active = this._active();
    const labels = getLabels(this._hass);
    const status = (this._state && this._state.status) || {};
    const year = (draft && draft.year) || (active && active.year) || new Date().getFullYear();
    const rows = (draft && draft.rows) || [];
    const events = (this._state && this._state.events) || [];
    const nextPickup = this._state && this._state.next_pickup;
    const options = (this._state && this._state.options) || {};
    const availableNotifyTargets = (this._state && this._state.available_notify_targets) || [];

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          min-height: 100vh;
          background: var(--primary-background-color);
          color: var(--primary-text-color);
          font-family: var(--paper-font-body1_-_font-family, system-ui, sans-serif);
        }
        .wrap {
          max-width: 1280px;
          margin: 0 auto;
          padding: 24px;
        }
        header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 16px;
          margin-bottom: 20px;
        }
        h1 {
          margin: 0;
          font-size: 28px;
          font-weight: 600;
          letter-spacing: 0;
        }
        h2 {
          margin: 28px 0 12px;
          font-size: 18px;
          font-weight: 600;
          letter-spacing: 0;
        }
        .status {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          align-items: center;
        }
        .pill {
          border: 1px solid var(--divider-color);
          border-radius: 999px;
          padding: 6px 10px;
          background: var(--card-background-color);
          font-size: 13px;
        }
        .toolbar {
          display: grid;
          grid-template-columns: minmax(220px, 1fr) 120px auto auto auto;
          gap: 10px;
          align-items: end;
          padding: 14px;
          border: 1px solid var(--divider-color);
          border-radius: 8px;
          background: var(--card-background-color);
        }
        label {
          display: grid;
          gap: 6px;
          font-size: 12px;
          color: var(--secondary-text-color);
        }
        input {
          min-height: 36px;
          box-sizing: border-box;
          border: 1px solid var(--divider-color);
          border-radius: 6px;
          padding: 7px 9px;
          background: var(--input-fill-color, var(--primary-background-color));
          color: var(--primary-text-color);
          font: inherit;
        }
        button {
          min-height: 36px;
          border: 0;
          border-radius: 6px;
          padding: 8px 12px;
          background: var(--primary-color);
          color: var(--text-primary-color);
          font: inherit;
          cursor: pointer;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          gap: 7px;
          white-space: nowrap;
        }
        button.secondary {
          background: var(--secondary-background-color);
          color: var(--primary-text-color);
          border: 1px solid var(--divider-color);
        }
        button.danger {
          background: var(--error-color, #db4437);
          color: var(--text-primary-color);
        }
        button:disabled {
          opacity: 0.55;
          cursor: progress;
        }
        .activation-warning {
          margin: 14px 0 0;
          padding: 12px 14px;
          border: 1px solid var(--error-color, #db4437);
          border-left-width: 5px;
          border-radius: 8px;
          background: var(--card-background-color);
        }
        .activation-warning strong {
          display: block;
          margin-bottom: 4px;
        }
        .settings {
          margin-top: 16px;
          padding: 14px;
          border: 1px solid var(--divider-color);
          border-radius: 8px;
          background: var(--card-background-color);
        }
        .settings-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
          gap: 10px;
          align-items: end;
        }
        .notify-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
          gap: 8px;
          margin: 10px 0;
        }
        .checkbox {
          display: flex;
          align-items: center;
          gap: 8px;
          min-height: 34px;
          padding: 7px 9px;
          border: 1px solid var(--divider-color);
          border-radius: 6px;
          color: var(--primary-text-color);
          background: var(--primary-background-color);
          font-size: 13px;
        }
        .checkbox input {
          min-height: auto;
          width: 16px;
          height: 16px;
          padding: 0;
        }
        .notice {
          margin: 14px 0 0;
          padding: 10px 12px;
          border-radius: 6px;
          background: var(--warning-color, #f5a623);
          color: var(--text-primary-color);
        }
        .error {
          margin: 14px 0 0;
          padding: 10px 12px;
          border-radius: 6px;
          background: var(--error-color, #db4437);
          color: var(--text-primary-color);
        }
        .table-wrap {
          overflow: auto;
          border: 1px solid var(--divider-color);
          border-radius: 8px;
          background: var(--card-background-color);
        }
        table {
          width: 100%;
          min-width: 960px;
          border-collapse: collapse;
        }
        th, td {
          border-bottom: 1px solid var(--divider-color);
          border-right: 1px solid var(--divider-color);
          padding: 8px;
          vertical-align: middle;
        }
        th:last-child, td:last-child { border-right: 0; }
        tr:last-child td { border-bottom: 0; }
        th {
          text-align: left;
          font-size: 12px;
          color: var(--secondary-text-color);
          background: var(--secondary-background-color);
        }
        td.category {
          min-width: 170px;
          font-weight: 600;
        }
        td.month input {
          width: 72px;
          text-align: center;
        }
        .muted {
          color: var(--secondary-text-color);
        }
        .events {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
          gap: 8px;
        }
        .event {
          border: 1px solid var(--divider-color);
          border-radius: 8px;
          padding: 10px 12px;
          background: var(--card-background-color);
        }
        .event strong {
          display: block;
          margin-bottom: 4px;
        }
        @media (max-width: 820px) {
          .wrap { padding: 16px; }
          header { align-items: flex-start; flex-direction: column; }
          .toolbar { grid-template-columns: 1fr; }
          .settings-grid { grid-template-columns: 1fr; }
          button { width: 100%; }
        }
      </style>
      <div class="wrap">
        <header>
          <h1>${labels.title}</h1>
          <div class="status">
            <span class="pill">${labels.status}: ${escapeHtml(status.state || labels.none)}</span>
            <span class="pill">${labels.events}: ${status.event_count || 0}</span>
            ${nextPickup ? `<span class="pill">${labels.next}: ${escapeHtml(nextPickup.date)} · ${escapeHtml(nextPickup.categories.join(", "))}</span>` : ""}
          </div>
        </header>

        <div class="toolbar">
          <label>
            ${labels.image}
            <input id="image" type="file" accept="image/jpeg,image/png,image/webp" />
          </label>
          <label>
            ${labels.year}
            <input id="year" type="number" min="2000" max="2100" value="${escapeHtml(year)}" />
          </label>
          <button id="scan" ${this._loading ? "disabled" : ""}>
            <ha-icon icon="mdi:upload"></ha-icon>
            ${labels.scan}
          </button>
          <button id="activate" class="danger" ${this._loading || !rows.length ? "disabled" : ""}>
            <ha-icon icon="mdi:calendar-sync"></ha-icon>
            ${labels.replaceCalendar}
          </button>
          <button id="test" class="secondary">
            <ha-icon icon="mdi:bell-outline"></ha-icon>
            ${labels.test}
          </button>
        </div>

        ${rows.length ? renderActivationWarning(labels) : ""}

        ${renderNotificationOptions(options, availableNotifyTargets, labels)}

        ${this._loading ? `<div class="notice">${labels.processing}</div>` : ""}
        ${this._message ? `<div class="notice">${escapeHtml(this._message)}</div>` : ""}
        ${this._error ? `<div class="error">${escapeHtml(this._error)}</div>` : ""}
        ${renderWarnings(draft, status)}

        <h2>${labels.verification}</h2>
        <p class="muted">${labels.verificationHint}</p>
        ${rows.length ? renderTable(rows, labels) : `<p class="muted">${labels.noVerificationData}</p>`}

        <h2>${labels.activeDates}</h2>
        ${events.length ? renderEvents(events.slice(0, 24)) : `<p class="muted">${labels.noActiveDates}</p>`}
      </div>
    `;

    this.shadowRoot.querySelector("#scan")?.addEventListener("click", () => this._scan());
    this.shadowRoot.querySelector("#activate")?.addEventListener("click", () => this._activate());
    this.shadowRoot.querySelector("#test")?.addEventListener("click", () => this._testNotification());
    this.shadowRoot.querySelector("#save-options")?.addEventListener("click", () => this._saveOptions());
    this.shadowRoot.querySelectorAll("td.month input").forEach((input) => {
      input.addEventListener("change", () => this._saveCell(input));
    });
  }
}

function renderActivationWarning(labels) {
  return `
    <div class="activation-warning">
      <strong>${labels.replaceCalendarTitle}</strong>
      <span>${labels.replaceCalendarWarning}</span>
    </div>
  `;
}

function renderNotificationOptions(options, availableNotifyTargets, labels) {
  const selected = Array.isArray(options.notify_targets) ? options.notify_targets : [];
  const known = [...availableNotifyTargets];
  selected.forEach((target) => {
    if (!known.some((item) => item.value === target)) {
      known.push({ value: target, label: `notify.${target}` });
    }
  });
  const knownValues = new Set(known.map((item) => item.value));
  const customTargets = selected.filter((target) => !knownValues.has(target)).join(", ");
  return `
    <section class="settings">
      <h2>${labels.notifications}</h2>
      <div class="muted">${labels.notificationTargetsHint}</div>
      ${
        known.length
          ? `<div class="notify-grid">
              ${known.map((item) => `
                <label class="checkbox">
                  <input
                    type="checkbox"
                    name="notify-target"
                    value="${escapeHtml(item.value)}"
                    ${selected.includes(item.value) ? "checked" : ""}
                  />
                  ${escapeHtml(item.label)}
                </label>
              `).join("")}
            </div>`
          : `<p class="muted">${labels.noNotifyServices}</p>`
      }
      <div class="settings-grid">
        <label>
          ${labels.customNotifyTargets}
          <input id="custom-notify" value="${escapeHtml(customTargets)}" placeholder="mobile_app_iphone" />
        </label>
        <label>
          ${labels.morningTime}
          <input id="morning-time" type="time" value="${escapeHtml(options.morning_time || "08:00")}" />
        </label>
        <label>
          ${labels.eveningTime}
          <input id="evening-time" type="time" value="${escapeHtml(options.evening_time || "20:00")}" />
        </label>
        <label>
          ${labels.annualTime}
          <input id="annual-time" type="time" value="${escapeHtml(options.annual_scan_reminder_time || "09:00")}" />
        </label>
        <button id="save-options" class="secondary">
          <ha-icon icon="mdi:content-save-outline"></ha-icon>
          ${labels.saveOptions}
        </button>
      </div>
    </section>
  `;
}

function renderTable(rows, labels) {
  const monthHeaders = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"];
  return `
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>${labels.category}</th>
            ${monthHeaders.map((month) => `<th>${month}</th>`).join("")}
          </tr>
        </thead>
        <tbody>
          ${rows.map((row, rowIndex) => `
            <tr>
              <td class="category">
                ${escapeHtml(row.category_raw)}
                ${row.notify ? "" : `<div class="muted">${labels.noNotifications}</div>`}
              </td>
              ${monthHeaders.map((_, index) => {
                const month = String(index + 1);
                const value = ((row.days_by_month && row.days_by_month[month]) || []).join(", ");
                return `<td class="month"><input data-row-index="${rowIndex}" data-month="${month}" value="${escapeHtml(value)}" /></td>`;
              }).join("")}
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

const STRINGS = {
  en: {
    title: "Działdowo Waste",
    status: "Status",
    events: "Events",
    next: "Next",
    none: "none",
    image: "Image",
    year: "Year",
    scan: "Scan",
    replaceCalendar: "Replace calendar",
    test: "Test",
    processing: "Processing...",
    verification: "Verification",
    verificationHint:
      "Edit the cells below before replacing the calendar. These values are the source of truth for the active Waste calendar.",
    replaceCalendarTitle: "Replacing the calendar is destructive",
    replaceCalendarWarning:
      "The button Replace calendar saves the current Verification table as the new Waste calendar, removes previous pickup dates, and resets sent-notification tracking.",
    activateConfirm:
      "Replace the current Waste calendar with the dates from the Verification table? Previous pickup dates will be removed.",
    noVerificationData: "No data to verify.",
    activeDates: "Active pickup dates",
    noActiveDates: "No active pickup dates.",
    category: "Category",
    noNotifications: "notifications off",
    selectFile: "Select a JPG, PNG, or WebP file.",
    scanDone: "Scan complete.",
    enterYear: "Enter the schedule year.",
    scheduleActive: "Waste calendar replaced.",
    testSent: "Test sent.",
    notifications: "Notifications",
    notificationTargetsHint: "Select Home Assistant notify services that should receive reminders.",
    noNotifyServices: "No notify services found. Add a custom service name below if needed.",
    customNotifyTargets: "Custom notify services",
    morningTime: "Morning reminder",
    eveningTime: "Evening reminder",
    annualTime: "January 1 reminder",
    saveOptions: "Save options",
    optionsSaved: "Notification options saved.",
    unknownError: "Unknown error.",
  },
  pl: {
    title: "Odpady Działdowo",
    status: "Status",
    events: "Zdarzenia",
    next: "Najbliżej",
    none: "brak",
    image: "Zdjęcie",
    year: "Rok",
    scan: "Skanuj",
    replaceCalendar: "Nadpisz kalendarz",
    test: "Test",
    processing: "Przetwarzanie...",
    verification: "Weryfikacja",
    verificationHint:
      "Popraw pola poniżej przed nadpisaniem kalendarza. To właśnie wartości z tej tabeli zostaną zapisane jako aktywny kalendarz Odpady.",
    replaceCalendarTitle: "Nadpisanie kalendarza usuwa poprzednie terminy",
    replaceCalendarWarning:
      "Przycisk Nadpisz kalendarz zapisze aktualną tabelę Weryfikacja jako nowy kalendarz Odpady, usunie poprzednie terminy odbioru i zresetuje historię wysłanych powiadomień.",
    activateConfirm:
      "Nadpisać obecny kalendarz Odpady terminami z tabeli Weryfikacja? Poprzednie terminy odbioru zostaną usunięte.",
    noVerificationData: "Brak danych do weryfikacji.",
    activeDates: "Aktywne terminy",
    noActiveDates: "Brak aktywnych terminów.",
    category: "Kategoria",
    noNotifications: "bez powiadomień",
    selectFile: "Wybierz plik JPG, PNG albo WebP.",
    scanDone: "Skan zakończony.",
    enterYear: "Podaj rok harmonogramu.",
    scheduleActive: "Kalendarz Odpady został nadpisany.",
    testSent: "Wysłano test.",
    notifications: "Powiadomienia",
    notificationTargetsHint: "Wybierz usługi notify Home Assistanta, które mają dostawać przypomnienia.",
    noNotifyServices: "Nie znaleziono usług notify. W razie potrzeby dopisz nazwę usługi ręcznie niżej.",
    customNotifyTargets: "Własne usługi notify",
    morningTime: "Poranne przypomnienie",
    eveningTime: "Wieczorne przypomnienie",
    annualTime: "Przypomnienie 1 stycznia",
    saveOptions: "Zapisz opcje",
    optionsSaved: "Zapisano opcje powiadomień.",
    unknownError: "Nieznany błąd.",
  },
};

function getLabels(hass) {
  const language = String(
    (hass && hass.locale && hass.locale.language) || (hass && hass.language) || navigator.language || "en"
  ).toLowerCase();
  return language.startsWith("pl") ? STRINGS.pl : STRINGS.en;
}

function renderEvents(events) {
  return `
    <div class="events">
      ${events.map((event) => `
        <div class="event">
          <strong>${escapeHtml(event.date)}</strong>
          <span>${escapeHtml(event.categories.join(", "))}</span>
        </div>
      `).join("")}
    </div>
  `;
}

function renderWarnings(draft, status) {
  const warnings = [
    ...((draft && draft.warnings) || []),
    ...((draft && draft.errors) || []),
    ...((status && status.warnings) || []),
    ...((status && status.errors) || []),
  ].filter(Boolean);
  if (!warnings.length) return "";
  return `<div class="notice">${warnings.map(escapeHtml).join("<br>")}</div>`;
}

function readFileAsDataURL(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

function splitTargets(value) {
  return String(value || "")
    .split(/[\n,]+/)
    .map((item) => item.trim().replace(/^notify\./, ""))
    .filter(Boolean);
}

function uniqueValues(values) {
  const seen = new Set();
  return values.filter((value) => {
    if (seen.has(value)) return false;
    seen.add(value);
    return true;
  });
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

customElements.define("waste-pickup-ai-panel", WastePickupAIPanel);
