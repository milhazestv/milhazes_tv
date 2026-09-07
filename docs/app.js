/* Renderiza docs/data/stats.json. Sem dependências, sem pedidos a terceiros.
   O site não calcula nada de opinativo: os totais vêm todos do ficheiro
   versionado, para que qualquer número seja contestável contra um commit
   concreto. As únicas contas feitas aqui são somas de um período (semana,
   mês, ano, ou desde o início) a partir das repartições diárias que já
   vêm prontas no stats.json — nenhuma agregação nova é inventada no
   browser. */

(function () {
  "use strict";

  var CORES = ["var(--bar-1)", "var(--bar-2)", "var(--bar-3)", "var(--bar-4)", "var(--bar-5)"];
  var MESES = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"
  ];

  // period.id -> { tab: texto curto no botão, frase: texto médio da frase }
  var PERIODOS = [
    { id: "week", tab: "Esta semana", frase: "esta semana" },
    { id: "month", tab: "Este mês", frase: "este mês" },
    { id: "year", tab: "Este ano", frase: "este ano" },
    { id: "all", tab: "Desde a guerra", frase: "desde o início da guerra Ucrânia-Rússia" }
  ];

  var state = { stats: null, topic: null, reading: "shared_equal", period: "month" };

  function pad(n) { return n < 10 ? "0" + n : String(n); }

  function timecode(seconds) {
    var s = Math.max(0, Math.round(seconds));
    return String(Math.floor(s / 3600)) + ":" + pad(Math.floor((s % 3600) / 60)) + ":" + pad(s % 60);
  }

  function humanDuration(seconds) {
    var s = Math.max(0, Math.round(seconds));
    if (s < 60) { return "menos de um minuto"; }
    var h = Math.floor(s / 3600);
    var m = Math.floor((s % 3600) / 60);
    var horas = h === 1 ? "1 hora" : h + " horas";
    var minutos = m === 1 ? "1 minuto" : m + " minutos";
    if (h === 0) { return minutos; }
    if (m === 0) { return horas; }
    return horas + " e " + minutos;
  }

  function days(seconds) { return (seconds / 86400).toFixed(1); }

  function isoDate(date) {
    return date.getFullYear() + "-" + pad(date.getMonth() + 1) + "-" + pad(date.getDate());
  }

  function startOfWeek(date) {
    var d = new Date(date);
    var day = d.getDay();
    var diff = day === 0 ? -6 : 1 - day;
    d.setDate(d.getDate() + diff);
    return d;
  }

  function formatDatePT(date) {
    return date.getDate() + " de " + MESES[date.getMonth()];
  }

  function monthLabel(iso) {
    var parts = iso.split("-");
    return parts[1] + "/" + parts[0].slice(2);
  }

  function capitalize(text) {
    return text.charAt(0).toUpperCase() + text.slice(1);
  }

  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (key) {
      if (key === "text") { node.textContent = attrs[key]; }
      else if (key === "html") { node.innerHTML = attrs[key]; }
      else { node.setAttribute(key, attrs[key]); }
    });
    (children || []).forEach(function (child) { node.appendChild(child); });
    return node;
  }

  function currentTopic() {
    return state.stats.topics.filter(function (t) { return t.id === state.topic; })[0];
  }

  /* Intervalo [de, até] do período escolhido, em datas ISO, mais o texto
     que aparece por baixo do número grande. */
  function periodRange(topic, periodId) {
    var today = new Date();
    var from;

    if (periodId === "week") {
      from = startOfWeek(today);
    } else if (periodId === "year") {
      from = new Date(today.getFullYear(), 0, 1);
    } else if (periodId === "all") {
      var parts = (topic.since || "2022-02-24").split("-").map(Number);
      from = new Date(parts[0], parts[1] - 1, parts[2]);
    } else {
      from = new Date(today.getFullYear(), today.getMonth(), 1);
    }

    return { fromIso: isoDate(from), toIso: isoDate(today), fromDate: from, toDate: today };
  }

  function sumRange(byDay, fromIso, toIso, field) {
    var seconds = 0;
    var blocks = 0;
    byDay.forEach(function (day) {
      if (day.date < fromIso || day.date > toIso) { return; }
      seconds += day[field];
      blocks += day.blocks;
    });
    return { seconds: seconds, blocks: blocks };
  }

  function sumSubjectsInRange(topic, fromIso, toIso, reading) {
    var totals = {};
    (topic.subject_by_day || []).forEach(function (day) {
      if (day.date < fromIso || day.date > toIso) { return; }
      Object.keys(day.subjects).forEach(function (sid) {
        totals[sid] = (totals[sid] || 0) + day.subjects[sid][reading];
      });
    });
    return totals;
  }

  function sumProgramsInRange(topic, fromIso, toIso) {
    var totals = {};
    (topic.program_by_day || []).forEach(function (day) {
      if (day.date < fromIso || day.date > toIso) { return; }
      Object.keys(day.programs).forEach(function (prog) {
        totals[prog] = (totals[prog] || 0) + day.programs[prog].airtime_s;
      });
    });
    return totals;
  }

  // ---- gráfico circular, em SVG puro -------------------------------

  function polarToCartesian(cx, cy, r, angleDeg) {
    var rad = (angleDeg * Math.PI) / 180;
    return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
  }

  function arcPath(cx, cy, r, startAngle, endAngle) {
    var start = polarToCartesian(cx, cy, r, startAngle);
    var end = polarToCartesian(cx, cy, r, endAngle);
    var largeArc = endAngle - startAngle > 180 ? 1 : 0;
    return [
      "M", cx, cy,
      "L", start.x.toFixed(2), start.y.toFixed(2),
      "A", r, r, 0, largeArc, 1, end.x.toFixed(2), end.y.toFixed(2),
      "Z"
    ].join(" ");
  }

  /* entries: [{label, seconds, blocks}], já sem os de valor zero.
     Devolve null se não houver nada para mostrar. */
  function renderPie(entries, opts) {
    var total = entries.reduce(function (sum, e) { return sum + e.seconds; }, 0);
    if (total <= 0) { return null; }

    var size = 200;
    var cx = size / 2, cy = size / 2, r = 90;
    var svg = '<svg class="pie" viewBox="0 0 ' + size + " " + size +
      '" role="img" aria-label="' + (opts.ariaLabel || "Gráfico circular") + '">';

    if (entries.length === 1) {
      svg += '<circle cx="' + cx + '" cy="' + cy + '" r="' + r + '" fill="' + CORES[0] + '"></circle>';
    } else {
      var angle = -90;
      entries.forEach(function (e, i) {
        var sliceAngle = (e.seconds / total) * 360;
        var path = arcPath(cx, cy, r, angle, angle + sliceAngle);
        svg += '<path d="' + path + '" fill="' + CORES[i % CORES.length] + '">' +
          "<title>" + e.label + ": " + humanDuration(e.seconds) + "</title></path>";
        angle += sliceAngle;
      });
    }
    svg += "</svg>";

    var legend = el("ul", { class: "pie-legend" });
    entries.forEach(function (e, i) {
      var pct = Math.round((e.seconds / total) * 100);
      var dot = el("span", { class: "pie-dot" });
      dot.style.background = CORES[i % CORES.length];
      legend.appendChild(el("li", {}, [
        dot,
        el("span", { class: "pie-legend-label", text: e.label }),
        el("span", { class: "pie-legend-value", text: pct + "% · " + humanDuration(e.seconds) })
      ]));
    });

    var wrap = el("div", { class: "pie-wrap" }, [
      el("div", { class: "pie-svg", html: svg }),
      legend
    ]);
    return wrap;
  }

  // ---- secções da página --------------------------------------------

  function renderTabs() {
    var nav = document.getElementById("topics");
    nav.innerHTML = "";
    state.stats.topics.forEach(function (topic) {
      var tab = el("button", {
        class: "topic-tab",
        type: "button",
        role: "tab",
        "aria-selected": String(topic.id === state.topic),
        text: topic.name
      });
      tab.addEventListener("click", function () {
        state.topic = topic.id;
        renderTabs();
        renderPanel();
      });
      nav.appendChild(tab);
    });
  }

  function renderEmpty(panel, topic) {
    panel.appendChild(el("div", { class: "empty" }, [
      el("h2", { text: "Ainda sem dados" }),
      el("p", { text: "Ainda não há nada registado para " + topic.name + "." })
    ]));
  }

  function renderPeriodSelector(panel) {
    var selector = el("div", { class: "period-selector", role: "tablist", "aria-label": "Período" });
    PERIODOS.forEach(function (p) {
      var button = el("button", {
        class: "period-btn",
        type: "button",
        role: "tab",
        "aria-selected": String(p.id === state.period),
        text: p.tab
      });
      button.addEventListener("click", function () {
        state.period = p.id;
        renderPanel();
      });
      selector.appendChild(button);
    });
    panel.appendChild(selector);
  }

  /* Frase grande: "Este mês já tivemos 4 horas e 22 minutos de
     Infotainment de Guerra na TV." — o número muda com o período
     escolhido, nunca é o total acumulado disfarçado de outra coisa. */
  function renderHero(panel, topic, range) {
    var periodo = PERIODOS.filter(function (p) { return p.id === state.period; })[0];
    var totals = sumRange(topic.by_day, range.fromIso, range.toIso, "airtime_s");

    var frase = totals.seconds > 0
      ? capitalize(periodo.frase) + " já tivemos"
      : capitalize(periodo.frase) + " ainda não houve";

    panel.appendChild(el("p", { class: "hero-lead", text: frase }));
    panel.appendChild(el("p", {
      class: "hero-figure",
      text: totals.seconds > 0 ? humanDuration(totals.seconds) : "nada registado"
    }));
    panel.appendChild(el("p", { class: "hero-tail", text: "de " + topic.name + " na TV." }));

    if (totals.seconds > 0) {
      var vezes = totals.blocks === 1 ? "1 vez" : totals.blocks + " vezes";
      panel.appendChild(el("p", {
        class: "hero-caption",
        text: "Foi para o ar " + vezes + " " + periodo.frase + "."
      }));
    }

    return totals;
  }

  function renderProgramPie(panel, topic, range) {
    var totals = sumProgramsInRange(topic, range.fromIso, range.toIso);
    var entries = Object.keys(totals)
      .map(function (program) { return { label: program, seconds: totals[program] }; })
      .filter(function (e) { return e.seconds > 0; })
      .sort(function (a, b) { return b.seconds - a.seconds; });

    var periodo = PERIODOS.filter(function (p) { return p.id === state.period; })[0];
    var section = el("section", {}, [
      el("h2", { text: "Em que programas apareceu" }),
      el("p", { class: "section-caption", text: "Como se reparte o tempo " + periodo.frase + "." })
    ]);

    var pie = renderPie(entries, { ariaLabel: "Tempo por programa" });
    if (pie) {
      section.appendChild(pie);
    } else {
      section.appendChild(el("p", { class: "section-caption", text: "Sem dados para este período." }));
    }
    panel.appendChild(section);
  }

  function renderSubjectPie(panel, topic, range) {
    if (!topic.subjects.length) { return; }

    var section = el("section", {}, [el("h2", { text: "Quem fala mais tempo" })]);

    var readings = el("div", { class: "readings" }, [el("span", { text: "Como contar:" })]);
    [["shared_equal", "Tempo dividido"], ["each_full", "Tempo completo"]].forEach(function (pair) {
      var button = el("button", {
        class: "reading-btn",
        type: "button",
        "aria-pressed": String(state.reading === pair[0]),
        text: pair[1]
      });
      button.addEventListener("click", function () {
        state.reading = pair[0];
        renderPanel();
      });
      readings.appendChild(button);
    });
    section.appendChild(readings);
    section.appendChild(el("p", {
      class: "section-caption",
      text: state.reading === "shared_equal"
        ? "Quando os dois aparecem juntos, o tempo é dividido a meio entre eles."
        : "Quando os dois aparecem juntos, cada um fica com o tempo todo do bloco."
    }));

    var totals = sumSubjectsInRange(topic, range.fromIso, range.toIso, state.reading);
    var entries = topic.subjects
      .map(function (subject) {
        return { label: subject.name, seconds: totals[subject.id] || 0 };
      })
      .filter(function (e) { return e.seconds > 0; })
      .sort(function (a, b) { return b.seconds - a.seconds; });

    var pie = renderPie(entries, { ariaLabel: "Tempo por pessoa" });
    if (pie) {
      section.appendChild(pie);
    } else {
      section.appendChild(el("p", { class: "section-caption", text: "Sem dados para este período." }));
    }
    panel.appendChild(section);
  }

  /* Não é filtrado pelo período escolhido — mostra sempre a evolução
     completa, porque a pergunta aqui é outra: está a crescer? */
  function renderEvolucao(panel, topic) {
    if (!topic.by_month.length) { return; }

    var months = topic.by_month;
    var max = Math.max.apply(null, months.map(function (m) { return m.airtime_s; }));
    var width = 1000, height = 220, padBottom = 26;
    var slot = width / months.length;

    var svg = '<svg class="chart" viewBox="0 0 ' + width + " " + height +
      '" role="img" aria-label="Como o tempo de emissão cresceu desde 2022">';
    months.forEach(function (month, i) {
      var barHeight = max ? (month.airtime_s / max) * (height - padBottom - 6) : 0;
      svg += '<rect x="' + (i * slot + slot * 0.15).toFixed(1) +
        '" y="' + (height - padBottom - barHeight).toFixed(1) +
        '" width="' + (slot * 0.7).toFixed(1) +
        '" height="' + barHeight.toFixed(1) + '"><title>' + month.month + ": " +
        humanDuration(month.airtime_s) + "</title></rect>";
      if (months.length < 40 || i % 4 === 0) {
        svg += '<text class="axis" x="' + (i * slot + slot / 2).toFixed(1) +
          '" y="' + (height - 8) + '" text-anchor="middle">' +
          monthLabel(month.month) + "</text>";
      }
    });
    svg += '<line class="baseline" x1="0" y1="' + (height - padBottom) +
      '" x2="' + width + '" y2="' + (height - padBottom) + '"/></svg>';

    panel.appendChild(el("section", {}, [
      el("h2", { text: "Como tem crescido desde 2022" }),
      el("p", { class: "section-caption", text: "Cada barra é um mês. Quanto mais alta, mais tempo esteve no ar." }),
      el("div", { html: svg })
    ]));
  }

  function renderPanel() {
    var panel = document.getElementById("panel");
    var topic = currentTopic();
    panel.innerHTML = "";
    if (!topic) { return; }
    if (!topic.totals.blocks) { renderEmpty(panel, topic); return; }

    var range = periodRange(topic, state.period);
    renderPeriodSelector(panel);
    renderHero(panel, topic, range);
    renderProgramPie(panel, topic, range);
    renderSubjectPie(panel, topic, range);
    renderEvolucao(panel, topic);
  }

  function boot(stats) {
    state.stats = stats;
    state.reading = stats.default_attribution || "shared_equal";
    state.topic = stats.topics.length ? stats.topics[0].id : null;
    document.getElementById("generated").textContent =
      "Última recolha: " + stats.generated_at.replace("T", " ").replace("+00:00", " UTC");
    renderTabs();
    renderPanel();
  }

  fetch("data/stats.json", { cache: "no-cache" })
    .then(function (response) {
      if (!response.ok) { throw new Error("HTTP " + response.status); }
      return response.json();
    })
    .then(boot)
    .catch(function () {
      document.getElementById("panel").innerHTML =
        '<div class="empty"><h2>Dados indisponíveis</h2>' +
        '<p>Não foi possível carregar <code>data/stats.json</code>. ' +
        "Correr <code>python -m collector.main</code> para gerar o ficheiro.</p></div>";
    });
})();
