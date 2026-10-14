'use strict';
/* Chỉ dựng DOM từ văn bản, không dùng innerHTML với phản hồi AI.
 * Tài liệu và LLM đều có thể chứa HTML độc hại. Bộ định dạng nhỏ này chỉ
 * tạo những thẻ cố định cho đậm, nghiêng, đoạn văn và danh sách. */
(function (root) {
  const normalize = value => String(value ?? '').replace(/[\u2013\u2014]/g, '-');

  function inline(parent, value) {
    // Đọc dấu định dạng theo thứ tự dài trước ngắn để hỗ trợ cả đậm + nghiêng.
    // Chuỗi HTML, URL và thuộc tính sự kiện luôn là text, không được thực thi.
    const tokens = /(\*\*\*([^*\n]+)\*\*\*|\*\*([^*\n]+)\*\*|__([^_\n]+)__|\*([^*\n]+)\*|_([^_\n]+)_|`([^`\n]+)`|\[([^\]\n]+)\]\([^\)\n]+\))/g;
    let position = 0;
    for (const match of value.matchAll(tokens)) {
      parent.append(document.createTextNode(value.slice(position, match.index)));
      const content = match[2] || match[3] || match[4] || match[5] || match[6] || match[7] || match[8];
      const tag = match[2] || match[3] || match[4] ? 'strong' : match[5] || match[6] ? 'em' : match[7] ? 'code' : 'span';
      const node = document.createElement(tag);
      if (match[2]) {
        const emphasis = document.createElement('em');
        emphasis.textContent = content;
        node.append(emphasis);
      } else if (tag === 'strong') inline(node, content);
      else node.textContent = content;
      parent.append(node);
      position = match.index + match[0].length;
    }
    parent.append(document.createTextNode(value.slice(position)));
  }

  function render(target, value) {
    // replaceChildren xóa thông báo chờ và phản hồi trước mà không parse HTML.
    target.replaceChildren();
    const lines = normalize(value).split(/\r?\n/);
    let list = null;
    for (const line of lines) {
      // Bỏ dấu khối code của LLM; nội dung bên trong vẫn là text an toàn.
      if (/^\s*```/.test(line)) continue;
      if (!line.trim()) { list = null; continue; }
      const item = line.match(/^\s*(?:[-*+]\s+|\d+[.)]\s+)(.*)$/);
      if (item) {
        const type = /^\s*\d/.test(line) ? 'ol' : 'ul';
        if (!list || list.tagName.toLowerCase() !== type) {
          list = document.createElement(type);
          target.append(list);
        }
        const li = document.createElement('li');
        inline(li, item[1]);
        list.append(li);
      } else {
        list = null;
        const paragraph = document.createElement('p');
        const heading = line.match(/^\s*#{1,6}\s+(.*)$/);
        if (heading) {
          const strong = document.createElement('strong');
          inline(strong, heading[1]);
          paragraph.append(strong);
        } else inline(paragraph, line);
        target.append(paragraph);
      }
    }
  }
  root.ChatFormatting = {normalize, render};
})(globalThis);
