import io
import logging
import os
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import boto3
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import requests
import seaborn as sns
from boto3.dynamodb.conditions import Key

matplotlib.use("Agg")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

USGS_API     = "https://earthquake.usgs.gov/fdsnws/event/1/query"
REGION       = "global"
TABLE_NAME   = os.environ["DYNAMODB_TABLE"]
S3_BUCKET    = os.environ["S3_BUCKET"]
AWS_REGION   = os.environ.get("AWS_REGION", "us-east-1")


# ---------------------------------------------------------------------------
# Step 1 — Fetch recent earthquakes from USGS API
# ---------------------------------------------------------------------------
def fetch_earthquakes() -> list[dict]:
    """Fetch M2.5+ earthquakes from the last 24 hours."""
    start = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S")
    resp = requests.get(USGS_API, timeout=30, params={
        "format":       "geojson",
        "starttime":    start,
        "minmagnitude": "2.5",
    })
    resp.raise_for_status()
    features = resp.json().get("features", [])
    log.info("USGS returned %d events (M2.5+ in last 24 h)", len(features))
    return features


# ---------------------------------------------------------------------------
# Step 2 — Query DynamoDB for already-stored event IDs
# ---------------------------------------------------------------------------
def get_existing_ids(table) -> set[str]:
    """Return the set of event_id values already stored for our region."""
    ids, kwargs = set(), dict(
        KeyConditionExpression=Key("region").eq(REGION),
        ProjectionExpression="event_id",
    )
    while True:
        resp = table.query(**kwargs)
        for item in resp.get("Items", []):
            ids.add(item["event_id"])
        if "LastEvaluatedKey" not in resp:
            break
        kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]
    return ids


# ---------------------------------------------------------------------------
# Step 3 — Classify earthquake significance
# ---------------------------------------------------------------------------
def classify(mag: float) -> str:
    if mag >= 6.0:
        return "MAJOR"
    if mag >= 4.0:
        return "MODERATE"
    return "MINOR"


# ---------------------------------------------------------------------------
# Step 4 — Store new events in DynamoDB
# ---------------------------------------------------------------------------
def store_new_events(table, features: list[dict], existing_ids: set[str]) -> int:
    """Write new earthquake events to DynamoDB. Returns count of new items."""
    new_count = 0
    with table.batch_writer() as batch:
        for f in features:
            eid = f["id"]
            if eid in existing_ids:
                continue
            props = f["properties"]
            coords = f["geometry"]["coordinates"]  # [lon, lat, depth]
            mag = props.get("mag") or 0.0
            batch.put_item(Item={
                "region":       REGION,
                "event_id":     eid,
                "timestamp":    datetime.fromtimestamp(
                    props["time"] / 1000, tz=timezone.utc
                ).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "magnitude":    Decimal(str(round(mag, 2))),
                "place":        props.get("place", "Unknown"),
                "latitude":     Decimal(str(round(coords[1], 6))),
                "longitude":    Decimal(str(round(coords[0], 6))),
                "depth_km":     Decimal(str(round(coords[2], 3))),
                "significance": classify(mag),
                "tsunami":      int(props.get("tsunami", 0)),
                "mag_type":     props.get("magType", "unknown"),
            })
            new_count += 1
    return new_count


# ---------------------------------------------------------------------------
# Step 5 — Fetch full history & generate plot
# ---------------------------------------------------------------------------
def fetch_history(table) -> pd.DataFrame:
    """Return all stored earthquake records as a DataFrame."""
    items, kwargs = [], dict(
        KeyConditionExpression=Key("region").eq(REGION),
        ScanIndexForward=True,
    )
    while True:
        resp = table.query(**kwargs)
        items.extend(resp.get("Items", []))
        if "LastEvaluatedKey" not in resp:
            break
        kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]

    if not items:
        return pd.DataFrame()

    df = pd.DataFrame(items)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["magnitude"] = df["magnitude"].astype(float)
    df["depth_km"]  = df["depth_km"].astype(float)
    return df.sort_values("timestamp").reset_index(drop=True)


def generate_plot(df: pd.DataFrame) -> io.BytesIO | None:
    """Scatter plot of magnitude vs. time, color-coded by significance."""
    if df.empty or len(df) < 2:
        log.info("Not enough history to plot yet (%d point(s))", len(df))
        return None

    sns.set_theme(style="darkgrid", context="talk", font_scale=0.9)

    palette = {"MINOR": "#4FC3F7", "MODERATE": "#FFA726", "MAJOR": "#EF5350"}
    fig, ax = plt.subplots(figsize=(14, 6))

    sns.scatterplot(
        data=df, x="timestamp", y="magnitude", hue="significance",
        palette=palette, hue_order=["MINOR", "MODERATE", "MAJOR"],
        s=80, alpha=0.75, edgecolor="white", linewidth=0.5, ax=ax, zorder=3,
    )

    # Annotate major events
    majors = df[df["significance"] == "MAJOR"]
    for _, row in majors.iterrows():
        label = row.get("place", "")
        if isinstance(label, str) and len(label) > 30:
            label = label[:27] + "..."
        ax.annotate(
            f"M{row['magnitude']:.1f} {label}",
            xy=(row["timestamp"], row["magnitude"]),
            xytext=(0, 12), textcoords="offset points",
            ha="center", fontsize=7, fontweight="bold", color="#B71C1C", zorder=5,
        )

    ax.set_title(
        "Global Earthquake Activity (M2.5+)\n"
        f"Last updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        fontsize=14, fontweight="bold", pad=14,
    )
    ax.set_xlabel("Time (UTC)", labelpad=8)
    ax.set_ylabel("Magnitude", labelpad=8)
    ax.set_ylim(2.0, max(df["magnitude"].max() + 0.5, 5.0))
    ax.legend(title="Significance", loc="upper left", fontsize=9, framealpha=0.85, edgecolor="#555555")

    sns.despine(ax=ax, top=True, right=True)
    fig.autofmt_xdate(rotation=25, ha="right")
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    buf.seek(0)
    plt.close(fig)
    log.info("Plot generated (%d bytes, %d points)", len(buf.getvalue()), len(df))
    return buf


# ---------------------------------------------------------------------------
# Step 6 — Upload plot to S3
# ---------------------------------------------------------------------------
def push_plot(buf: io.BytesIO) -> None:
    s3 = boto3.client("s3", region_name=AWS_REGION)
    s3.put_object(
        Bucket=S3_BUCKET,
        Key="earthquake-activity.png",
        Body=buf.getvalue(),
        ContentType="image/png",
    )
    log.info("Uploaded earthquake-activity.png to s3://%s", S3_BUCKET)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    table    = dynamodb.Table(TABLE_NAME)

    features     = fetch_earthquakes()
    existing_ids = get_existing_ids(table)
    new_count    = store_new_events(table, features, existing_ids)

    log.info(
        "Stored %d new events (%d already existed, %d total from API)",
        new_count, len(existing_ids), len(features),
    )

    history  = fetch_history(table)
    plot_buf = generate_plot(history)
    if plot_buf:
        push_plot(plot_buf)


if __name__ == "__main__":
    main()
