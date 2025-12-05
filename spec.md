# Lunar Lander Simulator - Game Design Specification

## 1. Project Overview
**Title:** Python Lunar Lander Simulator
**Goal:** Pilot a lander from a starting point to one of three landing pads on variable terrain using physics-based thrust and rotation.
**Platform:** Python
**Visual Style:** 2D vector graphics (rectangles and lines).

---

## 2. Technical Stack
* **Language:** Python 3.x
* **Rendering:** Pygame (for screen animation performance).
* **Physics Engine:** Pymunk (preferred) or Box2D.
    * *Reasoning:* Required for realistic rigid body dynamics, collision detection, and calculating thrust vectors based on ship rotation.

---

## 3. Game Objects & Visuals

### A. The Lunar Lander
* **Structure:** Composite shape made of multiple joined rectangles (not a single block).
    * *Body:* Central rectangle.
    * *Legs/Footpads:* Small rectangles attached to the body.
* **Thrust Visuals:**
    * Animated graphic (particle effect or flickering triangle) appearing at the bottom of the lander when the main thruster is active.
* **Spawn Point:**
    * Top-left corner of the screen.
    * Initial Velocity: $0 \text{ m/s}$ (Horizontal and Vertical).

### B. Terrain Generation
* **Style:** Continuous 2D line drawing.
* **Features:** Procedurally generated mix of:
    * Mountainous peaks.
    * Deep valleys.
    * Flat areas.
* **Landing Pads:**
    * **Quantity:** 3 distinct pads.
    * **Visual:** Small filled rectangles overlaid on the terrain line.
    * **Difficulty/Scoring:**
        * *Easy Pad:* Close/Flat approach $\rightarrow$ Low Score.
        * *Medium Pad:* Moderate obstacles $\rightarrow$ Medium Score.
        * *Hard Pad:* Difficult approach (behind mountains/tight spots) $\rightarrow$ High Score.

---

## 4. Physics & Controls

### A. Control Scheme
* **Rotation (Left/Right Arrows):**
    * Applies torque to the lander body.
    * No horizontal side thrusters. Horizontal movement is achieved by tilting the ship and using the main thruster.
* **Main Thruster (Spacebar):**
    * Applies force in the direction of the ship's current vertical axis.
    * Consumes fuel while active.

### B. Landing Envelope (Safe Landing Criteria)
* **Horizontal Velocity ($v_x$):** Must be $\leq 3 \text{ m/s}$.
* **Vertical Velocity ($v_y$):** Must be within a realistic structural limit (e.g., $\leq 5 \text{ m/s}$).
* **Alignment:** The lander footpads must touch the pad surface roughly simultaneously (angle near $0^{\circ}$).

### C. Crash Mechanics
* **Trigger:** Exceeding velocity limits or landing on non-pad terrain.
* **Visual Effect:**
    * Lander breaks apart.
    * Individual composite rectangles become independent physics bodies.
    * Parts scatter using projectile motion based on an explosion force.

---

## 5. UI & HUD (Heads Up Display)

### A. Velocity Readout
* **Location:** Top center of screen.
* **Data:** Display current Horizontal and Vertical velocity in $\text{m/s}$.
* **Color Coding:**
    * **White:** Within safe landing envelope.
    * **Yellow:** Approaching dangerous velocity (Warning).
    * **Red:** Exceeding safe limits (Fatal).

### B. Fuel Gauge
* **Location:** Upper Right corner.
* **Style:** Vertical Bar.
* **Behavior:**
    * Decreases as Spacebar is held.
    * **Colors:**
        * *Green:* High Fuel.
        * *Orange:* Medium/Low Fuel.
        * *Red:* Critical Fuel.
    * **Fuel Out:** If fuel hits 0, thrusters disable, lander falls due to gravity.

---

## 6. Logic & Algorithms

### A. Fuel Calculation
* System must calculate a "Minimum Viable Fuel" amount at the start of the round.
* **Algorithm:**
    * Pathfind to the most difficult (highest scoring) pad.
    * Account for climbing over maximum terrain height + deceleration thrust + landing adjustments.
    * Add a buffer (e.g., 120% of calculated need) to ensure fairness.

### B. Game Loop
1.  **Generate Terrain** and place pads.
2.  **Spawn Lander** (Top Left, 0 velocity).
3.  **Physics Step** (Input $\rightarrow$ Forces $\rightarrow$ Pymunk Simulation).
4.  **Render** (Draw lines, lander, HUD).
5.  **Check State:**
    * *Landed Safe:* Show Score, Next Level.
    * *Crashed:* Explosion animation, Retry/Game Over.

---

## 7. Options Menu
* **Access:** Accessible before game start or via Pause.
* **Configurable Parameters:**
    * **Gravity:** Slider/Input to adjust gravitational acceleration (simulating Moon, Mars, Earth, etc.).