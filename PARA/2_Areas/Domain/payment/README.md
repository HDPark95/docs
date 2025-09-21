# 결제 API 엔드포인트(기본)

이 문서는 환불과 기본 결제수단 관리를 포함한 일회성 결제 플로우를 구현하기 위한 기본 엔드포인트를 정리합니다. 결제 대행사(PG)의 상세는 백엔드 뒤로 추상화하세요.

## 범위와 흐름
- 클라이언트가 체크아웃 시작 → 백엔드가 결제 인텐트/세션 생성 → 사용자가 결제 완료(리디렉트 또는 위젯) → 게이트웨이가 웹훅으로 알림 → 백엔드가 주문을 확정하고 클라이언트에 반영.
- 결제 상태의 단일 진실 원본은 웹훅으로 취급합니다.

## 핵심 리소스
- Payment: 단일 거래 시도(승인/매입 또는 즉시 결제).
- Order: 하나 이상의 결제와 연결된 비즈니스 주문.
- PaymentMethod: 고객 단위로 저장된 토큰화된 결제수단.
- Refund: 특정 결제에 연결된 부분/전체 환불.

## 엔드포인트
- 결제 인텐트 생성
  - POST `/payments/intent`
  - Body: `{ orderId, amount, currency, description?, customerId?, capture=true|false, returnUrl, cancelUrl, methodOptions?, metadata? }`
  - Returns: `{ paymentId, status, clientToken?, redirectUrl?, expiresAt }`

- 결제 조회
  - GET `/payments/{paymentId}` → `{ paymentId, status, amount, currency, orderId, capturedAt?, failureReason?, metadata }`

- 결제 확정(서버 간, 필요 시)
  - POST `/payments/{paymentId}/confirm` → `{ paymentId, status }`

- 매입(capture)
  - POST `/payments/{paymentId}/capture` → `{ paymentId, status, capturedAmount }`

- 승인 취소/무효(매입 전)
  - POST `/payments/{paymentId}/cancel` → `{ paymentId, status }`

- 환불 생성
  - POST `/refunds` with `{ paymentId, amount?, reason?, metadata? }` → `{ refundId, status, amount }`

- 환불 조회
  - GET `/refunds/{refundId}` → `{ refundId, status, amount, paymentId }`

- 결제수단 등록(보관형)
  - POST `/customers/{customerId}/payment-methods` with `{ token, type, billingDetails? }` → `{ paymentMethodId, brand, last4, exp }`

- 결제수단 목록 조회
  - GET `/customers/{customerId}/payment-methods` → `[ { paymentMethodId, brand, last4, exp, default } ]`

- 결제수단 삭제/해제
  - DELETE `/payment-methods/{paymentMethodId}` → `{ deleted: true }`

- 웹훅 수신
  - POST `/webhooks/payments` (세션/쿠키 인증 없음). 서명 헤더와 타임스탬프를 검증. 자세한 내용은 `webhook.md` 참고.

## 동작과 계약
- 상태 모델: `created` → `pending` → `succeeded` | `failed` | `canceled`; 승인/매입 방식은 `authorized` → `captured` | `voided`.
- 멱등성: 모든 POST 엔드포인트에서 `Idempotency-Key`를 수용하고 재시도에 동일 응답을 반환.
- 통화/금액: 최소 단위 사용(예: KRW는 원). 서버의 주문 합계와 일치 검증.
- 보안: 클라이언트 금액을 신뢰하지 말 것; 웹훅 서명 검증; 민감 라우트 레이트 리밋.
- 3DS/리디렉트: `redirectUrl` 처리; 사용자가 `returnUrl`로 복귀하면 GET으로 결제 조회하고 웹훅을 대기.

## 예시 시퀀스: 일회성 결제
- 1) 클라이언트가 주문 생성 요청 → 백엔드가 POST `/payments/intent` 호출.
- 2) 백엔드가 `redirectUrl`(또는 `clientToken`) 반환.
- 3) 클라이언트가 리디렉트; 사용자가 결제 완료.
- 4) 게이트웨이가 `/webhooks/payments`로 `payment.succeeded|failed` 전송.
- 5) 백엔드가 주문을 결제/실패 처리 후, 프론트는 GET `/payments/{id}` 폴링 또는 앱 이벤트 수신.

## 오류 모델(예시)
```json
{
  "error": {
    "type": "validation|processing|gateway|not_found",
    "code": "AMOUNT_MISMATCH",
    "message": "Amount does not match order total.",
    "details": { "orderId": "ord_123" }
  }
}
```

## 관련
- 웹훅과 페이로드: `webhook.md`
- 구독(정기결제) 플로우: `../subscription/`
