/* Utilitários partilhados pelo site e pelo calendário.

   Existem num ficheiro só para não haver duas cópias de humanDuration a
   divergir com o tempo: duas páginas a formatar durações de maneiras
   diferentes seria uma incoerência visível, e do tipo que ninguém repara
   até estar publicada. Sem dependências, como o resto do site. */

var MTV = (function () {
  "use strict";

  var MESES = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"
  ];

  var DIAS = ["domingo", "segunda", "terça", "quarta", "quinta", "sexta", "sábado"];

  function pad(n) { return n < 10 ? "0" + n : String(n); }

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

  function isoDate(date) {
    return date.getFullYear() + "-" + pad(date.getMonth() + 1) + "-" + pad(date.getDate());
  }

  /* Datas em ISO são tratadas como datas civis, não como instantes.
     new Date("2024-03-10") é interpretado como UTC pelos browsers e, num
     fuso a oeste, devolve o dia anterior. Num projeto cujo assunto é
     precisamente em que dia as coisas aconteceram, isso seria um erro
     silencioso e caro. */
  function fromIso(iso) {
    var p = iso.split("-").map(Number);
    return new Date(p[0], p[1] - 1, p[2]);
  }

  function monthNameLabel(iso) {
    var parts = iso.split("-");
    return MESES[Number(parts[1]) - 1] + " de " + parts[0];
  }

  function fullDateLabel(iso) {
    var d = fromIso(iso);
    return DIAS[d.getDay()] + ", " + d.getDate() + " de " + MESES[d.getMonth()] +
      " de " + d.getFullYear();
  }

  function capitalize(text) {
    return text.charAt(0).toUpperCase() + text.slice(1);
  }

  function escapeHtml(text) {
    return String(text).replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  /* Nomes de temas e programas escritos como HTML, com "Infotainment"
     sempre em itálico. É uma regra de escrita da casa, e vive aqui para
     não haver duas páginas a aplicá-la de maneiras diferentes. O texto
     é escapado antes, porque o nome vem do stats.json. */
  function nameHtml(text) {
    return escapeHtml(text).replace(/\bInfotainment\b/g, "<em>Infotainment</em>");
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

  function loadStats() {
    return fetch("data/stats.json", { cache: "no-cache" }).then(function (response) {
      if (!response.ok) { throw new Error("HTTP " + response.status); }
      return response.json();
    });
  }

  return {
    MESES: MESES,
    DIAS: DIAS,
    pad: pad,
    humanDuration: humanDuration,
    isoDate: isoDate,
    fromIso: fromIso,
    monthNameLabel: monthNameLabel,
    fullDateLabel: fullDateLabel,
    capitalize: capitalize,
    escapeHtml: escapeHtml,
    nameHtml: nameHtml,
    el: el,
    loadStats: loadStats
  };
})();
