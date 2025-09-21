# 구독(Subscription) 도메인 개요

이 디렉토리는 구독 도메인의 핵심 개념과 모델링 패턴을 정리합니다. 두 가지 모델을 구분해 설명합니다.

- 상태형 구독(Stateful Subscription): 상태 전이를 중심으로 갱신/청구/일시중지/해지 로직을 다루는 일반적 구독.
- 계약형 구독(Contract Subscription): 정해진 약정 기간(예: 12개월)과 위약/갱신 조건을 명시하는 계약 중심 구독.

## 문서
- 상태형: `stateful-subscription.md`
- 계약형: `contract-subscription.md`

## 공통 용어
- 구독(Subscription): 고객이 특정 플랜/상품을 지속적으로 이용하는 관계.
- 갱신(Renewal): 과금 주기 종료 시 다음 주기로 상태를 연장.
- 일시중지(Pause) / 재개(Resume): 이용권을 잠시 멈추거나 다시 시작.
- 해지(Cancel): 다음 갱신을 중단(즉시/만기)하는 결정.
- 소급/일할(Proration): 기간 일부만 이용했을 때 금액을 비례 계산.

## 모델링 힌트
- 시간(주기, 만료일)과 상태 전이가 주도하는 로직은 상태형으로 단순화.
- 법적 구속력/위약/약정 할인 등 계약 조항이 핵심이면 계약형을 채택.

## 참고 문서
- Stripe Billing: Subscriptions & Lifecycle — https://stripe.com/docs/billing/subscriptions/overview
- Stripe Proration — https://stripe.com/docs/billing/subscriptions/prorations
- Chargebee: Subscription Lifecycle — https://www.chargebee.com/resources/guides/subscription-billing/
- Recurly: Subscription State Model — https://docs.recurly.com/docs/subscriptions
- DDD Aggregate 설계(Vaughn Vernon) — https://www.domainlanguage.com/ddd/
- 내부 관련: 아마존 Q 회고(서버리스·API 연계 아이디어) — `think/review/AmazonQ회고.md`
