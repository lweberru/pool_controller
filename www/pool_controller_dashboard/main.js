/**
 * Pool Controller dashboard custom card (no iframe).
 * Draft 1: climate-like dial + mode controls + water quality + PV + calendar.
 */

const CARD_TYPE = "pc-pool-controller";
const DEFAULTS = {
	min_temp: 10,
	max_temp: 40,
	show_calendar: 1,
	chlor_ok_min: 650,
	chlor_ok_max: 850,
	pv_on: 1000,
	pv_off: 500,
};

class PoolControllerCard extends HTMLElement {
	setConfig(config) {
		if (!config || !config.climate_entity) {
			throw new Error("climate_entity ist erforderlich");
		}
		this._config = { ...DEFAULTS, ...config };
		this._calendarCache = { ts: 0, events: [] };
		if (!this.shadowRoot) {
			this.attachShadow({ mode: "open" });
		}
		this._render();
	}

	set hass(hass) {
		this._hass = hass;
		this._render();
	}

	connectedCallback() {
		this._render();
	}

	getCardSize() {
		return 5;
	}

	async _render() {
		if (!this._hass || !this._config) return;
		const h = this._hass;
		const c = this._config;
		const climate = h.states[c.climate_entity];
		if (!climate) {
			this._renderError(`Entity ${c.climate_entity} nicht gefunden`);
			return;
		}

		const current = this._num(climate.attributes.current_temperature);
		const target = this._num(climate.attributes.temperature) ?? this._num(climate.attributes.target_temp) ?? this._num(climate.attributes.max_temp);
		const hvac = climate.state;
		const hvacAction = climate.attributes.hvac_action;
		const status = c.status_entity ? h.states[c.status_entity]?.state : null;
		const auxOn = c.aux_entity ? this._isOn(h.states[c.aux_entity]) : (h.states[c.aux_binary]?.state === "on");

		const bathingState = this._modeState(h, c.bathing_entity, c.bathing_until);
		const filterState = this._modeState(h, c.filter_entity, c.filter_until, c.next_filter_in);
		const chlorState = this._modeState(h, c.chlorine_entity, c.chlorine_until, c.chlorine_active_entity);
		const pauseState = this._modeState(h, c.pause_entity, c.pause_until, c.pause_active_entity);
		const frost = c.frost_entity ? this._isOn(h.states[c.frost_entity]) : false;
		const quiet = c.quiet_entity ? this._isOn(h.states[c.quiet_entity]) : false;
		const pvVal = c.pv_entity ? this._num(h.states[c.pv_entity]?.state) : null;
		const powerVal = c.power_entity ? this._num(h.states[c.power_entity]?.state) : null;

		const ph = c.ph_entity ? this._num(h.states[c.ph_entity]?.state) : null;
		const chlor = c.chlorine_value_entity ? this._num(h.states[c.chlorine_value_entity]?.state) : null;
		const salt = c.salt_entity ? this._num(h.states[c.salt_entity]?.state) : null;
		const tds = c.tds_entity ? this._num(h.states[c.tds_entity]?.state) : null;
		const phPlus = c.ph_plus_entity ? this._num(h.states[c.ph_plus_entity]?.state) : null;
		const phMinus = c.ph_minus_entity ? this._num(h.states[c.ph_minus_entity]?.state) : null;
		const chlorDose = c.chlor_dose_entity ? this._num(h.states[c.chlor_dose_entity]?.state) : null;

		const nextStartMins = c.next_start_entity ? this._num(h.states[c.next_start_entity]?.state) : null;
		const nextEventTs = c.next_event_entity ? h.states[c.next_event_entity]?.state : null;

		const dialAngle = this._calcDial(target ?? current ?? c.min_temp, c.min_temp, c.max_temp);
		const pvProgress = pvVal != null ? this._clamp((pvVal - c.pv_off) / Math.max(1, c.pv_on - c.pv_off), 0, 1) : null;

		const events = await this._loadCalendarEvents();
		const maxEvents = Number(c.show_calendar || 1);
		const shownEvents = events.length ? events.slice(0, maxEvents) : (nextEventTs ? [{ title: "Geplanter Start", start: new Date(nextEventTs), source: "calendar" }] : []);

		this.shadowRoot.innerHTML = `
		<style>
			:host { display: block; }
			ha-card { padding: 16px; background: linear-gradient(180deg, #fdfbfb 0%, #f2f5f8 100%); color: var(--primary-text-color); }
			* { box-sizing: border-box; }
			.header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; font-family: "Montserrat", "Segoe UI", sans-serif; }
			.title { font-size: 18px; font-weight: 600; letter-spacing: 0.3px; }
			.pill { padding: 4px 10px; border-radius: 999px; font-size: 12px; font-weight: 600; text-transform: uppercase; background: #f4f6f8; color: #333; }
			.pill.on { background: #d0f0d0; color: #0f6b2f; }
			.pill.warn { background: #ffe5d5; color: #b44; }
			.grid { display: grid; gap: 16px; }
			.top { grid-template-columns: minmax(200px, 1fr) minmax(220px, 1.1fr); }
			.dial { position: relative; aspect-ratio: 1 / 1; display: grid; place-items: center; }
			.ring { width: 100%; height: 100%; border-radius: 50%; background: conic-gradient(var(--accent, #8a3b32) var(--angle, 0deg), #e6e9ed 0deg); display: grid; place-items: center; padding: 18px; }
			.ring::after { content: ""; width: 100%; height: 100%; border-radius: 50%; background: radial-gradient(circle at 50% 50%, #fff 62%, transparent 63%); }
			.dial-core { position: absolute; display: grid; gap: 6px; place-items: center; text-align: center; }
			.temp { font-size: 38px; font-weight: 700; }
			.unit { font-size: 14px; color: var(--secondary-text-color); }
			.sub { font-size: 13px; color: var(--secondary-text-color); }
			.dial-buttons { display: grid; grid-template-columns: repeat(2, 48px); gap: 10px; margin-top: 8px; }
			.btn { height: 46px; border-radius: 12px; border: 1px solid #d0d7de; background: #fff; font-weight: 700; cursor: pointer; transition: transform 120ms ease, box-shadow 120ms ease; }
			.btn:hover { box-shadow: 0 6px 14px rgba(0,0,0,0.08); transform: translateY(-1px); }
			.btn.ghost { background: transparent; border-color: transparent; color: #555; }
			.mode-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px; }
			.mode { border: 1px solid #d0d7de; border-radius: 12px; padding: 10px; display: grid; gap: 6px; align-items: center; background: #fff; }
			.mode.on { border-color: #8a3b32; box-shadow: 0 4px 12px rgba(138,59,50,0.15); }
			.mode .label { font-weight: 600; font-size: 14px; display: flex; align-items: center; gap: 8px; }
			.mode .detail { font-size: 12px; color: #555; }
			.quality { border: 1px solid #d0d7de; border-radius: 12px; padding: 12px; background: #fff; display: grid; gap: 12px; }
			.bar { position: relative; height: 40px; border-radius: 10px; overflow: hidden; }
			.ph-bar { background: linear-gradient(90deg, #d7263d 0%, #e45a2a 10%, #fbb13c 20%, #f6d32b 30%, #8bd448 45%, #27ae60 55%, #1abc9c 65%, #1c9ed8 75%, #2a7fdb 85%, #5c4ac7 100%); }
			.chlor-bar { background: linear-gradient(90deg, #d7263d 0%, #f5a524 30%, #1bbc63 60%, #1bbc63 80%, #f5a524 90%, #d7263d 100%); }
			.bar .marker { position: absolute; top: 0; width: 2px; height: 100%; background: #0b132b; box-shadow: 0 0 0 6px rgba(0,0,0,0.08); }
			.bar .thumb { position: absolute; top: -6px; width: 18px; height: 52px; border-radius: 12px; background: #fff; border: 2px solid #0b132b; display: grid; place-items: center; font-size: 11px; font-weight: 700; }
			.badges { display: flex; flex-wrap: wrap; gap: 8px; }
			.badge { padding: 6px 10px; border-radius: 10px; background: #f4f6f8; font-size: 12px; border: 1px solid #e0e6ed; }
			.badge.alert { background: #ffe5d5; color: #8a3b32; border-color: #f3c2a2; }
			.pv { border: 1px solid #d0d7de; border-radius: 12px; padding: 12px; background: #fff; display: grid; gap: 8px; }
			.progress { position: relative; height: 12px; border-radius: 999px; background: #eef1f4; overflow: hidden; }
			.progress .fill { position: absolute; height: 100%; left: 0; top: 0; border-radius: inherit; background: linear-gradient(90deg, #f08a5d, #8a3b32); }
			.progress .mark { position: absolute; top: -2px; width: 2px; height: 16px; background: #0b132b; opacity: 0.5; }
			.calendar { border: 1px solid #d0d7de; border-radius: 12px; padding: 12px; background: #fff; display: grid; gap: 8px; }
			.event { padding: 8px 10px; border-radius: 10px; background: #f8fafc; border: 1px solid #e5e9f0; display: flex; justify-content: space-between; gap: 8px; }
			.event .time { color: #555; font-size: 12px; }
			.section-title { font-weight: 700; font-size: 14px; text-transform: uppercase; letter-spacing: 0.04em; color: #4a5568; }
			.status-row { display: flex; gap: 8px; flex-wrap: wrap; }
			.status-chip { display: inline-flex; align-items: center; gap: 6px; padding: 6px 10px; border-radius: 10px; background: #f4f6f8; font-size: 12px; border: 1px solid #e0e6ed; }
			.status-chip.on { background: #d0f0d0; color: #0f6b2f; border-color: #b8e3b8; }
		</style>
		<ha-card>
			<div class="header">
				<div class="title">${c.title || climate.attributes.friendly_name || "Pool Controller"}</div>
				<div class="pill ${status === "paused" ? "warn" : status === "frost_protection" ? "on" : ""}">${status || hvac}</div>
			</div>
			<div class="grid top">
				<div class="dial" style="--angle:${dialAngle}deg; --accent:${auxOn ? "#c0392b" : "#8a3b32"}">
					<div class="ring"></div>
					<div class="dial-core">
						<div class="temp">${(target ?? current ?? 0).toFixed(1)}°C</div>
						<div class="sub">Ist ${current != null ? `${current.toFixed(1)}°C` : "–"} • Modus ${hvac}</div>
						<div class="sub">${hvacAction || "idle"}${auxOn ? " • Zusatzheizung" : ""}</div>
						<div class="dial-buttons">
							<button class="btn" data-action="dec">−</button>
							<button class="btn" data-action="inc">+</button>
						</div>
					</div>
				</div>
				<div class="mode-panel">
					<div class="mode-row">
						${this._modeTile("Baden", "mdi:pool", bathingState, c.bathing_start, c.bathing_stop)}
						${this._modeTile("Filtern", "mdi:rotate-right", filterState, c.filter_start, c.filter_stop)}
						${this._modeTile("Chloren", "mdi:fan", chlorState, c.chlorine_start, c.chlorine_stop)}
						${this._modeTile("Pause", "mdi:pause-circle", pauseState, c.pause_start, c.pause_stop)}
					</div>
					<div class="status-row">
						${this._chip("Frost", frost)}
						${this._chip("Ruhezeit", quiet)}
						${this._chip("PV ok", c.pv_entity ? pvVal != null && pvVal >= c.pv_on : false)}
						${this._chip("Nächster Start", nextStartMins != null ? `${nextStartMins} min` : "–")}
					</div>
				</div>
			</div>
			<div class="quality" style="margin-top:16px;">
				<div class="section-title">Wasserqualität</div>
				<div>
					<div class="label" style="margin-bottom:4px; font-weight:600;">pH ${ph != null ? ph.toFixed(2) : "–"}</div>
					<div class="bar ph-bar">${this._marker(ph, 1, 14)}</div>
				</div>
				<div>
					<div class="label" style="margin-bottom:4px; font-weight:600;">Chlor ${chlor != null ? chlor.toFixed(0) : "–"}</div>
					<div class="bar chlor-bar">${this._marker(chlor, 0, 1200)}</div>
				</div>
				<div class="badges">
					${salt != null ? `<div class="badge">Salz ${salt}</div>` : ""}
					${tds != null ? `<div class="badge">TDS ${tds}</div>` : ""}
					${phPlus && phPlus > 0 ? `<div class="badge alert">pH+ ${phPlus} g</div>` : ""}
					${phMinus && phMinus > 0 ? `<div class="badge alert">pH- ${phMinus} g</div>` : ""}
					${chlorDose && chlorDose > 0 ? `<div class="badge alert">Chlor ${chlorDose}</div>` : ""}
				</div>
			</div>
			<div class="pv" style="margin-top:16px;">
				<div class="section-title">Photovoltaik & Verbrauch</div>
				<div class="progress">
					<div class="fill" style="width:${pvProgress != null ? pvProgress * 100 : 0}%"></div>
					<div class="mark" style="left:${this._pct(c.pv_off, c.pv_off, c.pv_on)}%"></div>
					<div class="mark" style="left:${this._pct(c.pv_on, c.pv_off, c.pv_on)}%"></div>
				</div>
				<div class="status-row">
					${this._chip("PV", pvVal != null ? `${pvVal} W` : "–")}
					${this._chip("Verbrauch", powerVal != null ? `${powerVal} W` : "–")}
				</div>
			</div>
			<div class="calendar" style="margin-top:16px;">
				<div class="section-title">Nächste Termine</div>
				${shownEvents.length ? shownEvents.map(ev => this._eventRow(ev)).join("") : `<div class="event"><div>Keine Einträge</div></div>`}
			</div>
		</ha-card>`;

		this._attachHandlers();
	}

	_renderError(msg) {
		this.shadowRoot.innerHTML = `<ha-card><div style="padding:16px; color:red;">${msg}</div></ha-card>`;
	}

	_attachHandlers() {
		const buttons = this.shadowRoot.querySelectorAll(".btn");
		buttons.forEach((btn) => {
			btn.addEventListener("click", () => {
				const action = btn.dataset.action;
				if (!this._hass) return;
				const step = Number(this._config.step || 0.5);
				const climate = this._hass.states[this._config.climate_entity];
				const currentTarget = this._num(climate?.attributes?.temperature) ?? this._num(climate?.attributes?.target_temp) ?? this._config.min_temp;
				const next = action === "inc" ? currentTarget + step : currentTarget - step;
				this._hass.callService("climate", "set_temperature", { entity_id: this._config.climate_entity, temperature: this._clamp(next, this._config.min_temp, this._config.max_temp) });
			});
		});

		const modeTiles = this.shadowRoot.querySelectorAll("[data-start]");
		modeTiles.forEach((tile) => {
			tile.addEventListener("click", () => {
				const { start, stop, active } = tile.dataset;
				if (active === "true" && stop) {
					this._triggerEntity(stop, false);
				} else if (start) {
					this._triggerEntity(start, true);
				}
			});
		});
	}

	_triggerEntity(entityId, turnOn = true) {
		if (!entityId || !this._hass) return;
		const [domain] = entityId.split(".");
		if (domain === "button") {
			this._hass.callService("button", "press", { entity_id: entityId });
			return;
		}
		if (domain === "switch") {
			this._hass.callService("switch", turnOn ? "turn_on" : "turn_off", { entity_id: entityId });
			return;
		}
		if (domain === "input_boolean") {
			this._hass.callService("input_boolean", turnOn ? "turn_on" : "turn_off", { entity_id: entityId });
			return;
		}
		// fallback: homeassistant.turn_on/off
		this._hass.callService("homeassistant", turnOn ? "turn_on" : "turn_off", { entity_id: entityId });
	}

	_modeTile(label, icon, state, start, stop) {
		const active = state?.active;
		const eta = state?.eta;
		return `<div class="mode ${active ? "on" : ""}" data-start="${start || ""}" data-stop="${stop || ""}" data-active="${active ? "true" : "false"}">
			<div class="label"><ha-icon icon="${icon}"></ha-icon><span>${label}</span></div>
			<div class="detail">${active ? (eta != null ? `Noch ${eta} min` : "Aktiv") : "Bereit"}</div>
		</div>`;
	}

	_chip(label, value) {
		const isOn = value === true || value === "on" || (typeof value === "string" && value.endsWith("min")) || (typeof value === "string" && value !== "–");
		return `<div class="status-chip ${isOn ? "on" : ""}"><span>${label}</span><strong>${value === true ? "" : value ?? ""}</strong></div>`;
	}

	_marker(val, min, max) {
		if (val == null) return "";
		const pct = this._clamp(((val - min) / (max - min)) * 100, 0, 100);
		return `<div class="marker" style="left:${pct}%"></div><div class="thumb" style="left:calc(${pct}% - 9px)">${val}</div>`;
	}

	_eventRow(ev) {
		const dt = ev.start instanceof Date ? ev.start : new Date(ev.start);
		const dateStr = dt ? dt.toLocaleString(undefined, { weekday: "short", hour: "2-digit", minute: "2-digit" }) : "";
		return `<div class="event"><div>${ev.title || ev.summary || "Termin"}</div><div class="time">${dateStr}</div></div>`;
	}

	_modeState(h, entity, untilEntity, fallbackActiveEntity) {
		const now = Date.now();
		let active = false;
		let eta = null;
		if (entity && h.states[entity]) {
			active = this._isOn(h.states[entity]);
		}
		if (!active && fallbackActiveEntity && h.states[fallbackActiveEntity]) {
			active = this._isOn(h.states[fallbackActiveEntity]);
		}
		if (untilEntity && h.states[untilEntity]?.state) {
			const ts = new Date(h.states[untilEntity].state).getTime();
			if (!Number.isNaN(ts) && ts > now) {
				active = true;
				eta = Math.max(0, Math.round((ts - now) / 60000));
			}
		}
		return { active, eta };
	}

	_calcDial(val, min, max) {
		const pct = this._clamp((val - min) / (max - min), 0, 1);
		return Math.round(pct * 300 + 30); // leave 60deg gap
	}

	_num(v) {
		const n = Number(v);
		return Number.isFinite(n) ? n : null;
	}

	_clamp(v, a, b) {
		return Math.min(Math.max(v, a), b);
	}

	_isOn(stateObj) {
		if (!stateObj) return false;
		return stateObj.state === "on" || stateObj.state === "heat" || stateObj.state === "heating";
	}

	_pct(val, min, max) {
		return this._clamp(((val - min) / (max - min)) * 100, 0, 100);
	}

	async _loadCalendarEvents() {
		const cfg = this._config;
		if (!this._hass || !cfg.calendar_entities || !cfg.calendar_entities.length) return [];
		const now = new Date();
		if (now.getTime() - this._calendarCache.ts < 60000) {
			return this._calendarCache.events;
		}
		const end = new Date(now.getTime() + 7 * 24 * 3600 * 1000);
		const promises = cfg.calendar_entities.map((id) => this._hass.callWS({ type: "calendar/list_events", entity_id: id, start_time: now.toISOString(), end_time: end.toISOString() }));
		try {
			const results = await Promise.allSettled(promises);
			const events = results.flatMap((r, idx) => {
				if (r.status !== "fulfilled") return [];
				return (r.value || []).map((ev) => ({ ...ev, source: cfg.calendar_entities[idx] }));
			});
			this._calendarCache = { ts: now.getTime(), events };
			return events;
		} catch (e) {
			// ignore
			return [];
		}
	}
}

customElements.define(`${CARD_TYPE}-card`, PoolControllerCard);

// Provide Lovelace UI config editor
PoolControllerCard.getConfigElement = async function () {
	return document.createElement(`${CARD_TYPE}-editor`);
};

class PoolControllerCardEditor extends HTMLElement {
	set hass(hass) {
		this._hass = hass;
		this._render();
	}

	setConfig(config) {
		this._config = { ...DEFAULTS, ...config };
		this._render();
	}

	get value() {
		return this._config;
	}

	_render() {
		if (!this.shadowRoot) this.attachShadow({ mode: "open" });
		const c = this._config || DEFAULTS;
		this.shadowRoot.innerHTML = `
		<style>
			:host { display:block; }
			.wrapper { display:grid; gap:12px; padding:12px; }
			.row { display:grid; gap:6px; }
			label { font-weight:600; }
			.grid2 { display:grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap:10px; }
			.box { border:1px solid #d0d7de; border-radius:10px; padding:10px; background:#fff; }
			.badge { display:inline-block; padding:4px 8px; border-radius:8px; background:#f4f6f8; border:1px solid #e0e6ed; margin:2px 4px 0 0; font-size:12px; }
			button { border:1px solid #d0d7de; border-radius:8px; padding:8px 10px; cursor:pointer; background:#fff; font-weight:600; }
		</style>
		<div class="wrapper">
			<div class="row">
				<label>Pool Controller Instanz</label>
				<ha-entity-picker id="controller" .hass="${""}" .value="${c.controller_entity || ""}" allow-custom-entity="false" .includeDomains="${JSON.stringify(["climate","sensor","switch","binary_sensor","button"])}"></ha-entity-picker>
				<div class="box" id="derived"></div>
				<button id="derive">Automatisch aus Instanz übernehmen</button>
			</div>
			<div class="grid2">
				<div class="row">
					<label>Temperatur-Minimum</label>
					<input id="min_temp" type="number" step="0.5" value="${c.min_temp}">
				</div>
				<div class="row">
					<label>Temperatur-Maximum</label>
					<input id="max_temp" type="number" step="0.5" value="${c.max_temp}">
				</div>
				<div class="row">
					<label>Schrittweite</label>
					<input id="step" type="number" step="0.1" value="${c.step || 0.5}">
				</div>
				<div class="row">
					<label>Kalender-Einträge anzeigen</label>
					<input id="show_calendar" type="number" step="1" min="0" value="${c.show_calendar || 1}">
				</div>
			</div>
			<div class="grid2">
				<div class="row">
					<label>PV Ein (W)</label>
					<input id="pv_on" type="number" step="10" value="${c.pv_on}">
				</div>
				<div class="row">
					<label>PV Aus (W)</label>
					<input id="pv_off" type="number" step="10" value="${c.pv_off}">
				</div>
			</div>
		</div>`;

		const picker = this.shadowRoot.querySelector("#controller");
		if (picker) {
			picker.hass = this._hass;
			picker.value = c.controller_entity || "";
			picker.addEventListener("value-changed", (ev) => {
				const val = ev.detail?.value;
				this._updateConfig({ controller_entity: val, climate_entity: val && val.startsWith("climate.") ? val : this._config?.climate_entity });
			});
		}

		this.shadowRoot.querySelectorAll("input").forEach((inp) => {
			inp.addEventListener("change", () => {
				const id = inp.id;
				const num = Number(inp.value);
				this._updateConfig({ [id]: Number.isFinite(num) ? num : inp.value });
			});
		});

		const deriveBtn = this.shadowRoot.querySelector("#derive");
		if (deriveBtn) deriveBtn.addEventListener("click", () => this._deriveFromController());

		this._renderDerivedBox();
	}

	async _deriveFromController() {
		if (!this._hass || !this._config?.controller_entity) return;
		const reg = await this._getEntityRegistry();
		const selected = reg.find((r) => r.entity_id === this._config.controller_entity);
		if (!selected || !selected.config_entry_id) return;
		const ceid = selected.config_entry_id;
		const entries = reg.filter((r) => r.config_entry_id === ceid && r.platform === "pool_controller");
		const pick = (domain, suffix) => {
			const hit = entries.find((e) => e.entity_id.startsWith(`${domain}.`) && (suffix ? e.unique_id?.endsWith(`_${suffix}`) : true));
			return hit?.entity_id;
		};
		const cfg = {
			controller_entity: this._config.controller_entity,
			climate_entity: pick("climate", "climate") || this._config.climate_entity,
			status_entity: pick("sensor", "status") || this._config.status_entity,
			aux_entity: pick("switch", "aux") || this._config.aux_entity,
			bathing_start: pick("button", "bath_60") || pick("button", "bath_30") || this._config.bathing_start,
			bathing_stop: pick("button", "bath_stop") || this._config.bathing_stop,
			bathing_until: pick("sensor", "bathing_until") || this._config.bathing_until,
			filter_start: pick("button", "filter_60") || pick("button", "filter_30") || this._config.filter_start,
			filter_stop: pick("button", "filter_stop") || this._config.filter_stop,
			filter_until: pick("sensor", "filter_until") || this._config.filter_until,
			next_filter_in: pick("sensor", "next_filter_mins") || this._config.next_filter_in,
			chlorine_start: pick("button", "quick_chlor") || this._config.chlorine_start,
			chlorine_active_entity: pick("binary_sensor", "is_quick_chlor") || this._config.chlorine_active_entity,
			pause_start: pick("button", "pause_60") || pick("button", "pause_30") || this._config.pause_start,
			pause_stop: pick("button", "pause_stop") || this._config.pause_stop,
			pause_until: pick("sensor", "pause_until") || this._config.pause_until,
			ph_entity: pick("sensor", "ph_val") || this._config.ph_entity,
			chlorine_value_entity: pick("sensor", "chlor_val") || this._config.chlorine_value_entity,
			ph_plus_entity: pick("sensor", "ph_plus_g") || this._config.ph_plus_entity,
			ph_minus_entity: pick("sensor", "ph_minus_g") || this._config.ph_minus_entity,
			chlor_dose_entity: pick("sensor", "chlor_spoons") || this._config.chlor_dose_entity,
			next_start_entity: pick("sensor", "next_start_mins") || this._config.next_start_entity,
			next_event_entity: pick("sensor", "next_event") || this._config.next_event_entity,
		};
		this._updateConfig(cfg, true);
	}

	async _getEntityRegistry() {
		if (this._registry) return this._registry;
		this._registry = await this._hass.callWS({ type: "config/entity_registry/list" });
		return this._registry;
	}

	_renderDerivedBox() {
		const box = this.shadowRoot.querySelector("#derived");
		if (!box || !this._config) return;
		const cfg = this._config;
		const rows = [
			["climate", cfg.climate_entity],
			["status", cfg.status_entity],
			["aux", cfg.aux_entity],
			["bathing", `${cfg.bathing_start || ""} / ${cfg.bathing_stop || ""}`],
			["filter", `${cfg.filter_start || ""} / ${cfg.filter_stop || ""}`],
			["chlorine", cfg.chlorine_start],
			["pause", `${cfg.pause_start || ""} / ${cfg.pause_stop || ""}`],
			["quality", `${cfg.ph_entity || ""}, ${cfg.chlorine_value_entity || ""}`],
			["timers", `${cfg.next_start_entity || ""}, ${cfg.next_event_entity || ""}`],
		];
		box.innerHTML = rows
			.map(([k, v]) => `<div class="badge"><strong>${k}</strong>: ${v || "–"}</div>`)
			.join("");
	}

	_updateConfig(patch, renderOnly = false) {
		this._config = { ...DEFAULTS, ...this._config, ...patch };
		this._renderDerivedBox();
		if (!renderOnly) {
			this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: this._config } }));
		}
	}
}

customElements.define(`${CARD_TYPE}-editor`, PoolControllerCardEditor);

window.customCards = window.customCards || [];
window.customCards.push({
	type: CARD_TYPE,
	name: "Pool Controller",
	description: "Whirlpool/Pool Steuerung ohne iFrame.",
});

window.customElements.define(
	CARD_TYPE,
	class extends HTMLElement {
		setConfig(config) {
			this._config = config;
		}
		set hass(hass) {
			if (!this._card) {
				this._card = document.createElement(`${CARD_TYPE}-card`);
				this._card.setConfig(this._config);
				this.appendChild(this._card);
			}
			this._card.hass = hass;
		}
	}
);
