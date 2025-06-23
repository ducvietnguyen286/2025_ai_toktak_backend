# 🔧 Tối ưu Database Connection - Khắc phục lỗi "Too many connections"

## ⚠️ **Vấn đề đã được sửa:**

### 1. **Connection Pool Configuration**
- ✅ Giảm `pool_size` từ 200 xuống 20
- ✅ Giảm `max_overflow` từ 500 xuống 50
- ✅ Thêm `pool_recycle = 1800` (30 phút)
- ✅ Bật `pool_pre_ping = True`

### 2. **Session Management**
- ✅ Loại bỏ việc tạo `Session` riêng biệt trong `CouponService`
- ✅ Sử dụng `db.session` thay vì tạo session mới
- ✅ Loại bỏ `db.session.close()` không cần thiết

## 📋 **Best Practices cần tuân thủ:**

### 1. **KHÔNG tạo Session riêng biệt**
```python
# ❌ SAI - Tạo session riêng
session = Session(bind=db.engine)
session.query(Model).filter(...).update(...)
session.commit()
session.close()

# ✅ ĐÚNG - Sử dụng db.session
Model.query.filter(...).update(..., synchronize_session=False)
db.session.commit()
```

### 2. **KHÔNG gọi db.session.close() thủ công**
```python
# ❌ SAI - Flask-SQLAlchemy tự động quản lý
def get_user():
    user = User.query.get(1)
    db.session.close()  # Không cần thiết!
    return user

# ✅ ĐÚNG - Để Flask-SQLAlchemy tự quản lý
def get_user():
    user = User.query.get(1)
    return user
```

### 3. **Sử dụng Context Manager cho bulk operations**
```python
# ✅ ĐÚNG - Cho các operation lớn
with db.session.begin():
    for item in large_list:
        db.session.add(Model(**item))
    # Tự động commit và cleanup
```

### 4. **Sử dụng try-except cho transaction**
```python
# ✅ ĐÚNG - Xử lý lỗi transaction
try:
    db.session.add(model_instance)
    db.session.commit()
except Exception as e:
    db.session.rollback()
    raise e
```

## 🔍 **Monitoring & Debugging:**

### 1. **Kiểm tra số connection hiện tại**
```sql
-- MySQL
SHOW PROCESSLIST;
SHOW STATUS LIKE 'Threads_connected';
SHOW VARIABLES LIKE 'max_connections';

-- Xem connections theo user
SELECT USER, COUNT(*) as connections 
FROM INFORMATION_SCHEMA.PROCESSLIST 
GROUP BY USER;
```

### 2. **Tăng max_connections của MySQL (nếu cần)**
```sql
-- Tạm thời
SET GLOBAL max_connections = 200;

-- Vĩnh viễn trong my.cnf
[mysqld]
max_connections = 200
```

### 3. **Log monitoring**
```python
# Thêm vào config để debug
SQLALCHEMY_ECHO = True  # Chỉ dùng khi debug
SQLALCHEMY_ENGINE_OPTIONS = {
    'echo_pool': True,  # Log pool events
}
```

## 🚀 **Performance Tips:**

### 1. **Sử dụng connection pooling hiệu quả**
```python
# Cấu hình tối ưu cho production
SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_size": 20,           # Số connection cơ bản
    "max_overflow": 50,        # Số connection tạm thời tối đa
    "pool_timeout": 30,        # Thời gian chờ connection
    "pool_recycle": 1800,      # Recycle connection sau 30 phút
    "pool_pre_ping": True,     # Kiểm tra connection trước khi sử dụng
}
```

### 2. **Tối ưu query**
```python
# ✅ Sử dụng bulk operations
db.session.bulk_insert_mappings(Model, data_list)
db.session.bulk_update_mappings(Model, update_list)

# ✅ Eager loading để giảm N+1 queries
users = User.query.options(joinedload(User.posts)).all()

# ✅ Sử dụng raw SQL cho complex queries
result = db.session.execute(text("SELECT * FROM table WHERE condition"))
```

### 3. **Cleanup trong consumers**
```python
# Cho các consumer chạy lâu dài
def process_queue():
    while True:
        try:
            # Process message
            process_message()
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error: {e}")
        finally:
            # Cleanup mỗi lần xử lý
            db.session.remove()
```

## 🔧 **Các file đã được sửa:**
- `app/config.py` - Giảm connection pool size
- `app/services/coupon.py` - Loại bỏ Session riêng biệt
- `app/lib/query.py` - Loại bỏ db.session.close()
- `app/services/auth.py` - Sửa session management

## 🎯 **Kết quả mong đợi:**
- ✅ Giảm 80-90% số connection đồng thời
- ✅ Tăng performance và stability
- ✅ Không còn lỗi "Too many connections"
- ✅ Giảm memory usage của MySQL 