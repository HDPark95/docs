# 결제 웹훅

웹훅 엔드포인트는 결제 상태 전이의 기준(source of truth)입니다. 멱등성, 보안, 복원력을 갖추어 구현하세요.

## 엔드포인트
- POST `/webhooks/payments`
- 세션/쿠키 인증 없음. 제공된 서명 헤더와 타임스탬프를 검증.
- 성공 시 2xx, 잘못된 서명은 4xx, 일시 오류는 5xx(재시도 유도).

## 보안
- 서명: 공유된 시크릿으로 `timestamp + '.' + rawBody`에 대한 HMAC 생성/검증.
- 헤더(예시): `X-Pay-Signature`, `X-Pay-Timestamp`.
- 검증 절차
  - 타임스탬프 유효성(예: 5분 이내) 확인.
  - 시크릿으로 HMAC 재계산 후 상수시간 비교.
  - 불일치/만료는 거부.

## 멱등성
- 이벤트 `id` 기반 중복 제거를 영속 저장소로 수행. 반복 호출은 무시.

## 이벤트(제안)
- `payment.pending` — 사용자가 체크아웃 시작.
- `payment.succeeded` — 결제 최종 확정; 주문 결제 처리 및 권한 부여.
- `payment.failed` — 결제 실패; 사용자 알림 및 재시도 허용.
- `refund.succeeded` — 환불 완료; 잔액/권한 업데이트.
- `refund.failed` — 환불 실패; 에스컬레이션 또는 재시도.

## 페이로드(예시)
```json
{
  "id": "evt_123",
  "type": "payment.succeeded",
  "created": 1699999999,
  "data": {
    "payment": {
      "id": "pay_123",
      "orderId": "ord_456",
      "amount": 12000,
      "currency": "KRW",
      "status": "succeeded",
      "capturedAt": "2025-09-12T09:00:00Z",
      "method": { "brand": "Visa", "last4": "4242" }
    }
  }
}
```

## 처리 로직
- `id`로 이벤트를 조회하고 신규인 경우 저장 후 처리.
- `type`별로 라우팅하여 집계(주문, 결제, 환불)를 원자적으로 갱신.
- 필요 시 애플리케이션 이벤트/알림 발행.
- 커밋 성공 후에만 2xx 응답.
