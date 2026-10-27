"""Generate the reviewed starter set used by the evaluation pipeline.

The cases are hand-authored intents/entities and only the wording is varied.
They are deliberately kept separate from any future model-training export.
"""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "ai_questions" / "seed.jsonl"

CASES = [
    ("inventory", "ask_stock", ["Kho còn SH 160i không?", "Kiểm giúp tôi SH 160i còn xe ở đâu.", "SH 160i hiện còn mấy chiếc?", "Xem tồn kho mẫu SH 160i giúp mình.", "Chi nhánh nào còn SH 160i vậy?", "Bạn kiểm tra hàng SH 160i nhé.", "SH 160i ở đại lý nào còn hàng?", "Tìm giúp những nơi còn SH 160i.", "Trong kho còn mẫu SH 160i nào không?", "Có thể kiểm kê SH 160i cho tôi không?"]),
    ("inventory", "ask_stock", ["Kho còn Air Blade 125 không?", "Kiểm hàng AB 125 giúp tôi.", "AB 125 còn mấy xe?", "Xem tồn AB 125 ở NT01.", "Chi nhánh NT01 còn Air Blade 125 không?", "Tìm AB 125 còn hàng ở đâu.", "Đại lý nào còn AB 125?", "Kiểm tra số lượng AB 125 trong kho.", "AB 125 đang còn xe chứ?", "Cho tôi xem tồn kho Air Blade 125."]),
    ("inventory", "ask_stock", ["Mẫu nào sắp hết hàng?", "Kiểm tra các xe tồn ít.", "Xe nào trong kho còn dưới mức an toàn?", "Có mẫu nào sắp hết không?", "Xem danh sách xe sắp hết hàng.", "Tồn kho nào đang thấp vậy?", "Giúp tôi rà các mẫu gần hết.", "Kiểm kê các mặt hàng ít tồn.", "Mẫu xe nào còn rất ít?", "Kho có xe nào dưới ngưỡng không?"]),
    ("inventory", "ask_stock", ["Chi nhánh NT01 còn hàng gì?", "Ở NT01 đang có những xe nào?", "Xem tồn kho chi nhánh NT01.", "Cửa hàng NT01 còn mẫu nào?", "Liệt kê hàng còn ở NT01.", "Kiểm kho NT01 giúp mình.", "Đại lý NT01 đang còn những phiên bản nào?", "Tồn tại NT01 xem ở đâu?", "Cho tôi danh sách xe còn tại NT01.", "NT01 có hàng xe gì vậy?"]),
    ("inventory", "ask_stock", ["Chi nhánh nào hết hàng?", "Xem các dòng xe đã hết.", "Mẫu nào có số lượng bằng 0?", "Kiểm tra xe hết kho.", "Có mẫu nào không còn hàng không?", "Tìm các phiên bản hết hàng.", "Kho nào đang hết xe?", "Liệt kê mặt hàng hết tồn.", "Xe nào hết ở các cửa hàng?", "Rà giúp các mẫu đã hết hàng."]),
    ("product", "ask_price_list", ["Giá SH 160i bao nhiêu?", "Cho tôi bảng giá SH 160i.", "SH 160i hiện bán giá nào?", "Xem giá niêm yết SH 160i.", "Tư vấn giá các bản SH 160i.", "SH 160i có những phiên bản và giá nào?", "Tra giá mẫu SH 160i.", "Bảng giá SH 160i giúp mình.", "Các bản SH 160i giá ra sao?", "Kiểm tra giá bán SH 160i."]),
    ("product", "ask_price_list", ["Tra tất cả sản phẩm.", "Cho tôi xem danh sách xe.", "Xem toàn bộ bảng giá xe.", "Liệt kê các mẫu xe đang bán.", "Tôi muốn tra cứu sản phẩm.", "Danh mục sản phẩm hiện có gồm gì?", "Cho xem các phiên bản xe.", "Xem tất cả mẫu xe và giá.", "Tra danh sách sản phẩm giúp tôi.", "Có những mẫu xe nào?"]),
    ("product", "ask_price_list", ["Xe ga giá dưới 50 triệu có gì?", "Tìm các mẫu tay ga.", "Bảng giá xe số cho tôi xem.", "Xe côn tay đang có những mẫu nào?", "Tra các xe tay ga.", "Mẫu xe số nào đang bán?", "Xe con tay giá bao nhiêu?", "Liệt kê dòng xe ga.", "Tìm sản phẩm thuộc phân khúc xe số.", "Có xe côn nào không?"]),
    ("product", "ask_price_list", ["So sánh giá Vision và Lead.", "Giá Vision với Lead chênh nhau thế nào?", "So sánh các bản Vision và Lead.", "Vision hay Lead giá cao hơn?", "Cho tôi đối chiếu giá Vision Lead.", "Xem bảng giá hai mẫu Vision và Lead.", "So sánh mẫu Vision với Lead giúp tôi.", "Giá các phiên bản Vision và Lead.", "Đặt Vision cạnh Lead để so sánh.", "Tôi cần so sánh Vision và Lead."]),
    ("product", "ask_price_list", ["Có mấy phiên bản SH 160i?", "SH 160i có bao nhiêu bản?", "Đếm các phiên bản SH 160i.", "Mẫu SH 160i gồm mấy phiên bản?", "Tra số bản của SH 160i.", "SH 160i có bao nhiêu lựa chọn?", "Bao nhiêu phiên bản SH 160i đang có?", "Cho biết số phiên bản SH 160i.", "Danh sách bản SH 160i có mấy loại?", "Đếm giúp tôi phiên bản SH 160i."]),
    ("customer", "ask_customer_info", ["Có bao nhiêu khách đã mua?", "Đếm khách hàng đã mua xe.", "Hiện có mấy khách đã mua?", "Tổng số khách đã mua là bao nhiêu?", "Cho biết số khách đã mua.", "Có bao nhiêu người đã mua xe rồi?", "Thống kê khách đã mua.", "Đếm giúp nhóm khách đã mua.", "Số khách hàng hoàn tất mua là bao nhiêu?", "Xem tổng khách đã mua."]),
    ("customer", "ask_customer_info", ["Tra khách hàng giúp tôi.", "Cho xem danh sách khách.", "Tìm thông tin khách hàng.", "Liệt kê khách hàng trong hệ thống.", "Tôi muốn tra cứu khách.", "Xem hồ sơ khách hàng.", "Danh sách người mua đâu?", "Tra cứu toàn bộ khách hàng.", "Cho tôi xem các khách đã lưu.", "Kiểm tra dữ liệu khách hàng."]),
    ("customer", "ask_customer_info", ["Có bao nhiêu khách tiềm năng?", "Đếm khách đang chờ tư vấn.", "Khách nào đang được tư vấn?", "Xem danh sách khách tiềm năng.", "Thống kê khách đang tư vấn.", "Có những khách nào cần gọi lại?", "Tra khách chưa chốt mua.", "Cho biết số khách đang chờ tư vấn.", "Liệt kê khách tiềm năng.", "Khách nào còn đang tư vấn vậy?"]),
    ("order", "ask_order_status", ["Tổng số đơn là bao nhiêu?", "Có tất cả mấy đơn hàng?", "Đếm số đơn trong hệ thống.", "Hiện có bao nhiêu đơn?", "Thống kê tổng đơn hàng.", "Cho biết số lượng đơn.", "Đơn hàng tất cả là mấy đơn?", "Kiểm tra tổng số đơn bán.", "Có bao nhiêu giao dịch đơn hàng?", "Xem số đơn hiện có."]),
    ("order", "ask_order_status", ["Doanh thu chi nhánh NT01 là bao nhiêu?", "Tổng tiền đơn ở NT01.", "Xem doanh thu đơn hàng NT01.", "NT01 bán được bao nhiêu tiền?", "Tính tổng giá trị đơn tại NT01.", "Doanh thu cửa hàng NT01 giúp tôi.", "Chi nhánh NT01 có doanh số bao nhiêu?", "Tổng tiền bán hàng của NT01.", "Kiểm tra doanh thu NT01.", "Các đơn ở NT01 trị giá bao nhiêu?"]),
    ("order", "ask_order_status", ["Đơn này đang ở trạng thái nào?", "Kiểm tra tình trạng đơn hàng.", "Đơn hàng đi tới đâu rồi?", "Xem trạng thái các đơn.", "Đơn đã xử lý chưa?", "Tra tình trạng đơn giúp tôi.", "Các đơn đang chờ hay đã xong?", "Theo dõi trạng thái đơn hàng.", "Đơn hàng hiện thế nào?", "Kiểm tra đơn đang xử lý."]),
    ("cost", "ask_cost_margin", ["Giá vốn SH 160i là bao nhiêu?", "Cho tôi xem giá nhập SH 160i.", "SH 160i nhập vào giá nào?", "Tra giá vốn mẫu SH 160i.", "Chi phí vốn của SH 160i.", "Giá nhập các bản SH 160i.", "Xem cost SH 160i.", "Giá vốn xe SH 160i giúp tôi.", "Mẫu SH 160i có giá nhập bao nhiêu?", "Kiểm tra giá vốn SH 160i."]),
    ("cost", "ask_cost_margin", ["Giá vốn Air Blade 125 thế nào?", "AB 125 nhập giá bao nhiêu?", "Xem cost của AB 125.", "Tra giá nhập Air Blade 125.", "Giá vốn mẫu AB 125.", "Kiểm tra chi phí vốn AB125.", "AB 125 có giá vốn nào?", "Cho biết giá nhập AB 125.", "Tôi cần xem vốn Air Blade 125.", "Giá vốn xe AB 125 là bao nhiêu?"]),
    ("inventory", "ask_stock", ["Kho còn xe ga nào?", "Xem các mẫu tay ga đang còn.", "Liệt kê xe số còn hàng.", "Còn xe côn tay nào trong kho?", "Mẫu xe ga nào còn số lượng?", "Kiểm tra xe số còn tồn.", "Tay ga nào còn xe?", "Cửa hàng còn xe côn nào?", "Danh sách xe ga còn hàng.", "Kho đang còn những xe số nào?"]),
    ("product", "ask_price_list", ["SH 160i bản ABS giá bao nhiêu?", "Tra phiên bản ABS của SH 160i.", "Giá SH 160i ABS.", "Bản phanh ABS SH 160i có giá nào?", "Xem giá bản ABS.", "SH160 ABS niêm yết bao nhiêu?", "Cho tôi thông tin bản ABS SH 160i.", "Kiểm tra giá phiên bản ABS.", "Bản ABS của SH 160i bao nhiêu tiền?", "Tra giá SH 160i ABS giúp tôi."]),
]


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    number = 1
    for department, intent, questions in CASES:
        for question in questions:
            rows.append({
                "id": f"{department.upper()[:3]}-{number:03d}",
                "question": question,
                "department": department,
                "intent": intent,
                "expected_route": "SQL",
                "expected_action": {"inventory": "query_inventory", "product": "query_catalog", "customer": "query_customers", "order": "query_orders", "cost": "query_costs"}[department],
                "required_permission": {"inventory": "inventory:read", "product": "product:read", "customer": "customer:read", "order": "order:read", "cost": "price:cost:read"}[department],
                "expected_scope": "branch" if department in {"inventory", "customer", "order"} else "all",
                "expected_entities": {},
                "expected_behavior": "query_and_answer",
                "expected_result": {"mode": "live_sql_assertion", "assertion": "result_shape_checked_on_snapshot"},
                "required_answer_facts": [department, intent],
                "difficulty": "natural" if number % 3 else "multi_constraint",
                "source": "human_reviewed_seed",
                "split": "evaluation" if number % 5 == 0 else "development",
            })
            number += 1
    OUT.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} cases to {OUT}")


if __name__ == "__main__":
    main()
