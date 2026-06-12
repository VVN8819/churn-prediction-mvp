-- Очистка старых тестовых данных (если есть)
TRUNCATE TABLE profiles CASCADE;
TRUNCATE TABLE raw_events CASCADE;

-- =========== ПРОФИЛИ ПОЛЬЗОВАТЕЛЕЙ (5 штук) ============
-- 1. Активный клиент (часто заказывает)
-- 2. Неактивный клиент (давно не заказывал - риск оттока)
-- 3. Рисковый клиент (бросает корзины, негативные отзывы)
-- 4. Охотник за скидками (использует купоны)
-- 5. Новый клиент (недавно зарегистрировался)
INSERT INTO profiles (profile_id, phone, firstname, birthday, created_at, updated_at, last_seen) VALUES
('e9922810-0a85-43c1-8e78-be8343c1f8ed', '79000000001', 'VVNvvn', '1989-04-20', NOW(), NOW(), NOW() - INTERVAL '2 days'),
('8a2edca4-5129-412a-8395-7a7a54b4f1a8', '79000000002', 'Ivan', '1985-07-15', NOW(), NOW(), NOW() - INTERVAL '95 days'),
('d64347d4-8145-4161-8cb4-affc276ed890', '79000000003', 'Petr', '1990-11-30', NOW(), NOW(), NOW() - INTERVAL '20 days'),
('99e5b77f-a446-4704-ac87-6595c39d1953', '79000000004', 'Anna', '1992-03-08', NOW(), NOW(), NOW() - INTERVAL '5 days'),
('f47ac10b-58cc-4372-a567-0e02b2c3d479', '79000000005', 'Olga', '1995-09-25', NOW(), NOW(), NOW() - INTERVAL '10 days');

-- ======== 1. Активный клиент (часто заказывает) события ============
INSERT INTO raw_events (event_id, event_type, profile_id, session_id, event_data, inserted_at) VALUES
-- Визит на главную
('a1b2c3d4-0001-4000-8000-000000000001', 'page-view', 
 'e9922810-0a85-43c1-8e78-be8343c1f8ed', '11111111-1111-1111-1111-111111111111',
 '{"event": {"id": "a1b2c3d4-0001-4000-8000-000000000001", "type": "page-view", 
   "properties": {"is_authenticated": true},
   "context": {"page": {"url": "https://demo.vsem-edu-oblako.ru/", "path": "/", "title": "Главная"}},
   "profile": {"id": "e9922810-0a85-43c1-8e78-be8343c1f8ed"},
   "session": {"id": "11111111-1111-1111-1111-111111111111"},
   "metadata": {"time": {"insert": "2026-06-07T10:00:00Z"}}}}'::JSONB,
 NOW() - INTERVAL '1 day'),

 -- Просмотр каталога
('a1b2c3d4-0001-4000-8000-000000000002', 'page-view',
 'e9922810-0a85-43c1-8e78-be8343c1f8ed', '11111111-1111-1111-1111-111111111111',
 '{"event": {"id": "a1b2c3d4-0001-4000-8000-000000000002", "type": "page-view",
   "properties": {"is_authenticated": true},
   "context": {"page": {"url": "https://demo.vsem-edu-oblako.ru/catalog", "path": "/catalog", "title": "Каталог"}},
   "profile": {"id": "e9922810-0a85-43c1-8e78-be8343c1f8ed"},
   "session": {"id": "11111111-1111-1111-1111-111111111111"},
   "metadata": {"time": {"insert": "2026-06-07T10:01:00Z"}}}}'::JSONB,
 NOW() - INTERVAL '1 day'),

 -- Просмотр товара
('a1b2c3d4-0001-4000-8000-000000000003', 'product-details-page-view',
 'e9922810-0a85-43c1-8e78-be8343c1f8ed', '11111111-1111-1111-1111-111111111111',
 '{"event": {"id": "a1b2c3d4-0001-4000-8000-000000000003", "type": "product-details-page-view",
   "properties": {"id": "102856298", "name": "Калифорния Классическая", "price": 540},
   "profile": {"id": "e9922810-0a85-43c1-8e78-be8343c1f8ed"},
   "session": {"id": "11111111-1111-1111-1111-111111111111"},
   "metadata": {"time": {"insert": "2026-06-07T10:02:00Z"}}}}'::JSONB,
 NOW() - INTERVAL '1 day'),

 -- Добавление в корзину
('a1b2c3d4-0001-4000-8000-000000000004', 'cart-changes',
 'e9922810-0a85-43c1-8e78-be8343c1f8ed', '11111111-1111-1111-1111-111111111111',
 '{"event": {"id": "a1b2c3d4-0001-4000-8000-000000000004", "type": "cart-changes",
   "properties": {
     "products": [{"id": "102856298", "name": "Калифорния Классическая", "price": 540, "quantity": 1}],
     "total": 540
   },
   "profile": {"id": "e9922810-0a85-43c1-8e78-be8343c1f8ed"},
   "session": {"id": "11111111-1111-1111-1111-111111111111"},
   "metadata": {"time": {"insert": "2026-06-07T10:03:00Z"}}}}'::JSONB,
 NOW() - INTERVAL '1 day'),

 -- Параллельные события: identification + checkout-started
('a1b2c3d4-0001-4000-8000-000000000005', 'identification',
 'e9922810-0a85-43c1-8e78-be8343c1f8ed', '11111111-1111-1111-1111-111111111111',
 '{"event": {"id": "a1b2c3d4-0001-4000-8000-000000000005", "type": "identification",
   "properties": {"phone": {"main": "79000000001"}, "firstname": "VVNvvn"},
   "context": {"page": {"url": "https://demo.vsem-edu-oblako.ru/checkout", "path": "/checkout"}},
   "profile": {"id": "e9922810-0a85-43c1-8e78-be8343c1f8ed"},
   "session": {"id": "11111111-1111-1111-1111-111111111111"},
   "metadata": {"time": {"insert": "2026-06-07T10:05:00.087Z"}}}}'::JSONB,
 NOW() - INTERVAL '1 day'),

('a1b2c3d4-0001-4000-8000-000000000006', 'checkout-started',
 'e9922810-0a85-43c1-8e78-be8343c1f8ed', '11111111-1111-1111-1111-111111111111',
 '{"event": {"id": "a1b2c3d4-0001-4000-8000-000000000006", "type": "checkout-started",
   "properties": {
     "id": "23924582",
     "order_type": "pickup",
     "products": [{"id": "102856298", "name": "Калифорния Классическая", "price": 540, "quantity": 1}],
     "value": 540,
     "coupon": null,
     "channel": "android"
   },
   "profile": {"id": "e9922810-0a85-43c1-8e78-be8343c1f8ed"},
   "session": {"id": "11111111-1111-1111-1111-111111111111"},
   "metadata": {"time": {"insert": "2026-06-07T10:05:00.092Z"}}}}'::JSONB,
 NOW() - INTERVAL '1 day'),

 -- Подтверждение заказа
('a1b2c3d4-0001-4000-8000-000000000007', 'page-view',
 'e9922810-0a85-43c1-8e78-be8343c1f8ed', '11111111-1111-1111-1111-111111111111',
 '{"event": {"id": "a1b2c3d4-0001-4000-8000-000000000007", "type": "page-view",
   "properties": {"is_authenticated": true},
   "context": {"page": {"url": "https://demo.vsem-edu-oblako.ru/order?id=23924582", "path": "/order", "title": "Заказ успешно оформлен"}},
   "profile": {"id": "e9922810-0a85-43c1-8e78-be8343c1f8ed"},
   "session": {"id": "11111111-1111-1111-1111-111111111111"},
   "metadata": {"time": {"insert": "2026-06-07T10:05:00.360Z"}}}}'::JSONB,
 NOW() - INTERVAL '1 day'),

 -- Отзыв (положительный)
('a1b2c3d4-0001-4000-8000-000000000008', 'rating',
 'e9922810-0a85-43c1-8e78-be8343c1f8ed', '11111111-1111-1111-1111-111111111111',
 '{"event": {"id": "a1b2c3d4-0001-4000-8000-000000000008", "type": "rating",
   "properties": {"id": "23924582", "review": "Отлично", "rate": 5},
   "context": {"page": {"url": "https://demo.vsem-edu-oblako.ru/", "path": "/"}},
   "profile": {"id": "e9922810-0a85-43c1-8e78-be8343c1f8ed"},
   "session": {"id": "11111111-1111-1111-1111-111111111111"},
   "metadata": {"time": {"insert": "2026-06-08T10:00:00Z"}}}}'::JSONB,
 NOW() - INTERVAL '0 days');

 -- ======== 2. Неактивный клиент (давно не заказывал - риск оттока - 95 дней назад) ===========
INSERT INTO raw_events (event_id, event_type, profile_id, session_id, event_data, inserted_at) VALUES
('b2c3d4e5-0002-4000-8000-000000000001', 'page-view',
 '8a2edca4-5129-412a-8395-7a7a54b4f1a8', '22222222-2222-2222-2222-222222222222',
 '{"event": {"id": "b2c3d4e5-0002-4000-8000-000000000001", "type": "page-view",
   "properties": {"is_authenticated": true},
   "context": {"page": {"url": "https://demo.vsem-edu-oblako.ru/", "path": "/", "title": "Главная"}},
   "profile": {"id": "8a2edca4-5129-412a-8395-7a7a54b4f1a8"},
   "session": {"id": "22222222-2222-2222-2222-222222222222"},
   "metadata": {"time": {"insert": "2026-03-05T10:00:00Z"}}}}'::JSONB,
 NOW() - INTERVAL '95 days'),

 ('b2c3d4e5-0002-4000-8000-000000000002', 'checkout-started',
 '8a2edca4-5129-412a-8395-7a7a54b4f1a8', '22222222-2222-2222-2222-222222222222',
 '{"event": {"id": "b2c3d4e5-0002-4000-8000-000000000002", "type": "checkout-started",
   "properties": {"id": "23123001", "order_type": "delivery", "value": 1500, "coupon": null, "channel": "desktop"},
   "profile": {"id": "8a2edca4-5129-412a-8395-7a7a54b4f1a8"},
   "session": {"id": "22222222-2222-2222-2222-222222222222"},
   "metadata": {"time": {"insert": "2026-03-05T10:05:00Z"}}}}'::JSONB,
 NOW() - INTERVAL '95 days'),

 -- Подтверждение заказа
 ('b2c3d4e5-0002-4000-8000-000000000003', 'page-view',
 '8a2edca4-5129-412a-8395-7a7a54b4f1a8', '22222222-2222-2222-2222-222222222222',
 '{"event": {"id": "b2c3d4e5-0002-4000-8000-000000000003", "type": "page-view",
   "properties": {"is_authenticated": true},
   "context": {"page": {"url": "https://demo.vsem-edu-oblako.ru/order?id=23123001", "path": "/order", "title": "Заказ успешно оформлен"}},
   "profile": {"id": "8a2edca4-5129-412a-8395-7a7a54b4f1a8"},
   "session": {"id": "22222222-2222-2222-2222-222222222222"},
   "metadata": {"time": {"insert": "2026-03-05T10:05:30Z"}}}}'::JSONB,
 NOW() - INTERVAL '95 days');

 