[공식문서](https://learn.microsoft.com/ko-kr/sql/relational-databases/indexes/create-filtered-indexes?view=sql-server-ver17)

## 정의

전체 테이블이 아닌 특정 조건을 만족하는 일부 행만 인덱싱하는 비클러스터형 인덱스(비클러스터형 = 데이터의 위치를 직접 가르키지 않는다는 의미)

### 특징

1. 필터링된 범위에 대해서만 통계 유지.
2. 전체 인덱스 보다 적은 범위에 인덱스를 생성하므로 조건에 해당하면 더 좋은 성능을 발휘함.
3. 불필요한 전체 테이블 인덱스를 대체함.

### 제약 사항

- 뷰 테이블에는 생성 불가
- 다중 테이블, 복잡한 논리를 포함하는 필터식 불가 (인덱싱 뷰를 고려해볼 수 있음)

    ```sql
    -- 인덱싱 뷰 생성 구문
    CREATE VIEW vw_APACOrders
    WITH SCHEMABINDING
    AS
    SELECT o.OrderID, o.CustomerID
    FROM dbo.Orders AS o
    JOIN dbo.Customer AS c
        ON o.CustomerID = c.CustomerID
    WHERE c.Region = 'APAC';
    
    CREATE UNIQUE CLUSTERED INDEX idx_vw_APACOrders
        ON vw_APACOrders (OrderID);
    ```

- Like 연산자, 계산된 열, 특정 CLR 데이터형(.net코드로 구현된 좌표같은 데이터형) 지원 불가
- 기본 키 고유 제약 조건에는 필터 적용 불가, unique속성은 가능

### 언제 쓰면 좋은가?

쿼리에 조건을 필터링을 했을 때, 비율이 적은 경우

### Mysql에서도 지원하는가?

- 공식적인 지원 X, 100% 동일한 효율을 내는 방법은 없음.