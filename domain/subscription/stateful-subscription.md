# 상태형 구독 (Stateful Subscription)

상태(State)와 전이(Transition)를 중심으로 갱신/청구/일시중지/해지를 관리하는 일반적 구독 모델입니다.

## 핵심 개념
- 주요 상태: `pending`(시작대기) → `active`(이용중) → `paused`(일시중지) → `canceled`(해지) → `expired`(만료)
- 시간 축: `current_period_start`, `current_period_end`, `renew_at` 로 주기 경계 관리
- 갱신: `renew_at` 시점에 결제 성공 시 `active` 유지, 실패 시 그레이스(`past_due`) 후 `canceled/expired`

## 도메인 모델(예시)
- Aggregate: `Subscription`
  - `id`, `customer_id`, `plan_id`, `status`, `current_period_start/end`, `renew_at`
  - `payment_method`, `trial_end`, `grace_until`
- Entities: `SubscriptionItem`(추가 좌석/애드온), `Invoice`(청구), `PaymentAttempt`(시도)

## 주요 규칙
- 일시중지: `active → paused` 전이 시 `renew_at` 정지, 재개 시 남은 기간 복원 또는 새 주기 시작
- 해지: 즉시 해지(`active → canceled`)와 만기 해지(`cancel_at_period_end=true`) 구분
- 변동(업/다운그레이드): 남은 기간 기준 일할(proration) 계산해 크레딧·추가 청구 반영

## 이벤트(예시)
- `SubscriptionActivated`, `SubscriptionRenewed`, `PaymentFailed`, `SubscriptionPaused`, `SubscriptionResumed`, `SubscriptionCanceled`

## API 스케치
```http
POST /subscriptions { customerId, planId, trialDays }
POST /subscriptions/{id}/pause
POST /subscriptions/{id}/resume
POST /subscriptions/{id}/cancel { atPeriodEnd: true }
POST /subscriptions/{id}/change-plan { newPlanId, proration: true }
```

## 엣지 케이스
- 결제 실패 후 그레이스 기간: 접근 권한 유지/차단 기준 명확화
- 시차/서버 시간: 모든 연산을 UTC로, 일정은 크론/이벤트 기반으로 트리거
- 동시 변경: 동일 구독에 대한 커맨드는 직렬화(락/큐)로 순서 보장
