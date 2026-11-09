// Мини-графики на SVG без зависимостей и без Node: работает офлайн из локальной папки.
(function (global) {
  "use strict";

  var PALETTE = ["#feb622", "#3b5803", "#ff5858", "#3b3a3a", "#c98f13"];

  function svg(tag, attrs) {
    var node = document.createElementNS("http://www.w3.org/2000/svg", tag);
    Object.keys(attrs).forEach(function (key) {
      node.setAttribute(key, attrs[key]);
    });
    return node;
  }

  function frame(host, height) {
    host.innerHTML = "";
    var width = host.clientWidth || 640;
    var root = svg("svg", { viewBox: "0 0 " + width + " " + height, width: "100%", height: height });
    host.appendChild(root);
    return { root: root, width: width, height: height };
  }

  function niceMax(values) {
    var max = Math.max.apply(null, values.concat([0.0001]));
    return max * 1.12;
  }

  function compact(value) {
    var units = [[1e9, " млрд"], [1e6, " млн"], [1e3, " тыс"]];
    var hit = units.filter(function (pair) { return value >= pair[0]; })[0];
    var digits = hit ? 1 : 2;
    return hit ? (value / hit[0]).toFixed(digits) + hit[1] : value.toFixed(digits);
  }

  function axes(ctx, values, labels) {
    var pad = { l: 58, r: 12, t: 14, b: 30 };
    var h = ctx.height - pad.t - pad.b;
    var w = ctx.width - pad.l - pad.r;
    var top = niceMax(values);
    var ticks = [0, 0.25, 0.5, 0.75, 1];
    ticks.forEach(function (share) {
      var y = pad.t + h * (1 - share);
      ctx.root.appendChild(svg("line", { x1: pad.l, x2: pad.l + w, y1: y, y2: y, stroke: "#ece7dd", "stroke-width": 1 }));
      var label = svg("text", { x: 6, y: y + 4, fill: "#717171", "font-size": 10 });
      label.textContent = compact(top * share);
      ctx.root.appendChild(label);
    });
    labels.forEach(function (item, index) {
      var x = pad.l + (w * index) / Math.max(labels.length - 1, 1);
      var text = svg("text", { x: x, y: ctx.height - 8, fill: "#717171", "font-size": 10, "text-anchor": "middle" });
      text.textContent = item;
      ctx.root.appendChild(text);
    });
    return { pad: pad, w: w, h: h, top: top };
  }

  function project(point, box) {
    return {
      x: box.pad.l + box.w * point.x,
      y: box.pad.t + box.h * (1 - Math.min(point.y / box.top, 1))
    };
  }

  function line(host, spec) {
    var ctx = frame(host, spec.height || 300);
    var series = spec.series || [];
    var flat = series.reduce(function (acc, item) { return acc.concat(item.points.map(function (p) { return p.y; })); }, []);
    var box = axes(ctx, flat, spec.labels || []);
    series.forEach(function (item, index) {
      var color = item.color || PALETTE[index % PALETTE.length];
      var path = item.points.map(function (point, i) {
        var p = project(point, box);
        return (i === 0 ? "M" : "L") + p.x.toFixed(1) + " " + p.y.toFixed(1);
      }).join(" ");
      ctx.root.appendChild(svg("path", { d: path, fill: "none", stroke: color, "stroke-width": 2.4, "stroke-linecap": "round" }));
      if (item.dots) {
        item.points.forEach(function (point) {
          var p = project(point, box);
          ctx.root.appendChild(svg("circle", { cx: p.x, cy: p.y, r: 3, fill: color }));
        });
      }
    });
    ctx.root.appendChild(svg("line", { x1: box.pad.l, x2: box.pad.l + box.w, y1: box.pad.t + box.h, y2: box.pad.t + box.h, stroke: "#3b3a3a", "stroke-width": 1.2 }));
  }

  function bars(host, spec, height) {
    var ctx = frame(host, height || 300);
    var groups = spec.groups || [];
    var values = groups.reduce(function (acc, group) { return acc.concat(group.values); }, []);
    var box = axes(ctx, values, groups.map(function (g) { return g.label; }));
    var slot = box.w / Math.max(groups.length, 1) * 0.66;
    var barW = slot / Math.max(spec.series.length, 1);
    groups.forEach(function (group, gi) {
      var baseX = box.pad.l + (box.w / Math.max(groups.length, 1)) * gi + (box.w / Math.max(groups.length, 1) - slot) / 2;
      group.values.forEach(function (value, si) {
        var h = Math.max(box.h * Math.min(value / box.top, 1), 0);
        ctx.root.appendChild(svg("rect", {
          x: baseX + barW * si + 1,
          y: box.pad.t + box.h - h,
          width: Math.max(barW - 3, 2),
          height: h,
          rx: 4,
          fill: spec.series[si].color || PALETTE[si % PALETTE.length]
        }));
      });
    });
    return ctx;
  }

  function legend(host, items) {
    host.innerHTML = items.map(function (item, index) {
      return '<span><i style="background:' + (item.color || PALETTE[index % PALETTE.length]) + '"></i>' + item.name + "</span>";
    }).join("");
  }

  function money(value) {
    return new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 }).format(value) + " ₽";
  }

  function pct(value) {
    return (value * 100).toFixed(1) + "%";
  }

  global.MiniChart = { line: line, bars: bars, legend: legend, money: money, pct: pct, palette: PALETTE };
})(window);
