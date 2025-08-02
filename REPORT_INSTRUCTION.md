# Tiểu luận: Giải pháp IAM cho Software Agent – Kiến trúc và Ứng dụng

## I. MỞ ĐẦU

### 1. Bối cảnh và vấn đề
- Sự phổ biến của software agents trong hệ thống hiện đại, đặc biệt trong trí tuệ nhân tạo (AI) và tự động hóa.
- Ví dụ: LLM agents, CI/CD bots, data workers,...
- Tại sao IAM (Identity and Access Management) truyền thống lấy con nguời làm trung tâm không phù hợp?
- Nhu cầu cấp thiết về một giải pháp IAM mới, phù hợp với đặc thù của software agents.

### 2. Mục tiêu bài viết
- Đề xuất giải pháp kiến trúc IAM phù hợp cho software agents
- - Giải thích rõ các khái niệm cốt lõi
- Trình bày use case minh họa: LLM agent dùng RAG

---

## II. CÁC KHÁI NIỆM CƠ BẢN

### 1. Software Agent là gì?
- Định nghĩa, ví dụ: CI bot, LLM agent, data worker
- Đặc điểm: tự động, có thể tương tác với hệ thống, không cần can thiệp con người
- Tại sao cần IAM cho software agents?

### 2. IAM và IAM truyền thống là gì?
- Định nghĩa IAM: quản lý danh tính, quyền truy cập và bảo mật
- IAM truyền thống, human-orient:
    - Danh tính: user, group, role (thường lâu dài)
    - Mô hình xác thực: password, SSO, MFA
    - Kiểm soát truy cập: thường là RBAC

### 3. IAM cho Software Agents
- Các đặc tính của Non-human identities (NHIs):
    - Danh tính động, ngắn hạn
    - Không cần lưu trữ key lâu dài
    - Tự động cấp phát và thu hồi
- Mô hình xác thực: dựa trên chứng chỉ (cert) và ephemeral token (ngắn hạn)
- Kiểm soát truy cập thích ứng theo ngữ cảnh: ABAC, PBAC
- Tại sao IAM truyền thống không phù hợp?

### 4. Workload Identity
- Định nghĩa: danh tính động cho phần mềm
- Các công nghệ phổ biến cung cấp Workload Identity
- Cụ thể về SPIFFE/SPIRE cấp danh tính (SPIFFE ID, x.509/JWT SVID ?)
- Ví dụ SPIFFE ID: `spiffe://domain.local/ns/app/sa/agent`

### 5. Just-in-Time Access
- Định nghĩa: cấp phát quyền truy cập theo nhu cầu, không lưu trữ lâu dài
- Lợi ích: giảm rủi ro bảo mật, tăng tính linh hoạt
- Các công cụ phổ biến: HashiCorp Vault, AWS IAM Roles Anywhere
- Cụ thể về Vault của HashiCorp

### 6. Policy Engine và kiểm soát truy cập
- PDP vs PEP: ai quyết định, ai thực thi
- Các công cụ phổ biến: OPA, Authzed, Cerbos
- Cerbos là gì? Hoạt động ra sao?

### 7. Kiểm soát truy cập qua Proxy
- Tại sao cần proxy trong kiến trúc IAM?
- Các công cụ phổ biến: Envoy, API Gateway
- Cách hoạt động: xác thực token, kiểm tra policy, chuyển tiếp request
- Ví dụ: Envoy làm gateway

---

## III. KIẾN TRÚC GIẢI PHÁP IAM CHO SOFTWARE AGENT

### 1. Các thành phần chính
- Agent
- SPIRE (identity)
- Vault (token)
- Cerbos (policy)
- Envoy (gateway)
- Backend services

### 2. Luồng hoạt động tổng quát
1. Agent khởi động → cấp SPIFFE ID
2. Agent dùng x.509 cert để lấy JWT từ Vault
3. Gửi request đến API nội bộ qua Envoy
4. Envoy xác minh token → gọi Cerbos
5. Cerbos trả về allow/deny → forward hoặc từ chối

### 3. Kiểm soát truy cập chi tiết
- Theo vai trò, loại tài nguyên, hành động
- Theo ngữ cảnh (thời gian, môi trường, vị trí...)

---

## IV. USE CASE DEMO: LLM AGENT SỬ DỤNG RAG

### 1. Giới thiệu use case
- RAG (Retrieval-Augmented Generation) là gì?
- LLM agent (chatbot) cần lấy vector từ ChromaDB, tài liệu từ MinIO cho các tác vụ QA chat

### 2. Áp dụng kiến trúc IAM
- Danh tính cấp qua SPIRE
- Token lấy từ Vault
- Truy cập tài nguyên đi qua Envoy + Cerbos

### 3. Minh họa
- Sơ đồ kiến trúc
- Sequence diagram: từ khởi động đến lấy tài nguyên

---

## V. ĐÁNH GIÁ GIẢI PHÁP

### 1. Ưu điểm
- Không cần lưu trữ key
- Có thể kiểm soát chi tiết và thời gian thực
- Dễ mở rộng, chuẩn hóa

### 2. Thách thức
- Tăng độ phức tạp triển khai
- Phải làm chủ các công cụ: SPIRE, Vault, Cerbos, Envoy

---

## VI. KẾT LUẬN

- IAM cho software agent là yêu cầu tất yếu
- Giải pháp đề xuất tuân thủ chuẩn mở, bảo mật cao
- Có thể áp dụng cho nhiều loại agent: LLM, CI/CD bot, data workers...
- Hướng phát triển: mở rộng ra cloud IAM, tích hợp SIEM, ZTA...

---

## PHỤ LỤC (tuỳ chọn)
- Mẫu SPIFFE ID
- Mẫu JWT claim
- Cerbos policy YAML
- docker-compose mẫu cho PoC
- Tài liệu tham khảo