## 개요

사내 레거시 소스의 성능 개선을 위해, 
Spring Framework의 `@Transactional` 어노테이션 유무에 따른 
MyBatis SqlSession의 동작과 성능 차이를 분석한 내용이다. 
이를 토대로 사내 서비스 코드 컨벤션을 제안한다.

## 데이터베이스
현재 회사는 MSSql 서버를 사용하고 있으며, 데이터베이스는 '단일 데이터베이스 구조'이다.
복원을 위한 Slave가 있으나, 복원용이고 Read 부하를 부담하지 않는 구조이다.

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

#### @Transactional 없이 사용해도 되는 경우
- [ ] 단일 조회 작업만 수행하는 경우 (한 번의 쿼리만 실행)
- [ ] 각 연산이 독립적이고 캐시 효과가 필요 없는 경우

위의 경우를 제외하고는 SqlSession을 생성하고, 커넥션을 맺는 비용이 크기 때문에 모든 서비스 메서드에 트랜잭션을 선언해야한다.
현 프로젝트는 xml에서 mgr로 끝나는 서비스에, select, insert, update, delete로 시작하는 메서드의 경우 트랜잭션을 생성하고 있다.
이로 인해 다른 이름으로 시작하는 메서드들에 트랜잭션 누락이 빈번하게 발생하여, 명시적으로 트랜잭션 어노테이션을 추가하는 것을 제안한다.
기존의 xml 조건으로 트랜잭션이 발급된 경우, 어노테이션으로 적용하는 트랜잭션은 우선순위가 낮아 수행되지 않는다. 

### 사내 레거시 소스에서 개선해야할 것

1. 컨트롤러에서 여러 서비스를 호출하는 경우
   - 컨트롤러에서 여러 서비스의 메서드를 호출하는 경우가 대다수인데 이럴 경우, 매번 새로운 세션을 생성하고 반납한다.
   - 아래와 같이 개별로 서비스를 호출하는 경우, 세션과 커넥션을 여러번 생성하고 가져오게 된다.

```java

@RequestMapping("/study/*")
public class NotRecommendStudyController{
    
    private final StudyService studyService; 
    private final UserService userService;
    
    public ModelAndView studyList(Long userId){
        //커넥션 1회 생성
        UserInfo info = userService.findById(dto.getUserId());
        //커넥션 2회 생성
        List<Study> studyList = studyService.getList(dto.getUserId);
        mav.addAttribute("userInfo", info);
        mav.addAttribute("studyList", studyList);
        return mav;
    }
}
```
- 개선 방법
  - 컨트롤러와 서비스 사이에 유즈케이스 혹은 파사드라는 레이어를 추가하고 해당 레이어의 메서드에 트랜잭션을 추가하여 작업한다.
```java

public class StudyFacade{
    private final UserService userService;
    private final StudyService studyService;
    
    @Transcational(readOnly=true)
    public StudyResult getStudyResult(Long userId){
        UserInfo userInfo = userService.findById(dto.getUserId());
        List<Study> studyList = studyService.getList(dto.getUserId);
        return new StudyResult(userInfo, studyList);   
    }
}

@RequiredArgumentConstructor
@RequestMapping("/study/*")
public class RecommendStudyController{
    
    private final StudyFacade studyFacade;
    
    public ModelAndView studyList(Long userId){
        //커넥션 1회 생성
        StudyListResult result = studyFacade.getStudyList(userId);
        mav.addAttribute("userInfo", result.getUserInfo());
        mav.addAttribute("studyList", result.getStudyList());
        return mav;
    }
}
```
- 개별 트랜잭션으로 수행해야 하는 경우, 전파수준을 변경하면 새로운 트랜잭션으로 수행할 수 있다.
```java
public class StudyService{
    
    @Transactional(propagation=REQUIRED_NEW)
    public void updateStudyReadStatus(){
        //...
    }
    
}
```
### 주의할점
- 한 트랜잭션 내에서, 쿼리 수행시간이 너무 길어지면 커넥션을 반납하기 떄문에 Mssql 서버의 SocketTimeout 설정을 너무 짧게 하면, 쿼리 중간에 커넥션이 끊겨 결과를 얻어오지 못할 수 있다.
