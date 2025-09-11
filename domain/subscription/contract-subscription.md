# 계약형 구독 (Contract Subscription)

약정 기간(예: 3/6/12개월)과 조기 해지/갱신 조항 등 계약(Contract)을 중심으로 운영되는 구독 모델입니다.

## 핵심 개념
- 계약 기간: `contract_start` ~ `contract_end` 사이에 이용 권리 보장, 중도 해지 시 위약 가능
- 청구 주기: 월별/분기별/선불 일괄 등 계약서에 명시된 스케줄 고정
- 가격/할인: 약정 할인, 선결제 할인 등 계약 조항에 종속

## 도메인 모델(예시)
- Aggregate: `SubscriptionContract`
  - `id`, `customer_id`, `plan_id`, `contract_start`, `contract_end`, `billing_schedule`
  - `cancellation_policy`(위약 규칙), `renewal_policy`(자동/수동 갱신), `early_termination_fee`
- Entities: `ContractAmendment`(변경/추가조항), `Invoice`, `Payment`

## 주요 규칙
- 해지 정책: 중도 해지 시 위약금·남은 기간 정산(정액/정률), 만기 해지는 위약 없음
- 갱신 정책: 자동 갱신(동일 조건) 또는 재협상 필요(가격/기간 재설정)
- 변경(업/다운그레이드): 보통 주기 중 변경은 제한되거나, 변경 합의 시 `Amendment`로 추적

## 이벤트(예시)
- `ContractActivated`, `InvoiceIssued`, `EarlyTerminationRequested`, `ContractAmended`, `ContractRenewed`, `ContractExpired`

## API 스케치
```http
POST /contracts { customerId, planId, termMonths, billing: "monthly" }
POST /contracts/{id}/terminate { effectiveDate, reason }
POST /contracts/{id}/renew { termMonths, price }
POST /contracts/{id}/amend { addendum }
```

## 엣지 케이스
- 조기 해지: 사용 기간/혜택 대비 위약 산정 방식 명확화(정액 vs 잔여가치 기반)
- 선불 계약 환불: 회계/세금 정책에 부합하도록 환불 규칙 별도 정의
- 데이터 이관: 재계약/갱신 시 기존 사용량·좌석·할인 이력 승계 기준 합의
