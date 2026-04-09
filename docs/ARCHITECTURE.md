```mermaid
classDiagram
    class UserService {
        +createUser()
        +getUser()
        +updateUser()
        +deleteUser()
    }
    class ProductService {
        +createProduct()
        +getProduct()
        +updateProduct()
        +deleteProduct()
    }
    class OrderService {
        +createOrder()
        +getOrder()
        +updateOrder()
        +deleteOrder()
    }
    class UserRepository {
        +save()
        +findById()
        +delete()
    }
    class ProductRepository {
        +save()
        +findById()
        +delete()
    }
    class OrderRepository {
        +save()
        +findById()
        +delete()
    }
    class UserModel {
        +String name
        +String email
        +String password
    }
    class ProductModel {
        +String title
        +String description
        +float price
    }
    class OrderModel {
        +int userId
        +int productId
        +int quantity
    }
    UserService --> UserModel : utilizes
    ProductService --> ProductModel : utilizes
    OrderService --> OrderModel : utilizes
    UserRepository --> UserModel : interacts
    ProductRepository --> ProductModel : interacts
    OrderRepository --> OrderModel : interacts
    UserService --> UserRepository : uses
    ProductService --> ProductRepository : uses
    OrderService --> UserService : depends on
    OrderService --> ProductService : depends on
    ```