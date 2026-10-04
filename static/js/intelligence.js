(function () {
  let D = window.FLEET_DATA || { vehicles: [], drivers: [], trips: [], maintenance: [], fuel: [] };
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const today = new Date();
  const vehicleById = (id) => D.vehicles.find(v => String(v.id) === String(id));
  const driverById = (id) => D.drivers.find(d => String(d.id) === String(id));
  const daysSince = (iso) => iso ? Math.floor((today - new Date(iso)) / 86400000) : 9999;
  const hash = (s) => { let h = 0; for (const c of String(s)) h = (h * 31 + c.charCodeAt(0)) >>> 0; return h; };
  const kmBetween = (a, b) => 120 + (hash(String(a).toLowerCase() + "|" + String(b).toLowerCase()) % 480);

  // ---------- KPIs ----------
  function kpis() {
    const onTrip = D.vehicles.filter(v => v.status === "On Trip").length;
    const available = D.vehicles.filter(v => v.status === "Available").length;
    const inShop = D.vehicles.filter(v => v.status === "In Shop").length;
    const activeTrips = D.trips.filter(t => t.status === "Dispatched" || t.status === "Draft").length;
    const highRisk = maintenanceRisk().filter(r => r.risk >= 70).length;
    const avgSafety = D.drivers.length ? Math.round(D.drivers.reduce((s, d) => s + (d.safety_score || 0), 0) / D.drivers.length) : 0;
    $("intelKpis").innerHTML = [["Active Fleet", onTrip], ["Available", available], ["In Shop", inShop], ["Active Trips", activeTrips], ["High-Risk Vehicles", highRisk], ["Avg Safety Score", avgSafety]]
      .map(([l, v]) => `<div class="card metric-card"><div class="metric-head"><span>${l}</span></div><div class="metric-value">${v}</div></div>`).join("");
  }

  // ---------- Live Tracking (data from /api/fleet/data) ----------
  const trackEls = {};
  let trackingBuilt = false;
  function buildTracking() {
    const svg = $("trackMap");
    if (!svg) return;
    let roads = "";
    for (let y = 40; y < 360; y += 60) roads += `<line x1="0" y1="${y}" x2="640" y2="${y}" stroke="#e2e8f0" stroke-width="10"/>`;
    for (let x = 60; x < 640; x += 90) roads += `<line x1="${x}" y1="0" x2="${x}" y2="360" stroke="#e2e8f0" stroke-width="10"/>`;
    svg.innerHTML = roads + `<rect x="8" y="320" width="14" height="14" rx="3" fill="#3b82f6"/><text x="26" y="332" font-size="11" fill="#64748b">Garage</text>`;
    const list = $("trackList");
    list.innerHTML = "";
    D.vehicles.forEach((v) => {
      const trip = v.active_trip || null;
      if (v.route) {
        const pl = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
        pl.setAttribute("points", `${v.route.x1},${v.route.y1} ${v.route.x2},${v.route.y2}`);
        pl.setAttribute("fill", "none");
        pl.setAttribute("stroke", "#fdba74");
        pl.setAttribute("stroke-width", "3");
        pl.setAttribute("stroke-dasharray", "6 4");
        svg.appendChild(pl);
      }
      const color = v.status === "On Trip" ? "#ff7a18" : v.status === "In Shop" ? "#8b5cf6" : "#22c55e";
      const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
      g.setAttribute("class", "vehicle-marker");
      g.innerHTML = `<circle r="7" fill="${color}" stroke="#fff" stroke-width="2"/><text x="10" y="4" font-size="10" fill="#334155">${esc(v.license_plate)}</text>`;
      svg.appendChild(g);
      trackEls[v.id] = g;
      const item = document.createElement("div");
      item.className = "track-item";
      item.innerHTML = `<b>${esc(v.license_plate)}</b> · ${esc(v.model_name)}<br><span class="badge ${v.status === 'On Trip' ? 'badge-amber' : v.status === 'In Shop' ? 'badge-blue' : 'badge-green'}">${esc(v.status)}</span>${trip ? `<br>${esc(trip.origin)} → ${esc(trip.destination)}` : ""}`;
      item.addEventListener("click", () => {
        document.querySelectorAll(".track-item").forEach(e => e.classList.remove("selected"));
        item.classList.add("selected");
      });
      list.appendChild(item);
    });
    trackingBuilt = true;
  }
  function updateTracking() {
    if (!trackingBuilt) { buildTracking(); return; }
    D.vehicles.forEach(v => {
      const g = trackEls[v.id];
      if (g && typeof v.x === "number" && typeof v.y === "number") {
        g.style.transform = `translate(${v.x}px, ${v.y}px)`;
      }
    });
  }

  // ---------- Route Optimization ----------
  (function routeOpt() {
    const cities = new Set();
    D.trips.forEach(t => { if (t.origin) cities.add(t.origin); if (t.destination) cities.add(t.destination); });
    $("cityList").innerHTML = [...cities].map(c => `<option value="${esc(c)}">`).join("");
    $("routeBtn").addEventListener("click", () => {
      const from = $("routeFrom").value.trim(), to = $("routeTo").value.trim();
      const svg = $("routeMap");
      if (!from || !to || from === to) { $("routeResult").innerHTML = "<div>Enter two different cities.</div>"; svg.innerHTML = ""; return; }
      const base = kmBetween(from, to);
      const options = [
        { name: "Shortest", km: Math.round(base * 0.92), factor: 1.15 },
        { name: "Balanced", km: base, factor: 1.0 },
        { name: "Fuel Saver", km: Math.round(base * 1.08), factor: 0.85 },
      ].map(o => {
        const timeH = (o.km / 55 * o.factor).toFixed(1);
        const liters = (o.km / 11 * o.factor).toFixed(1);
        return { ...o, timeH, liters, score: o.km * 0.5 + Number(liters) * 3 };
      });
      const best = options.reduce((a, b) => (a.score <= b.score ? a : b));
      svg.innerHTML = `<circle cx="60" cy="110" r="7" fill="#22c55e"/><text x="75" y="114" font-size="12" fill="#334155">${esc(from)}</text><circle cx="580" cy="110" r="7" fill="#ef4444"/><text x="470" y="100" font-size="12" fill="#334155">${esc(to)}</text>` +
        options.map((o, i) => `<polyline points="60,110 ${200 + i * 120},${60 + i * 60} 580,110" fill="none" stroke="${o.name === best.name ? '#ff7a18' : '#cbd5e1'}" stroke-width="${o.name === best.name ? 4 : 2}" ${o.name === best.name ? '' : 'stroke-dasharray="6 5"'}/>`).join("");
      $("routeResult").innerHTML = options.map(o => `<div><b>${o.name}</b>: ${o.km} km · ~${o.timeH}h · ~${o.liters}L ${o.name === best.name ? '<span class="badge badge-amber">Recommended</span>' : ''}</div>`).join("");
    });
  })();

  // ---------- Fuel Efficiency ----------
  function fuelStats() {
    const byVehicle = {};
    D.fuel.forEach(f => {
      byVehicle[f.vehicle_id] = byVehicle[f.vehicle_id] || { liters: 0, cost: 0 };
      byVehicle[f.vehicle_id].liters += Number(f.liters);
      byVehicle[f.vehicle_id].cost += Number(f.cost);
    });
    return Object.entries(byVehicle).map(([vid, s]) => {
      const estKm = D.trips.filter(t => String(t.vehicle_id) === String(vid) && t.status === "Completed")
        .reduce((sum, t) => sum + kmBetween(t.origin, t.destination), 0) || 500;
      const kmpl = (estKm / Math.max(s.liters, 0.1));
      return { vehicle: vehicleById(vid), ...s, estKm, kmpl };
    });
  }
  function fuelInit() {
    const stats = fuelStats();
    drawBars($("fuelChart"), stats.map(s => s.vehicle ? s.vehicle.license_plate : "?"), stats.map(s => s.kmpl.toFixed(1)), "#ff7a18");
    if (stats.length) {
      const best = stats.reduce((a, b) => (a.kmpl >= b.kmpl ? a : b));
      const worst = stats.reduce((a, b) => (a.kmpl <= b.kmpl ? a : b));
      $("fuelInsights").innerHTML = `<div><b>Most efficient:</b> ${esc(best.vehicle.license_plate)} — ${best.kmpl.toFixed(1)} km/L</div><div><b>Needs attention:</b> ${esc(worst.vehicle.license_plate)} — ${worst.kmpl.toFixed(1)} km/L</div><div><b>Total fuel spend:</b> ₹${Math.round(stats.reduce((s, x) => s + x.cost, 0))}</div>`;
    }
  }

  function maintenanceRisk() {
    return D.vehicles.map(v => {
      const logs = D.maintenance.filter(m => String(m.vehicle_id) === String(v.id));
      const lastDate = logs.length ? logs[0].date : null;
      const ds = daysSince(lastDate);
      let risk = Math.min(100, Math.round((v.odometer / 50000) * 40 + Math.min(ds, 180) / 180 * 40 + logs.length * 3 + (v.status === "In Shop" ? 15 : 0)));
      return { vehicle: v, risk, daysSinceLast: ds, count: logs.length };
    }).sort((a, b) => b.risk - a.risk);
  }

  function predMaint() {
    $("predMaint").innerHTML = maintenanceRisk().slice(0, 6).map(r => `<div class="bar-row"><div class="bar-label"><span>${esc(r.vehicle.license_plate)}</span><span>${r.risk}% risk</span></div><div class="bar-track"><div class="bar-fill" style="width:${r.risk}%;background:${r.risk >= 70 ? '#ef4444' : r.risk >= 40 ? '#f59e0b' : '#22c55e'}"></div></div><div class="bar-label" style="color:#6b7280">${r.daysSinceLast > 9000 ? 'No service logged' : r.daysSinceLast + ' days since service'} · ${r.count} records</div></div>`).join("");
  }

  function driverPerf() {
    const perf = D.drivers.map(d => {
      const expired = new Date(d.license_expiry_date) < today;
      const completed = D.trips.filter(t => String(t.driver_id) === String(d.id) && t.status === "Completed").length;
      const score = Math.max(0, Math.min(100, Math.round((d.safety_score || 0) * 0.7 + completed * 3 - (expired ? 25 : 0) + (d.status === "Suspended" ? -20 : 0))));
      return { driver: d, score, expired, completed };
    }).sort((a, b) => b.score - a.score);
    $("driverScores").innerHTML = perf.slice(0, 6).map(p => `<div class="bar-row"><div class="bar-label"><span>${esc(p.driver.name)} ${p.expired ? '<span class="badge badge-red">License expired</span>' : ''}</span><span>${p.score}</span></div><div class="bar-track"><div class="bar-fill" style="width:${p.score}%;background:${p.score >= 75 ? '#22c55e' : p.score >= 50 ? '#f59e0b' : '#ef4444'}"></div></div></div>`).join("");
  }

  function alerts() {
    const out = [];
    D.drivers.forEach(d => {
      const exp = new Date(d.license_expiry_date);
      const days = Math.floor((exp - today) / 86400000);
      if (days < 0) out.push({ level: "critical", text: `License expired for ${d.name} (${d.license_number}).` });
      else if (days < 30) out.push({ level: "warn", text: `License for ${d.name} expires in ${days} days.` });
      if (d.status === "Suspended") out.push({ level: "warn", text: `${d.name} is suspended — do not assign.` });
    });
    maintenanceRisk().forEach(r => {
      if (r.risk >= 80) out.push({ level: "critical", text: `${r.vehicle.license_plate} has critical maintenance risk (${r.risk}%).` });
      else if (r.risk >= 60) out.push({ level: "warn", text: `${r.vehicle.license_plate} approaching service interval.` });
    });
    D.vehicles.filter(v => v.status === "In Shop").forEach(v => out.push({ level: "info", text: `${v.license_plate} currently In Shop.` }));
    if (!out.length) out.push({ level: "info", text: "No active compliance alerts. Fleet is healthy." });
    $("alerts").innerHTML = out.slice(0, 8).map(a => `<div class="alert-item ${a.level === 'critical' ? 'critical' : a.level === 'info' ? 'info' : ''}">${esc(a.text)}</div>`).join("");
  }

  function delayPred() {
    const active = D.trips.filter(t => t.status === "Dispatched" || t.status === "Draft").slice(0, 8);
    $("delayPred").innerHTML = active.length ? active.map(t => {
      const d = driverById(t.driver_id);
      const v = vehicleById(t.vehicle_id);
      let risk = 10 + kmBetween(t.origin, t.destination) / 20;
      if (d && d.safety_score < 70) risk += 20;
      if (v && v.status === "In Shop") risk += 30;
      if (v && t.cargo_weight > v.max_capacity_kg * 0.9) risk += 15;
      if (d && new Date(d.license_expiry_date) < today) risk += 25;
      risk = Math.round(Math.min(risk, 99));
      const label = risk >= 60 ? "High" : risk >= 35 ? "Medium" : "Low";
      const cls = risk >= 60 ? "badge-red" : risk >= 35 ? "badge-amber" : "badge-green";
      return `<div class="bar-row"><div class="bar-label"><span>#${t.id} ${esc(t.origin)} → ${esc(t.destination)}</span><span class="badge ${cls}">${label} ${risk}%</span></div><div class="bar-track"><div class="bar-fill" style="width:${risk}%;background:${risk >= 60 ? '#ef4444' : risk >= 35 ? '#f59e0b' : '#22c55e'}"></div></div></div>`;
    }).join("") : "<div>No active trips to evaluate.</div>";
  }

  function charts() {
    const statuses = ["Draft", "Dispatched", "Completed", "Cancelled"];
    const counts = statuses.map(s => D.trips.filter(t => t.status === s).length);
    drawBars($("tripsChart"), statuses, counts, "#3b82f6");
    const mntCost = D.maintenance.reduce((s, m) => s + Number(m.cost), 0);
    const fuelCost = D.fuel.reduce((s, f) => s + Number(f.cost), 0);
    drawDonut($("costChart"), [{ label: "Maintenance", value: mntCost, color: "#ff7a18" }, { label: "Fuel", value: fuelCost, color: "#3b82f6" }]);
  }

  function drawBars(canvas, labels, values, color) {
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const w = canvas.width = canvas.offsetWidth || 300;
    const h = canvas.height = 220;
    ctx.clearRect(0, 0, w, h);
    const max = Math.max(...values.map(Number), 1);
    const bw = Math.min(40, (w - 40) / Math.max(labels.length, 1) - 10);
    values.forEach((v, i) => {
      const x = 30 + i * ((w - 50) / Math.max(labels.length, 1));
      const bh = (Number(v) / max) * (h - 60);
      ctx.fillStyle = color;
      ctx.beginPath();
      if (ctx.roundRect) ctx.roundRect(x, h - 30 - bh, bw, bh, 4); else ctx.rect(x, h - 30 - bh, bw, bh);
      ctx.fill();
      ctx.fillStyle = "#64748b"; ctx.font = "10px Poppins, sans-serif"; ctx.textAlign = "center";
      ctx.fillText(labels[i], x + bw / 2, h - 12);
      ctx.fillStyle = "#1f2937"; ctx.fillText(String(v), x + bw / 2, h - 36 - bh);
    });
  }

  function drawDonut(canvas, parts) {
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const w = canvas.width = canvas.offsetWidth || 300;
    const h = canvas.height = 220;
    ctx.clearRect(0, 0, w, h);
    const total = parts.reduce((s, p) => s + p.value, 0) || 1;
    let angle = -Math.PI / 2;
    const cx = w / 2 - 60, cy = h / 2, r = 70;
    parts.forEach(p => {
      const slice = (p.value / total) * Math.PI * 2;
      ctx.beginPath(); ctx.moveTo(cx, cy); ctx.arc(cx, cy, r, angle, angle + slice);
      ctx.fillStyle = p.color; ctx.fill();
      angle += slice;
    });
    ctx.beginPath(); ctx.arc(cx, cy, 40, 0, Math.PI * 2); ctx.fillStyle = "#fff"; ctx.fill();
    ctx.fillStyle = "#1f2937"; ctx.font = "bold 13px Poppins, sans-serif"; ctx.textAlign = "center";
    ctx.fillText("Costs", cx, cy + 4);
    parts.forEach((p, i) => {
      ctx.fillStyle = p.color; ctx.fillRect(cx + r + 30, 60 + i * 30, 12, 12);
      ctx.fillStyle = "#334155"; ctx.font = "11px Poppins, sans-serif"; ctx.textAlign = "left";
      ctx.fillText(`${p.label}: ₹${Math.round(p.value)}`, cx + r + 50, 70 + i * 30);
    });
  }

  // ---------- Fleet AI Assistant ----------
  (function chatInit() {
    const log = $("chatLog");
    const say = (who, text) => {
      const div = document.createElement("div");
      div.className = "chat-msg " + who;
      div.textContent = text;
      log.appendChild(div);
      log.scrollTop = log.scrollHeight;
    };
    say("bot", "Hi! I analyze your live fleet data. Ask me about high-risk vehicles, maintenance, best vehicle for a trip, licenses, fuel, delays, or drivers.");
    const answer = (q) => {
      q = q.toLowerCase();
      if (/high.?risk|risky|dangerous/.test(q)) {
        const top = maintenanceRisk().filter(x => x.risk >= 60);
        return top.length ? "High-risk vehicles:\n" + top.map(x => `• ${x.vehicle.license_plate} (${x.vehicle.model_name}) — risk ${x.risk}%, ${x.daysSinceLast > 9000 ? 'no service logged' : x.daysSinceLast + 'd since service'}`).join("\n") : "No vehicles are currently high-risk.";
      }
      if (/maintenance|service|shop/.test(q)) {
        const c = D.maintenance.length;
        const cost = D.maintenance.reduce((s, m) => s + Number(m.cost), 0);
        const inShop = D.vehicles.filter(v => v.status === "In Shop");
        return `Maintenance summary: ${c} logs, total spend ₹${Math.round(cost)}.\nVehicles in shop: ${inShop.length ? inShop.map(v => v.license_plate).join(", ") : "none"}.\nMost recent: ${D.maintenance[0] ? D.maintenance[0].description + " (" + D.maintenance[0].date + ")" : "n/a"}.`;
      }
      if (/best.*vehicle|suggest.*vehicle|which vehicle/.test(q)) {
        const cands = D.vehicles.filter(v => v.status === "Available");
        if (!cands.length) return "No vehicles are currently available.";
        const scored = cands.map(v => {
          const f = fuelStats().find(x => x.vehicle && x.vehicle.id === v.id);
          return { v, score: v.max_capacity_kg / 1000 + (f ? f.kmpl : 8) };
        }).sort((a, b) => b.score - a.score);
        const top = scored[0].v;
        return `Recommended vehicle: ${top.license_plate} (${top.model_name}, capacity ${top.max_capacity_kg} kg, odometer ${top.odometer}). It is available and has the best capacity/efficiency balance.`;
      }
      if (/license|expir|compliance/.test(q)) {
        const exp = D.drivers.filter(d => new Date(d.license_expiry_date) < today);
        const soon = D.drivers.filter(d => { const days = (new Date(d.license_expiry_date) - today) / 86400000; return days >= 0 && days < 30; });
        return `Expired licenses: ${exp.length ? exp.map(d => d.name).join(", ") : "none"}.\nExpiring within 30 days: ${soon.length ? soon.map(d => d.name).join(", ") : "none"}.\nSuspended: ${D.drivers.filter(d => d.status === "Suspended").map(d => d.name).join(", ") || "none"}.`;
      }
      if (/fuel|efficien|km\/?l|liter/.test(q)) {
        const s = fuelStats();
        if (!s.length) return "No fuel logs recorded yet.";
        const best = s.slice().sort((a, b) => b.kmpl - a.kmpl)[0];
        return `Fuel leaders: ${s.slice().sort((a, b) => b.kmpl - a.kmpl).slice(0, 3).map(x => x.vehicle.license_plate + " ~" + x.kmpl.toFixed(1) + " km/L").join(", ")}.\nBest: ${best.vehicle.license_plate}.`;
      }
      if (/delay|late/.test(q)) {
        return "Delay-prone factors: vehicles In Shop, drivers with safety score < 70, near-capacity cargo, expired licenses. See the Trip Delay Prediction panel for per-trip risk.";
      }
      if (/driver|performance|safety/.test(q)) {
        const top = D.drivers.slice().sort((a, b) => (b.safety_score || 0) - (a.safety_score || 0)).slice(0, 3);
        return "Top drivers by safety score:\n" + top.map(d => `• ${d.name} — ${d.safety_score} (${d.status})`).join("\n");
      }
      if (/available|free/.test(q)) {
        const avail = D.vehicles.filter(v => v.status === "Available");
        return avail.length ? "Available vehicles:\n" + avail.map(v => `• ${v.license_plate} (${v.model_name}, ${v.max_capacity_kg} kg)`).join("\n") : "No vehicles available right now.";
      }
      if (/cost|expense|money|spend/.test(q)) {
        const m = D.maintenance.reduce((s, x) => s + Number(x.cost), 0);
        const f = D.fuel.reduce((s, x) => s + Number(x.cost), 0);
        return `Operational spend: maintenance ₹${Math.round(m)}, fuel ₹${Math.round(f)}, total ₹${Math.round(m + f)}.`;
      }
      return "I can help with: high-risk vehicles, maintenance summary, best vehicle for a trip, license/compliance, fuel efficiency, delays, drivers, availability, and costs.";
    };
    const send = () => {
      const q = $("chatInput").value.trim();
      if (!q) return;
      say("user", q);
      $("chatInput").value = "";
      setTimeout(() => say("bot", answer(q)), 250);
    };
    $("chatSend").addEventListener("click", send);
    $("chatInput").addEventListener("keydown", (e) => { if (e.key === "Enter") send(); });
  })();

  // ---------- Live polling from backend ----------
  function renderAll() {
    kpis();
    fuelInit();
    predMaint();
    driverPerf();
    alerts();
    delayPred();
    charts();
    updateTracking();
  }
  async function poll() {
    try {
      const res = await fetch("/api/fleet/data", { headers: { "Accept": "application/json" } });
      if (!res.ok) return;
      D = await res.json();
      renderAll();
    } catch (e) { /* keep stale data */ }
  }
  renderAll();
  buildTracking();
  updateTracking();
  poll();
  setInterval(poll, 3000);
})();
