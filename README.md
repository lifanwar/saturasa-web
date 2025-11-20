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


extract all file in terminal

find . -type f \( -name "*.py" -o -name "*.html" -o -name "*.js" -o -name "*.css" -o -name "*.txt" -o -name "*.md" -o -name "*.json" -o -name "*.yml" -o -name "*.yaml" \) \
! -path "*/__pycache__/*" \
! -path "*/migrations/*" \
! -path "*/staticfiles/*" \
! -path "*/static/*" \
! -path "*/node_modules/*" \
! -path "*/.git/*" \
! -path "*/venv/*" \
! -path "*/env/*" \
! -path "*/.venv/*" \
! -name "*.pyc" \
! -name "*.min.js" \
! -name "*.min.css" \
-exec sh -c 'echo "\n########## FILE: {} ##########\n" && cat {} && echo "\n########## END: {} ##########\n"' \; > full_project_export.txt && echo "✅ Done: full_project_export.txt"