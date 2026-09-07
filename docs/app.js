/* Renderiza docs/data/stats.json. Sem dependencias, sem pedidos a terceiros.
   O site nao calcula nada: o que esta no ecra e exactamente o que esta no
   ficheiro versionado, para que qualquer numero seja contestavel contra um
   commit concreto. */

(function () {
  "use strict";

  var BAR_COLOURS = ["var(--bar-1)", "var(--bar-2)", "var(--bar-3)", "var(--bar-4)"];
  var state = { stats: null, topic: null, reading: "shared_equal" };

  function pad(n) { return n < 10 ? "0" + n : String(n); }

  function timecode(seconds) {
    var s = Math.max(0, Math.round(seconds));
    return String(Math.floor(s / 3600)) + ":" + pad(Math.floor((s % 3600) / 60)) + ":" + pad(s % 60);
  }

  function days(seconds) { return (seconds / 86400).toFixed(1); }

  function monthLabel(iso) {
    var parts = iso.split("-");
    return parts[1] + "/" + parts[0].slice(2);
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
      el("p", { text: "Nao ha blocos recolhidos para " + topic.name + "." })
    ]));
  }

  /* Manchete: tempo de relogio. Um bloco com dois intervenientes conta uma
     vez, nunca duas. A leitura rateada ou integral so faz sentido ao nivel
     do interveniente e e la que o selector aparece. */
  function renderHero(panel, topic) {
    var total = topic.totals.airtime_s;
    panel.appendChild(el("p", { class: "question", text: topic.question }));
    panel.appendChild(el("p", { class: "hero-figure", text: timecode(total) }));
    panel.appendChild(el("p", {
      class: "hero-caption",
      text: "de emissao contabilizada entre " + topic.first_record + " e " +
            topic.last_record + ", em " + topic.totals.blocks +
            " blocos. Equivale a " + days(total) + " dias de emissao continua."
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
        ? "Um bloco partilhado e dividido em partes iguais pelos intervenientes."
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
      '" role="img" aria-label="Tempo de emissao por mes">';
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
      el("h2", { text: "Por mes" }),
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
            el("th", { class: "num", text: "Emissao" }),
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
      "Ultima recolha: " + stats.generated_at.replace("T", " ").replace("+00:00", " UTC");
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
      /* Estado vazio explicito. Nunca mostrar dados de exemplo: um site de
         factos que inventa numeros para a demo perde o unico argumento que tem. */
      document.getElementById("panel").innerHTML =
        '<div class="empty"><h2>Dados indisponiveis</h2>' +
        '<p>Nao foi possivel carregar <code>data/stats.json</code>. ' +
        'Correr <code>python -m collector.main</code> para gerar o ficheiro.</p></div>';
    });
})();
