# Orders Ingestion Sources

The automated USMC orders ingestion pipeline currently pulls from these public sources:

- https://www.marines.mil/News/Messages/
- https://www.marines.mil/News/Publications/
- https://www.marines.mil/
- https://www.esd.whs.mil/DD/

## What the pipeline does

1. Crawls source pages.
2. Finds candidate links for MCO/MCBUL/MARADMIN/ALMAR/NAVMC/directive/order/publication.
3. Downloads candidate documents (PDF or HTML).
4. Extracts text and metadata (title, order type, order number, issue date, topic tags).
5. Upserts documents into `order_document`.
6. Updates ingestion state in:
   - `app/data/orders/ingestion_state.json`

## Manual run

From project root:

```powershell
python app/scripts/orders_ingest_refresh.py
```

## Schedule daily (Windows Task Scheduler)

Program/script:

```text
C:\Users\rober\Desktop\mcpd-portal\.venv\Scripts\python.exe
```

Arguments:

```text
C:\Users\rober\Desktop\mcpd-portal\app\scripts\orders_ingest_refresh.py
```

Start in:

```text
C:\Users\rober\Desktop\mcpd-portal
```

Recommended frequency: every 24 hours.

