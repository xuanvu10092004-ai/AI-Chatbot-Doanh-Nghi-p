/* Chạy bộ định dạng với DOM tối thiểu: mọi chỗ gán innerHTML đều gây lỗi.
 * Kiểm tra cấu trúc thẻ và văn bản, không chỉ đối chiếu mã nguồn. */
const assert = require('node:assert/strict');
class Node {
  constructor(tag = '#text', value = '') { this.tagName = tag; this.value = value; this.children = []; }
  set textContent(value) { this.value = value; this.children = []; }
  get textContent() { return this.value + this.children.map(node => node.textContent).join(''); }
  set innerHTML(value) { throw new Error('Không được parse HTML từ LLM'); }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.value = ''; this.children = nodes; }
}
global.document = {
  createElement: tag => new Node(tag.toUpperCase()),
  createTextNode: value => new Node('#text', value),
};
require('../static/chat-formatting.js');
const target = new Node('DIV');
const tags = node => [node.tagName, ...node.children.flatMap(tags)];
ChatFormatting.render(target, '# Khuyến mãi\n- **Vision**: *Ghi chú*\n- ***Đậm nghiêng***\n\n__Nguồn__ - `id=5`\n```md\nKiểm chứng\n```');
assert(tags(target).includes('UL'));
assert(tags(target).includes('STRONG'));
assert(tags(target).includes('EM'));
assert(!/[#*`]/.test(target.textContent));
assert(!target.textContent.includes('md'));
assert(target.textContent.includes('Khuyến mãi'));
assert(target.textContent.includes('id=5'));
ChatFormatting.render(target, '<img src=x onerror=alert(1)>\n[liên kết](javascript:alert(1))\n**<script>alert(2)</script>**');
assert(!tags(target).includes('IMG'));
assert(!tags(target).includes('SCRIPT'));
assert(!tags(target).includes('A'));
assert(target.textContent.includes('<script>alert(2)</script>'));
assert(!target.textContent.includes('javascript:'));
ChatFormatting.render(target, '1. A\n2. B\n\nC\u2014D\u2013E');
assert(tags(target).includes('OL'));
assert(target.textContent.includes('C-D-E'));
assert(!target.textContent.includes('alert'));
console.log('Định dạng đậm/nghiêng, danh sách, thay gạch và chống HTML: đạt.');
