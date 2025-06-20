# 🔍 Phân tích Sleep Connections - Nguyên nhân & Giải pháp

## 📊 **Đánh giá tổng thể:**

**Hiện trạng:** `toktak | Sleep | 17 | | NULL` 
- Connection đang idle trong **17 giây**
- Đây là nguyên nhân chính gây **"Too many connections"**
- Tích tụ connection không được cleanup đúng cách

## 🚨 **Top 5 nguyên nhân gây Sleep Connections:**

### 1. **Consumer processes không cleanup session** ⚠️ **CAO**
**Vị trí:** `consumer_youtube.py`, `consumer_facebook.py`, `consumer_tiktok.py`...
```python
# ❌ HIỆN TẠI: Không có session cleanup
def action_send_post_to_link(message):
    with app.app_context():  # Tạo context mới
        result = action_send_post_to_link(message)  # DB operations
        # Không cleanup session!
```

**Tác động:**
- Mỗi message tạo 1 connection mới
- Connection không được đóng sau khi xử lý
- Tích tụ **hàng trăm idle connections**

### 2. **Long-running operations với time.sleep()** ⚠️ **CAO** 
**Vị trí:** `app/third_parties/` - Facebook, TikTok, Instagram, Thread
```python
# Ví dụ trong app/third_parties/facebook.py
time.sleep(LimitSNS.WAIT_PER_API_CALL.value)  # 2-5 giây
time.sleep(LimitSNS.WAIT_SECOND_CHECK_STATUS.value)  # 10-30 giây
```

**Tác động:**
- Connection giữ **5-30 giây** mỗi API call
- Với nhiều request đồng thời = nhiều connection idle
- Tích tụ connection trong quá trình chờ API response

### 3. **Selenium consumers với polling loops** ⚠️ **TRUNG BÌNH**
**Vị trí:** `selenium_consumer.py`
```python
while not stop_event.is_set():
    task_item = redis_client.blpop("toktak:crawl_ali_queue", timeout=10)
    # Giữ connection trong suốt 10s timeout
    time.sleep(1)  # Thêm sleep giữa các iteration
```

### 4. **Schedule tasks với bulk operations** ⚠️ **TRUNG BÌNH**
**Vị trí:** `schedule_tasks.py`
```python
while has_more_batches:
    batches = db.session.query(Batch).limit(100).all()  # Giữ connection
    # Xử lý 100 records mỗi lần
    # Connection idle trong quá trình xử lý
```

### 5. **Image processing với file wait loops** ⚠️ **THẤP**
**Vị trí:** `app/makers/images.py`
```python
while not os.path.exists(image_path) and (time.time() - start_time < timeout):
    sleep(0.5)  # Giữ connection trong 0.5s x nhiều lần
```

## 🛠️ **Giải pháp chi tiết:**

### 1. **Sửa Consumer Session Management** - **KHẨN CẤP**

**Sửa tất cả consumer files:**
```python
# ✅ ĐÚNG - Thêm session cleanup
def action_send_post_to_link(message):
    try:
        # ... xử lý logic ...
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e
    finally:
        db.session.remove()  # QUAN TRỌNG: Cleanup session
```

### 2. **Tối ưu Third-party API calls** - **CAO**

**Tách riêng DB operations và API calls:**
```python
# ✅ ĐÚNG - Không giữ connection khi sleep
def upload_to_facebook(post_data):
    # 1. Lấy data từ DB và đóng connection
    post = Post.query.get(post_id)
    db.session.remove()  # Đóng connection
    
    # 2. Gọi API với sleep (không giữ DB connection)
    response = facebook_api.upload(post_data)
    time.sleep(LimitSNS.WAIT_PER_API_CALL.value)
    
    # 3. Tạo connection mới để update result
    Post.query.filter_by(id=post_id).update({'status': 'uploaded'})
    db.session.commit()
    db.session.remove()
```

### 3. **Cải thiện Selenium Consumer** - **TRUNG BÌNH**

```python
# ✅ ĐÚNG - Sử dụng connection pool riêng
def worker_instance():
    app = create_app()
    browser = create_driver_instance()
    
    while not stop_event.is_set():
        try:
            with app.app_context():
                task_item = redis_client.blpop("queue", timeout=10)
                if task_item:
                    process_task_on_tab(browser, task)
                    db.session.commit()
                else:
                    time.sleep(1)
        finally:
            db.session.remove()  # Cleanup sau mỗi iteration
```

### 4. **Tối ưu Schedule Tasks** - **TRUNG BÌNH**

```python
# ✅ ĐÚNG - Xử lý batch với session management
def cleanup_pending_batches(app):
    with app.app_context():
        while True:
            # Chỉ lấy IDs trước
            batch_ids = db.session.query(Batch.id).filter(
                Batch.process_status == "PENDING"
            ).limit(100).all()
            
            if not batch_ids:
                break
                
            # Đóng session sau khi lấy IDs
            db.session.remove()
            
            # Xử lý từng batch riêng biệt
            for batch_id in batch_ids:
                try:
                    # Tạo session mới cho mỗi batch
                    batch = Batch.query.get(batch_id)
                    batch.delete()
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                finally:
                    db.session.remove()  # Cleanup
```

## 🔧 **Cấu hình bổ sung:**

### 1. **Thêm connection timeout ngắn hơn**
```python
# Trong app/config.py
SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_size": 20,
    "max_overflow": 50, 
    "pool_timeout": 10,      # Giảm từ 30 xuống 10 giây
    "pool_recycle": 900,     # Giảm từ 1800 xuống 900 giây (15 phút)
    "pool_pre_ping": True,
}
```

### 2. **Thêm MySQL timeout settings**
```sql
-- Trong MySQL config
SET GLOBAL wait_timeout = 600;        -- 10 phút thay vì 8 giờ
SET GLOBAL interactive_timeout = 600;  -- 10 phút
SET GLOBAL innodb_lock_wait_timeout = 50;  -- 50 giây cho lock
```

### 3. **Monitoring & Alerting**
```python
# Thêm vào các consumer
import threading
import time

def monitor_connections():
    while True:
        result = db.session.execute(text("SHOW PROCESSLIST")).fetchall()
        sleep_connections = [r for r in result if r[4] == 'Sleep']
        
        if len(sleep_connections) > 50:  # Alert threshold
            logger.warning(f"Too many sleep connections: {len(sleep_connections)}")
        
        time.sleep(30)  # Check mỗi 30 giây

# Chạy monitoring thread
monitor_thread = threading.Thread(target=monitor_connections, daemon=True)
monitor_thread.start()
```

## 📈 **Kết quả mong đợi:**

### Trước khi sửa:
- ❌ 200-500 connections đồng thời
- ❌ Sleep connections: 17-30 giây
- ❌ Lỗi "Too many connections" thường xuyên

### Sau khi sửa:
- ✅ 20-50 connections đồng thời
- ✅ Sleep connections: < 5 giây
- ✅ Không còn lỗi connection limit
- ✅ Giảm 80-90% số connection idle

## 🚀 **Thứ tự ưu tiên thực hiện:**

1. **KHẨN CẤP:** Sửa consumer session cleanup
2. **CAO:** Tối ưu third-party API calls
3. **CAO:** Cập nhật connection pool config  
4. **TRUNG BÌNH:** Sửa selenium consumer
5. **TRUNG BÌNH:** Tối ưu schedule tasks
6. **THẤP:** Cải thiện image processing

**Thời gian hoàn thành dự kiến:** 1-2 ngày làm việc 