project_root/
├── apps/
│   ├── core/
│   │   └── models.py           # TenantAwareModel (base model)
│   │
│   ├── menu/
│   │   ├── models.py           # Category, MenuItem
│   │   ├── admin.py            # Menu admin dengan stock display
│   │   ├── views.py            # menu_list, menu_items_json
│   │   └── templates/
│   │       └── menu/
│   │           └── menu_list.html
│   │
│   ├── orders/
│   │   ├── models.py           # Order, OrderItem, OrderTimeline, CustomerAnalytics, MenuOrderLog
│   │   ├── admin.py            # Order admin dengan stock actions
│   │   ├── views.py            # checkout_view, checkout_confirm, order_success
│   │   ├── signals.py          # Auto-populate MenuOrderLog
│   │   ├── analytics.py        # MenuAnalytics helper
│   │   ├── apps.py             # Signal registration
│   │   ├── utils.py            # generate_order_number
│   │   └── templates/
│   │       └── orders/
│   │           ├── checkout.html
│   │           └── order_success.html
│   │
│   └── customers/
│       └── models.py           # Customer model
│
├── config/                     # atau project_name/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
│
├── static/
├── media/
└── manage.py