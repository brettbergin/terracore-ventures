import pytest
from app.terracore.views import aggregate_financials, parse_prospect_data
from types import SimpleNamespace

def make_prospect(data):
    return SimpleNamespace(data=data)

def test_aggregate_financials_basic(app):
    with app.app_context():
        prospects = [
            make_prospect({'price': '100000', 'estimated_rent': '1000', 'beds': 2, 'baths': 1}),
            make_prospect({'price': '200000', 'estimated_rent': '2000', 'beds': 3, 'baths': 2}),
        ]
        result = aggregate_financials(prospects)
        assert result['count'] == 2
        assert abs(result['total_price'] - 300000) < 1
        assert abs(result['total_rent'] - 3000) < 1
        assert result['avg_price'] > 0
        assert result['avg_rent'] > 0
        assert result['avg_cap_rate'] > 0
        assert result['partner_split'] != 0 