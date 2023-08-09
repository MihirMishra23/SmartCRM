from typing import Any, Optional, Literal, List
import pandas as pd


def search_drive(
    service,
    *,
    name: Optional[str] = None,
    parent: Optional[str] = None,
    file_type: Literal["sheet", "folder", None] = None,
) -> str:
    """
    Returns the file id of the first query

    :param name: The name of the requested file.
    :param parent: The name of the parent folder.
    :param file_type:
    """
    lst = []
    if name:
        lst.append(f"name = '{name}'")
    if parent:
        lst.append(f"parents in {search_drive(service, name=parent)}")
    if file_type:
        if file_type == "folder":
            lst.append(f"mimeType = 'application/vnd.google-apps.folder'")
        if file_type == "sheet":
            lst.append(f"mimeType = 'application/vnd.google-apps.spreadsheet'")
    query = " and ".join(lst)
    results = service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get("files", [])
    if not items:
        return ""
    return items[0]["id"]


def add_row(service, *, row_data: list, sheet_id: str, tab_name: str):
    """
    Adds a row to the given spreadsheet.

    :param row_data: The row data to append to the sheet
    :param sheet_id: The id of the spreadsheet to add to.
    :param tab_name: The name of the specific tab to add to.
    """
    value_input_option = "USER_ENTERED"
    insert_data_option = "INSERT_ROWS"
    value_range_body = {
        "values": [row_data],
        "majorDimension": "ROWS",
    }
    (
        service.spreadsheets()
        .values()
        .append(
            spreadsheetId=sheet_id,
            range=f"{tab_name}!A1",
            valueInputOption=value_input_option,
            insertDataOption=insert_data_option,
            body=value_range_body,
        )
    ).execute()


def update_cell(
    service, *, cell_value: Any, cell_loc: str, sheet_id: str, tab_name: str
):
    """
    Updates a cell of the given spreadsheet.

    :param cell_value: The new value replacing the old cell value.
    :param sheet_id: The id of the spreadsheet to add to.
    :param tab_name: The name of the specific tab to add to.
    """
    value_input_option = "USER_ENTERED"
    value_range_body = {
        "values": [[cell_value]],
        "majorDimension": "ROWS",
    }
    (
        service.spreadsheets()
        .values()
        .update(
            spreadsheetId=sheet_id,
            range=f"{tab_name}!{cell_loc}",
            valueInputOption=value_input_option,
            # insertDataOption=insert_data_option,
            body=value_range_body,
        )
    ).execute()


def read_sheet(
    service,
    sheet_id: str,
    *,
    range: str,
    axis: Literal["rows", "columns"] = "rows",
) -> pd.DataFrame:
    """
    Returns a 2D list of the sheet section as defined by the range.

    :param sheet_id: The id of the sheet to read.
    :param range: The range of the sheet to read. e.g. "Sheet1!A:B".
    :param axis: The organization of the data by rows or columns.
    """
    result = (
        service.spreadsheets()
        .values()
        .get(
            spreadsheetId=sheet_id,
            range=range,
            majorDimension=axis.upper(),
        )
        .execute()
    )
    values = result.get("values", [])
    max_len = max(len(row) for row in values)
    for row in values:
        row.extend([None] * (max_len - len(row)))
    df = pd.DataFrame(values[1:], columns=values[0])
    # df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
    df = df.replace(["", None], "", regex=True)
    return df
