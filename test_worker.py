
# AFRIFLOW/backend/tests/test_worker.py :

import redis
import json
import uuid

# Connexion à Redis
r = redis.Redis(host='localhost', port=6379, db=0)

# Test 1: Nettoyage
task1 = {
    "id": str(uuid.uuid4()),
    "type": "cleanup_temp",
    "data": {"days_old": 7}
}
r.lpush('afriflow:tasks', json.dumps(task1))
print(f"✅ Tâche de nettoyage envoyée: {task1['id']}")

# Test 2: Notification (si vous avez SMTP activé)
task2 = {
    "id": str(uuid.uuid4()),
    "type": "notify_user",
    "data": {
        "user_id": 1,
        "notification_type": "test",
        "message": "Ceci est un test"
    }
}
r.lpush('afriflow:tasks', json.dumps(task2))
print(f"✅ Tâche de notification envoyée: {task2['id']}")

# Test 3: Export rapport
task3 = {
    "id": str(uuid.uuid4()),
    "type": "export_report",
    "data": {
        "business_id": 1,
        "type": "monthly",
        "format": "excel",
        "date_range": {
            "start": "2024-01-01",
            "end": "2024-12-31"
        }
    }
}
r.lpush('afriflow:tasks', json.dumps(task3))
print(f"✅ Tâche d'export envoyée: {task3['id']}")

print("\n👀 Regardez le terminal du worker pour voir les résultats!")