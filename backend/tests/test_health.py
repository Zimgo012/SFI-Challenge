import unittest

from fastapi.testclient import TestClient

from main import app


class HealthTests(unittest.TestCase):
    def test_health_endpoint(self):
        with TestClient(app) as client:
            response = client.get('/health')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})

    def test_openapi_exposes_health_response(self):
        with TestClient(app) as client:
            response = client.get('/openapi.json')

        self.assertEqual(response.status_code, 200)
        document = response.json()
        schema = document['paths']['/health']['get']['responses']['200'][
            'content'
        ]['application/json']['schema']
        self.assertEqual(schema['$ref'], '#/components/schemas/HealthResponse')
