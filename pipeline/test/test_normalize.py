from src.normalize import normalize_element, category_for

CATEGORY_MAP = {
    "amenity": {"restaurant": "Dining", "bench": None},
    "shop": {"*": "Retail & Shopping", "bakery": "Grocery & Food"},
}
TAG_KEYS = ["amenity", "shop"]


def test_restaurant_maps_to_dining():
    el = {
        "type": "node",
        "id": 42,
        "lat": 43.0,
        "lon": -83.6,
        "tags": {"name": "Jilly's Pizza", "amenity": "restaurant"},
    }
    f = normalize_element(el, CATEGORY_MAP, TAG_KEYS)
    assert f["id"] == "osm:node/42"
    assert f["properties"]["category"] == "Dining"
    assert f["geometry"]["coordinates"] == [-83.6, 43.0]


def test_shop_wildcard_default():
    el = {"type": "node", "id": 1, "lat": 43, "lon": -83.6,
          "tags": {"name": "Staples", "shop": "stationery"}}
    assert normalize_element(el, CATEGORY_MAP, TAG_KEYS)["properties"]["category"] == "Retail & Shopping"


def test_shop_specific_overrides_wildcard():
    el = {"type": "node", "id": 2, "lat": 43, "lon": -83.6,
          "tags": {"name": "Crust", "shop": "bakery"}}
    assert normalize_element(el, CATEGORY_MAP, TAG_KEYS)["properties"]["category"] == "Grocery & Food"


def test_unnamed_dropped():
    el = {"type": "node", "id": 3, "lat": 43, "lon": -83.6, "tags": {"amenity": "restaurant"}}
    assert normalize_element(el, CATEGORY_MAP, TAG_KEYS) is None


def test_uncategorized_dropped():
    el = {"type": "node", "id": 4, "lat": 43, "lon": -83.6,
          "tags": {"name": "A Bench", "amenity": "waste_basket"}}
    assert normalize_element(el, CATEGORY_MAP, TAG_KEYS) is None


def test_address_assembly_and_way_center():
    el = {
        "type": "way",
        "id": 99,
        "center": {"lat": 43.0, "lon": -83.6},
        "tags": {
            "name": "Shop",
            "shop": "hardware",
            "addr:housenumber": "100",
            "addr:street": "Center Rd",
            "addr:postcode": "48519",
        },
    }
    f = normalize_element(el, CATEGORY_MAP, TAG_KEYS)
    assert f["id"] == "osm:way/99"
    assert f["properties"]["address"] == "100 Center Rd, Burton, MI 48519"
    assert f["geometry"]["coordinates"] == [-83.6, 43.0]


def test_category_for_precedence():
    # amenity checked before shop
    assert category_for(
        {"amenity": "restaurant", "shop": "bakery"}, CATEGORY_MAP, TAG_KEYS
    ) == "Dining"
