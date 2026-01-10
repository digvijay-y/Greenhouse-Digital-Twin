# Project Digital Twin - Final Year Overhaul Plan
# Focus: Transform the into a "decision support system."

## PHASE 1: Implement the "What-If" Simulation (The Fortune Teller)
This is the core feature. It moves the project from passive monitoring to active prediction.

- [ ] **UI Changes:**
    - [ ] Add input fields to your main interface for user-defined scenarios:
        - `Watering Amount (mL)`
        - `Watering Frequency (hours)`
        - `Ambient Temperature (°C)`
    - [ ] Add a button: "Simulate Future".

- [ ] **Backend Logic:**
    - [ ] Create a function that triggers when the "Simulate Future" button is pressed.
    - [ ] Inside this function, build a simple predictive model for soil moisture over the next 24-72 hours.
    - [ ] **Evaporation Model:** Moisture decreases over time. Use an exponential decay `Moisture * exp(-k * t)`. Make the decay constant `k` slightly dependent on the user's `Ambient Temperature` input to look smart.
    - [ ] **Watering Model:** Moisture increases instantly. At intervals defined by `Watering Frequency`, add a value derived from `Watering Amount`.

- [ ] **Visualization:**
    - [ ] On your main graph, plot the output of your simulation as a **dotted line**.
    - [ ] Keep plotting the live sensor data as a **solid line**.
    - [ ] Add a legend: "Live Data" vs. "Simulated Scenario".

## PHASE 2: Bolt on the Gen AI (The AI Agronomist)
This is the "wow" factor for your presentation. It's overkill, which makes it perfect.

- [ ] **UI Changes:**
    - [ ] Add a button: "Get AI Analysis".
    - [ ] Add a text box to display the AI's recommendation.

- [ ] **Backend Logic:**
    - [ ] Create a Python function `get_ai_recommendation()` that calls a Generative AI API (e.g., Gemini, OpenAI).
    - [ ] **CRITICAL: Prompt Engineering.** Construct a detailed prompt that gives the AI all context:
        - Tell it to act as an "expert agronomist".
        - Provide all **current** sensor readings (Moisture, Temp, N, P, K).
        - State the user's simulation parameters for context.
        - Ask a specific question: "Based on the current NPK levels, suggest a fertilizer if needed."
    - [ ] **API Call:** Use the `requests` library to send the prompt and get the response.
    - [ ] **Security:** Load your API key from an environment variable or a file ignored by git. DO NOT HARDCODE THE KEY.
    - [ ] Display the AI's text response in the UI text box.

## PHASE 3: Presentation Narrative
How you talk about it is as important as what it does.

- [ ] Frame the project not as a "greenhouse twin" but as a "small-scale, cyber-physical testbed for soil analysis."
- [ ] Emphasize the "What-If" feature as a "decision support tool."
- [ ] Present the Gen AI as an "AI-augmented advisory system."
- [ ] Remember to re-frame the MATLAB simulation as a "spatial interpolation model," not a perfect physics simulation.

## Get it on cloud!