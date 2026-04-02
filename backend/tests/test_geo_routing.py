import sys
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.geo_routing import AddressLookupError, AddressNotFoundError, resolve_address_distance


class GeoRoutingTest(unittest.TestCase):
    @patch("app.services.geo_routing._fetch_json")
    def test_resolve_address_distance_returns_route_summary(self, fetch_json):
        fetch_json.side_effect = [
            [
                {
                    "lat": "50.941278",
                    "lon": "6.958281",
                    "display_name": "Domkloster 4, 50667 Koeln, Deutschland",
                }
            ],
            {
                "code": "Ok",
                "routes": [{"distance": 18654.8}],
            },
        ]

        result = resolve_address_distance("Domkloster 4, 50667 Koeln")

        self.assertEqual(result.resolved_address, "Domkloster 4, 50667 Koeln, Deutschland")
        self.assertAlmostEqual(result.route_distance_meters, 18654.8)
        self.assertAlmostEqual(result.route_distance_km, 18.65)
        self.assertTrue(result.should_apply_extended_km_surcharge)

        route_call = fetch_json.call_args_list[1]
        self.assertEqual(
            route_call.args[1],
            "/route/v1/driving/6.8560315,51.0114979;6.958281,50.941278",
        )
        self.assertEqual(route_call.kwargs["params"], {"overview": "false"})

    @patch("app.services.geo_routing._fetch_json")
    def test_resolve_address_distance_raises_when_address_not_found(self, fetch_json):
        fetch_json.return_value = []

        with self.assertRaises(AddressNotFoundError):
            resolve_address_distance("Unbekannte Adresse")

    @patch("app.services.geo_routing._fetch_json")
    def test_resolve_address_distance_raises_when_route_missing(self, fetch_json):
        fetch_json.side_effect = [
            [{"lat": "50.0", "lon": "6.0", "display_name": "Test"}],
            {"code": "NoRoute", "routes": []},
        ]

        with self.assertRaises(AddressLookupError):
            resolve_address_distance("Teststrasse 1")


if __name__ == "__main__":
    unittest.main()
