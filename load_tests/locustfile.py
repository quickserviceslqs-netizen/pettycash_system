from locust import HttpUser, task, between
from random import randint

class PettyCashUser(HttpUser):
    wait_time = between(1, 3)

    @task(5)
    def view_dashboard(self):
        self.client.get('/dashboard/')

    @task(2)
    def submit_requisition(self):
        payload = {
            'transaction_id': f'LOC-{randint(1000,9999)}',
            'requested_by': 1,
            'origin_type': 'branch',
            'company': 1,
            'branch': 1,
            'amount': '100.00',
            'purpose': 'Stationery'
        }
        self.client.post('/api/requisitions/', json=payload)

    @task(1)
    def trigger_payment_check(self):
        self.client.get('/api/treasury/pending-payments/')

# Usage:
# pip install locust
# locust -f load_tests/locustfile.py --host=http://staging.example.com
