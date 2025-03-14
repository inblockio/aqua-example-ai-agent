import json

from amadeus import Client
from smolagents import tool, OpenAIServerModel
from smolagents.agents import CodeAgent

import human_in_the_loop

# https://github.com/ben4mn/amadeus-mcp
# https://github.com/nirbar1985/ai-travel-agent
# https://github.com/krharsh17/ai-amadeus-travel-agent


@tool
def format_flights(offer: str) -> str:
    """
    Format the output of search_flights for human choice.
    Args:
        offer: A JSON string
    """
    offer = json.loads(offer)
    itinerary = offer["itineraries"][0]
    if len(itinerary["segments"]) == 0:
        raise Exception("No flights found")
    flights = (
        f"Duration: {itinerary['duration']} "
        f"Price: ${float(offer['price']['total']):.2f}\n"
    )
    for i, segment in enumerate(itinerary["segments"]):
        _from = segment["departure"]["iataCode"]
        _to = segment["arrival"]["iataCode"]
        flights += (
            f"{i}. Flight: {segment['carrierCode']} {segment['number']} "
            f"from {_from} to {_to}, departure {segment['departure']['at']} arrival {segment['arrival']['at']}\n"
        )
    return str(flights)


@tool
def book_flight(origin: str, destination: str, date: str) -> str:
    """
    Book a flight using the Amadeus API. The flight output is already in JSON string
    Args:
        origin: origin city, must be in IATA 3-character format
        destination: destination city, must be in IATA 3-character format
        date: the date in YYY-MM-DD format
    """
    try:
        print(f"Searching flights: {origin} to {destination} on {date}")
        response = amadeus.shopping.flight_offers_search.get(
            originLocationCode=origin,
            destinationLocationCode=destination,
            departureDate=date,
            adults=1,
            currencyCode="USD",
        )
        data = response.data[:1]
        message = "Which flight do you want?\n" + "\n\n".join(
            [
                f"Option {i} " + format_flights(json.dumps(offer))
                for i, offer in enumerate(data)
            ]
        )
        choice = human_in_the_loop.HumanInterventionTool()(
            scenario="multiple_choice",
            message_for_human=message,
            choices=list(range(len(data))),
        )
        return data[int(choice)]
    except Exception as e:
        print(f"Error searching flights: {e}")
        return f"Error searching flights: {e}"


if __name__ == "__main__":
    with open("./credentials_agent.json") as f:
        credentials = json.load(f)

    amadeus = Client(
        client_id=credentials["amadeus_key"],
        client_secret=credentials["amadeus_secret"],
        hostname="test",  # switch to "production" for real money
    )

    # model = HfApiModel(
    #     "Qwen/Qwen2.5-72B-Instruct",
    #     token=credentials["hf_token"],
    # )
    model = OpenAIServerModel(
        model_id="gpt-4o-mini",
        # model_id="o3-mini",
        api_base="https://api.openai.com/v1",
        api_key=credentials["openai_token"],
        temperature=0,
    )

    agent = CodeAgent(
        tools=[book_flight],
        model=model,
        # additional_authorized_imports=["json"],
        max_steps=7,
    )

    traveler = {
        "id": "1",
        "dateOfBirth": "1982-01-16",
        "name": {"firstName": "JORGE", "lastName": "GONZALES"},
        "gender": "MALE",
        "contact": {
            "emailAddress": "jorge.gonzales833@telefonica.es",
            "phones": [
                {
                    "deviceType": "MOBILE",
                    "countryCallingCode": "34",
                    "number": "480080076",
                }
            ],
        },
        "documents": [
            {
                "documentType": "PASSPORT",
                "birthPlace": "Madrid",
                "issuanceLocation": "Madrid",
                "issuanceDate": "2015-04-14",
                "number": "00000000",
                "expiryDate": "2025-04-14",
                "issuanceCountry": "ES",
                "validityCountry": "ES",
                "nationality": "ES",
                "holder": True,
            }
        ],
    }

    # query = "I'm looking for a flight from Berlin to San Francisco on April 30 2025. Let me choose the available flights. Output the flight data in JSON format"
    with open("./user_input.txt") as f:
        query = f.read()
    flight = agent.run(query)

    # Flight Offers Price to confirm the price of the chosen flight
    confirmation = amadeus.shopping.flight_offers.pricing.post(flight).data

    # Flight Create Orders to book the flight
    booked_flight = amadeus.booking.flight_orders.post(
        confirmation["flightOffers"][0], traveler
    ).data

    print(booked_flight)

    from smolagents.monitoring import AgentLogger, LogLevel
    from rich.console import Console

    logger = AgentLogger(level=LogLevel.INFO)
    with open("agent_log.txt", "wt") as report_file:
        logger.console = Console(file=report_file)
        agent.memory.replay(logger, detailed=True)
