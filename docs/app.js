/* Renderiza docs/data/stats.json. Sem dependências, sem pedidos a terceiros.
   O site não calcula nada de opinativo: os totais vêm todos do ficheiro
   versionado, para que qualquer número seja contestável contra um commit
   concreto. As únicas contas feitas aqui são somas de períodos, a partir
   de by_day, que já vem agregado no stats.json. */

(function () {
  "use strict";

  var BAR_COLOURS = ["var(--bar-1)", "var(--bar-2)", "var(--bar-3)", "var(--bar-4)"];
  var MESES = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"
  ];
  var PERIODOS = [
    { id: "day", label: "Hoje" },
    { id: "week", label: "Esta semana" },
    { id: "month", label: "Este mês" }
  ];

  var state = { stats: null, topic: null, reading: "shared_equal", period: "week" };

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

  /* Soma os dias de by_day que caem dentro do período escolhido.
     "Hoje" e "esta semana" usam a data local de quem visita o site;
     é uma aproximação aceitável para este fim, não um relógio de emissão. */
  function periodTotals(topic, period) {
    var today = new Date();
    var from, to = today, label;

    if (period === "day") {
      from = today;
      label = "hoje, " + formatDatePT(today);
    } else if (period === "month") {
      from = new Date(today.getFullYear(), today.getMonth(), 1);
      label = "em " + MESES[today.getMonth()];
    } else {
      from = startOfWeek(today);
      label = "de " + formatDatePT(from) + " a " + formatDatePT(to);
    }

    var fromIso = isoDate(from);
    var toIso = isoDate(to);
    var seconds = 0;
    var blocks = 0;

    topic.by_day.forEach(function (day) {
      if (day.date >= fromIso && day.date <= toIso) {
        seconds += day.airtime_s;
        blocks += day.blocks;
      }
    });

    return { seconds: seconds, blocks: blocks, label: label };
  }

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
      el("h2", { text: "Ainda sem registos" }),
      el("p", { text: "Não há blocos recolhidos para " + topic.name + "." })
    ]));
  }

  /* Cabeçalho: o número do período escolhido, não o total acumulado.
     "Esta semana já tivemos 3 horas de Infotainment de Guerra na TV." */
  function renderHero(panel, topic) {
    var period = periodTotals(topic, state.period);
    var periodoAtivo = PERIODOS.filter(function (p) { return p.id === state.period; })[0];

    var selector = el("div", { class: "period-selector", role: "tablist", "aria-label": "Período" });
    PERIODOS.forEach(function (p) {
      var button = el("button", {
        class: "period-btn",
        type: "button",
        role: "tab",
        "aria-selected": String(p.id === state.period),
        text: p.label
      });
      button.addEventListener("click", function () {
        state.period = p.id;
        renderPanel();
      });
      selector.appendChild(button);
    });
    panel.appendChild(selector);

    var frase = period.seconds > 0
      ? capitalize(periodoAtivo.label.toLowerCase()) + " já tivemos"
      : capitalize(periodoAtivo.label.toLowerCase()) + " ainda não houve";

    panel.appendChild(el("p", { class: "hero-lead", text: frase }));
    panel.appendChild(el("p", {
      class: "hero-figure",
      text: period.seconds > 0 ? humanDuration(period.seconds) : "registos"
    }));
    panel.appendChild(el("p", { class: "hero-tail", text: "de " + topic.name + " na TV." }));
    panel.appendChild(el("p", {
      class: "hero-caption",
      text: (period.blocks === 1 ? "1 bloco" : period.blocks + " blocos") + " " + period.label + "."
    }));

    panel.appendChild(el("p", {
      class: "hero-cumulative",
      text: "Desde " + topic.since + ", o total acumulado é de " + timecode(topic.totals.airtime_s) +
            " em " + topic.totals.blocks + " blocos — o equivalente a " + days(topic.totals.airtime_s) +
            " dias de emissão contínua."
    }));
  }

  function renderSubjects(panel, topic) {
    if (!topic.subjects.length) { return; }

    var max = Math.max.apply(null, topic.subjects.map(function (s) {
      return s.totals[state.reading];
    }).concat([1]));

    var section = el("section", {}, [el("h2", { text: "Por interveniente" })]);

    var readings = el("div", { class: "readings" }, [el("span", { text: "Leitura:" })]);
    [["shared_equal", "Tempo rateado"], ["each_full", "Bloco integral"]].forEach(function (pair) {
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
      class: "subject-meta",
      text: state.reading === "shared_equal"
        ? "Um bloco partilhado é dividido em partes iguais pelos intervenientes."
        : "Cada bloco conta por inteiro para cada interveniente presente."
    }));

    topic.subjects.forEach(function (subject, index) {
      var value = subject.totals[state.reading];
      var fill = el("span", { class: "subject-fill" });
      fill.style.width = (value / max * 100) + "%";
      fill.style.background = BAR_COLOURS[index % BAR_COLOURS.length];

      section.appendChild(el("div", { class: "subject" }, [
        el("div", { class: "subject-head" }, [
          el("span", { class: "subject-name", text: subject.name }),
          el("span", { class: "subject-time", text: timecode(value) })
        ]),
        el("div", { class: "subject-track" }, [fill]),
        el("p", { class: "subject-meta", text: subject.totals.blocks + " blocos" })
      ]));
    });

    panel.appendChild(section);
  }

  function renderMonthly(panel, topic) {
    if (!topic.by_month.length) { return; }

    var months = topic.by_month;
    var max = Math.max.apply(null, months.map(function (m) { return m.airtime_s; }));
    var width = 1000;
    var height = 260;
    var padBottom = 26;
    var slot = width / months.length;

    var svg = '<svg class="chart" viewBox="0 0 ' + width + ' ' + height +
      '" role="img" aria-label="Tempo de emissão por mês">';
    months.forEach(function (month, i) {
      var barHeight = max ? (month.airtime_s / max) * (height - padBottom - 6) : 0;
      svg += '<rect x="' + (i * slot + slot * 0.15).toFixed(1) +
        '" y="' + (height - padBottom - barHeight).toFixed(1) +
        '" width="' + (slot * 0.7).toFixed(1) +
        '" height="' + barHeight.toFixed(1) + '"><title>' + month.month + ": " +
        timecode(month.airtime_s) + '</title></rect>';
      if (months.length < 40 || i % 3 === 0) {
        svg += '<text class="axis" x="' + (i * slot + slot / 2).toFixed(1) +
          '" y="' + (height - 8) + '" text-anchor="middle">' +
          monthLabel(month.month) + '</text>';
      }
    });
    svg += '<line class="baseline" x1="0" y1="' + (height - padBottom) +
      '" x2="' + width + '" y2="' + (height - padBottom) + '"/></svg>';

    panel.appendChild(el("section", {}, [
      el("h2", { text: "Por mês" }),
      el("div", { html: svg })
    ]));
  }

  function renderPrograms(panel, topic) {
    if (!topic.by_program.length) { return; }

    var body = el("tbody");
    topic.by_program.forEach(function (row) {
      body.appendChild(el("tr", {}, [
        el("td", { text: row.program || "Sem programa" }),
        el("td", { class: "num", text: timecode(row.airtime_s) }),
        el("td", { class: "num", text: String(row.blocks) })
      ]));
    });

    panel.appendChild(el("section", {}, [
      el("h2", { text: "Por programa" }),
      el("table", {}, [
        el("thead", {}, [
          el("tr", {}, [
            el("th", { text: "Programa" }),
            el("th", { class: "num", text: "Emissão" }),
            el("th", { class: "num", text: "Blocos" })
          ])
        ]),
        body
      ])
    ]));
  }

  function renderPanel() {
    var panel = document.getElementById("panel");
    var topic = currentTopic();
    panel.innerHTML = "";
    if (!topic) { return; }
    if (!topic.totals.blocks) { renderEmpty(panel, topic); return; }
    renderHero(panel, topic);
    renderSubjects(panel, topic);
    renderMonthly(panel, topic);
    renderPrograms(panel, topic);
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
      /* Estado vazio explícito. Nunca mostrar dados de exemplo: um site de
         factos que inventa números para a demonstração perde o único
         argumento que tem. */
      document.getElementById("panel").innerHTML =
        '<div class="empty"><h2>Dados indisponíveis</h2>' +
        '<p>Não foi possível carregar <code>data/stats.json</code>. ' +
        'Correr <code>python -m collector.main</code> para gerar o ficheiro.</p></div>';
    });
})();
