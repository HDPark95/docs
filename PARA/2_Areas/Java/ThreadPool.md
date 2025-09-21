# 자바는 Executors 클래스를 통해 3가지 기본 전략을 제공한다.

1. newSingleThreadPool(): 단일 스레드 풀
2. newFixedThreadPool(): 고정 스레드 풀
3. newCachedThreadPool(): 캐시 스레드 풀

## 고정 풀 전략
* 스레드 풀에 고정된 수 만큼 기본 스레드를 생성한다. 초과 스레드는 생성하지 않는다.
* 큐 사이즈에 제한이 없다.
* 스레드 수가 고정되어 있기 때문에 CPU, 메모리 리소스가 어느정도 예측 가능한 안정적인 방식이다.

### 자바 예시 코드
```java
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

public class FixedThreadPoolExample {
    public static void main(String[] args) {
        // CPU 코어 수에 맞게 고정 스레드 풀 생성
        int numOfCores = Runtime.getRuntime().availableProcessors();
        ExecutorService executor = Executors.newFixedThreadPool(numOfCores);
        
        // 10개의 작업 제출
        for (int i = 0; i < 10; i++) {
            final int taskId = i;
            executor.submit(() -> {
                String threadName = Thread.currentThread().getName();
                System.out.println("Task " + taskId + " is running on " + threadName);
                
                // 작업 시뮬레이션
                try {
                    TimeUnit.SECONDS.sleep(1);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
                
                return "Task " + taskId + " completed";
            });
        }
        
        // 스레드 풀 종료
        executor.shutdown();
        try {
            // 모든 작업이 완료될 때까지 최대 10초 대기
            if (!executor.awaitTermination(10, TimeUnit.SECONDS)) {
                // 10초 내에 완료되지 않으면 강제 종료
                executor.shutdownNow();
            }
        } catch (InterruptedException e) {
            executor.shutdownNow();
        }
        
        System.out.println("All tasks completed");
    }
}
```

## 캐시 풀 전략
* 기본 스레드를 사용하지 않고, 60 초 생존 주기를 가진 초과 스레드만 사용한다.
* 초과 스레드의 수 제한은 없음.
* 큐에 작업을 저장하지 않는다.
  * 대신에 생산자의 요청을 스레드 풀의 소비자가 직접 받아서 바로 처리한다.
* 모든 요청이 대기하지 않고 스레드가 바로바로 처리한다.
* SynchronousQueue 
  * BlockingQueue 인터페이스의 구현체 중 하나
  * 이 큐는 내부에 저장 공간이 없음. 대신 생산자의 작업을 소비자 스레드에 직접 전달한다.
  * 이름 그대로 생사낮와 소비자를 동기화하는 큐
  * 중간에 버퍼를 두지 않고 스레드 간의 직거래라고 생각하면 된다.

### 자바 예시 코드
```java
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

public class CachedThreadPoolExample {
    public static void main(String[] args) {
        // 캐시 스레드 풀 생성
        ExecutorService executor = Executors.newCachedThreadPool();
        
        System.out.println("작업 제출 시작");
        
        // 첫 번째 배치: 5개 작업 제출
        for (int i = 0; i < 5; i++) {
            final int taskId = i;
            executor.submit(() -> {
                String threadName = Thread.currentThread().getName();
                System.out.println("첫 번째 배치 - Task " + taskId + " 실행 중: " + threadName);
                
                // 작업 시뮬레이션 (2초)
                try {
                    TimeUnit.SECONDS.sleep(2);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
                
                System.out.println("첫 번째 배치 - Task " + taskId + " 완료");
                return null;
            });
        }
        
        // 잠시 대기 (첫 번째 배치가 실행 중일 때)
        try {
            TimeUnit.SECONDS.sleep(1);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
        
        // 두 번째 배치: 10개 작업 추가 제출 (부하 증가 시뮬레이션)
        System.out.println("\n부하 증가: 추가 작업 제출");
        for (int i = 5; i < 15; i++) {
            final int taskId = i;
            executor.submit(() -> {
                String threadName = Thread.currentThread().getName();
                System.out.println("두 번째 배치 - Task " + taskId + " 실행 중: " + threadName);
                
                // 작업 시뮬레이션 (1초)
                try {
                    TimeUnit.SECONDS.sleep(1);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
                
                System.out.println("두 번째 배치 - Task " + taskId + " 완료");
                return null;
            });
        }
        
        // 스레드 풀 종료
        executor.shutdown();
        try {
            // 모든 작업이 완료될 때까지 최대 15초 대기
            if (!executor.awaitTermination(15, TimeUnit.SECONDS)) {
                executor.shutdownNow();
            }
        } catch (InterruptedException e) {
            executor.shutdownNow();
        }
        
        System.out.println("\n모든 작업 완료. 캐시 스레드 풀은 사용되지 않는 스레드를 60초 후 자동으로 제거합니다.");
    }
}
```

## ForkJoinPool 전략
* ForkJoinPool의 고정 병렬 처리 버전으로, 작업 분할-정복(divide-and-conquer) 알고리즘에 최적화되어 있다.
* 일반 스레드 풀과 달리 작업 훔치기(work-stealing) 알고리즘을 사용한다.
  * 유휴 상태의 스레드가 다른 바쁜 스레드의 작업 큐에서 작업을 가져와 처리한다.
  * 이를 통해 부하 분산과 효율적인 CPU 활용이 가능하다.
* 병렬 스트림 작업이나 CompletableFuture와 함께 사용될 때 성능이 극대화된다.
* 주요 특징:
  * 고정된 수의 스레드를 사용하여 안정적인 리소스 사용이 가능하다.
  * 재귀적 작업 처리에 최적화되어 있다.
  * 작업을 더 작은 하위 작업으로 분할하여 병렬로 처리한 후 결과를 결합한다.
* 사용 예시:
  * ForkJoinPool.commonPool(): 기본 공통 풀 사용
  * new ForkJoinPool(N): N개의 병렬 처리 수준으로 커스텀 풀 생성

### 자바 예시 코드
```java
import java.util.concurrent.ForkJoinPool;
import java.util.concurrent.RecursiveTask;
import java.util.Arrays;
import java.util.concurrent.TimeUnit;

public class ForkJoinPoolExample {
    public static void main(String[] args) {
        // 큰 배열 생성 (1부터 1,000,000까지의 숫자)
        int[] numbers = new int[1_000_000];
        for (int i = 0; i < numbers.length; i++) {
            numbers[i] = i + 1;
        }
        
        // 기본 공통 풀 사용
        ForkJoinPool commonPool = ForkJoinPool.commonPool();
        System.out.println("공통 풀의 병렬 처리 수준: " + commonPool.getParallelism());
        
        // 작업 생성 및 제출
        SumTask task = new SumTask(numbers, 0, numbers.length);
        long startTime = System.currentTimeMillis();
        long sum = commonPool.invoke(task);
        long endTime = System.currentTimeMillis();
        
        System.out.println("합계: " + sum);
        System.out.println("소요 시간: " + (endTime - startTime) + "ms");
        
        // 커스텀 풀 생성 (4개의 스레드)
        ForkJoinPool customPool = new ForkJoinPool(4);
        System.out.println("\n커스텀 풀의 병렬 처리 수준: " + customPool.getParallelism());
        
        try {
            // 작업 제출
            startTime = System.currentTimeMillis();
            sum = customPool.invoke(new SumTask(numbers, 0, numbers.length));
            endTime = System.currentTimeMillis();
            
            System.out.println("합계: " + sum);
            System.out.println("소요 시간: " + (endTime - startTime) + "ms");
        } finally {
            // 커스텀 풀 종료
            customPool.shutdown();
            try {
                if (!customPool.awaitTermination(1, TimeUnit.SECONDS)) {
                    customPool.shutdownNow();
                }
            } catch (InterruptedException e) {
                customPool.shutdownNow();
            }
        }
    }
    
    // RecursiveTask를 확장한 작업 클래스 (결과를 반환)
    static class SumTask extends RecursiveTask<Long> {
        private static final int THRESHOLD = 10_000; // 분할 임계값
        private final int[] array;
        private final int start;
        private final int end;
        
        public SumTask(int[] array, int start, int end) {
            this.array = array;
            this.start = start;
            this.end = end;
        }
        
        @Override
        protected Long compute() {
            int length = end - start;
            
            // 작업이 충분히 작으면 직접 계산
            if (length <= THRESHOLD) {
                return computeDirectly();
            }
            
            // 작업을 두 개의 하위 작업으로 분할
            int mid = start + length / 2;
            
            // 첫 번째 하위 작업 생성 및 포크(비동기 실행)
            SumTask leftTask = new SumTask(array, start, mid);
            leftTask.fork();
            
            // 두 번째 하위 작업 생성 및 직접 실행
            SumTask rightTask = new SumTask(array, mid, end);
            Long rightResult = rightTask.compute();
            
            // 첫 번째 하위 작업의 결과를 기다리고 두 결과를 결합
            Long leftResult = leftTask.join();
            return leftResult + rightResult;
        }
        
        private long computeDirectly() {
            long sum = 0;
            for (int i = start; i < end; i++) {
                sum += array[i];
            }
            return sum;
        }
    }
}
```

## CommonPool 전략
* ForkJoinPool.commonPool()은 JDK 8부터 도입된 시스템 전체에서 공유되는 기본 ForkJoinPool이다.
* 모든 병렬 스트림 작업과 CompletableFuture 작업은 별도로 지정하지 않으면 이 공통 풀을 사용한다.
* 주요 특징:
  * 시스템 전체에서 공유되므로 별도의 풀 생성 비용이 없다.
  * 기본적으로 (CPU 코어 수 - 1)개의 스레드를 사용한다.
  * java.util.concurrent.ForkJoinPool.common.parallelism 시스템 속성으로 병렬 처리 수준을 조정할 수 있다.
  * 공유 리소스이므로 다른 애플리케이션 코드와 경쟁할 수 있다.
* 사용 시 고려사항:
  * 짧고 CPU 바운드 작업에 적합하다.
  * I/O 바운드 작업이나 장기 실행 작업에는 적합하지 않다.
  * 애플리케이션 전체의 성능에 영향을 줄 수 있으므로 사용 시 주의가 필요하다.

### 자바 예시 코드
```java
import java.util.concurrent.ForkJoinPool;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.TimeUnit;

public class CommonPoolExample {
    public static void main(String[] args) {
        System.out.println("CommonPool 정보:");
        System.out.println("병렬 처리 수준: " + ForkJoinPool.commonPool().getParallelism());
        System.out.println("풀 크기: " + ForkJoinPool.commonPool().getPoolSize());
        System.out.println("활성 스레드 수: " + ForkJoinPool.commonPool().getActiveThreadCount());
        System.out.println("실행 대기 중인 작업 수: " + ForkJoinPool.commonPool().getQueuedSubmissionCount());
        
        // 병렬 스트림 예제 (내부적으로 CommonPool 사용)
        List<Integer> numbers = Arrays.asList(1, 2, 3, 4, 5, 6, 7, 8, 9, 10);
        
        System.out.println("\n병렬 스트림 실행 (CommonPool 사용):");
        long startTime = System.currentTimeMillis();
        
        long sum = numbers.parallelStream()
                         .map(n -> {
                             String threadName = Thread.currentThread().getName();
                             System.out.println("스레드 " + threadName + "에서 처리 중: " + n);
                             
                             // 작업 시뮬레이션
                             try {
                                 TimeUnit.MILLISECONDS.sleep(100);
                             } catch (InterruptedException e) {
                                 Thread.currentThread().interrupt();
                             }
                             
                             return n * 2;
                         })
                         .reduce(0, Integer::sum);
        
        long endTime = System.currentTimeMillis();
        
        System.out.println("\n결과: " + sum);
        System.out.println("소요 시간: " + (endTime - startTime) + "ms");
        
        // CompletableFuture 예제 (내부적으로 CommonPool 사용)
        System.out.println("\nCompletableFuture 실행 (CommonPool 사용):");
        startTime = System.currentTimeMillis();
        
        int result = java.util.concurrent.CompletableFuture
                        .supplyAsync(() -> {
                            String threadName = Thread.currentThread().getName();
                            System.out.println("CompletableFuture 작업 실행 중: " + threadName);
                            
                            // 작업 시뮬레이션
                            try {
                                TimeUnit.MILLISECONDS.sleep(500);
                            } catch (InterruptedException e) {
                                Thread.currentThread().interrupt();
                            }
                            
                            return 42;
                        })
                        .join();
        
        endTime = System.currentTimeMillis();
        
        System.out.println("CompletableFuture 결과: " + result);
        System.out.println("소요 시간: " + (endTime - startTime) + "ms");
        
        // CommonPool 정보 다시 확인
        System.out.println("\n작업 후 CommonPool 정보:");
        System.out.println("활성 스레드 수: " + ForkJoinPool.commonPool().getActiveThreadCount());
        System.out.println("실행 대기 중인 작업 수: " + ForkJoinPool.commonPool().getQueuedSubmissionCount());
    }
}
```
  

## 단일 스레드 풀 전략
* Executors.newSingleThreadExecutor()는 단일 스레드로 작업을 순차적으로 처리하는 풀이다.
* 주요 특징:
  * 단 하나의 스레드만 사용하여 모든 작업을 순차적으로 실행한다.
  * 작업 간의 순서가 보장된다 (FIFO: First In, First Out).
  * 작업 큐의 크기에 제한이 없다.
  * 스레드가 예외로 종료되면 새 스레드가 자동으로 생성되어 대체된다.
* 사용 시 고려사항:
  * 작업 간의 순서가 중요한 경우에 적합하다.
  * 동시성 문제를 피하고 싶을 때 유용하다.
  * 단일 스레드이므로 처리량이 제한적이다.
  * 장시간 실행되는 작업이 있으면 다른 작업이 지연될 수 있다.

### 자바 예시 코드
```java
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

public class SingleThreadExecutorExample {
    public static void main(String[] args) {
        // 단일 스레드 풀 생성
        ExecutorService executor = Executors.newSingleThreadExecutor();
        
        System.out.println("작업 제출 시작 (순서대로 실행됨)");
        
        // 5개의 작업 제출
        for (int i = 0; i < 5; i++) {
            final int taskId = i;
            executor.submit(() -> {
                String threadName = Thread.currentThread().getName();
                System.out.println("Task " + taskId + " 실행 중: " + threadName);
                
                // 작업 시뮬레이션 (각 작업마다 다른 시간 소요)
                try {
                    TimeUnit.SECONDS.sleep(1 + taskId % 3);  // 1~3초 소요
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
                
                System.out.println("Task " + taskId + " 완료: " + threadName);
                return "Task " + taskId + " 결과";
            });
        }
        
        // 스레드 예외 상황 시뮬레이션
        executor.submit(() -> {
            System.out.println("\n예외 발생 작업 실행");
            String threadName = Thread.currentThread().getName();
            System.out.println("예외 발생 전 스레드 이름: " + threadName);
            
            // 예외 발생
            throw new RuntimeException("의도적인 예외 발생");
        });
        
        // 잠시 대기 (예외 발생 후 새 스레드 생성 확인)
        try {
            TimeUnit.SECONDS.sleep(1);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
        
        // 추가 작업 제출 (새 스레드에서 실행됨)
        executor.submit(() -> {
            String threadName = Thread.currentThread().getName();
            System.out.println("\n예외 발생 후 새 작업 실행 중: " + threadName);
            return "새 스레드에서 실행된 작업 결과";
        });
        
        // 스레드 풀 종료
        executor.shutdown();
        try {
            // 모든 작업이 완료될 때까지 최대 10초 대기
            if (!executor.awaitTermination(10, TimeUnit.SECONDS)) {
                executor.shutdownNow();
            }
        } catch (InterruptedException e) {
            executor.shutdownNow();
        }
        
        System.out.println("\n모든 작업 완료. 단일 스레드 풀은 작업 간 순서를 보장합니다.");
    }
}
```

## 스케줄 스레드 풀 전략
* Executors.newScheduledThreadPool()은 작업을 지연 실행하거나 주기적으로 실행할 수 있는 풀이다.
* 주요 특징:
  * 지정된 지연 시간 후에 작업을 실행할 수 있다.
  * 고정된 주기로 작업을 반복 실행할 수 있다.
  * 이전 작업 완료 후 일정 시간 간격으로 작업을 실행할 수 있다.
  * 내부적으로 DelayedWorkQueue를 사용하여 작업의 실행 시간을 관리한다.
* 사용 시 고려사항:
  * 타이머 작업, 주기적 유지 관리 작업, 폴링 작업에 적합하다.
  * 장기 실행 작업은 다른 예약된 작업의 실행을 지연시킬 수 있다.
  * 시간에 민감한 작업의 경우 정확한 타이밍을 보장하지 않는다.
  * 고정 속도 실행(fixedRate)과 고정 지연 실행(fixedDelay)의 차이를 이해하고 사용해야 한다.

### 자바 예시 코드
```java
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ScheduledFuture;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

public class ScheduledThreadPoolExample {
    public static void main(String[] args) {
        // 2개의 스레드를 가진 스케줄 스레드 풀 생성
        ScheduledExecutorService scheduler = Executors.newScheduledThreadPool(2);
        
        System.out.println("스케줄 스레드 풀 예제 시작: " + System.currentTimeMillis() + "ms");
        
        // 1. 지연 실행 (3초 후 한 번 실행)
        scheduler.schedule(() -> {
            System.out.println("\n지연 작업 실행: " + System.currentTimeMillis() + "ms");
            System.out.println("스레드: " + Thread.currentThread().getName());
            return "지연 작업 완료";
        }, 3, TimeUnit.SECONDS);
        
        // 2. 고정 속도 실행 (1초 후 시작, 2초 간격으로 실행)
        final AtomicInteger fixedRateCounter = new AtomicInteger(0);
        ScheduledFuture<?> fixedRateTask = scheduler.scheduleAtFixedRate(() -> {
            int count = fixedRateCounter.incrementAndGet();
            long time = System.currentTimeMillis();
            System.out.println("\n고정 속도 작업 #" + count + " 실행: " + time + "ms");
            System.out.println("스레드: " + Thread.currentThread().getName());
            
            // 작업 시뮬레이션
            try {
                // 작업이 간격보다 오래 걸리는 경우 시뮬레이션
                if (count == 2) {
                    System.out.println("긴 작업 시뮬레이션 (3초)...");
                    TimeUnit.SECONDS.sleep(3);
                } else {
                    TimeUnit.MILLISECONDS.sleep(500);
                }
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
            
            System.out.println("고정 속도 작업 #" + count + " 완료: " + System.currentTimeMillis() + "ms");
            
            // 5번 실행 후 취소
            if (count >= 5) {
                System.out.println("고정 속도 작업 최대 실행 횟수 도달, 취소됨");
                fixedRateTask.cancel(false);
            }
        }, 1, 2, TimeUnit.SECONDS);
        
        // 3. 고정 지연 실행 (2초 후 시작, 이전 작업 완료 후 1.5초 간격으로 실행)
        final AtomicInteger fixedDelayCounter = new AtomicInteger(0);
        scheduler.scheduleWithFixedDelay(() -> {
            int count = fixedDelayCounter.incrementAndGet();
            long time = System.currentTimeMillis();
            System.out.println("\n고정 지연 작업 #" + count + " 실행: " + time + "ms");
            System.out.println("스레드: " + Thread.currentThread().getName());
            
            // 작업 시뮬레이션
            try {
                // 두 번째 실행에서 더 오래 걸리는 작업 시뮬레이션
                if (count == 2) {
                    System.out.println("긴 작업 시뮬레이션 (2초)...");
                    TimeUnit.SECONDS.sleep(2);
                } else {
                    TimeUnit.MILLISECONDS.sleep(500);
                }
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
            
            System.out.println("고정 지연 작업 #" + count + " 완료: " + System.currentTimeMillis() + "ms");
            
            // 4번 실행 후 종료 조건
            if (count >= 4) {
                System.out.println("고정 지연 작업 최대 실행 횟수 도달");
                // 전체 스케줄러 종료 신호
                scheduler.shutdown();
            }
        }, 2, 1, TimeUnit.SECONDS);
        
        // 4. 일회성 작업 여러 개 예약
        for (int i = 1; i <= 3; i++) {
            final int taskId = i;
            scheduler.schedule(() -> {
                System.out.println("\n일회성 작업 " + taskId + " 실행: " + System.currentTimeMillis() + "ms");
                System.out.println("스레드: " + Thread.currentThread().getName());
                return "일회성 작업 " + taskId + " 완료";
            }, i * 2, TimeUnit.SECONDS);
        }
        
        // 모든 작업이 완료될 때까지 대기
        try {
            // 최대 30초 대기
            if (!scheduler.awaitTermination(30, TimeUnit.SECONDS)) {
                System.out.println("일부 작업이 완료되지 않았지만 스케줄러를 강제 종료합니다.");
                scheduler.shutdownNow();
            }
        } catch (InterruptedException e) {
            scheduler.shutdownNow();
            Thread.currentThread().interrupt();
        }
        
        System.out.println("\n모든 예약 작업 완료. 스케줄 스레드 풀 종료됨.");
    }
}
```

## 작업 훔치기 풀 전략
* Java 8에서 도입된 Executors.newWorkStealingPool()은 ForkJoinPool을 기반으로 한 작업 훔치기 알고리즘을 사용하는 풀이다.
* 주요 특징:
  * 기본적으로 사용 가능한 프로세서 수만큼의 병렬 처리 수준을 가진다.
  * 각 스레드는 자신의 작업 큐를 가지며, 자신의 큐가 비면 다른 스레드의 큐에서 작업을 "훔친다".
  * 내부적으로 ForkJoinPool을 사용하지만 일반 Executor 인터페이스로 노출된다.
  * 데몬 스레드를 사용하므로 명시적으로 종료하지 않아도 JVM이 종료될 수 있다.
* 사용 시 고려사항:
  * 많은 독립적인 작업을 병렬로 처리할 때 효율적이다.
  * 작업이 불균등하게 분배될 때 특히 유용하다.
  * 작업이 다른 작업을 생성하거나 분할하는 경우에 적합하다.
  * 작업 간 데이터 지역성이 중요한 경우 성능이 향상될 수 있다.

### 자바 예시 코드
```java
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;

public class WorkStealingPoolExample {
    public static void main(String[] args) {
        // 작업 훔치기 풀 생성 (기본적으로 사용 가능한 프로세서 수만큼의 병렬 처리 수준)
        ExecutorService executor = Executors.newWorkStealingPool();
        
        // 또는 병렬 처리 수준을 명시적으로 지정
        // ExecutorService executor = Executors.newWorkStealingPool(4);
        
        System.out.println("작업 훔치기 풀 예제 시작");
        System.out.println("사용 가능한 프로세서 수: " + Runtime.getRuntime().availableProcessors());
        
        // 다양한 실행 시간을 가진 작업 생성 (불균등한 작업 부하 시뮬레이션)
        List<Future<String>> futures = new ArrayList<>();
        
        for (int i = 0; i < 20; i++) {
            final int taskId = i;
            final long duration = (i % 5 + 1) * 500; // 500ms ~ 2500ms
            
            futures.add(executor.submit(() -> {
                String threadName = Thread.currentThread().getName();
                System.out.println("Task " + taskId + " 시작 (소요 시간: " + duration + "ms), 스레드: " + threadName);
                
                // 작업 시뮬레이션
                try {
                    TimeUnit.MILLISECONDS.sleep(duration);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
                
                System.out.println("Task " + taskId + " 완료, 스레드: " + threadName);
                return "Task " + taskId + " 결과";
            }));
        }
        
        // 모든 작업의 결과 수집
        for (int i = 0; i < futures.size(); i++) {
            try {
                String result = futures.get(i).get();
                System.out.println("결과 수신: " + result);
            } catch (Exception e) {
                System.out.println("작업 실행 중 오류 발생: " + e.getMessage());
            }
        }
        
        // 재귀적 작업 예제 (작업 훔치기가 효과적인 시나리오)
        System.out.println("\n재귀적 작업 처리 예제 시작");
        
        long startTime = System.currentTimeMillis();
        
        // 여러 개의 재귀적 작업 제출
        List<Future<Long>> recursiveFutures = new ArrayList<>();
        for (int i = 25; i <= 35; i++) {
            final int n = i;
            recursiveFutures.add(executor.submit(() -> {
                String threadName = Thread.currentThread().getName();
                System.out.println("피보나치(" + n + ") 계산 시작, 스레드: " + threadName);
                long result = fibonacci(n);
                System.out.println("피보나치(" + n + ") = " + result + ", 스레드: " + threadName);
                return result;
            }));
        }
        
        // 재귀적 작업 결과 수집
        for (Future<Long> future : recursiveFutures) {
            try {
                future.get();
            } catch (Exception e) {
                System.out.println("재귀 작업 실행 중 오류 발생: " + e.getMessage());
            }
        }
        
        long endTime = System.currentTimeMillis();
        System.out.println("모든 재귀 작업 완료, 총 소요 시간: " + (endTime - startTime) + "ms");
        
        // 작업 훔치기 풀은 데몬 스레드를 사용하므로 명시적으로 종료할 필요가 없지만,
        // 좋은 습관을 위해 종료 코드 추가
        executor.shutdown();
        try {
            if (!executor.awaitTermination(10, TimeUnit.SECONDS)) {
                executor.shutdownNow();
            }
        } catch (InterruptedException e) {
            executor.shutdownNow();
            Thread.currentThread().interrupt();
        }
        
        System.out.println("\n작업 훔치기 풀 예제 종료");
    }
    
    // 피보나치 수열 계산 (의도적으로 비효율적인 재귀 구현)
    private static long fibonacci(int n) {
        if (n <= 1) return n;
        return fibonacci(n - 1) + fibonacci(n - 2);
    }
}
```

## 가상 스레드 풀 전략
* Java 21에서 정식 도입된 Executors.newVirtualThreadPerTaskExecutor()는 가상 스레드를 사용하는 풀이다.
* 주요 특징:
  * 각 작업마다 새로운 가상 스레드를 생성한다.
  * 가상 스레드는 경량 스레드로, OS 스레드보다 훨씬 적은 리소스를 사용한다.
  * 수백만 개의 가상 스레드를 생성할 수 있어 높은 동시성을 지원한다.
  * 특히 I/O 바운드 작업에 최적화되어 있다.
  * 스레드 블로킹이 발생하면 OS 스레드를 차단하지 않고 다른 가상 스레드로 전환한다.
* 사용 시 고려사항:
  * I/O 바운드 작업이나 네트워크 작업에 매우 효과적이다.
  * 스레드 로컬 변수 사용 시 주의가 필요하다.
  * CPU 바운드 작업에는 기존의 플랫폼 스레드 풀이 더 효율적일 수 있다.
  * 기존 코드를 최소한의 변경으로 높은 동시성을 달성할 수 있다.

### 자바 예시 코드
```java
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

public class VirtualThreadPoolExample {
    public static void main(String[] args) {
        // 가상 스레드 풀 생성
        try (ExecutorService executor = Executors.newVirtualThreadPerTaskExecutor()) {
            System.out.println("가상 스레드 풀 예제 시작");
            
            // 동시에 실행 중인 가상 스레드 수 추적
            AtomicInteger activeThreads = new AtomicInteger(0);
            AtomicInteger maxActiveThreads = new AtomicInteger(0);
            
            // 많은 수의 I/O 바운드 작업 시뮬레이션
            int taskCount = 10_000;
            List<Future<String>> futures = new ArrayList<>(taskCount);
            
            long startTime = System.currentTimeMillis();
            
            for (int i = 0; i < taskCount; i++) {
                final int taskId = i;
                futures.add(executor.submit(() -> {
                    // 활성 스레드 카운터 증가
                    int currentActive = activeThreads.incrementAndGet();
                    maxActiveThreads.updateAndGet(max -> Math.max(max, currentActive));
                    
                    String threadName = Thread.currentThread().toString();
                    
                    // 로깅은 처음 10개와 마지막 10개 작업만 (출력 과부하 방지)
                    if (taskId < 10 || taskId >= taskCount - 10) {
                        System.out.println("Task " + taskId + " 시작, 스레드: " + threadName + 
                                          ", 현재 활성 스레드: " + currentActive);
                    }
                    
                    // I/O 작업 시뮬레이션 (블로킹 작업)
                    try {
                        // 다양한 지연 시간 (10ms ~ 100ms)
                        TimeUnit.MILLISECONDS.sleep(10 + taskId % 10 * 10);
                    } catch (InterruptedException e) {
                        Thread.currentThread().interrupt();
                    }
                    
                    // 활성 스레드 카운터 감소
                    activeThreads.decrementAndGet();
                    
                    // 로깅은 처음 10개와 마지막 10개 작업만
                    if (taskId < 10 || taskId >= taskCount - 10) {
                        System.out.println("Task " + taskId + " 완료, 스레드: " + threadName);
                    }
                    
                    return "Task " + taskId + " 결과";
                }));
            }
            
            // 모든 작업 완료 대기
            int completedTasks = 0;
            for (Future<String> future : futures) {
                try {
                    future.get();
                    completedTasks++;
                    
                    // 진행 상황 로깅 (1000개 작업마다)
                    if (completedTasks % 1000 == 0) {
                        System.out.println(completedTasks + " 작업 완료...");
                    }
                } catch (Exception e) {
                    System.out.println("작업 실행 중 오류 발생: " + e.getMessage());
                }
            }
            
            long endTime = System.currentTimeMillis();
            long duration = endTime - startTime;
            
            System.out.println("\n성능 통계:");
            System.out.println("총 작업 수: " + taskCount);
            System.out.println("총 소요 시간: " + duration + "ms");
            System.out.println("초당 처리된 작업: " + (taskCount * 1000.0 / duration));
            System.out.println("최대 동시 활성 가상 스레드: " + maxActiveThreads.get());
            
            // 가상 스레드와 플랫폼 스레드 비교 예제
            System.out.println("\n가상 스레드와 플랫폼 스레드 비교 (메모리 사용량):");
            
            // 플랫폼 스레드 생성 시뮬레이션
            System.out.println("플랫폼 스레드 1000개를 생성하려면 약 1GB의 메모리가 필요합니다.");
            
            // 가상 스레드 생성 시뮬레이션
            System.out.println("가상 스레드 1,000,000개는 약 1GB의 메모리만 사용합니다.");
            
            System.out.println("\n가상 스레드 풀 예제 종료");
        } // try-with-resources가 자동으로 executor.close() 호출
    }
}
```
