window.MD = (function () {
  function renderInline(escaped) {
    return escaped
      .replace(/`([^`\n]+)`/g, '<code>$1</code>')
      .replace(/\*\*([^*\n][^*]*?)\*\*/g, '<strong>$1</strong>')
      .replace(/(^|[\s(])\*([^*\s][^*\n]*?)\*(?=[\s.,;:!?)]|$)/g, '$1<em>$2</em>')
      .replace(/\[([^\]]+)\]\((https?:[^)\s"]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  }

  function renderListItems(items) {
    var out = '';
    var open = [];
    for (var k = 0; k < items.length; k++) {
      var it = items[k];
      var tag = it.ord ? 'ol' : 'ul';
      var depth = it.lvl + 1;
      while (open.length > depth) { out += '</' + open.pop() + '>'; }
      if (open.length === depth && open[open.length - 1] !== tag && it.lvl === 0) {
        out += '</' + open.pop() + '>';
      }
      while (open.length < depth) { out += '<' + tag + '>'; open.push(tag); }
      out += (it.ord && it.num ? '<li value="' + it.num + '">' : '<li>') + renderInline(it.text) + '</li>';
    }
    while (open.length) { out += '</' + open.pop() + '>'; }
    return out;
  }

  function renderBlocks(escaped) {
    var lines = escaped.split('\n');
    var out = '';
    var para = [];
    var i, m;

    function flushPara() {
      if (para.length) {
        out += '<p>' + para.join('<br>') + '</p>';
        para = [];
      }
    }

    for (i = 0; i < lines.length; i++) {
      var line = lines[i];

      if (/^```/.test(line)) {
        flushPara();
        var code = [];
        i++;
        while (i < lines.length && !/^```/.test(lines[i])) { code.push(lines[i]); i++; }
        out += '<div class="code-block"><button type="button" class="copy-btn">copy</button><pre><code>' + code.join('\n') + '</code></pre></div>';
        continue;
      }

      m = line.match(/^(#{1,6})\s+(.*)$/);
      if (m) {
        flushPara();
        out += '<div class="md-h md-h' + m[1].length + '">' + renderInline(m[2]) + '</div>';
        continue;
      }

      if (/^\s*([-*_])\s*\1\s*\1[\s\-*_]*$/.test(line)) {
        flushPara();
        out += '<hr>';
        continue;
      }

      if (/^&gt;\s?/.test(line)) {
        flushPara();
        var quote = [];
        while (i < lines.length && /^&gt;\s?/.test(lines[i])) {
          quote.push(renderInline(lines[i].replace(/^&gt;\s?/, '')));
          i++;
        }
        i--;
        out += '<blockquote>' + quote.join('<br>') + '</blockquote>';
        continue;
      }

      m = line.match(/^(\s*)([-*+]|\d+[.)])\s+(.*)$/);
      if (m) {
        flushPara();
        var items = [];
        while (i < lines.length) {
          if (lines[i].trim() === '' && i + 1 < lines.length &&
              /^(\s*)([-*+]|\d+[.)])\s+/.test(lines[i + 1])) {
            i++;
            continue;
          }
          var lm = lines[i].match(/^(\s*)([-*+]|\d+[.)])\s+(.*)$/);
          if (!lm) break;
          items.push({
            lvl: lm[1].length >= 2 ? 1 : 0,
            ord: /\d/.test(lm[2].charAt(0)),
            num: parseInt(lm[2], 10) || 0,
            text: lm[3]
          });
          i++;
        }
        i--;
        out += renderListItems(items);
        continue;
      }

      if (line.trim() === '') {
        flushPara();
        continue;
      }
      para.push(renderInline(line));
    }
    flushPara();
    return out;
  }

  function stripThink(text) {
    var OPEN_TAG = '<' + 'think>';
    var CLOSE_TAG = '</' + 'think>';
    var escapedOpen = OPEN_TAG.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    var escapedClose = CLOSE_TAG.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    var pattern = escapedOpen + '.*?' + escapedClose;
    text = text.replace(new RegExp(pattern, 'gs'), '');
    var pattern2 = escapedOpen + '.+$';
    text = text.replace(new RegExp(pattern2, 's'), '');
    return text;
  }

  function renderThink(text) {
    text = text.replace(/<\/think>\s*<think>/g, '');
    var html = '';
    var parts = text.split(/(<think>|<\/think>)/);
    var inThink = false;
    for (var i = 0; i < parts.length; i++) {
      var part = parts[i];
      if (part === '<think>') { inThink = true; continue; }
      if (part === '</think>') { inThink = false; continue; }
      var escaped = part.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
      if (inThink) {
        html += '<span class="think-content" data-testid="think-content">' + escaped.replace(/^\s+|\s+$/g, '') + '</span>';
      } else {
        var visiblePart = escaped.replace(/^\s+|\s+$/g, '');
        if (visiblePart !== '') {
          html += '<div class="md">' + renderBlocks(visiblePart) + '</div>';
        }
      }
    }
    return html;
  }

  return {
    inline: renderInline,
    blocks: renderBlocks,
    listItems: renderListItems,
    stripThink: stripThink,
    renderThink: renderThink
  };
})();
