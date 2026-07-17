from io import BytesIO

import app as pin_app


MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def _authorized_client():
    pin_app.app.config.update(TESTING=True)
    client = pin_app.app.test_client()
    with client.session_transaction() as session:
        session["csrf_token"] = "test-token"
    return client


def test_import_rejects_workbook_over_size_limit():
    client = _authorized_client()

    response = client.post(
        "/api/import",
        data={"file": (BytesIO(b"x" * (MAX_UPLOAD_BYTES + 1)), "pins.xlsx")},
        headers={"X-CSRF-Token": "test-token"},
    )

    assert response.status_code == 413
    assert response.get_json() == {"ok": False, "error": "Workbook is too large."}


def test_import_does_not_return_parser_exception_details():
    client = _authorized_client()

    response = client.post(
        "/api/import",
        data={"file": (BytesIO(b"not an xlsx"), "pins.xlsx")},
        headers={"X-CSRF-Token": "test-token"},
    )

    assert response.status_code == 400
    assert response.get_json() == {"ok": False, "error": "Could not read that workbook."}
