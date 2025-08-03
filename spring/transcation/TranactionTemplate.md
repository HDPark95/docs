## TransactionTemplate

## 개요

`TransactionTemplate`은 스프링 프레임워크에서 제공하는 프로그래밍 방식의 트랜잭션 관리 도구로, 선언적 트랜잭션(`@Transactional`)의 대안이다. 
복잡한 트랜잭션 로직이 필요하거나 트랜잭션 경계를 세밀하게 제어해야 할 때 유용하다.

## 선언적 트랜잭션과 프로그래밍 방식 트랜잭션

### 선언적 트랜잭션 (@Transactional)
- 어노테이션 기반으로 메서드나 클래스에 트랜잭션 속성을 선언
- AOP를 통해 트랜잭션 처리 로직이 자동으로 적용됨
- 코드가 간결하고 비즈니스 로직과 트랜잭션 처리 로직이 분리됨
- 메서드 단위로 트랜잭션 경계가 고정됨

### 프로그래밍 방식 트랜잭션 (TransactionTemplate)
- 코드 내에서 명시적으로 트랜잭션 경계를 설정
- 트랜잭션 시작과 종료 시점을 프로그래밍 방식으로 제어
- 조건부 트랜잭션 처리나 동적인 트랜잭션 속성 설정이 가능
- 세밀한 예외 처리와 트랜잭션 제어가 필요한 경우에 적합

## TransactionTemplate 사용 방법

```java
@Service
public class UserService {
    
    @Autowired
    private TransactionTemplate transactionTemplate;
    
    @Autowired
    private UserRepository userRepository;
    
    public User createUser(final User user) {
        return transactionTemplate.execute(status -> {
            userRepository.save(user);
            return user;
        });
    }
}
```

### 예외 처리와 롤백
```java
public void transferMoney(long fromId, long toId, BigDecimal amount) {
    transactionTemplate.execute(status -> {
        try {
            Account fromAccount = accountRepository.findById(fromId);
            Account toAccount = accountRepository.findById(toId);
            
            if (fromAccount.getBalance().compareTo(amount) < 0) {
                // 잔액 부족 시 명시적 롤백
                status.setRollbackOnly();
                throw new InsufficientBalanceException("잔액이 부족합니다");
            }
            
            fromAccount.debit(amount);
            toAccount.credit(amount);
            
            accountRepository.save(fromAccount);
            accountRepository.save(toAccount);
            
            return null;
        } catch (Exception e) {
            // 예외 발생 시 자동 롤백
            throw new RuntimeException("송금 처리 중 오류 발생", e);
        }
    });
}
```

### 읽기 전용 트랜잭션

```java
public List<User> getAllUsers() {
    TransactionTemplate readOnlyTemplate = new TransactionTemplate(transactionManager);
    readOnlyTemplate.setReadOnly(true);
    
    return readOnlyTemplate.execute(status -> {
        return userRepository.findAll();
    });
}
```

## TransactionTemplate 사용 시 장점
1. **세밀한 트랜잭션 제어**: 트랜잭션의 시작과 종료 시점을 코드 내에서 명확하게 제어할 수 있다.
2. **조건부 트랜잭션**: 특정 조건에 따라 트랜잭션을 시작하거나 롤백할 수 있다.

## TransactionTemplate 사용 시 단점
1. **코드 복잡성 증가**: 선언적 방식보다 코드가 복잡해지고 길어질 수 있다.
2. **비즈니스 로직과 트랜잭션 로직의 혼합**: 비즈니스 로직과 트랜잭션 처리 로직이 혼합되어 코드 가독성이 저하될 수 있다.

## 실제 사용 예시: 복잡한 비즈니스 로직

```java
@Service
public class OrderService {
    
    @Autowired
    private TransactionTemplate transactionTemplate;
    
    @Autowired
    private OrderRepository orderRepository;
    
    @Autowired
    private InventoryService inventoryService;
    
    @Autowired
    private PaymentService paymentService;
    
    public OrderResult processOrder(Order order) {
        // 트랜잭션 외부에서 수행할 작업
        validateOrder(order);
        
        return transactionTemplate.execute(status -> {
            try {
                // 재고 확인
                if (!inventoryService.checkAvailability(order.getItems())) {
                    return new OrderResult(false, "재고 부족");
                }
                
                // 결제 처리
                PaymentResult paymentResult = paymentService.processPayment(order.getPayment());
                if (!paymentResult.isSuccess()) {
                    status.setRollbackOnly();
                    return new OrderResult(false, "결제 실패: " + paymentResult.getMessage());
                }
                
                // 재고 감소
                inventoryService.decreaseStock(order.getItems());
                
                // 주문 저장
                Order savedOrder = orderRepository.save(order);
                
                return new OrderResult(true, "주문 처리 완료", savedOrder.getId());
            } catch (Exception e) {
                status.setRollbackOnly();
                return new OrderResult(false, "주문 처리 중 오류 발생: " + e.getMessage());
            }
        });
    }
}
```