---
title: "3-4. 데이터 영속성(JPA)과 트랜잭션"
order: 4
tags: [jpa, hibernate, transaction]
status: draft
author: vivace
---

# 3-4. 데이터 영속성(JPA)과 트랜잭션

SQL을 직접 쓰는 것은 번거롭습니다. 테이블 구조가 바뀔 때마다 SQL도 따라 바뀝니다. JPA는 객체와 데이터베이스 사이의 간극을 줄입니다. 자바 코드로 DB를 다루고, SQL은 JPA가 만들어줍니다.

---

## JPA란

JPA(Java Persistence API)는 자바 객체와 관계형 데이터베이스를 매핑하는 표준 명세입니다. Hibernate가 이 명세의 대표 구현체이고, Spring Boot는 기본으로 Hibernate를 사용합니다.

```
Java 객체 (User)  ←→  JPA/Hibernate  ←→  DB 테이블 (users)
```

ORM(Object-Relational Mapping)이라고도 부릅니다. 객체와 테이블을 자동으로 연결합니다.

---

## 엔티티 정의

```java
@Entity
@Table(name = "users")
@Getter
@Builder
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor
public class User {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 50)
    private String name;

    @Column(nullable = false, unique = true)
    private String email;

    @Enumerated(EnumType.STRING)
    private UserRole role;

    @CreationTimestamp
    private LocalDateTime createdAt;

    @UpdateTimestamp
    private LocalDateTime updatedAt;

    // 비즈니스 메서드
    public void changeName(String newName) {
        this.name = newName;
    }
}
```

| 애너테이션 | 역할 |
|-----------|------|
| `@Entity` | 이 클래스가 DB 테이블과 매핑됨을 선언 |
| `@Table(name = "users")` | 매핑할 테이블 이름 지정 (생략 시 클래스명) |
| `@Id` | 기본 키(Primary Key) 필드 |
| `@GeneratedValue` | 기본 키 자동 생성 전략 |
| `@Column` | 컬럼 속성 지정 (nullable, unique, length 등) |
| `@Enumerated(EnumType.STRING)` | Enum을 문자열로 저장 |
| `@CreationTimestamp` | 생성 시각 자동 기록 |

`@NoArgsConstructor(access = AccessLevel.PROTECTED)` — JPA는 기본 생성자가 필요합니다. `PROTECTED`로 외부에서 직접 생성하지 못하게 막습니다. `@Builder`로만 생성하도록 유도합니다.

---

## 연관 관계

데이터베이스의 외래키(FK)를 자바 객체 참조로 표현합니다.

### 일대다(One-to-Many) — 사용자와 게시글

```java
// Post 엔티티 (다 쪽 — FK가 있는 쪽)
@Entity
public class Post {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String title;
    private String content;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id")
    private User author;
}

// User 엔티티 (일 쪽)
@Entity
public class User {
    // ...

    @OneToMany(mappedBy = "author", cascade = CascadeType.ALL)
    private List<Post> posts = new ArrayList<>();
}
```

`fetch = FetchType.LAZY` — 연관 객체를 즉시 가져오지 않고, 실제로 사용할 때 조회합니다. 성능에 중요합니다. 기본값은 `EAGER`(즉시 로딩)이지만, 실무에서는 항상 `LAZY`를 권장합니다.

---

## 트랜잭션

트랜잭션은 **여러 DB 작업을 하나의 논리적 단위로 묶는 것**입니다. 모두 성공하거나, 하나라도 실패하면 전부 취소(롤백)합니다.

```java
@Service
@Transactional(readOnly = true)
public class OrderService {

    @Transactional  // 쓰기 작업: readOnly 오버라이드
    public OrderResponse placeOrder(OrderRequest request) {
        // 1. 재고 확인
        Product product = productRepository.findById(request.getProductId())
                .orElseThrow(() -> new EntityNotFoundException("상품 없음"));

        // 2. 재고 차감
        product.decreaseStock(request.getQuantity()); // 재고 부족 시 예외 발생

        // 3. 주문 생성
        Order order = Order.builder()
                .product(product)
                .quantity(request.getQuantity())
                .build();

        return OrderResponse.from(orderRepository.save(order));
        // 2번에서 예외 발생 시 → 3번도 취소됨 (롤백)
    }
}
```

`@Transactional`이 없으면 DB 작업마다 별개의 트랜잭션이 실행됩니다. 재고는 줄었는데 주문은 안 만들어지는 상황이 생길 수 있습니다.

### 변경 감지(Dirty Checking)

JPA 트랜잭션 안에서는 엔티티를 직접 수정하면 자동으로 UPDATE가 실행됩니다.

```java
@Transactional
public UserResponse updateName(Long id, String newName) {
    User user = userRepository.findById(id)
            .orElseThrow(() -> new EntityNotFoundException("사용자 없음"));

    user.changeName(newName);  // save() 호출 없이도 트랜잭션 끝날 때 자동 UPDATE
    return UserResponse.from(user);
}
```

`save()`를 다시 호출하지 않아도 됩니다. JPA가 트랜잭션 종료 시점에 변경된 필드를 감지해 SQL을 실행합니다.

---

## JPQL과 네이티브 쿼리

메서드 이름으로 해결이 안 되는 복잡한 쿼리는 직접 작성합니다.

```java
public interface PostRepository extends JpaRepository<Post, Long> {

    // JPQL — 테이블명 대신 엔티티명, 컬럼명 대신 필드명 사용
    @Query("SELECT p FROM Post p WHERE p.author.id = :userId ORDER BY p.createdAt DESC")
    List<Post> findByUserId(@Param("userId") Long userId);

    // 네이티브 SQL — 복잡한 집계, DB 전용 함수 사용 시
    @Query(value = "SELECT * FROM posts WHERE MATCH(title, content) AGAINST(:keyword)", nativeQuery = true)
    List<Post> searchByKeyword(@Param("keyword") String keyword);
}
```

---

> JPA를 처음 쓸 때 가장 흔한 실수는 `EAGER` 로딩입니다. 연관 관계는 항상 `LAZY`로 시작하세요. 성능 문제의 절반이 여기서 나옵니다.

---

## 실습

```java
// 아래 요구사항을 JPA로 구현해보세요.
//
// 1. Category와 Product 엔티티 생성
//    - 하나의 Category에 여러 Product (일대다)
//    - Product: id, name, price, stock
//    - Category: id, name, products
//
// 2. 재고 차감 트랜잭션 구현
//    - 재고가 0이면 예외 발생
//    - 재고 차감과 주문 저장이 하나의 트랜잭션에서 처리되는지 확인
//
// 3. 변경 감지 확인
//    - 상품 가격을 수정하는 메서드 작성
//    - save() 없이 가격이 DB에 반영되는지 확인
```
