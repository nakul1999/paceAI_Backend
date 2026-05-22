import pandas as pd
import numpy as np


def calculate_acwr_from_activities(
    activities: list
) -> dict:

    if not activities:
        return {
            "error": "No activities provided"
        }

    df = pd.DataFrame(activities)

    df["date"] = pd.to_datetime(
        df["date"]
    ).dt.date

    df["date"] = pd.to_datetime(
        df["date"]
    )

    df = df.sort_values("date")

    df["load"] = pd.to_numeric(
        df["distance_km"],
        errors="coerce"
    ).fillna(0)

    # Daily aggregation
    daily = (
        df.groupby("date")["load"]
        .sum()
        .reset_index()
    )

    # Fill missing days
    full_range = pd.date_range(
        daily["date"].min(),
        daily["date"].max()
    )

    daily = (
        daily.set_index("date")
        .reindex(full_range, fill_value=0)
        .reset_index()
    )

    daily.columns = ["date", "load"]

    # Rolling loads
    daily["acute_7d"] = (
        daily["load"]
        .rolling(7, min_periods=1)
        .sum()
    )

    daily["chronic_28d_avg"] = (
        daily["load"]
        .rolling(28, min_periods=7)
        .sum() / 4
    )

    daily["acwr"] = (
        daily["acute_7d"] /
        daily["chronic_28d_avg"]
    )

    daily["acwr"] = daily["acwr"].replace(
        [np.inf, -np.inf],
        np.nan
    )

    # Weekly summary
    daily["training_week"] = (
        (
            daily["date"] -
            daily["date"].min()
        ).dt.days // 7
    ) + 1

    weekly = (
        daily.groupby("training_week")["load"]
        .sum()
        .reset_index()
        .rename(columns={
            "training_week": "week_number",
            "load": "total_load"
        })
    )

    latest = daily.iloc[-1]

    current_acwr = (
        float(latest["acwr"])
        if pd.notna(latest["acwr"])
        else None
    )

    if current_acwr is None:
        status = "Insufficient Data"
    elif current_acwr < 0.8:
        status = "Low Load"
    elif current_acwr <= 1.3:
        status = "Optimal"
    elif current_acwr <= 1.5:
        status = "Elevated Risk"
    else:
        status = "High Risk"

    # Convert date column to string
    daily["date"] = (
        daily["date"]
        .dt.strftime("%Y-%m-%d")
    )

    # Replace NaN / inf for JSON compatibility
    daily = daily.replace(
        [np.inf, -np.inf],
        np.nan
    )

    weekly = weekly.replace(
        [np.inf, -np.inf],
        np.nan
    )

    return {
        "current_acwr": current_acwr,

        "acute_load_7d": float(
            latest["acute_7d"]
        ),

        "chronic_load_28d_avg": (
            float(latest["chronic_28d_avg"])
            if pd.notna(latest["chronic_28d_avg"])
            else None
        ),

        "status": status,

        "analysis_period": (
            f"{daily['date'].min()} "
            f"to "
            f"{daily['date'].max()}"
        ),

        "weekly_loads": (
            weekly
            .replace({np.nan: None})
            .to_dict("records")
        ),

        "daily_data": (
            daily
            .replace({np.nan: None})
            .to_dict("records")
        ),
    }