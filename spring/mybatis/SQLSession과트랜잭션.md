## 개요

사내 레거시 소스의 성능 개선을 위해, Spring Framework의 `@Transactional` 어노테이션 유무에 따른 
MyBatis SqlSession의 동작과 성능 차이를 분석해보고자 한다.

## 트랜잭션 유무의 차이점 

### @Transactional이 있는 경우
- Spring의 트랜잭션 관리자가 SqlSession 생명주기를 관리
- 하나의 트랜잭션 범위 내에서 동일한 SqlSession 인스턴스 재사용
- 트랜잭션 종료 시점에 자동 커밋/롤백
- 1차 캐시 활용 가능

### @Transactional이 없는 경우
- 각 데이터베이스 연산마다 새로운 SqlSession 생성
- 자동 커밋 모드로 동작
- 1차 캐시를 활용할 수 없음 (매번 새로운 SqlSession이므로)
- 개별 연산별 즉시 커밋

## 검증

아래의 코드를 수행해보고 1차캐시와 수행시간에 대해서 검증

```java
public void test() {
    User user1 = userMapper.selectUserById(1L);  
    User user2 = userMapper.selectUserById(1L);  
    User user3 = userMapper.selectUserById(2L);  
    User user4 = userMapper.selectUserById(1L);
    List<User> users = userMapper.selectAllUsers();  // 전체 조회
}
```

### 1차 캐시 사용 유무

* 트랜잭션 어노테이션이 없는 경우 - 동일한 파라미터여도 매번 쿼리 수행
```
o.m.s.t.SpringManagedTransaction - JDBC Connection [HikariProxyConnection@1255319830 wrapping com.mysql.cj.jdbc.ConnectionImpl@20441386] will not be managed by Spring
p.s.mapper.UserMapper.selectUserById - ==>  Preparing: SELECT id, name, email, age FROM users WHERE id = ?
p.s.mapper.UserMapper.selectUserById - ==> Parameters: 1(Long)
p.s.mapper.UserMapper.selectUserById - <==      Total: 1
org.mybatis.spring.SqlSessionUtils - Closing non transactional SqlSession [org.apache.ibatis.session.defaults.DefaultSqlSession@44154fe4]
org.mybatis.spring.SqlSessionUtils - Creating a new SqlSession
org.mybatis.spring.SqlSessionUtils - SqlSession [org.apache.ibatis.session.defaults.DefaultSqlSession@befa32d] was not registered for synchronization because synchronization is not active
o.s.jdbc.datasource.DataSourceUtils - Fetching JDBC Connection from DataSource
o.m.s.t.SpringManagedTransaction - JDBC Connection [HikariProxyConnection@984492137 wrapping com.mysql.cj.jdbc.ConnectionImpl@20441386] will not be managed by Spring
p.s.mapper.UserMapper.selectUserById - ==>  Preparing: SELECT id, name, email, age FROM users WHERE id = ?
p.s.mapper.UserMapper.selectUserById - ==> Parameters: 1(Long)
p.s.mapper.UserMapper.selectUserById - <==      Total: 1
```

* 트랜잭션 어노테이션이 있는 경우 - 각 파라미터에 대해 한번만 쿼리 수행
```
org.mybatis.spring.SqlSessionUtils - Creating a new SqlSession
org.mybatis.spring.SqlSessionUtils - Registering transaction synchronization for SqlSession [org.apache.ibatis.session.defaults.DefaultSqlSession@6b43d462]
o.m.s.t.SpringManagedTransaction - JDBC Connection [HikariProxyConnection@1639694098 wrapping com.mysql.cj.jdbc.ConnectionImpl@20441386] will be managed by Spring
p.s.mapper.UserMapper.selectUserById - ==>  Preparing: SELECT id, name, email, age FROM users WHERE id = ?
p.s.mapper.UserMapper.selectUserById - ==> Parameters: 1(Long)
p.s.mapper.UserMapper.selectUserById - <==      Total: 1
org.mybatis.spring.SqlSessionUtils - Releasing transactional SqlSession [org.apache.ibatis.session.defaults.DefaultSqlSession@6b43d462]
org.mybatis.spring.SqlSessionUtils - Fetched SqlSession [org.apache.ibatis.session.defaults.DefaultSqlSession@6b43d462] from current transaction
org.mybatis.spring.SqlSessionUtils - Releasing transactional SqlSession [org.apache.ibatis.session.defaults.DefaultSqlSession@6b43d462]
org.mybatis.spring.SqlSessionUtils - Fetched SqlSession [org.apache.ibatis.session.defaults.DefaultSqlSession@6b43d462] from current transaction
p.s.mapper.UserMapper.selectUserById - ==>  Preparing: SELECT id, name, email, age FROM users WHERE id = ?
p.s.mapper.UserMapper.selectUserById - ==> Parameters: 2(Long)
p.s.mapper.UserMapper.selectUserById - <==      Total: 1
```
### 트랜잭션 유무에 따른 성능 비교

* 트랜잭션 어노테이션이 없는 경우
```
 p.s.service.TransactionTestService - 복합 작업 (트랜잭션 없음) 소요시간: 31ms
```
* 트랜잭션 어노테이션이 있는 경우
```
p.s.service.TransactionTestService - 복합 작업 (트랜잭션 있음) 소요시간: 4ms
```

### 검증 결과
단일 트랜잭션 내에서 동작하지 않으면 1차 캐시를 활용하지 않는다.
1차 캐시를 활용하지 않고 매번 새로은 세션을 사용하여 쿼리를 수행하기 때문에 오버헤드가 발생하고
단순 조회쿼리로만 성능을 비교했음에도 불구하고 7-8배의 차이가 난다.

### 개발 작업시 가이드

#### @Transactional 사용을 권장하는 경우
- [ ] 여러 데이터베이스 연산이 하나의 논리적 작업 단위인 경우
- [ ] 데이터 일관성이 중요한 경우
- [ ] 같은 데이터를 반복 조회하는 경우 (캐시 활용)
- [ ] 예외 발생 시 롤백이 필요한 경우

#### @Transactional 없이 사용해도 되는 경우
- [ ] 단일 조회 작업만 수행하는 경우 (한 번의 쿼리만 실행)
- [ ] 각 연산이 독립적이고 캐시 효과가 필요 없는 경우
- [ ] 즉시 커밋이 필요한 경우
- [ ] 트랜잭션 오버헤드를 최소화해야 하는 경우

### 사내 레거시 소스에서 개선해야할 것
- 컨트롤러에서 여러 서비스의 메서드를 호출하는 경우가 대다수인데 이럴 경우, 매번 새로운 세션을 생성하고 반납한다.
- 이렇게 작성되어있는 코드의 경우, 위 성능 비교와 같이 성능 지연을 유발한다.
- 따라서 유즈케이스 혹은 파사드라는 레이어를 추가하고 해당 레이어의 메서드에 트랜잭션을 추가하여 작업하는 방향을 건의한다.
- 트랜잭션이 필요 없거나, 새로운 트랜잭션으로 수행해하는 경우 `@Transcational` 어노테이션의 propagation 속성을 required_new로 설정하여 사용해야한다.
