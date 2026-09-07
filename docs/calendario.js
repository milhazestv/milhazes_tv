/* Calendário de emissões. Uma grelha por ano: cada coluna é uma semana,
   cada linha um dia da semana, cada quadrado um dia.

   A forma foi escolhida pelo que revela: com os dias da semana em linha,
   uma rubrica de dia fixo aparece como uma faixa horizontal contínua, e
   uma mudança de grelha aparece como a faixa a saltar de linha. Foi
   exatamente assim que se descobriu que o Guerra Fria teve duas emissões
   semanais até fev/2025 (ver L10), e o calendário torna isso visível a
   quem visita, sem precisar de correr nada.

   Distinção que esta página tem obrigação de não apagar: nem todos os
   registos têm data de emissão declarada pelo canal. Os que não têm
   ficam com a data em que o episódio saiu no feed, tipicamente um dia
   depois. Esses são desenhados vazados. O site não corrige a data nem
   adivinha a certa: mostra a que tem e diz que aquela não é declarada. */

(function () {
  "use strict";

  var el = MTV.el;
  var humanDuration = MTV.humanDuration;
  var fromIso = MTV.fromIso;
  var isoDate = MTV.isoDate;
  var fullDateLabel = MTV.fullDateLabel;
  var capitalize = MTV.capitalize;
  var MESES = MTV.MESES;

  var CORES = ["var(--bar-1)", "var(--bar-2)", "var(--bar-3)", "var(--bar-4)", "var(--bar-5)"];
  var CELL = 13, GAP = 3, STEP = CELL + GAP;
  var LEFT = 30, TOP = 20;

  var state = { stats: null, topic: null, year: null };

  function currentTopic() {
    return state.stats.topics.filter(function (t) { return t.id === state.topic; })[0];
  }

  /* program_by_day -> { "2024-03-10": [{program, seconds, blocks, declared}] }
     ordenado por duração, para que o programa dominante fique à esquerda
     no quadrado dividido. */
  function indexDays(topic) {
    var index = {};
    (topic.program_by_day || []).forEach(function (day) {
      var lista = Object.keys(day.programs).map(function (name) {
        var p = day.programs[name];
        return {
          program: name,
          seconds: p.airtime_s,
          blocks: p.blocks,
          // Campo ausente em stats.json antigos: nesse caso não se afirma
          // nada sobre a origem da data, e o dia fica como não declarado.
          declared: (p.blocks_from_synopsis || 0) >= p.blocks
        };
      });
      lista.sort(function (a, b) { return b.seconds - a.seconds; });
      index[day.date] = lista;
    });
    return index;
  }

  function programColours(topic) {
    var mapa = {};
    (topic.by_program || []).forEach(function (entry, i) {
      mapa[entry.program] = CORES[i % CORES.length];
    });
    return mapa;
  }

  function yearsOf(topic) {
    var anos = {};
    (topic.program_by_day || []).forEach(function (day) { anos[day.date.slice(0, 4)] = true; });
    return Object.keys(anos).sort();
  }

  /* Segunda-feira da semana que contém a data. Alinha as colunas, para
     que a mesma linha seja sempre o mesmo dia da semana. */
  function weekStart(date) {
    var d = new Date(date);
    var dia = d.getDay();
    d.setDate(d.getDate() + (dia === 0 ? -6 : 1 - dia));
    return d;
  }

  function buildGrid(year, index, cores) {
    var jan = new Date(Number(year), 0, 1);
    var dez = new Date(Number(year), 11, 31);
    var inicio = weekStart(jan);
    var semanas = Math.ceil(((dez - inicio) / 86400000 + 1) / 7);
    var width = LEFT + semanas * STEP;
    var height = TOP + 7 * STEP;

    var svg = '<svg class="cal" width="' + width + '" height="' + height +
      '" viewBox="0 0 ' + width + " " + height +
      '" role="group" aria-label="Calendário de emissões de ' + year + '">';

    ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"].forEach(function (nome, linha) {
      svg += '<text class="cal-axis" x="' + (LEFT - 6) + '" y="' +
        (TOP + linha * STEP + CELL - 2) + '" text-anchor="end">' + nome + "</text>";
    });

    var mesVisto = {};
    var cursor = new Date(inicio);
    for (var semana = 0; semana < semanas; semana++) {
      for (var linha = 0; linha < 7; linha++) {
        var iso = isoDate(cursor);
        var x = LEFT + semana * STEP;
        var y = TOP + linha * STEP;

        if (cursor.getFullYear() === Number(year)) {
          if (!mesVisto[cursor.getMonth()] && cursor.getDate() <= 7 && linha === 0) {
            mesVisto[cursor.getMonth()] = true;
            svg += '<text class="cal-axis" x="' + x + '" y="' + (TOP - 7) + '">' +
              MESES[cursor.getMonth()].slice(0, 3) + "</text>";
          }

          var dia = index[iso];
          if (!dia) {
            svg += '<rect class="cal-cell cal-empty" x="' + x + '" y="' + y +
              '" width="' + CELL + '" height="' + CELL + '" rx="2"></rect>';
          } else {
            var fatia = CELL / dia.length;
            svg += '<g class="cal-day" data-date="' + iso + '" tabindex="0" role="img" aria-label="' +
              dayLabel(iso, dia) + '">';
            dia.forEach(function (p, i) {
              var cor = cores[p.program] || CORES[0];
              svg += '<rect class="cal-cell' + (p.declared ? "" : " cal-undeclared") +
                '" x="' + (x + i * fatia).toFixed(2) + '" y="' + y +
                '" width="' + fatia.toFixed(2) + '" height="' + CELL +
                '" rx="1.5" fill="' + (p.declared ? cor : "none") +
                '" stroke="' + (p.declared ? "none" : cor) + '"></rect>';
            });
            svg += "</g>";
          }
        }
        cursor.setDate(cursor.getDate() + 1);
      }
    }

    svg += "</svg>";
    return svg;
  }

  function dayLabel(iso, dia) {
    var partes = dia.map(function (p) {
      return p.program + ", " + humanDuration(p.seconds) +
        (p.declared ? "" : ", data de publicação");
    });
    return capitalize(fullDateLabel(iso)) + ": " + partes.join("; ");
  }

  function renderLegend(topic, year, index, cores) {
    var totais = {};
    Object.keys(index).forEach(function (iso) {
      if (iso.slice(0, 4) !== year) { return; }
      index[iso].forEach(function (p) {
        var t = totais[p.program] || { seconds: 0, blocks: 0, undeclared: 0 };
        t.seconds += p.seconds;
        t.blocks += p.blocks;
        if (!p.declared) { t.undeclared += p.blocks; }
        totais[p.program] = t;
      });
    });

    var lista = el("ul", { class: "pie-legend" });
    Object.keys(totais)
      .sort(function (a, b) { return totais[b].seconds - totais[a].seconds; })
      .forEach(function (nome) {
        var t = totais[nome];
        var dot = el("span", { class: "pie-dot" });
        dot.style.background = cores[nome] || CORES[0];
        var vezes = t.blocks === 1 ? "1 vez" : t.blocks + " vezes";
        lista.appendChild(el("li", {}, [
          dot,
          el("span", { class: "pie-legend-label", text: nome }),
          el("span", {
            class: "pie-legend-value",
            text: vezes + " · " + humanDuration(t.seconds)
          })
        ]));
      });
    return lista;
  }

  function render() {
    var painel = document.getElementById("panel");
    var topic = currentTopic();
    painel.innerHTML = "";
    if (!topic || !(topic.program_by_day || []).length) {
      painel.appendChild(el("div", { class: "empty" }, [
        el("h2", { text: "Ainda sem dados" }),
        el("p", { text: "Ainda não há emissões registadas." })
      ]));
      return;
    }

    var index = indexDays(topic);
    var cores = programColours(topic);
    var anos = yearsOf(topic);
    if (anos.indexOf(state.year) === -1) { state.year = anos[anos.length - 1]; }

    var seletor = el("div", { class: "period-selector", role: "tablist", "aria-label": "Ano" });
    anos.forEach(function (ano) {
      var botao = el("button", {
        class: "period-btn",
        type: "button",
        role: "tab",
        "aria-selected": String(ano === state.year),
        text: ano
      });
      botao.addEventListener("click", function () {
        state.year = ano;
        render();
      });
      seletor.appendChild(botao);
    });
    painel.appendChild(seletor);

    var leitura = el("p", { class: "chart-readout" });
    painel.appendChild(leitura);

    var grelha = el("div", {
      class: "cal-holder",
      html: buildGrid(state.year, index, cores)
    });
    painel.appendChild(grelha);

    function mostrar(iso) {
      var dia = index[iso];
      if (!dia) { return; }
      leitura.textContent = dayLabel(iso, dia);
      Array.prototype.forEach.call(grelha.querySelectorAll("g.cal-day"), function (g) {
        g.classList.toggle("is-active", g.getAttribute("data-date") === iso);
      });
    }

    Array.prototype.forEach.call(grelha.querySelectorAll("g.cal-day"), function (g) {
      var iso = g.getAttribute("data-date");
      ["mouseenter", "focus", "click"].forEach(function (evt) {
        g.addEventListener(evt, function () { mostrar(iso); });
      });
    });

    var doAno = Object.keys(index).filter(function (iso) {
      return iso.slice(0, 4) === state.year;
    }).sort();
    if (doAno.length) { mostrar(doAno[doAno.length - 1]); }

    painel.appendChild(el("h2", { class: "subhead", text: "Rubricas em " + state.year }));
    painel.appendChild(renderLegend(topic, state.year, index, cores));

    var vazados = doAno.reduce(function (n, iso) {
      return n + index[iso].filter(function (p) { return !p.declared; }).length;
    }, 0);
    painel.appendChild(el("p", {
      class: "section-caption",
      text: vazados > 0
        ? "Os quadrados vazados são dias em que o canal não declarou a data "
          + "de emissão no texto do episódio. Nesses casos fica a data em que "
          + "o episódio saiu no feed, tipicamente um dia depois da emissão. "
          + "Em " + state.year + " são " + vazados + "."
        : "Em " + state.year + " todas as datas foram declaradas pelo canal."
    }));
  }

  MTV.loadStats()
    .then(function (stats) {
      state.stats = stats;
      state.topic = stats.topics.length ? stats.topics[0].id : null;
      var nav = document.getElementById("topics");
      stats.topics.forEach(function (topic) {
        var tab = el("button", {
          class: "topic-tab",
          type: "button",
          role: "tab",
          "aria-selected": String(topic.id === state.topic),
          text: topic.name
        });
        tab.addEventListener("click", function () {
          state.topic = topic.id;
          state.year = null;
          Array.prototype.forEach.call(nav.children, function (b) {
            b.setAttribute("aria-selected", String(b === tab));
          });
          render();
        });
        nav.appendChild(tab);
      });
      render();
    })
    .catch(function () {
      document.getElementById("panel").innerHTML =
        '<div class="empty"><h2>Dados indisponíveis</h2>' +
        "<p>Não foi possível carregar <code>data/stats.json</code>.</p></div>";
    });
})();
