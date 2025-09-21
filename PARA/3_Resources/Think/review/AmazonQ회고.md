# 아마존 Q 해커톤 회고

## 무엇을 만들었나
- 문제의식: “오늘 뭐 먹지?”에서 결정·준비·구매까지 이어지는 번거로움을 줄이고 싶었다.
- 가설: 식단/시간/제약 조건만 주면 레시피를 추천해주고 최저가 상품의 링크를 제공하여 사용자의 불필요한 고민을 줄일 수 있을 것이다.

- 한 줄 정의: 입력 기반 맞춤 레시피 + 장보기 최저가 추천.
- 입력: 식단(예: 저탄고지, 비건), 인분, 조리시간, 예산, 특이사항(알레르기, 도구 제한 등).
- 출력: 단계별 레시피, 예상 시간, 재료 목록, 구매 리스트, 최저가 후보.
- 사용자 흐름: 1) 조건 입력 → 2) 레시피 생성/구조화 → 3) 재료 추출 → 4) 가격 비교 → 5) 구매 링크 제안.

## 예시
- 입력: Diet=비건, Time=15분, Notes=땅콩 알레르기, 전자레인지만 사용
- 출력 요약
  - 메뉴: 두부 스크램블 볼
  - 재료: 두부, 시금치, 현미밥, 간장, 참기름(땅콩 성분 제외)
  - 시간: 15분
  - 예산: 10000원
  - 레시피: 물기 제거 → 전자레인지 조리 → 토핑 조합
  - 장보기: 두부/시금치/현미밥 최저가 후보 3개 리스트
  - 영양소: 탄수화물 30g / 단백질 10g / 지방 10g

## 어떻게 만들었나
- 서버리스 아키텍처
  - 관리형 인프라 중심으로 구성하여 배포·운영 부담 최소화.
  - API 엔드포인트 → 함수 실행(비즈니스 로직) → 저장소(예: 객체/키-값 스토어)의 단순 파이프라인.
  - 무상태 설계로 수평 확장 용이, 콜드스타트는 초기화 최소화로 완화.

- 프롬프트 전략
  - 출력 스키마(JSON 유사): title, ingredients[], steps[], duration, constraints_applied.
  - 제약 규칙 고정: 알레르겐 제외, 조리도구/시간 상한 엄수, 대체재 제안 기준.
  - 짧은 반복 사이클: 결과 점검 → 프롬프트/룰 조정 → 재시도로 품질 수렴.

- 데이터 구조화
  - “재료 목록”과 “조리 단계”를 분리 저장해 쇼핑/가격 비교, 추천 재사용성 확보.
  - 재료 정규화(단위/수량 분리, 동의어/브랜드 제거)로 검색·가격 비교 정확도 개선.

- 쇼핑/가격 정보(네이버 쇼핑 API)
  - 재료 키워드를 정규화한 뒤 네이버 쇼핑 검색 API로 가격/링크 조회.
  - 가격·용량·배송비 등을 간단 지표로 스코어링해 상위 N개만 노출.
  - 예외/쿼터 대응: 캐싱(단기), 백오프/재시도, 일시 실패 시 대체 키워드로 폴백.
  
## 무엇이 잘 되었나
- 팀워크: “어떻게든 사업적으로 풀자”는 태도, 빈번한 대화로 빠른 우선 순위 수립.
- 실행력: 막히면 우회, 작은 단위로 결과물 생성(MVP → 반복).
- 학습: AWS 서비스를 실전 맥락에서 사용하며 체득.

## 아쉬웠던 점
- CloudFormation 대신 Terraform을 썼다면
  - 모듈화/재사용이 쉬워 환경 분리가 명확했을 것.
  - 상태 관리와 드리프트 확인이 직관적.
- AWS 사전지식 부족
  - 서비스 선택지·요금·제한을 표로 정리했으면 시행착오 감소.
  - 초기 아키텍처 합의(간단 다이어그램)로 변경 비용 절감.

## Terraform vs CloudFormation (사용법과 차이)

### Terraform 사용법 요약
- 워크플로우: `terraform init` → `terraform plan` → `terraform apply` → `terraform destroy`
- 변수/환경: `-var-file=env/dev.tfvars`로 환경별 값 분리, 민감 정보는 `TF_VAR_` 또는 외부 비밀 저장소 사용
- 워크스페이스: `terraform workspace new dev`, `terraform workspace select dev`로 환경 격리
- 상태 관리(원격): S3 + DynamoDB 락 권장
```hcl
terraform {
  backend "s3" {
    bucket = "my-tf-state"
    key    = "env/dev/terraform.tfstate"
    region = "ap-northeast-2"
    dynamodb_table = "my-tf-lock"
  }
}
```
- 모듈화: `modules/network`, `modules/compute` 등으로 공통 패턴 재사용
- 변경 검토: `terraform plan -out=plan.tfplan`으로 리뷰 후 `terraform apply plan.tfplan`

### CloudFormation 사용법 요약
- 템플릿: YAML/JSON로 리소스 정의, 매개변수/출력 사용
- 배포(표준):
```bash
aws cloudformation deploy \
  --template-file template.yaml \
  --stack-name my-stack \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides Env=dev ImageTag=latest
```
- 패키징(SAM/람다 코드 포함):
```bash
aws cloudformation package \
  --template-file template.yaml \
  --s3-bucket my-artifacts \
  --output-template-file out.yaml

aws cloudformation deploy --template-file out.yaml --stack-name my-stack --capabilities CAPABILITY_IAM
```
- 변경셋: `create-change-set` → `describe-change-set` → `execute-change-set`로 변경 미리보기
- 스택 전략: Nested Stacks, StackSets로 멀티계정/리전 배포, 스택 정책으로 보호

### 핵심 차이(실무 관점)
- 선언/오케스트레이션
  - Terraform: 멀티클라우드/서드파티 리소스를 단일 언어(HCL)로 관리. 프로바이더 생태계 풍부.
  - CloudFormation: AWS 리소스에 최적화. 최신 서비스 지원이 가장 빠름(일반적으로).
- 상태/드리프트
  - Terraform: 원격 상태로 팀 협업과 드리프트 관리가 쉽고 명시적.
  - CloudFormation: 스택 상태는 AWS가 관리하지만, 외부 변경은 Change Set/Drift Detection로 확인.
- 모듈/재사용
  - Terraform: 모듈·레지스트리 패턴 성숙, 버저닝 용이.
  - CloudFormation: 매크로/모듈(서드파티)/Nested Stack으로 재사용 가능하나 개발 경험은 상대적으로 무겁다.
- 람다 코드 연계
  - Terraform: 아티팩트 빌드/업로드 파이프라인을 별도로 설계(예: S3 업로드 후 참조).
  - CloudFormation: `package/deploy`로 템플릿 내 코드 참조 업데이트 가능하지만 inline `ZipFile` 사용은 규모 커질수록 비추천.
- 개발자 경험
  - Terraform: `plan` 결과가 명확하고 리뷰 프로세스에 잘 녹음.
  - CloudFormation: Change Set으로 유사 기능 제공하나 템플릿 복잡도가 올라가면 가독성이 떨어질 수 있음.

## 배운 점
- 프롬프트는 “출력 스키마 + 제약 규칙”을 고정해야 재사용 가능.
- 사용자가 느끼는 가치는 “정확한 레시피”보다 “장보기로 바로 이어짐”에 있음.
- 초기에 범위를 넓히지 말고 핵심 가치(레시피→장보기 연결)부터 검증.

## 마무리
짧은 시간에도 “유저가 바로 쓸 수 있는 것”을 끝까지 만들었다는 점이 가장 값졌다.
더 참신하게 할 수 없었을까 라는 생각에 아쉬움이 남았다.


