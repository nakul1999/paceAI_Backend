import json

from app.services.openai_service import client

from app.tools.weather import get_current_weather
from app.tools.strava import get_recent_activities
from app.tools.recommendation import recommend_training_today
from app.tools.acwr import calculate_acwr_from_activities
from app.rag.vector_store import get_or_create_vector_store


SYSTEM_PROMPT = """
You are PaceAI, an intelligent AI assistant for runners and endurance athletes.

You are knowledgeable, encouraging, scientifically grounded, and highly practical.

YOUR CAPABILITIES:

1. Real-Time Weather
   - Fetch current weather conditions.
   - Recommend clothing, pacing adjustments, and training suitability.

2. Strava Training History
   - Access the athlete's recent running activities.
   - Analyse mileage, pace, elevation, frequency, and consistency.

3. ACWR & Training Load Analysis
   - Calculate Acute:Chronic Workload Ratio directly from Strava history.
   - Assess fatigue, injury risk, recovery status, and workload progression.

4. Sports Science Knowledge Base
   - Use file_search to retrieve sports science guidance.
   - Use retrieved knowledge when answering training, recovery, injury, ACWR, or weather-adaptation questions.

5. Coach Decision Engine
   - Decide whether the athlete should train today.
   - Recommend intensity, duration, recovery, clothing, and pacing strategy.

IMPORTANT RULES:

- The backend already has the user's Strava access token.
- Never ask the user for their Strava access token.
- Default city is Dublin,IE unless the user says otherwise.
- If the user asks whether they should run, train, rest, recover, or what workout to do, use recommend_training_today.
- If the user asks about weather, use get_current_weather.
- If the user asks about recent runs, use get_recent_activities.
- If the user asks about ACWR, fatigue, recovery, injury risk, overtraining, or training load, use recommend_training_today or get_recent_activities and explain using retrieved sports science.
- Use file_search for sports science, injury prevention, ACWR interpretation, recovery, running zones, and weather adaptation.

STYLE:
- Be practical and specific.
- Give clear recommendations.
- Use athlete-specific data whenever available.
- Avoid vague generic advice.
"""


def build_tools(vector_store_id: str):
    return [
        {
            "type": "function",
            "name": "get_current_weather",
            "description": "Fetch current weather conditions for a city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name. Default is Dublin,IE."
                    },
                    "units": {
                        "type": "string",
                        "enum": ["metric", "imperial"],
                        "description": "Use metric by default."
                    },
                },
                "required": [],
                "additionalProperties": False,
            },
            "strict": False,
        },
        {
            "type": "function",
            "name": "get_recent_activities",
            "description": (
                "Fetch recent Strava running activities. "
                "The backend automatically injects the Strava access token."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "per_page": {
                        "type": "integer",
                        "description": "Number of recent activities to fetch.",
                        "default": 40,
                    }
                },
                "required": [],
                "additionalProperties": False,
            },
            "strict": False,
        },
        {
            "type": "function",
            "name": "recommend_training_today",
            "description": (
                "Recommend whether the athlete should run today, how hard to train, "
                "duration, intensity, clothing, and rationale using Strava, ACWR and weather."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City for weather analysis. Default is Dublin,IE.",
                        "default": "Dublin,IE",
                    },
                    "per_page": {
                        "type": "integer",
                        "description": "Number of recent Strava activities to analyze.",
                        "default": 40,
                    },
                },
                "required": [],
                "additionalProperties": False,
            },
            "strict": False,
        },
        {
            "type": "file_search",
            "vector_store_ids": [vector_store_id],
        },
    ]


def run_paceai_agent(
    user_message: str,
    access_token: str,
    conversation_history: list | None = None,
):
    if conversation_history is None:
        conversation_history = []

    vector_store_id = get_or_create_vector_store()
    tools = build_tools(vector_store_id)

    conversation_history.append({
        "role": "user",
        "content": user_message,
    })

    conversation_history = conversation_history[-10:]

    def dispatch_tool(tool_name: str, tool_args: dict) -> str:
        try:
            if tool_name == "get_current_weather":
                city = tool_args.get("city") or "Dublin,IE"
                units = tool_args.get("units") or "metric"
                result = get_current_weather(city=city, units=units)

            elif tool_name == "get_recent_activities":
                per_page = tool_args.get("per_page", 40)
                result = get_recent_activities(
                    access_token=access_token,
                    per_page=per_page,
                )

            elif tool_name == "recommend_training_today":
                city = tool_args.get("city") or "Dublin,IE"
                per_page = tool_args.get("per_page", 40)
                result = recommend_training_today(
                    access_token=access_token,
                    city=city,
                    per_page=per_page,
                )

            else:
                result = {"error": f"Unknown tool: {tool_name}"}

            return json.dumps(result, default=str)

        except Exception as e:
            return json.dumps({
                "error": f"{type(e).__name__}: {str(e)}"
            })

    max_iterations = 8

    for _ in range(max_iterations):
        response = client.responses.create(
            model="gpt-4o-mini",
            instructions=SYSTEM_PROMPT,
            input=conversation_history,
            tools=tools,
            tool_choice="auto",
            max_output_tokens=900,
        )

        for item in response.output:
            conversation_history.append(item)

        function_calls = [
            item for item in response.output
            if getattr(item, "type", None) == "function_call"
        ]

        if not function_calls:
            final_text = ""

            for item in response.output:
                if getattr(item, "type", None) == "message":
                    for block in item.content:
                        if getattr(block, "type", None) == "output_text":
                            final_text += block.text

            return {
                "response": final_text,
                "history": conversation_history[-10:],
            }

        for call in function_calls:
            tool_name = call.name

            try:
                tool_args = json.loads(call.arguments or "{}")
            except Exception:
                tool_args = {}

            result = dispatch_tool(tool_name, tool_args)

            # Compact heavy outputs before sending back to model
            try:
                parsed = json.loads(result)

                if isinstance(parsed, dict):
                    compact = {
                        k: v
                        for k, v in parsed.items()
                        if k not in [
                            "daily_data",
                            "weekly_loads",
                            "activities",
                            "weather",
                            "acwr",
                        ]
                    }

                    if "recommendation" in parsed:
                        compact = {
                            "recommendation": parsed.get("recommendation"),
                            "recommended_duration": parsed.get("recommended_duration"),
                            "recommended_intensity": parsed.get("recommended_intensity"),
                            "rationale": parsed.get("rationale"),
                            "clothing": parsed.get("clothing"),
                            "runs_used": parsed.get("runs_used"),
                            "acwr_status": parsed.get("acwr", {}).get("status"),
                            "current_acwr": parsed.get("acwr", {}).get("current_acwr"),
                            "weather_summary": {
                                "temperature_c": parsed.get("weather", {}).get("temperature_c"),
                                "wind_speed_kmh": parsed.get("weather", {}).get("wind_speed_kmh"),
                                "humidity_pct": parsed.get("weather", {}).get("humidity_pct"),
                                "description": parsed.get("weather", {}).get("description"),
                            },
                        }

                    output_payload = json.dumps(compact, default=str)

                else:
                    output_payload = result[:1500]

            except Exception:
                output_payload = result[:1500]

            conversation_history.append({
                "type": "function_call_output",
                "call_id": call.call_id,
                "output": output_payload,
            })

    return {
        "response": "I could not complete the request after multiple tool calls.",
        "history": conversation_history[-10:],
    }