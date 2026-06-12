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

-- ======== Персональные предложения, чтение отзывов, push, сообщения ===========
INSERT INTO raw_events (event_id, event_type, profile_id, session_id, event_data, inserted_at) VALUES
-- personal-view в /profile
('a1b2c3d4-0001-4000-8000-000000000009', 'personal-view',
 'e9922810-0a85-43c1-8e78-be8343c1f8ed', '11111111-1111-1111-1111-111111111111',
 '{"event": {"id": "a1b2c3d4-0001-4000-8000-000000000009", "type": "personal-view",
   "properties": {"id": "941ea088-4074-43a7-a7b9-d53b48d8ab4c"},
   "context": {"page": {"url": "https://demo.vsem-edu-oblako.ru/profile", "path": "/profile", "title": "Личный кабинет"}},
   "profile": {"id": "e9922810-0a85-43c1-8e78-be8343c1f8ed"},
   "session": {"id": "11111111-1111-1111-1111-111111111111"},
   "metadata": {"time": {"insert": "2026-06-07T10:06:00Z"}}}}'::JSONB,
 NOW() - INTERVAL '1 day'),

-- copy-promocode через 30 секунд
('a1b2c3d4-0001-4000-8000-000000000010', 'copy-promocode',
 'e9922810-0a85-43c1-8e78-be8343c1f8ed', '11111111-1111-1111-1111-111111111111',
 '{"event": {"id": "a1b2c3d4-0001-4000-8000-000000000010", "type": "copy-promocode",
   "properties": {"id": "941ea088-4074-43a7-a7b9-d53b48d8ab4c"},
   "context": {"page": {"url": "https://demo.vsem-edu-oblako.ru/profile", "path": "/profile", "title": "Личный кабинет"}},
   "profile": {"id": "e9922810-0a85-43c1-8e78-be8343c1f8ed"},
   "session": {"id": "11111111-1111-1111-1111-111111111111"},
   "metadata": {"time": {"insert": "2026-06-07T10:06:30Z"}}}}'::JSONB,
 NOW() - INTERVAL '1 day'),

-- page-view /reviews (читает отзывы)
('a1b2c3d4-0001-4000-8000-000000000011', 'page-view',
 'e9922810-0a85-43c1-8e78-be8343c1f8ed', '11111111-1111-1111-1111-111111111111',
 '{"event": {"id": "a1b2c3d4-0001-4000-8000-000000000011", "type": "page-view",
   "properties": {"is_authenticated": true},
   "context": {"page": {"url": "https://demo.vsem-edu-oblako.ru/reviews", "path": "/reviews", "title": "Отзывы"}},
   "profile": {"id": "e9922810-0a85-43c1-8e78-be8343c1f8ed"},
   "session": {"id": "11111111-1111-1111-1111-111111111111"},
   "metadata": {"time": {"insert": "2026-06-07T09:55:00Z"}}}}'::JSONB,
 NOW() - INTERVAL '1 day'),

-- profile-traits-update с push_id (push_channel_available = true)
('a1b2c3d4-0001-4000-8000-000000000012', 'profile-traits-update',
 'e9922810-0a85-43c1-8e78-be8343c1f8ed', '11111111-1111-1111-1111-111111111111',
 '{"event": {"id": "a1b2c3d4-0001-4000-8000-000000000012", "type": "profile-traits-update",
   "properties": {"push_id": "fcm_token_12345_abcde"},
   "profile": {"id": "e9922810-0a85-43c1-8e78-be8343c1f8ed"},
   "session": {"id": "11111111-1111-1111-1111-111111111111"},
   "metadata": {"time": {"insert": "2026-06-01T10:00:00Z"}}}}'::JSONB,
 NOW() - INTERVAL '7 days'),

-- message-status: delivered
('a1b2c3d4-0001-4000-8000-000000000013', 'message-status',
 'e9922810-0a85-43c1-8e78-be8343c1f8ed', '11111111-1111-1111-1111-111111111111',
 '{"event": {"id": "a1b2c3d4-0001-4000-8000-000000000013", "type": "message-status",
   "properties": {"conversation": "conv-001", "type": "push", "status": "delivered"},
   "profile": {"id": "e9922810-0a85-43c1-8e78-be8343c1f8ed"},
   "session": {"id": "11111111-1111-1111-1111-111111111111"},
   "metadata": {"time": {"insert": "2026-06-06T12:00:00Z"}}}}'::JSONB,
 NOW() - INTERVAL '2 days'),

-- message-opened (открыл сообщение)
('a1b2c3d4-0001-4000-8000-000000000014', 'message-opened',
 'e9922810-0a85-43c1-8e78-be8343c1f8ed', '11111111-1111-1111-1111-111111111111',
 '{"event": {"id": "a1b2c3d4-0001-4000-8000-000000000014", "type": "message-opened",
   "properties": {"id": "msg-001", "conversation": "conv-001"},
   "profile": {"id": "e9922810-0a85-43c1-8e78-be8343c1f8ed"},
   "session": {"id": "11111111-1111-1111-1111-111111111111"},
   "metadata": {"time": {"insert": "2026-06-06T12:05:00Z"}}}}'::JSONB,
 NOW() - INTERVAL '2 days');


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

 -- ======== Неактивный: push есть, но сообщения не открывает ===========
INSERT INTO raw_events (event_id, event_type, profile_id, session_id, event_data, inserted_at) VALUES
-- profile-traits-update с push_id (95 дней назад)
('b2c3d4e5-0002-4000-8000-000000000004', 'profile-traits-update',
 '8a2edca4-5129-412a-8395-7a7a54b4f1a8', '22222222-2222-2222-2222-222222222222',
 '{"event": {"id": "b2c3d4e5-0002-4000-8000-000000000004", "type": "profile-traits-update",
   "properties": {"push_id": "fcm_token_old_xyz"},
   "profile": {"id": "8a2edca4-5129-412a-8395-7a7a54b4f1a8"},
   "session": {"id": "22222222-2222-2222-2222-222222222222"},
   "metadata": {"time": {"insert": "2026-03-01T10:00:00Z"}}}}'::JSONB,
 NOW() - INTERVAL '99 days'),

-- message-status: delivered (95 дней назад)
('b2c3d4e5-0002-4000-8000-000000000005', 'message-status',
 '8a2edca4-5129-412a-8395-7a7a54b4f1a8', '22222222-2222-2222-2222-222222222222',
 '{"event": {"id": "b2c3d4e5-0002-4000-8000-000000000005", "type": "message-status",
   "properties": {"conversation": "conv-002", "type": "push", "status": "delivered"},
   "profile": {"id": "8a2edca4-5129-412a-8395-7a7a54b4f1a8"},
   "session": {"id": "22222222-2222-2222-2222-222222222222"},
   "metadata": {"time": {"insert": "2026-03-05T09:00:00Z"}}}}'::JSONB,
 NOW() - INTERVAL '95 days');


 -- ======== 3. Рисковый клиент (бросает корзины, негативные отзывы) ===========
INSERT INTO raw_events (event_id, event_type, profile_id, session_id, event_data, inserted_at) VALUES
-- Визит на главную
('c3d4e5f6-0003-4000-8000-000000000001', 'page-view',
 'd64347d4-8145-4161-8cb4-affc276ed890', '33333333-3333-3333-3333-333333333333',
 '{"event": {"id": "c3d4e5f6-0003-4000-8000-000000000001", "type": "page-view",
   "properties": {"is_authenticated": true},
   "context": {"page": {"url": "https://demo.vsem-edu-oblako.ru/", "path": "/", "title": "Главная"}},
   "profile": {"id": "d64347d4-8145-4161-8cb4-affc276ed890"},
   "session": {"id": "33333333-3333-3333-3333-333333333333"},
   "metadata": {"time": {"insert": "2026-05-21T15:00:00Z"}}}}'::JSONB,
 NOW() - INTERVAL '20 days'),

-- Просмотр товара
('c3d4e5f6-0003-4000-8000-000000000002', 'product-details-page-view',
 'd64347d4-8145-4161-8cb4-affc276ed890', '33333333-3333-3333-3333-333333333333',
 '{"event": {"id": "c3d4e5f6-0003-4000-8000-000000000002", "type": "product-details-page-view",
   "properties": {"id": "102856305", "name": "Комбо 3=1", "price": 449},
   "profile": {"id": "d64347d4-8145-4161-8cb4-affc276ed890"},
   "session": {"id": "33333333-3333-3333-3333-333333333333"},
   "metadata": {"time": {"insert": "2026-05-21T15:01:00Z"}}}}'::JSONB,
 NOW() - INTERVAL '20 days'),

-- Добавление в корзину
('c3d4e5f6-0003-4000-8000-000000000003', 'cart-changes',
 'd64347d4-8145-4161-8cb4-affc276ed890', '33333333-3333-3333-3333-333333333333',
 '{"event": {"id": "c3d4e5f6-0003-4000-8000-000000000003", "type": "cart-changes",
   "properties": {"products": [{"id": "102856305", "name": "Комбо 3=1", "price": 449, "quantity": 1}], "total": 449},
   "profile": {"id": "d64347d4-8145-4161-8cb4-affc276ed890"},
   "session": {"id": "33333333-3333-3333-3333-333333333333"},
   "metadata": {"time": {"insert": "2026-05-21T15:02:00Z"}}}}'::JSONB,
 NOW() - INTERVAL '20 days'),

-- Удаление из корзины на /checkout (серьёзный отказ)
('c3d4e5f6-0003-4000-8000-000000000004', 'cart-delete',
 'd64347d4-8145-4161-8cb4-affc276ed890', '33333333-3333-3333-3333-333333333333',
 '{"event": {"id": "c3d4e5f6-0003-4000-8000-000000000004", "type": "cart-delete",
   "properties": {},
   "context": {"page": {"url": "https://demo.vsem-edu-oblako.ru/checkout", "path": "/checkout", "title": "Оформление заказа"}},
   "profile": {"id": "d64347d4-8145-4161-8cb4-affc276ed890"},
   "session": {"id": "33333333-3333-3333-3333-333333333333"},
   "metadata": {"time": {"insert": "2026-05-21T15:05:00Z"}}}}'::JSONB,
 NOW() - INTERVAL '20 days'),

-- Негативный отзыв (2 звезды)
('c3d4e5f6-0003-4000-8000-000000000005', 'rating',
 'd64347d4-8145-4161-8cb4-affc276ed890', '33333333-3333-3333-3333-333333333333',
 '{"event": {"id": "c3d4e5f6-0003-4000-8000-000000000005", "type": "rating",
   "properties": {"id": "23924500", "review": "Плохо", "rate": 2},
   "context": {"page": {"url": "https://demo.vsem-edu-oblako.ru/", "path": "/", "title": "Главная"}},
   "profile": {"id": "d64347d4-8145-4161-8cb4-affc276ed890"},
   "session": {"id": "33333333-3333-3333-3333-333333333333"},
   "metadata": {"time": {"insert": "2026-05-22T10:00:00Z"}}}}'::JSONB,
 NOW() - INTERVAL '19 days');

 -- ======== Рисковый: Персональные предложения игнорирует, читает отзывы, обновляет профиль ===========
INSERT INTO raw_events (event_id, event_type, profile_id, session_id, event_data, inserted_at) VALUES
-- personal-view в /profile (НО НЕ копирует промокод)
('c3d4e5f6-0003-4000-8000-000000000006', 'personal-view',
 'd64347d4-8145-4161-8cb4-affc276ed890', '33333333-3333-3333-3333-333333333333',
 '{"event": {"id": "c3d4e5f6-0003-4000-8000-000000000006", "type": "personal-view",
   "properties": {"id": "777ea088-4074-43a7-a7b9-d53b48d8ab4d"},
   "context": {"page": {"url": "https://demo.vsem-edu-oblako.ru/profile", "path": "/profile", "title": "Личный кабинет"}},
   "profile": {"id": "d64347d4-8145-4161-8cb4-affc276ed890"},
   "session": {"id": "33333333-3333-3333-3333-333333333333"},
   "metadata": {"time": {"insert": "2026-05-21T15:03:00Z"}}}}'::JSONB,
 NOW() - INTERVAL '20 days'),

-- page-view /reviews (читает отзывы)
('c3d4e5f6-0003-4000-8000-000000000007', 'page-view',
 'd64347d4-8145-4161-8cb4-affc276ed890', '33333333-3333-3333-3333-333333333333',
 '{"event": {"id": "c3d4e5f6-0003-4000-8000-000000000007", "type": "page-view",
   "properties": {"is_authenticated": true},
   "context": {"page": {"url": "https://demo.vsem-edu-oblako.ru/reviews", "path": "/reviews", "title": "Отзывы"}},
   "profile": {"id": "d64347d4-8145-4161-8cb4-affc276ed890"},
   "session": {"id": "33333333-3333-3333-3333-333333333333"},
   "metadata": {"time": {"insert": "2026-05-21T14:50:00Z"}}}}'::JSONB,
 NOW() - INTERVAL '20 days'),

 -- profile-update с birthday
('c3d4e5f6-0003-4000-8000-000000000008', 'profile-update',
 'd64347d4-8145-4161-8cb4-affc276ed890', '33333333-3333-3333-3333-333333333333',
 '{"event": {"id": "c3d4e5f6-0003-4000-8000-000000000008", "type": "profile-update",
   "properties": {
     "pii": {"firstname": "Petr", "birthday": "1990-11-30T00:00:00.000Z"},
     "contact": {"phone": {"main": "79000000003"}}
   },
   "context": {"page": {"url": "https://demo.vsem-edu-oblako.ru/profile", "path": "/profile", "title": "Редактирование профиля"}},
   "profile": {"id": "d64347d4-8145-4161-8cb4-affc276ed890"},
   "session": {"id": "33333333-3333-3333-3333-333333333333"},
   "metadata": {"time": {"insert": "2026-05-20T10:00:00Z"}}}}'::JSONB,
 NOW() - INTERVAL '21 days'),

-- sign-in
('c3d4e5f6-0003-4000-8000-000000000009', 'sign-in',
 'd64347d4-8145-4161-8cb4-affc276ed890', '33333333-3333-3333-3333-333333333333',
 '{"event": {"id": "c3d4e5f6-0003-4000-8000-000000000009", "type": "sign-in",
   "properties": {"phone": {"main": "79000000003"}},
   "context": {"page": {"url": "https://demo.vsem-edu-oblako.ru/login", "path": "/login", "title": "Вход"}},
   "profile": {"id": "d64347d4-8145-4161-8cb4-affc276ed890"},
   "session": {"id": "33333333-3333-3333-3333-333333333333"},
   "metadata": {"time": {"insert": "2026-05-21T14:45:00Z"}}}}'::JSONB,
 NOW() - INTERVAL '20 days');


 -- ======== 4. Охотник за скидками (использует купоны) ===========
INSERT INTO raw_events (event_id, event_type, profile_id, session_id, event_data, inserted_at) VALUES
-- Просмотр страницы акций
('d4e5f6a7-0004-4000-8000-000000000001', 'page-view',
 '99e5b77f-a446-4704-ac87-6595c39d1953', '44444444-4444-4444-4444-444444444444',
 '{"event": {"id": "d4e5f6a7-0004-4000-8000-000000000001", "type": "page-view",
   "properties": {"is_authenticated": true},
   "context": {"page": {"url": "https://demo.vsem-edu-oblako.ru/actions", "path": "/actions", "title": "Акции"}},
   "profile": {"id": "99e5b77f-a446-4704-ac87-6595c39d1953"},
   "session": {"id": "44444444-4444-4444-4444-444444444444"},
   "metadata": {"time": {"insert": "2026-06-05T12:00:00Z"}}}}'::JSONB,
 NOW() - INTERVAL '5 days'),

-- Просмотр баннера акции
('d4e5f6a7-0004-4000-8000-000000000002', 'promotion-viewed',
 '99e5b77f-a446-4704-ac87-6595c39d1953', '44444444-4444-4444-4444-444444444444',
 '{"event": {"id": "d4e5f6a7-0004-4000-8000-000000000002", "type": "promotion-viewed",
   "properties": {"id": "4524adb6-84e3-4054-99b9-d28822bc6361", "name": "Вам подарок!", "type": "sale"},
   "profile": {"id": "99e5b77f-a446-4704-ac87-6595c39d1953"},
   "session": {"id": "44444444-4444-4444-4444-444444444444"},
   "metadata": {"time": {"insert": "2026-06-05T12:01:00Z"}}}}'::JSONB,
 NOW() - INTERVAL '5 days'),

-- Клик по баннеру
('d4e5f6a7-0004-4000-8000-000000000003', 'promotion-clicked',
 '99e5b77f-a446-4704-ac87-6595c39d1953', '44444444-4444-4444-4444-444444444444',
 '{"event": {"id": "d4e5f6a7-0004-4000-8000-000000000003", "type": "promotion-clicked",
   "properties": {"id": "4524adb6-84e3-4054-99b9-d28822bc6361", "url": {"page": "https://demo.vsem-edu-oblako.ru/catalog"}},
   "profile": {"id": "99e5b77f-a446-4704-ac87-6595c39d1953"},
   "session": {"id": "44444444-4444-4444-4444-444444444444"},
   "metadata": {"time": {"insert": "2026-06-05T12:01:30Z"}}}}'::JSONB,
 NOW() - INTERVAL '5 days'),

-- Добавление в корзину
('d4e5f6a7-0004-4000-8000-000000000004', 'cart-changes',
 '99e5b77f-a446-4704-ac87-6595c39d1953', '44444444-4444-4444-4444-444444444444',
 '{"event": {"id": "d4e5f6a7-0004-4000-8000-000000000004", "type": "cart-changes",
   "properties": {"products": [{"id": "102856298", "name": "Калифорния Классическая", "price": 540, "quantity": 2}], "total": 1080},
   "profile": {"id": "99e5b77f-a446-4704-ac87-6595c39d1953"},
   "session": {"id": "44444444-4444-4444-4444-444444444444"},
   "metadata": {"time": {"insert": "2026-06-05T12:03:00Z"}}}}'::JSONB,
 NOW() - INTERVAL '5 days'),

-- Заказ с купоном
('d4e5f6a7-0004-4000-8000-000000000005', 'checkout-started',
 '99e5b77f-a446-4704-ac87-6595c39d1953', '44444444-4444-4444-4444-444444444444',
 '{"event": {"id": "d4e5f6a7-0004-4000-8000-000000000005", "type": "checkout-started",
   "properties": {"id": "23924600", "order_type": "pickup", "value": 1800, "coupon": "SUMMER20", "channel": "android"},
   "profile": {"id": "99e5b77f-a446-4704-ac87-6595c39d1953"},
   "session": {"id": "44444444-4444-4444-4444-444444444444"},
   "metadata": {"time": {"insert": "2026-06-05T12:05:00Z"}}}}'::JSONB,
 NOW() - INTERVAL '5 days'),

-- Подтверждение заказа
('d4e5f6a7-0004-4000-8000-000000000006', 'page-view',
 '99e5b77f-a446-4704-ac87-6595c39d1953', '44444444-4444-4444-4444-444444444444',
 '{"event": {"id": "d4e5f6a7-0004-4000-8000-000000000006", "type": "page-view",
   "properties": {"is_authenticated": true},
   "context": {"page": {"url": "https://demo.vsem-edu-oblako.ru/order?id=23924600", "path": "/order", "title": "Заказ успешно оформлен"}},
   "profile": {"id": "99e5b77f-a446-4704-ac87-6595c39d1953"},
   "session": {"id": "44444444-4444-4444-4444-444444444444"},
   "metadata": {"time": {"insert": "2026-06-05T12:05:30Z"}}}}'::JSONB,
 NOW() - INTERVAL '5 days');

 -- ======== Охотник за скидками: Персональные предложения, закрытие акций, сообщения ===========
INSERT INTO raw_events (event_id, event_type, profile_id, session_id, event_data, inserted_at) VALUES
-- personal-view в /profile
('d4e5f6a7-0004-4000-8000-000000000007', 'personal-view',
 '99e5b77f-a446-4704-ac87-6595c39d1953', '44444444-4444-4444-4444-444444444444',
 '{"event": {"id": "d4e5f6a7-0004-4000-8000-000000000007", "type": "personal-view",
   "properties": {"id": "888ea088-4074-43a7-a7b9-d53b48d8ab4e"},
   "context": {"page": {"url": "https://demo.vsem-edu-oblako.ru/profile", "path": "/profile", "title": "Личный кабинет"}},
   "profile": {"id": "99e5b77f-a446-4704-ac87-6595c39d1953"},
   "session": {"id": "44444444-4444-4444-4444-444444444444"},
   "metadata": {"time": {"insert": "2026-06-05T11:55:00Z"}}}}'::JSONB,
 NOW() - INTERVAL '5 days'),

-- copy-promocode через 20 с
('d4e5f6a7-0004-4000-8000-000000000008', 'copy-promocode',
 '99e5b77f-a446-4704-ac87-6595c39d1953', '44444444-4444-4444-4444-444444444444',
 '{"event": {"id": "d4e5f6a7-0004-4000-8000-000000000008", "type": "copy-promocode",
   "properties": {"id": "888ea088-4074-43a7-a7b9-d53b48d8ab4e"},
   "context": {"page": {"url": "https://demo.vsem-edu-oblako.ru/profile", "path": "/profile", "title": "Личный кабинет"}},
   "profile": {"id": "99e5b77f-a446-4704-ac87-6595c39d1953"},
   "session": {"id": "44444444-4444-4444-4444-444444444444"},
   "metadata": {"time": {"insert": "2026-06-05T11:55:20Z"}}}}'::JSONB,
 NOW() - INTERVAL '5 days'),

 -- promotion-close (закрыл другую акцию без клика)
('d4e5f6a7-0004-4000-8000-000000000009', 'promotion-close',
 '99e5b77f-a446-4704-ac87-6595c39d1953', '44444444-4444-4444-4444-444444444444',
 '{"event": {"id": "d4e5f6a7-0004-4000-8000-000000000009", "type": "promotion-close",
   "properties": {"id": "5555adb6-84e3-4054-99b9-d28822bc6362", "name": "Скидка 10%"},
   "profile": {"id": "99e5b77f-a446-4704-ac87-6595c39d1953"},
   "session": {"id": "44444444-4444-4444-4444-444444444444"},
   "metadata": {"time": {"insert": "2026-06-05T11:50:00Z"}}}}'::JSONB,
 NOW() - INTERVAL '5 days'),

-- profile-traits-update с push_id
('d4e5f6a7-0004-4000-8000-000000000010', 'profile-traits-update',
 '99e5b77f-a446-4704-ac87-6595c39d1953', '44444444-4444-4444-4444-444444444444',
 '{"event": {"id": "d4e5f6a7-0004-4000-8000-000000000010", "type": "profile-traits-update",
   "properties": {"push_id": "fcm_token_anna_67890"},
   "profile": {"id": "99e5b77f-a446-4704-ac87-6595c39d1953"},
   "session": {"id": "44444444-4444-4444-4444-444444444444"},
   "metadata": {"time": {"insert": "2026-06-01T11:00:00Z"}}}}'::JSONB,
 NOW() - INTERVAL '7 days'),

 -- message-status: delivered
('d4e5f6a7-0004-4000-8000-000000000011', 'message-status',
 '99e5b77f-a446-4704-ac87-6595c39d1953', '44444444-4444-4444-4444-444444444444',
 '{"event": {"id": "d4e5f6a7-0004-4000-8000-000000000011", "type": "message-status",
   "properties": {"conversation": "conv-003", "type": "push", "status": "delivered"},
   "profile": {"id": "99e5b77f-a446-4704-ac87-6595c39d1953"},
   "session": {"id": "44444444-4444-4444-4444-444444444444"},
   "metadata": {"time": {"insert": "2026-06-04T15:00:00Z"}}}}'::JSONB,
 NOW() - INTERVAL '4 days'),

-- message-status: clicked (кликнул по сообщению)
('d4e5f6a7-0004-4000-8000-000000000012', 'message-status',
 '99e5b77f-a446-4704-ac87-6595c39d1953', '44444444-4444-4444-4444-444444444444',
 '{"event": {"id": "d4e5f6a7-0004-4000-8000-000000000012", "type": "message-status",
   "properties": {"conversation": "conv-003", "type": "push", "status": "clicked"},
   "profile": {"id": "99e5b77f-a446-4704-ac87-6595c39d1953"},
   "session": {"id": "44444444-4444-4444-4444-444444444444"},
   "metadata": {"time": {"insert": "2026-06-04T15:05:00Z"}}}}'::JSONB,
 NOW() - INTERVAL '4 days');


 -- ======== 5. Новый клиент (недавно зарегистрировался) ===========
INSERT INTO raw_events (event_id, event_type, profile_id, session_id, event_data, inserted_at) VALUES
-- Регистрация (identification)
('e5f6a7b8-0005-4000-8000-000000000001', 'identification',
 'f47ac10b-58cc-4372-a567-0e02b2c3d479', '55555555-5555-5555-5555-555555555555',
 '{"event": {"id": "e5f6a7b8-0005-4000-8000-000000000001", "type": "identification",
   "properties": {"phone": {"main": "79000000005"}, "firstname": "Olga"},
   "context": {"page": {"url": "https://demo.vsem-edu-oblako.ru/", "path": "/", "title": "Главная"}},
   "profile": {"id": "f47ac10b-58cc-4372-a567-0e02b2c3d479"},
   "session": {"id": "55555555-5555-5555-5555-555555555555"},
   "metadata": {"time": {"insert": "2026-05-31T14:00:00Z"}}}}'::JSONB,
 NOW() - INTERVAL '10 days'),

-- Просмотр каталога
('e5f6a7b8-0005-4000-8000-000000000002', 'page-view',
 'f47ac10b-58cc-4372-a567-0e02b2c3d479', '55555555-5555-5555-5555-555555555555',
 '{"event": {"id": "e5f6a7b8-0005-4000-8000-000000000002", "type": "page-view",
   "properties": {"is_authenticated": true},
   "context": {"page": {"url": "https://demo.vsem-edu-oblako.ru/catalog", "path": "/catalog", "title": "Каталог"}},
   "profile": {"id": "f47ac10b-58cc-4372-a567-0e02b2c3d479"},
   "session": {"id": "55555555-5555-5555-5555-555555555555"},
   "metadata": {"time": {"insert": "2026-05-31T14:05:00Z"}}}}'::JSONB,
 NOW() - INTERVAL '10 days'),

-- Первый заказ
('e5f6a7b8-0005-4000-8000-000000000003', 'checkout-started',
 'f47ac10b-58cc-4372-a567-0e02b2c3d479', '55555555-5555-5555-5555-555555555555',
 '{"event": {"id": "e5f6a7b8-0005-4000-8000-000000000003", "type": "checkout-started",
   "properties": {"id": "23924700", "order_type": "delivery", "value": 1200, "coupon": null, "channel": "desktop"},
   "profile": {"id": "f47ac10b-58cc-4372-a567-0e02b2c3d479"},
   "session": {"id": "55555555-5555-5555-5555-555555555555"},
   "metadata": {"time": {"insert": "2026-05-31T14:10:00Z"}}}}'::JSONB,
 NOW() - INTERVAL '10 days'),

-- Подтверждение заказа
('e5f6a7b8-0005-4000-8000-000000000004', 'page-view',
 'f47ac10b-58cc-4372-a567-0e02b2c3d479', '55555555-5555-5555-5555-555555555555',
 '{"event": {"id": "e5f6a7b8-0005-4000-8000-000000000004", "type": "page-view",
   "properties": {"is_authenticated": true},
   "context": {"page": {"url": "https://demo.vsem-edu-oblako.ru/order?id=23924700", "path": "/order", "title": "Заказ успешно оформлен"}},
   "profile": {"id": "f47ac10b-58cc-4372-a567-0e02b2c3d479"},
   "session": {"id": "55555555-5555-5555-5555-555555555555"},
   "metadata": {"time": {"insert": "2026-05-31T14:10:30Z"}}}}'::JSONB,
 NOW() - INTERVAL '10 days');

 -- ======== Новый: Читает отзывы, обновляет профиль ===========
INSERT INTO raw_events (event_id, event_type, profile_id, session_id, event_data, inserted_at) VALUES
-- page-view /reviews (читает отзывы перед первым заказом)
('e5f6a7b8-0005-4000-8000-000000000005', 'page-view',
 'f47ac10b-58cc-4372-a567-0e02b2c3d479', '55555555-5555-5555-5555-555555555555',
 '{"event": {"id": "e5f6a7b8-0005-4000-8000-000000000005", "type": "page-view",
   "properties": {"is_authenticated": true},
   "context": {"page": {"url": "https://demo.vsem-edu-oblako.ru/reviews", "path": "/reviews", "title": "Отзывы"}},
   "profile": {"id": "f47ac10b-58cc-4372-a567-0e02b2c3d479"},
   "session": {"id": "55555555-5555-5555-5555-555555555555"},
   "metadata": {"time": {"insert": "2026-05-31T14:07:00Z"}}}}'::JSONB,
 NOW() - INTERVAL '10 days'),

-- profile-update с birthday (заполненный профиль)
('e5f6a7b8-0005-4000-8000-000000000006', 'profile-update',
 'f47ac10b-58cc-4372-a567-0e02b2c3d479', '55555555-5555-5555-5555-555555555555',
 '{"event": {"id": "e5f6a7b8-0005-4000-8000-000000000006", "type": "profile-update",
   "properties": {
     "pii": {"firstname": "Olga", "birthday": "1995-09-25T00:00:00.000Z"},
     "contact": {"phone": {"main": "79000000005"}}
   },
   "context": {"page": {"url": "https://demo.vsem-edu-oblako.ru/profile", "path": "/profile", "title": "Редактирование профиля"}},
   "profile": {"id": "f47ac10b-58cc-4372-a567-0e02b2c3d479"},
   "session": {"id": "55555555-5555-5555-5555-555555555555"},
   "metadata": {"time": {"insert": "2026-05-31T13:50:00Z"}}}}'::JSONB,
 NOW() - INTERVAL '10 days'),

-- sign-in
('e5f6a7b8-0005-4000-8000-000000000007', 'sign-in',
 'f47ac10b-58cc-4372-a567-0e02b2c3d479', '55555555-5555-5555-5555-555555555555',
 '{"event": {"id": "e5f6a7b8-0005-4000-8000-000000000007", "type": "sign-in",
   "properties": {"phone": {"main": "79000000005"}},
   "context": {"page": {"url": "https://demo.vsem-edu-oblako.ru/login", "path": "/login", "title": "Вход"}},
   "profile": {"id": "f47ac10b-58cc-4372-a567-0e02b2c3d479"},
   "session": {"id": "55555555-5555-5555-5555-555555555555"},
   "metadata": {"time": {"insert": "2026-05-31T13:45:00Z"}}}}'::JSONB,
 NOW() - INTERVAL '10 days');