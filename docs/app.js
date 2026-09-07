/* Renderiza docs/data/stats.json. Sem dependências, sem pedidos a terceiros.
   O site não calcula nada de opinativo: os totais vêm todos do ficheiro
   versionado, para que qualquer número seja contestável contra um commit
   concreto. As únicas contas feitas aqui são somas de um período (semana,
   mês, ano, ou desde o início) a partir das repartições diárias que já
   vêm prontas no stats.json. Nenhuma agregação nova é inventada no
   browser. */

(function () {
  "use strict";

  var CORES = ["var(--bar-1)", "var(--bar-2)", "var(--bar-3)", "var(--bar-4)", "var(--bar-5)"];

  // Utilitarios partilhados com o calendario. Ver common.js.
  var MESES = MTV.MESES;
  var pad = MTV.pad;
  var humanDuration = MTV.humanDuration;
  var isoDate = MTV.isoDate;
  var monthNameLabel = MTV.monthNameLabel;
  var capitalize = MTV.capitalize;
  var el = MTV.el;
  var nameHtml = MTV.nameHtml;

  // period.id -> { tab: texto curto no botão, frase: texto médio da frase }
  var PERIODOS = [
    { id: "week", tab: "Esta semana", frase: "esta semana" },
    { id: "month", tab: "Este mês", frase: "este mês" },
    { id: "year", tab: "Este ano", frase: "este ano" },
    { id: "all", tab: "Desde a guerra", frase: "desde o início da guerra Ucrânia-Rússia" }
  ];

  var state = { stats: null, topic: null, period: "month" };

  function startOfWeek(date) {
    var d = new Date(date);
    var day = d.getDay();
    var diff = day === 0 ? -6 : 1 - day;
    d.setDate(d.getDate() + diff);
    return d;
  }

  function monthLabel(iso) {
    var parts = iso.split("-");
    return parts[1] + "/" + parts[0].slice(2);
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
        el("span", { class: "pie-legend-label", html: nameHtml(e.label) }),
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
        html: nameHtml(topic.name)
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
      el("p", { html: "Ainda não há nada registado para " + nameHtml(topic.name) + "." })
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
     Infotainment de Guerra na TV." O número muda com o período
     escolhido, nunca é o total acumulado disfarçado de outra coisa. */
  function renderHero(panel, topic, range) {
    var periodo = PERIODOS.filter(function (p) { return p.id === state.period; })[0];
    var totals = sumRange(topic.by_day, range.fromIso, range.toIso, "airtime_s");

    var frase = totals.seconds > 0
      ? capitalize(periodo.frase) + " já tivemos"
      : capitalize(periodo.frase) + " ainda não houve";

    // O número grande vive num cartão próprio, para poder ser destacado
    // do resto da página pelo CSS sem depender da ordem dos irmãos.
    var card = el("div", { class: "hero-card" });
    card.appendChild(el("p", { class: "hero-lead", text: frase }));
    card.appendChild(el("p", {
      class: "hero-figure",
      text: totals.seconds > 0 ? humanDuration(totals.seconds) : "nada registado"
    }));
    card.appendChild(el("p", { class: "hero-tail", html: "de " + nameHtml(topic.name) + " na TV." }));

    if (totals.seconds > 0) {
      var vezes = totals.blocks === 1 ? "1 vez" : totals.blocks + " vezes";
      card.appendChild(el("p", {
        class: "hero-caption",
        text: "Foi para o ar " + vezes + " " + periodo.frase + "."
      }));
    }
    panel.appendChild(card);

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
      el("h2", { text: "Em que programas aconteceu" }),
      el("p", { class: "section-caption", text: "Como se reparte o tempo " + periodo.frase + "." })
    ]);

    var pie = renderPie(entries, { ariaLabel: "Tempo por programa" });
    if (pie) {
      section.appendChild(pie);
    } else {
      section.appendChild(el("p", { class: "section-caption", text: "Sem dados para este período." }));
    }

    /* O calendário é a pergunta seguinte desta secção, em que dias cada
       programa foi para o ar, por isso vive aqui e não no rodapé, onde
       ninguém o encontrava. Não é filtrado pelo período escolhido: a
       página mostra sempre o histórico ano a ano, e o texto diz isso
       para que a ligação não prometa o que a página não faz. */
    section.appendChild(el("p", { class: "section-link" }, [
      el("a", {
        href: "calendario.html",
        text: "Ver o calendário de emissões, dia a dia, ano a ano"
      })
    ]));

    panel.appendChild(section);
  }

  /* Barras horizontais medidas contra o tempo de emissão do período.
     Existe uma razão de fundo para não ser um circular: no tempo no ar
     as parcelas somam mais do que o tempo que houve de televisão, e um
     circular afirma visualmente que as fatias são partes de um todo.
     Seria um desenho a dizer uma coisa que os dados não dizem. */
  function renderAirtimeBars(entries, totalAirtime) {
    var list = el("ul", { class: "bars" });
    entries.forEach(function (e, i) {
      var ratio = totalAirtime > 0 ? e.seconds / totalAirtime : 0;
      var fill = el("span", { class: "bar-fill" });
      fill.style.width = (ratio * 100).toFixed(1) + "%";
      fill.style.background = CORES[i % CORES.length];
      list.appendChild(el("li", {}, [
        el("span", { class: "bar-label", html: nameHtml(e.label) }),
        el("span", { class: "bar-track" }, [fill]),
        el("span", {
          class: "bar-value",
          text: humanDuration(e.seconds) + " · " + Math.round(ratio * 100) + "% do tempo emitido"
        })
      ]));
    });
    return list;
  }

  /* O site publica uma só leitura por pessoa, o tempo no ar. A leitura
     repartida (shared_equal) continua a ser calculada, guardada no
     stats.json e definida na Metodologia, mas deixou de aparecer aqui:
     duas grandezas com a mesma unidade, lado a lado, faziam o leitor
     comum ler dois números diferentes para a mesma pergunta.

     Quem quiser a leitura repartida tem-na no dataset e na Metodologia.
     Não voltar a pô-la no site sem resolver esse problema de leitura.

     Nenhum texto aqui pode assumir que há exatamente duas pessoas: o
     número de intervenientes vem da configuração e pode mudar sem que
     ninguém se lembre desta frase. */
  function renderSubjects(panel, topic, range) {
    if (!topic.subjects.length) { return; }

    var totalAirtime = sumRange(topic.by_day, range.fromIso, range.toIso, "airtime_s").seconds;
    var noAr = sumSubjectsInRange(topic, range.fromIso, range.toIso, "each_full");

    function entriesFrom(totals) {
      return topic.subjects
        .map(function (subject) {
          return { label: subject.name, seconds: totals[subject.id] || 0 };
        })
        .filter(function (e) { return e.seconds > 0; })
        .sort(function (a, b) { return b.seconds - a.seconds; });
    }

    var section = el("section", {}, [el("h2", { text: "Quem esteve mais tempo no ar" })]);

    var noArEntries = entriesFrom(noAr);
    if (!noArEntries.length) {
      section.appendChild(el("p", { class: "section-caption", text: "Sem dados para este período." }));
      panel.appendChild(section);
      return;
    }

    section.appendChild(el("p", {
      class: "section-caption",
      text: "Quanto tempo cada pessoa esteve no ar. Um bloco com mais do que "
        + "uma pessoa conta por inteiro para cada uma delas, porque todas "
        + "estiveram lá o tempo todo. Por isso estes tempos sobrepõem-se e "
        + "não se somam."
    }));
    section.appendChild(renderAirtimeBars(noArEntries, totalAirtime));

    panel.appendChild(section);
  }

  /* Não é filtrado pelo período escolhido: mostra sempre a evolução
     completa, porque a pergunta aqui é outra: está a crescer?

     O tooltip nativo do SVG (<title>) foi substituído por uma linha de
     leitura própria. O nativo demora quase um segundo a aparecer e não
     se controla. Cada mês tem uma área de toque de altura inteira, para
     que apanhar um mês fraco não exija acertar numa barra de cinco
     pixels, e é focável por teclado, para que o gráfico nunca seja a
     única forma de chegar ao número. */
  function renderEvolucao(panel, topic) {
    if (!topic.by_month.length) { return; }

    var months = topic.by_month;
    var max = Math.max.apply(null, months.map(function (m) { return m.airtime_s; }));
    var width = 1000, height = 210, padBottom = 28, padTop = 6;
    var plot = height - padBottom - padTop;
    var slot = width / months.length;

    var svg = '<svg class="chart" viewBox="0 0 ' + width + " " + height +
      '" role="group" aria-label="Tempo de emissão mês a mês">';

    var seenYears = {};
    months.forEach(function (month, i) {
      var barHeight = max ? (month.airtime_s / max) * plot : 0;
      var x = i * slot;
      var vezes = month.blocks === 1 ? "1 vez no ar" : month.blocks + " vezes no ar";
      var label = capitalize(monthNameLabel(month.month)) + ", " +
        humanDuration(month.airtime_s) + ", " + vezes;

      svg += '<g class="month" data-i="' + i + '" tabindex="0" role="img" aria-label="' + label + '">';
      svg += '<rect class="hit" x="' + x.toFixed(1) + '" y="0" width="' + slot.toFixed(1) +
        '" height="' + (height - padBottom) + '" fill="transparent"></rect>';
      svg += '<rect class="bar" x="' + (x + slot * 0.15).toFixed(1) +
        '" y="' + (height - padBottom - barHeight).toFixed(1) +
        '" width="' + (slot * 0.7).toFixed(1) +
        '" height="' + barHeight.toFixed(1) + '" rx="1.5"></rect>';
      svg += "</g>";

      var year = month.month.slice(0, 4);
      if (!seenYears[year]) {
        seenYears[year] = true;
        // O primeiro e o último rótulo ancoram-se para dentro: centrados,
        // metade do texto cairia fora do viewBox e o ano aparecia cortado.
        var cx = x + slot / 2;
        var anchor = "middle";
        if (cx < 18) { cx = 1; anchor = "start"; }
        else if (cx > width - 18) { cx = width - 1; anchor = "end"; }
        svg += '<text class="axis" x="' + cx.toFixed(1) +
          '" y="' + (height - 9) + '" text-anchor="' + anchor + '">' + year + "</text>";
      }
    });

    svg += '<line class="baseline" x1="0" y1="' + (height - padBottom) +
      '" x2="' + width + '" y2="' + (height - padBottom) + '"/></svg>';

    var readout = el("p", { class: "chart-readout" });
    var holder = el("div", { class: "chart-holder", html: svg });

    function show(i) {
      var month = months[i];
      var vezes = month.blocks === 1 ? "1 vez no ar" : month.blocks + " vezes no ar";
      readout.textContent = capitalize(monthNameLabel(month.month)) + " · " +
        humanDuration(month.airtime_s) + " · " + vezes;
      Array.prototype.forEach.call(holder.querySelectorAll("g.month"), function (g) {
        g.classList.toggle("is-active", Number(g.getAttribute("data-i")) === i);
      });
    }

    Array.prototype.forEach.call(holder.querySelectorAll("g.month"), function (g) {
      var i = Number(g.getAttribute("data-i"));
      ["mouseenter", "focus", "click"].forEach(function (evt) {
        g.addEventListener(evt, function () { show(i); });
      });
    });

    panel.appendChild(el("section", {}, [
      el("h2", { text: "Como tem crescido desde " + (topic.first_record || topic.since || "").slice(0, 4) }),
      el("p", {
        class: "section-caption",
        text: "Cada barra é um mês. Passe o rato por cima, ou use o teclado, para ver os valores."
      }),
      readout,
      holder
    ]));

    show(months.length - 1);
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
    renderSubjects(panel, topic, range);
    renderEvolucao(panel, topic);
  }

  function boot(stats) {
    state.stats = stats;
    state.topic = stats.topics.length ? stats.topics[0].id : null;
    document.getElementById("generated").textContent =
      "Última recolha: " + stats.generated_at.replace("T", " ").replace("+00:00", " UTC");
    renderTabs();
    renderPanel();
  }

  MTV.loadStats()
    .then(boot)
    .catch(function () {
      document.getElementById("panel").innerHTML =
        '<div class="empty"><h2>Dados indisponíveis</h2>' +
        '<p>Não foi possível carregar <code>data/stats.json</code>. ' +
        "Correr <code>python -m collector.main</code> para gerar o ficheiro.</p></div>";
    });
})();
