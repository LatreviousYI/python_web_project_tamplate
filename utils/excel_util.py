import csv
import datetime
from io import BytesIO, StringIO


def write_stream(datas, header=None):
    output = StringIO()
    writer = csv.writer(output)
    if header:
        writer.writerow(header)
    for idx, row in enumerate(datas):
        values = []
        for field in row:
            value = field
            if isinstance(field, datetime.datetime):
                value = field.strftime("%Y-%m-%d %H:%M:%S")
            elif isinstance(field, datetime.date):
                value = field.strftime("%Y-%m-%d")
            values.append(value)
        writer.writerow(values)
    output.seek(0)
    csv_data = output.getvalue().encode("utf-8-sig")
    csv_data = BytesIO(csv_data)
    return csv_data
