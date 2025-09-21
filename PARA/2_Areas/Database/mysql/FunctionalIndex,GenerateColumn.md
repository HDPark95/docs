컬럼의 값을 변형해서 만들어진 값에 대해 인덱스를 구축

왜? 컬럼에 함수를 먹이면, 인덱스를 안탐. 인덱스를 타게 하려면 아래 두가지 방법을 선택해서 사용 가능.

### Function-based Indexes

```sql
CREATE INDEX ix_users_active_name 
    ON users ((IsActive = 1), last_name);
    
    
CREATE INDEX ix_orders_month
    ON orders ((YEAR(order_date)*100 + MONTH(order_date))); //복잡한 함수도 가능, 대신 쿼리에서 동일한 함수를 써야함.
```

### Generate Columns With Index

두가지 방식을 지원함. Virtual(실제 저장x), Stored(실제 저장)

```sql
ALTER TABLE orders
ADD order_month TINYINT
    AS (YEAR(order_date)*100 + MONTH(order_date) STORED,
    
ADD INDEX ix_orders_month (order_month);
```