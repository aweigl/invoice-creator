import sys
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import HTTPException

from app.main import autocomplete_address_query
from app.services.geo_routing import (
    AddressLookupError,
    AddressNotFoundError,
    autocomplete_addresses,
    resolve_address_distance,
)


class GeoRoutingTest(unittest.TestCase):
    @patch("app.services.geo_routing._fetch_json")
    def test_autocomplete_addresses_returns_suggestions(self, fetch_json):
        fetch_json.return_value = [
            {
                "lat": "50.941278",
                "lon": "6.958281",
                "display_name": "Domkloster 4, 50667 Koeln, Deutschland",
            },
            {
                "lat": "50.939",
                "lon": "6.96",
                "display_name": "Komoedienstrasse 1, 50667 Koeln, Deutschland",
            },
        ]

        result = autocomplete_addresses("Domkl")

        self.assertEqual(result.query, "Domkl")
        self.assertEqual(len(result.suggestions), 2)
        self.assertEqual(
            result.suggestions[0].label,
            "Domkloster 4, 50667 Koeln, Deutschland",
        )
        self.assertEqual(
            result.suggestions[0].value,
            "Domkloster 4, 50667 Koeln, Deutschland",
        )
        self.assertAlmostEqual(result.suggestions[0].latitude, 50.941278)
        self.assertAlmostEqual(result.suggestions[0].longitude, 6.958281)

        autocomplete_call = fetch_json.call_args
        self.assertEqual(autocomplete_call.args[1], "/search")
        self.assertEqual(autocomplete_call.kwargs["headers"], {"Accept-Language": "de"})
        self.assertEqual(autocomplete_call.kwargs["params"]["q"], "Domkl")
        self.assertEqual(autocomplete_call.kwargs["params"]["format"], "jsonv2")
        self.assertEqual(autocomplete_call.kwargs["params"]["limit"], 5)
        self.assertEqual(autocomplete_call.kwargs["params"]["countrycodes"], "de")
        self.assertIn("viewbox", autocomplete_call.kwargs["params"])

    @patch("app.services.geo_routing._fetch_json")
    def test_autocomplete_addresses_returns_empty_list_when_no_matches(self, fetch_json):
        fetch_json.return_value = []

        result = autocomplete_addresses("Unbekannt")

        self.assertEqual(result.query, "Unbekannt")
        self.assertEqual(result.suggestions, [])

    def test_autocomplete_address_query_rejects_short_queries(self):
        with self.assertRaises(HTTPException) as context:
            autocomplete_address_query("  ab ")

        self.assertEqual(context.exception.status_code, 400)

    @patch("app.main.autocomplete_addresses")
    def test_autocomplete_address_query_surfaces_lookup_errors(self, autocomplete_mock):
        autocomplete_mock.side_effect = AddressLookupError("Dienst nicht erreichbar.")

        with self.assertRaises(HTTPException) as context:
            autocomplete_address_query("Domkloster")

        self.assertEqual(context.exception.status_code, 502)
        self.assertEqual(context.exception.detail, "Dienst nicht erreichbar.")

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
            "/route/v1/driving/6.859771251678467,51.0122184753418;6.958281,50.941278",
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
